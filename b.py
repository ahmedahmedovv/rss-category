from supabase import create_client, Client
from feedgen.feed import FeedGenerator
from datetime import datetime
import pytz
import tempfile
import os

# Initialize Supabase client
supabase: Client = create_client(
    'https://vyfeecfsnvjanhzaojvq.supabase.co',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ5ZmVlY2ZzbnZqYW5oemFvanZxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNDM0MDExNywiZXhwIjoyMDQ5OTE2MTE3fQ.cBjja9V92dT0-QYmNfIXEgCU00vE91ZXEetTyc-dmBM'
)

def load_articles_from_supabase():
    """Load articles from Supabase database"""
    try:
        response = supabase.table('articles').select('*').execute()
        return response.data
    except Exception as e:
        print(f"Error loading articles from Supabase: {str(e)}")
        return []

def upload_to_supabase_storage(feed_content: str, filename: str):
    """Upload RSS feed content to Supabase storage"""
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.xml') as tmp_file:
            # Write content to temporary file
            tmp_file.write(feed_content)
            tmp_file.flush()
            tmp_path = tmp_file.name

        try:
            # Upload the temporary file to Supabase storage
            with open(tmp_path, 'rb') as f:
                response = supabase.storage.from_('rss-feeds').upload(
                    path=filename,
                    file=f,
                    file_options={"content-type": "application/xml"}
                )
            print(f"Successfully uploaded {filename} to Supabase storage")
            return response
        finally:
            # Clean up: remove temporary file
            os.unlink(tmp_path)
            
    except Exception as e:
        print(f"Error uploading to Supabase storage: {str(e)}")
        return None

def create_category_feeds(articles):
    """Group articles by category and create RSS feeds"""
    # Group articles by category
    category_articles = {}
    for article in articles:
        category = article.get('ai_category')
        if category:
            if category not in category_articles:
                category_articles[category] = []
            category_articles[category].append(article)

    # Create RSS feed for each category
    for category, category_articles in category_articles.items():
        fg = FeedGenerator()
        fg.title(f'News - {category}')
        fg.description(f'News articles related to {category}')
        fg.link(href=f'https://vyfeecfsnvjanhzaojvq.supabase.co/storage/v1/object/public/rss-feeds/{category.lower()}.xml')
        fg.language('en')

        # Add entries to feed
        for article in category_articles:
            fe = fg.add_entry()
            fe.title(article.get('ai_title', 'No Title'))
            fe.description(article.get('ai_summary', 'No Summary'))
            fe.link(href=article.get('link', '#'))
            
            # Parse and set publication date
            try:
                pub_date = datetime.strptime(article.get('published', ''), 
                                           '%a, %d %b %Y %H:%M:%S %z')
            except ValueError:
                try:
                    # Try parsing created_at if published date fails
                    pub_date = datetime.fromisoformat(article.get('created_at', '').replace('Z', '+00:00'))
                except ValueError:
                    pub_date = datetime.now(pytz.UTC)
            
            fe.published(pub_date)

        # Generate feed content as string
        feed_content = fg.rss_str(pretty=True).decode('utf-8')
        
        # Upload to Supabase storage
        filename = f'{category.lower().replace(" ", "_")}.xml'
        
        # Try to delete existing file first (ignore errors)
        try:
            supabase.storage.from_('rss-feeds').remove([filename])
        except:
            pass
        
        # Upload new file
        upload_to_supabase_storage(feed_content, filename)

def main():
    try:
        # Load articles from Supabase
        articles = load_articles_from_supabase()
        
        if not articles:
            print("No articles found in database")
            return
            
        # Create and upload RSS feeds by category
        create_category_feeds(articles)
        
        print("RSS feeds generation and upload completed successfully!")
        
    except Exception as e:
        print(f"Error generating RSS feeds: {str(e)}")

if __name__ == "__main__":
    main()