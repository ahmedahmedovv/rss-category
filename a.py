import feedparser
import json
import os
from deep_translator import GoogleTranslator
from datetime import datetime
import time
from bs4 import BeautifulSoup
from mistralai import Mistral
from mistralai.models import UserMessage
import asyncio
from dotenv import load_dotenv
import yaml

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

def create_data_folder():
    """Create a data folder if it doesn't exist"""
    if not os.path.exists(CONFIG['data_folder']):
        os.makedirs(CONFIG['data_folder'])

def clean_html(html_text):
    """Remove HTML tags and clean the text"""
    if html_text:
        soup = BeautifulSoup(html_text, 'html.parser')
        return soup.get_text(separator=' ', strip=True)
    return ''

def load_existing_articles(filename):
    """Load existing articles and return their URLs"""
    existing_urls = set()
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                articles = json.load(f)
                existing_urls = {article['link'] for article in articles}
        except json.JSONDecodeError:
            pass
    return existing_urls

def save_articles(articles, filename):
    """Save articles to JSON file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

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
    filename = os.path.join(CONFIG['data_folder'], CONFIG['articles_file'])
    
    existing_urls = load_existing_articles(filename)
    articles = []
    
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                articles = json.load(f)
        except json.JSONDecodeError:
            articles = []
    
    with open(url_file, 'r') as file:
        urls = [line.strip() for line in file if line.strip()]
    
    translator = GoogleTranslator(
        source=CONFIG['translator']['source'],
        target=CONFIG['translator']['target']
    )
    
    for url in urls:
        try:
            feed = feedparser.parse(url)
            
            if feed.entries:
                latest_entry = feed.entries[0]
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
                    'published': latest_entry.get('published', '')
                }
                
                articles.append(article)
                save_articles(articles, filename)
                
                print(f"Processed and saved: {url}")
                time.sleep(CONFIG['translator']['delay'])
            
        except Exception as e:
            print(f"Error processing {url}: {str(e)}")
    
    return filename

async def main():
    create_data_folder()
    filename = await fetch_and_translate_feeds(CONFIG['url_file'])
    print(f"Articles saved to {filename}")

if __name__ == "__main__":
    asyncio.run(main())
