import feedparser
import time

def fetch_latest_entry(rss_url):
    try:
        # Add a small delay to avoid overwhelming servers
        time.sleep(1)
        
        # Parse the RSS feed
        feed = feedparser.parse(rss_url)
        
        # Check if feed has entries
        if len(feed.entries) > 0:
            latest_entry = feed.entries[0]  # Get the first (most recent) entry
            
            return {
                'title': latest_entry.get('title', 'No title'),
                'link': latest_entry.get('link', 'No link'),
                'published': latest_entry.get('published', 'No date')
            }
        return None
    
    except Exception as e:
        print(f"Error fetching {rss_url}: {str(e)}")
        return None

def main():
    # Read URLs from file
    with open('url.md', 'r') as file:
        urls = [line.strip() for line in file if line.strip()]
    
    print("Fetching latest entries from RSS feeds...")
    print("-" * 50)
    
    for url in urls:
        result = fetch_latest_entry(url)
        if result:
            print(f"\nSource: {url}")
            print(f"Title: {result['title']}")
            print(f"Link: {result['link']}")
            print(f"Published: {result['published']}")
            print("-" * 50)

if __name__ == "__main__":
    main()
