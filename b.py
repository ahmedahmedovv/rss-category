import json
import os
from feedgen.feed import FeedGenerator
from datetime import datetime
import pytz

def load_articles(filename):
    """Load articles from JSON file"""
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_category_feeds(articles):
    """Group articles by category and create RSS feeds"""
    # Create feeds directory if it doesn't exist
    if not os.path.exists('feeds'):
        os.makedirs('feeds')

    # Group articles by category
    category_articles = {}
    for article in articles:
        category = article.get('ai_category')
        if category:
            if category not in category_articles:
                category_articles[category] = []
            category_articles[category].append(article)

    # Create RSS feed for each category
    for category, articles in category_articles.items():
        fg = FeedGenerator()
        fg.title(f'News - {category}')
        fg.description(f'News articles related to {category}')
        fg.link(href=f'https://yourdomain.com/feeds/{category.lower()}.xml')
        fg.language('en')

        # Add entries to feed
        for article in articles:
            fe = fg.add_entry()
            fe.title(article.get('ai_title', 'No Title'))
            fe.description(article.get('ai_summary', 'No Summary'))
            fe.link(href=article.get('link', '#'))
            
            # Parse and set publication date
            try:
                pub_date = datetime.strptime(article.get('published', ''), 
                                           '%a, %d %b %Y %H:%M:%S %z')
            except ValueError:
                pub_date = datetime.now(pytz.UTC)
            fe.published(pub_date)

        # Save the feed
        filename = os.path.join('feeds', f'{category.lower().replace(" ", "_")}.xml')
        fg.rss_file(filename)
        print(f"Created RSS feed for {category}: {filename}")

def main():
    try:
        # Load articles from JSON file
        articles = load_articles('data/articles.json')
        
        # Create RSS feeds by category
        create_category_feeds(articles)
        
        print("RSS feeds generation completed successfully!")
        
    except Exception as e:
        print(f"Error generating RSS feeds: {str(e)}")

if __name__ == "__main__":
    main()