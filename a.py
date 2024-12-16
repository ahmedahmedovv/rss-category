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

def fetch_rss_feed(url):
    """Fetch RSS feed from a given URL."""
    try:
        feed = feedparser.parse(url)
        if feed.get('entries'):
            # Get only the first (most recent) entry
            latest_entry = feed.entries[0]
            return {
                'title': feed.feed.get('title', 'No Title'),
                'link': url,
                'latest_article': {
                    'title': latest_entry.get('title', ''),
                    'link': latest_entry.get('link', ''),
                    'published': latest_entry.get('published', ''),
                    'summary': latest_entry.get('summary', ''),
                    'description': latest_entry.get('description', '')  # Added description field
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
    
    # Read URLs from file
    urls = read_urls('url.md')
    
    # Initialize feeds list
    feeds = []
    
    # Fetch feeds and save continuously
    for url in urls:
        print(f"Fetching: {url}")
        feed_data = fetch_rss_feed(url)
        if feed_data:
            feeds.append(feed_data)
            # Save current progress to JSON file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(feeds, f, ensure_ascii=False, indent=2)
            print(f"Updated {output_file} with {len(feeds)} feeds")
        time.sleep(1)  # Be nice to servers
    
    print(f"Completed! Total {len(feeds)} feeds saved to {output_file}")

if __name__ == "__main__":
    main()
