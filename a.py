import feedparser
from deep_translator import GoogleTranslator
from datetime import datetime
import time
from bs4 import BeautifulSoup
import asyncio
from dotenv import load_dotenv
import yaml
import os
from supabase import create_client, Client
from typing import List, Dict, Any
from logger_config import setup_logger
from dateutil import parser
from dateutil.relativedelta import relativedelta
import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.panel import Panel
from rich import print as rprint

# Load environment variables
load_dotenv()

# Add at the top after imports
logger = setup_logger('article_processor')

# Initialize Rich console
console = Console()

def load_config():
    """Load configuration from yaml file"""
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    return config

CONFIG = load_config()

# Initialize Supabase client with environment variables
supabase: Client = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

def clean_html(html_text):
    """Remove HTML tags and clean the text"""
    if html_text:
        soup = BeautifulSoup(html_text, 'html.parser')
        return soup.get_text(separator=' ', strip=True)
    return ''

def load_existing_articles() -> set:
    """Load existing article URLs from Supabase"""
    try:
        response = supabase.table('articles').select('link').execute()
        return {article['link'] for article in response.data}
    except Exception as e:
        print(f"Error loading existing articles: {str(e)}")
        return set()

def save_article(article: Dict[str, Any]):
    """Save article to Supabase"""
    try:
        # Add created_at timestamp
        article['created_at'] = datetime.now().isoformat()
        
        response = supabase.table('articles').insert(article).execute()
        return response
    except Exception as e:
        print(f"Error saving article: {str(e)}")
        return None

def load_categories() -> set:
    """Load valid categories from categories_config.yaml"""
    try:
        with open(CONFIG['ollama']['categories_file'], 'r') as f:
            categories_config = yaml.safe_load(f)
            return set(categories_config['categories'])
    except Exception as e:
        logger.error(f"Error loading categories: {str(e)}")
        return set()

async def get_ai_analysis(content, max_retries=3):
    """Get AI-generated title, summary, and category using Ollama"""
    valid_categories = load_categories()
    
    for attempt in range(max_retries):
        try:
            # Prepare the request to local Ollama server
            url = "http://localhost:11434/api/generate"
            
            # Use the ollama section from config instead of together
            prompt = CONFIG['ollama']['prompt_template'].format(content=content)
            
            payload = {
                "model": CONFIG['ollama']['model'],
                "prompt": prompt,
                "stream": False
            }
            
            # Make request to Ollama
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            # Extract response text
            response_text = response.json()['response']
            
            # Parse the response
            title = ""
            summary = ""
            category = ""
            
            for line in response_text.split('\n'):
                if line.startswith('TITLE:'):
                    title = line.replace('TITLE:', '').strip()
                elif line.startswith('SUMMARY:'):
                    summary = line.replace('SUMMARY:', '').strip()
                elif line.startswith('CATEGORY:'):
                    category = line.replace('CATEGORY:', '').strip()
            
            # Validate category
            if category not in valid_categories:
                logger.warning(f"Invalid category '{category}' received from AI")
                if attempt < max_retries - 1:
                    logger.info("Retrying with the same content...")
                    continue
                else:
                    raise ValueError(f"AI provided invalid category after {max_retries} attempts: {category}")
            
            # Validate response
            if not all([title, summary, category]):
                if attempt < max_retries - 1:
                    logger.warning(f"Incomplete AI analysis, retrying... (attempt {attempt + 1})")
                    continue
                else:
                    logger.error("Failed to get complete AI analysis after all retries")
                    if not summary:
                        summary = "Summary not available"
            
            return title, summary, category
            
        except Exception as e:
            logger.error(f"Error in AI analysis (attempt {attempt + 1}): {str(e)}")
            if attempt == max_retries - 1:
                raise

async def fetch_and_translate_feeds(url_file):
    """Fetch articles from RSS feeds and translate them"""
    existing_urls = load_existing_articles()
    
    with open(url_file, 'r') as file:
        urls = [line.strip() for line in file if line.strip()]
    
    translator = GoogleTranslator(
        source=CONFIG['translator']['source'],
        target=CONFIG['translator']['target']
    )
    
    # Create progress display
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        
        # Main feed processing task
        feed_task = progress.add_task(f"[yellow]Processing feeds...", total=len(urls))
        
        for url in urls:
            try:
                console.print(f"\n[cyan]Processing feed:[/cyan] [green]{url}[/green]")
                feed = feedparser.parse(url)
                
                # Get the last entries
                latest_entries = feed.entries[:CONFIG['feed']['entries_to_fetch']]
                
                # Add subtask for current feed's entries
                entry_task = progress.add_task(
                    f"[blue]Processing articles from current feed...",
                    total=len(latest_entries)
                )
                
                for latest_entry in latest_entries:
                    article_url = latest_entry.get('link', '')
                    
                    if article_url in existing_urls:
                        progress.print(f"[yellow]↺ Skipping (already exists):[/yellow] {article_url}")
                        progress.advance(entry_task)
                        continue
                    
                    try:
                        # Extract and clean content
                        original_title = clean_html(latest_entry.get('title', ''))
                        original_description = clean_html(latest_entry.get('description', ''))
                        
                        progress.print("[bold green]Translating content...")
                        translated_title = translator.translate(original_title)
                        translated_description = translator.translate(original_description)
                        
                        # Combine title and description for AI analysis
                        combined_content = f"{translated_title}\n\n{translated_description}"
                        
                        # Get AI analysis
                        progress.print("[bold green]Getting AI analysis...")
                        ai_title, ai_summary, ai_category = await get_ai_analysis(combined_content)
                        
                        article = {
                            'original_title': translated_title,
                            'original_description': translated_description,
                            'ai_title': ai_title,
                            'ai_summary': ai_summary,
                            'ai_category': ai_category,
                            'link': article_url,
                            'published': latest_entry.get('published', ''),
                            'source_url': url
                        }
                        
                        # Save to Supabase
                        save_article(article)
                        progress.print(f"[green]✓ Processed:[/green] {ai_title}")
                        
                    except Exception as e:
                        progress.print(f"[red]✗ Error processing article:[/red] {str(e)}")
                        
                    progress.advance(entry_task)
                    time.sleep(CONFIG['translator']['delay'])
                
                progress.remove_task(entry_task)
                progress.advance(feed_task)
                
            except Exception as e:
                progress.print(f"[red]✗ Error processing feed {url}:[/red] {str(e)}")
                progress.advance(feed_task)

def delete_old_articles():
    """Delete articles older than one month"""
    with console.status("[bold yellow]Deleting old articles...") as status:
        try:
            one_month_ago = datetime.now() - relativedelta(months=1)
            
            response = supabase.table('articles')\
                .delete()\
                .lt('created_at', one_month_ago.isoformat())\
                .execute()
                
            deleted_count = len(response.data)
            console.print(f"[green]✓ Deleted {deleted_count} old articles[/green]")
            return deleted_count
        except Exception as e:
            console.print(f"[red]✗ Error deleting old articles: {str(e)}[/red]")
            return 0

async def main():
    console.print(Panel.fit(
        "[bold blue]RSS Feed Processor[/bold blue]\n"
        "[cyan]Starting article processing...[/cyan]"
    ))
    
    # Delete old articles before processing new ones
    delete_old_articles()
    
    await fetch_and_translate_feeds(CONFIG['url_file'])
    
    console.print("\n[bold green]✓ Article processing completed![/bold green]")

if __name__ == "__main__":
    asyncio.run(main())
