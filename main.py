import asyncio
import subprocess
import time
from a import main as a_main
from b import main as b_main

async def main():
    try:
        # Run a.py's main function directly
        await a_main()
        
        time.sleep(2)
        
        # Run b.py's main function directly
        b_main()
        
        print("All operations completed successfully!")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
