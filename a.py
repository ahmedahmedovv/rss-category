import feedparser
import json
import os
from datetime import datetime
import time
from pathlib import Path

def read_urls(file_path):
    """Read URLs from the markdown file."""
    with open(file_path, 'r') as file:
        # Remove empty lines and strip whitespace
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

def fetch_rss_feed(url, existing_link=None):
    """Fetch RSS feed from a given URL."""
    try:
        feed = feedparser.parse(url)
        if feed.get('entries'):
            # Get only the first (most recent) entry
            latest_entry = feed.entries[0]
            latest_link = latest_entry.get('link', '')
            
            # Skip if we already have this article
            if existing_link and latest_link == existing_link:
                print(f"Skip fetching {url}: already have latest article")
                return None
                
            return {
                'title': feed.feed.get('title', 'No Title'),
                'link': url,
                'latest_article': {
                    'title': latest_entry.get('title', ''),
                    'link': latest_link,
                    'published': latest_entry.get('published', ''),
                    'summary': latest_entry.get('summary', ''),
                    'description': latest_entry.get('description', '')
                }
            }
        return None
    except Exception as e:
        print(f"Error fetching {url}: {str(e)}")
        return None

def main():
    # Create data directory if it doesn't exist
    data_dir = Path('data')
    data_dir.mkdir(exist_ok=True)
    
    # Use fixed output file name
    output_file = data_dir / 'rss_feeds.json'
    
    # Load existing feeds
    existing_feeds = load_existing_feeds(output_file)
    
    # Read URLs from file
    urls = read_urls('url.md')
    
    # Initialize feeds list with existing feeds
    feeds = existing_feeds.copy()
    
    # Fetch feeds and save continuously
    for url in urls:
        print(f"Fetching: {url}")
        existing_link = get_existing_article_link(existing_feeds, url)
        feed_data = fetch_rss_feed(url, existing_link)
        
        if feed_data:
            # Remove old entry if it exists
            feeds = [f for f in feeds if f['link'] != url]
            # Add new entry
            feeds.append(feed_data)
            # Save current progress to JSON file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(feeds, f, ensure_ascii=False, indent=2)
            print(f"Updated {output_file} with {len(feeds)} feeds")
        time.sleep(1)  # Be nice to servers
    
    print(f"Completed! Total {len(feeds)} feeds saved to {output_file}")

if __name__ == "__main__":
    main()
