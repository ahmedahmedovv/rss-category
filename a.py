import yaml
import os
from pathlib import Path
import asyncio
import logging
from logging.handlers import RotatingFileHandler
import aiohttp
from datetime import datetime
from supabase import create_client
import feedparser
import backoff
from aiohttp import ClientError

def load_config():
    config_path = Path(__file__).parent / 'config.yaml'
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

# Load configuration
config = load_config()

# Setup logging configuration
def setup_logging():
    log_config = config['logging']
    
    if not os.path.exists(log_config['directory']):
        os.makedirs(log_config['directory'])

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    today = datetime.now().strftime('%Y-%m-%d')
    file_handler = RotatingFileHandler(
        f"{log_config['directory']}/rss_feed_{today}.log",
        maxBytes=log_config['max_size_mb']*1024*1024,
        backupCount=log_config['backup_count']
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_config['level']))
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

logger = setup_logging()

# Initialize Supabase client
supabase = create_client(
    config['database']['supabase_url'],
    config['database']['supabase_key']
)

async def check_link_exists(link):
    try:
        result = supabase.table('rss_entries').select('link').eq('link', link).execute()
        return len(result.data) > 0
    except Exception as e:
        logger.error(f"Error checking link existence: {str(e)}")
        return False

@backoff.on_exception(
    backoff.expo,
    (ClientError, asyncio.TimeoutError),
    max_tries=config['feed']['max_retries']
)
async def fetch_feed(session, url):
    try:
        timeout = aiohttp.ClientTimeout(
            total=config['feed']['timeout']['total'],
            connect=config['feed']['timeout']['connect'],
            sock_read=config['feed']['timeout']['read']
        )
        headers = {
            'User-Agent': config['http']['user_agent']
        }
        
        async with session.get(url, timeout=timeout, headers=headers, ssl=False) as response:
            if response.status != 200:
                logger.error(f"HTTP {response.status} error for {url}")
                return None

            raw_content = await response.read()
            
            content = None
            for encoding in config['http']['encodings']:
                try:
                    content = raw_content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                logger.error(f"Could not decode content from {url}")
                return None

            feed = feedparser.parse(content)
            
            if not feed.entries:
                logger.warning(f"No entries found in feed: {url}")
                return None

            latest_entry = feed.entries[0]
            
            # Ensure link exists and is valid
            if not latest_entry.get('link'):
                logger.error(f"No link found in entry from {url}")
                return None

            # Check if link already exists in database
            if await check_link_exists(latest_entry.get('link')):
                logger.debug(f"Skipping existing entry from {url}")
                return None
            
            # Create entry with all required fields
            entry = {
                'title': latest_entry.get('title', 'No title')[:500],  # Add length limit
                'link': latest_entry.get('link', '')[:1000],
                'published': latest_entry.get('published', 
                           latest_entry.get('updated', 'No date'))[:100],
                'description': latest_entry.get('description', 
                             latest_entry.get('summary', 'No description'))[:5000],
                'source_url': url[:1000],
                'created_at': datetime.now().isoformat()
            }
            
            # Validate entry
            if not all(key in entry for key in TABLE_STRUCTURE.keys()):
                logger.error(f"Invalid entry structure from {url}")
                return None
            
            logger.info(f"Successfully fetched entry from {url}: {entry['title']}")
            return entry

    except Exception as e:
        logger.error(f"Error fetching {url}: {str(e)}")
        return None

async def process_feeds(urls):
    logger.info(f"Starting to process {len(urls)} feeds")
    
    batch_size = config['feed']['batch_size']
    valid_results = []
    
    async with aiohttp.ClientSession() as session:
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i+batch_size]
            tasks = [fetch_feed(session, url) for url in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for url, result in zip(batch, results):
                if isinstance(result, Exception):
                    logger.error(f"Failed URL: {url}", exc_info=result)
                elif result:
                    valid_results.append(result)
            
            await asyncio.sleep(1)  # Small delay between batches

    return valid_results

async def save_to_supabase(entries):
    if not entries:
        return
    
    try:
        # Log the entries being saved
        logger.info(f"Attempting to save {len(entries)} entries")
        for entry in entries:
            logger.debug(f"Entry to save: {entry['title']} - {entry['link']}")
        
        # Split into smaller batches if needed
        batch_size = 10
        for i in range(0, len(entries), batch_size):
            batch = entries[i:i+batch_size]
            try:
                response = supabase.table('rss_entries').insert(batch).execute()
                logger.info(f"Successfully saved batch of {len(batch)} entries")
                logger.debug(f"Supabase response: {response}")
            except Exception as e:
                logger.error(f"Error saving batch to database: {str(e)}")
                # Log the problematic entries
                for entry in batch:
                    logger.error(f"Problem entry: {entry}")
                continue
                    
    except Exception as e:
        logger.error(f"Critical error in save_to_supabase: {str(e)}")
        return None

async def main():
    logger.info("Starting RSS feed processing")
    
    try:
        # Test database connection
        try:
            test = supabase.table('rss_entries').select('link').limit(1).execute()
            logger.info("Successfully connected to Supabase")
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {str(e)}")
            return

        with open('url.md', 'r') as file:
            urls = [line.strip() for line in file if line.strip()]
        
        logger.info(f"Found {len(urls)} URLs to process")
        
        entries = await process_feeds(urls)
        
        if entries:
            logger.info(f"Found {len(entries)} new entries to save")
            await save_to_supabase(entries)
        else:
            logger.warning("No new entries to save")
            
    except Exception as e:
        logger.error("Critical error in main process", exc_info=True)
    finally:
        logger.info("RSS feed processing completed")

# Make sure your table structure matches these fields
TABLE_STRUCTURE = {
    'title': 'text',
    'link': 'text',
    'published': 'text',
    'description': 'text',
    'source_url': 'text',
    'created_at': 'timestamp'
}

if __name__ == "__main__":
    asyncio.run(main())
