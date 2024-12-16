import asyncio
import subprocess
import time
from a import main as a_main
from b import main as b_main
from logger_config import setup_logger

# Add at the top after imports
logger = setup_logger('main')

async def main():
    try:
        logger.info("Starting article processing...")
        await a_main()
        
        logger.info("Waiting 2 seconds before RSS generation...")
        time.sleep(2)
        
        logger.info("Starting RSS feed generation...")
        b_main()
        
        logger.info("All operations completed successfully!")
        
    except Exception as e:
        logger.error(f"An error occurred in main process: {str(e)}", exc_info=True)
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
