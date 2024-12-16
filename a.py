import feedparser
import json
import os
from deep_translator import GoogleTranslator
from datetime import datetime
import time

def create_data_folder():
    """Create a data folder if it doesn't exist"""
    if not os.path.exists('data'):
        os.makedirs('data')

def get_json_filename():
    """Generate JSON filename with timestamp"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f'data/articles_{timestamp}.json'

def save_article(article, filename, is_first):
    """Save single article to JSON file"""
    mode = 'w' if is_first else 'a'
    with open(filename, 'a' if os.path.exists(filename) else 'w', encoding='utf-8') as f:
        if is_first:
            f.write('[\n')
        else:
            f.write(',\n')
        json.dump(article, f, ensure_ascii=False, indent=2)

def fetch_and_translate_feeds(url_file):
    """Fetch articles from RSS feeds and translate them"""
    # Read URLs from file
    with open(url_file, 'r') as file:
        urls = [line.strip() for line in file if line.strip()]
    
    filename = get_json_filename()
    is_first = True
    
    for url in urls:
        try:
            # Parse the RSS feed
            feed = feedparser.parse(url)
            
            if feed.entries:
                # Get the latest entry
                latest_entry = feed.entries[0]
                
                # Extract relevant information
                original_title = latest_entry.get('title', '')
                original_description = latest_entry.get('description', '')
                
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
                    'link': latest_entry.get('link', ''),
                    'published': latest_entry.get('published', '')
                }
                
                # Save article immediately
                save_article(article, filename, is_first)
                is_first = False
                
                # Add delay to avoid hitting API limits
                time.sleep(1)
                
            print(f"Processed and saved: {url}")
            
        except Exception as e:
            print(f"Error processing {url}: {str(e)}")
    
    # Close the JSON array
    with open(filename, 'a', encoding='utf-8') as f:
        f.write('\n]')
    
    return filename

def main():
    create_data_folder()
    filename = fetch_and_translate_feeds('url.md')
    print(f"Articles saved to {filename}")

if __name__ == "__main__":
    main()
