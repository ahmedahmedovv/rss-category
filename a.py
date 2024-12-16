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

# Load environment variables
load_dotenv()

def load_config():
    """Load configuration from yaml file"""
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
        # Replace environment variables
        config['mistral_api_key'] = os.getenv(config['mistral_api_key'].replace('${', '').replace('}', ''))
    return config

CONFIG = load_config()

# Initialize Supabase client with direct credentials
supabase: Client = create_client(
    'https://vyfeecfsnvjanhzaojvq.supabase.co',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ5ZmVlY2ZzbnZqYW5oemFvanZxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNDM0MDExNywiZXhwIjoyMDQ5OTE2MTE3fQ.cBjja9V92dT0-QYmNfIXEgCU00vE91ZXEetTyc-dmBM'
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

async def get_ai_analysis(content):
    """Get AI-generated title, summary, and category"""
    client = Mistral(api_key=CONFIG['mistral_api_key'])

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
    
    return title, summary, category

async def fetch_and_translate_feeds(url_file):
    """Fetch articles from RSS feeds and translate them"""
    existing_urls = load_existing_articles()
    
    with open(url_file, 'r') as file:
        urls = [line.strip() for line in file if line.strip()]
    
    translator = GoogleTranslator(
        source=CONFIG['translator']['source'],
        target=CONFIG['translator']['target']
    )
    
    for url in urls:
        try:
            feed = feedparser.parse(url)
            
            # Get the last 2 entries instead of just the first one
            latest_entries = feed.entries[:2]
            
            for latest_entry in latest_entries:
                article_url = latest_entry.get('link', '')
                
                if article_url in existing_urls:
                    print(f"Skipping (already exists): {article_url}")
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
                print(f"Processed and saved: {url}")
                time.sleep(CONFIG['translator']['delay'])
            
        except Exception as e:
            print(f"Error processing {url}: {str(e)}")

async def main():
    await fetch_and_translate_feeds(CONFIG['url_file'])
    print("Article processing completed!")

if __name__ == "__main__":
    asyncio.run(main())
