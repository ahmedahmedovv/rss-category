import feedparser
from deep_translator import GoogleTranslator
from datetime import datetime
import time
from bs4 import BeautifulSoup
from mistralai import Mistral
from mistralai.models import UserMessage
import asyncio
from dotenv import load_dotenv
import yaml
import os
from supabase import create_client, Client
from typing import List, Dict, Any
from logger_config import setup_logger
from dateutil import parser
from dateutil.relativedelta import relativedelta

# Load environment variables
load_dotenv()

# Add at the top after imports
logger = setup_logger('article_processor')

# Add this line after load_dotenv():
MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')

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

async def get_ai_analysis(content, max_retries=3):
    """Get AI-generated title, summary, and category with retry logic"""
    client = Mistral(api_key=MISTRAL_API_KEY)
    
    for attempt in range(max_retries):
        try:
            prompt = CONFIG['mistral']['prompt_template'].format(content=content)
            
            chat_response = await client.chat.complete_async(
                model=CONFIG['mistral']['model'],
                messages=[UserMessage(content=prompt)],
            )
            
            response_text = chat_response.choices[0].message.content
            
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
            
            # Validate that we have all required fields
            if not all([title, summary, category]):
                if attempt < max_retries - 1:
                    logger.warning(f"Incomplete AI analysis, retrying... (attempt {attempt + 1})")
                    continue
                else:
                    logger.error("Failed to get complete AI analysis after all retries")
                    # Provide default summary if still empty
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
    logger.info(f"Starting to process feeds from {url_file}")
    
    with open(url_file, 'r') as file:
        urls = [line.strip() for line in file if line.strip()]
    
    translator = GoogleTranslator(
        source=CONFIG['translator']['source'],
        target=CONFIG['translator']['target']
    )
    
    for url in urls:
        try:
            feed = feedparser.parse(url)
            logger.info(f"Processing feed: {url}")
            
            # Get the last 2 entries instead of just the first one
            latest_entries = feed.entries[:CONFIG['feed']['entries_to_fetch']]
            
            for latest_entry in latest_entries:
                article_url = latest_entry.get('link', '')
                
                if article_url in existing_urls:
                    logger.debug(f"Skipping (already exists): {article_url}")
                    continue
                
                # Extract and clean content
                original_title = clean_html(latest_entry.get('title', ''))
                original_description = clean_html(latest_entry.get('description', ''))
                
                try:
                    translated_title = translator.translate(original_title)
                    translated_description = translator.translate(original_description)
                    
                    # Combine title and description for AI analysis
                    combined_content = f"{translated_title}\n\n{translated_description}"
                    
                    # Get AI analysis
                    ai_title, ai_summary, ai_category = await get_ai_analysis(combined_content)
                    
                except Exception as e:
                    print(f"Translation/AI error: {str(e)}")
                    continue
                
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
                logger.info(f"Successfully processed and saved article: {article_url}")
                time.sleep(CONFIG['translator']['delay'])
            
        except Exception as e:
            logger.error(f"Error processing {url}: {str(e)}", exc_info=True)

def delete_old_articles():
    """Delete articles older than one month"""
    try:
        # Calculate the date one month ago
        one_month_ago = datetime.now() - relativedelta(months=1)
        
        # Delete articles older than one month
        response = supabase.table('articles')\
            .delete()\
            .lt('created_at', one_month_ago.isoformat())\
            .execute()
            
        deleted_count = len(response.data)
        logger.info(f"Deleted {deleted_count} articles older than one month")
        return deleted_count
    except Exception as e:
        logger.error(f"Error deleting old articles: {str(e)}")
        return 0

async def main():
    # Delete old articles before processing new ones
    delete_old_articles()
    
    await fetch_and_translate_feeds(CONFIG['url_file'])
    logger.info("Article processing completed!")

if __name__ == "__main__":
    asyncio.run(main())
