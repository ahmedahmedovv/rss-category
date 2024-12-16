import feedparser
import json
import os
from deep_translator import GoogleTranslator
from datetime import datetime
import time
from bs4 import BeautifulSoup

def create_data_folder():
    """Create a data folder if it doesn't exist"""
    if not os.path.exists('data'):
        os.makedirs('data')

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
            # If file is empty or invalid, start fresh
            pass
    return existing_urls

def save_articles(articles, filename):
    """Save articles to JSON file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

def fetch_and_translate_feeds(url_file):
    """Fetch articles from RSS feeds and translate them"""
    filename = 'data/articles.json'
    
    # Load existing articles
    existing_urls = load_existing_articles(filename)
    articles = []
    
    # If we have existing articles, load them
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                articles = json.load(f)
        except json.JSONDecodeError:
            articles = []
    
    # Read URLs from file
    with open(url_file, 'r') as file:
        urls = [line.strip() for line in file if line.strip()]
    
    for url in urls:
        try:
            # Parse the RSS feed
            feed = feedparser.parse(url)
            
            if feed.entries:
                # Get the latest entry
                latest_entry = feed.entries[0]
                article_url = latest_entry.get('link', '')
                
                # Skip if article already exists
                if article_url in existing_urls:
                    print(f"Skipping (already exists): {article_url}")
                    continue
                
                # Extract and clean content
                original_title = clean_html(latest_entry.get('title', ''))
                original_description = clean_html(latest_entry.get('description', ''))
                
                # Translate content to English
                translator = GoogleTranslator(source='auto', target='en')
                
                try:
                    translated_title = translator.translate(original_title)
                    translated_description = translator.translate(original_description)
                except Exception as e:
                    translated_title = f"Translation error: {str(e)}"
                    translated_description = f"Translation error: {str(e)}"
                
                # Create article with only required fields
                article = {
                    'title': translated_title,
                    'description': translated_description,
                    'link': article_url,
                    'published': latest_entry.get('published', '')
                }
                
                # Add to articles list
                articles.append(article)
                
                # Save all articles
                save_articles(articles, filename)
                
                print(f"Processed and saved: {url}")
                
                # Add delay to avoid hitting API limits
                time.sleep(1)
            
        except Exception as e:
            print(f"Error processing {url}: {str(e)}")
    
    return filename

def main():
    create_data_folder()
    filename = fetch_and_translate_feeds('url.md')
    print(f"Articles saved to {filename}")

if __name__ == "__main__":
    main()
