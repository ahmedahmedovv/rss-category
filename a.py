import feedparser
import json
import os
from datetime import datetime
import asyncio
import aiohttp
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from mistralai import Mistral
from mistralai.models import UserMessage
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def read_urls(file_path):
    """Read URLs from the markdown file."""
    with open(file_path, 'r') as file:
        return [line.strip() for line in file if line.strip()]

def load_existing_feeds(file_path):
    """Load existing feeds from JSON file if it exists."""
    try:
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading existing feeds: {str(e)}")
    return []

def get_existing_article_link(feeds, feed_url):
    """Get the latest article link for a feed if it exists."""
    for feed in feeds:
        if feed['link'] == feed_url:
            return feed['latest_article']['link']
    return None

def clean_html(html_content):
    """Remove HTML tags and clean the text."""
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, 'html.parser')
    # Get text and remove extra whitespace
    text = ' '.join(soup.get_text().split())
    return text

async def get_ai_enhancements(client, title, description):
    """Get AI-enhanced title, summary, and category."""
    prompt = f"""
    Based on this article:
    Title: {title}
    Content: {description}

    Please provide:
    1. A more engaging title (max 100 characters)
    2. A concise summary (max 200 characters)
    3. A single category that best describes this article (e.g., Politics, Economy, Technology, Society, etc.)

    Format your response exactly like this:
    Title: [your title]
    Summary: [your summary]
    Category: [your category]
    """

    try:
        response = await client.chat.complete_async(
            model="mistral-tiny",
            messages=[UserMessage(content=prompt)],
        )
        
        result = response.choices[0].message.content
        
        # Parse the response
        lines = result.split('\n')
        ai_title = lines[0].replace('Title: ', '').strip()
        ai_summary = lines[1].replace('Summary: ', '').strip()
        ai_category = lines[2].replace('Category: ', '').strip()
        
        return {
            'ai_title': ai_title,
            'ai_summary': ai_summary,
            'ai_category': ai_category
        }
    except Exception as e:
        print(f"Error getting AI enhancements: {str(e)}")
        return {
            'ai_title': title,
            'ai_summary': description[:200],
            'ai_category': 'Unknown'
        }

async def fetch_rss_feed(session, url, existing_link=None, mistral_client=None):
    """Fetch RSS feed from a given URL using aiohttp."""
    try:
        async with session.get(url, timeout=10) as response:
            # Try different encodings
            try:
                content = await response.text()
            except UnicodeDecodeError:
                content = await response.text(encoding='iso-8859-1')
            except:
                raw_content = await response.read()
                try:
                    content = raw_content.decode('utf-8', errors='ignore')
                except:
                    content = raw_content.decode('iso-8859-1', errors='ignore')
            
        with ThreadPoolExecutor() as executor:
            feed = await asyncio.get_event_loop().run_in_executor(
                executor, feedparser.parse, content
            )
            
        if feed.get('entries'):
            latest_entry = feed.entries[0]
            latest_link = latest_entry.get('link', '')
            
            if existing_link and latest_link == existing_link:
                print(f"Skip fetching {url}: already have latest article")
                return None
            
            title = clean_html(latest_entry.get('title', ''))
            description = clean_html(latest_entry.get('description', ''))
            
            # Get AI enhancements
            if mistral_client:
                ai_content = await get_ai_enhancements(mistral_client, title, description)
            else:
                ai_content = {
                    'ai_title': title,
                    'ai_summary': description[:200],
                    'ai_category': 'Unknown'
                }
                
            return {
                'title': feed.feed.get('title', 'No Title'),
                'link': url,
                'latest_article': {
                    'title': title,
                    'link': latest_link,
                    'published': latest_entry.get('published', ''),
                    'summary': clean_html(latest_entry.get('summary', '')),
                    'description': description,
                    'ai_title': ai_content['ai_title'],
                    'ai_summary': ai_content['ai_summary'],
                    'ai_category': ai_content['ai_category']
                }
            }
        return None
    except Exception as e:
        print(f"Error fetching {url}: {str(e)}")
        return None

async def process_feeds(urls, existing_feeds, output_file):
    """Process all feeds concurrently."""
    feeds = existing_feeds.copy()
    connector = aiohttp.TCPConnector(limit=10)
    
    # Initialize Mistral client using API key from .env
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        print("Warning: MISTRAL_API_KEY not found in .env file")
    mistral_client = Mistral(api_key=api_key) if api_key else None
    
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for url in urls:
            existing_link = get_existing_article_link(existing_feeds, url)
            tasks.append(fetch_rss_feed(session, url, existing_link, mistral_client))
        
        results = await asyncio.gather(*tasks)
        
        for url, feed_data in zip(urls, results):
            if feed_data:
                feeds = [f for f in feeds if f['link'] != url]
                feeds.append(feed_data)
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(feeds, f, ensure_ascii=False, indent=2)
                print(f"Updated {output_file} with {len(feeds)} feeds")
    
    return feeds

async def main():
    data_dir = Path('data')
    data_dir.mkdir(exist_ok=True)
    
    output_file = data_dir / 'rss_feeds.json'
    existing_feeds = load_existing_feeds(output_file)
    urls = read_urls('url.md')
    
    feeds = await process_feeds(urls, existing_feeds, output_file)
    print(f"Completed! Total {len(feeds)} feeds saved to {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
