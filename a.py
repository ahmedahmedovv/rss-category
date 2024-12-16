import feedparser
import time
from supabase import create_client
import os
from datetime import datetime

# Supabase setup
SUPABASE_URL = "https://vyfeecfsnvjanhzaojvq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ5ZmVlY2ZzbnZqYW5oemFvanZxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNDM0MDExNywiZXhwIjoyMDQ5OTE2MTE3fQ.cBjja9V92dT0-QYmNfIXEgCU00vE91ZXEetTyc-dmBM"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_latest_entry(rss_url):
    try:
        time.sleep(1)
        feed = feedparser.parse(rss_url)
        
        if len(feed.entries) > 0:
            latest_entry = feed.entries[0]
            
            return {
                'title': latest_entry.get('title', 'No title'),
                'link': latest_entry.get('link', 'No link'),
                'published': latest_entry.get('published', 'No date'),
                'source_url': rss_url,
                'created_at': datetime.now().isoformat()
            }
        return None
    
    except Exception as e:
        print(f"Error fetching {rss_url}: {str(e)}")
        return None

def save_to_supabase(entry):
    try:
        # Insert the entry into your Supabase table
        data = supabase.table('rss_entries').insert(entry).execute()
        print(f"Successfully saved entry: {entry['title']}")
        return data
    except Exception as e:
        print(f"Error saving to Supabase: {str(e)}")
        return None

def main():
    with open('url.md', 'r') as file:
        urls = [line.strip() for line in file if line.strip()]
    
    print("Fetching latest entries from RSS feeds...")
    print("-" * 50)
    
    for url in urls:
        result = fetch_latest_entry(url)
        if result:
            # Save to Supabase
            save_to_supabase(result)
            
            # Print the results
            print(f"\nSource: {url}")
            print(f"Title: {result['title']}")
            print(f"Link: {result['link']}")
            print(f"Published: {result['published']}")
            print("-" * 50)

if __name__ == "__main__":
    main()
