import time
import schedule
from datetime import datetime
from b import main as rss_generator
from logger_config import setup_logger
from rich.console import Console
from rich.panel import Panel

# Initialize logger and console
logger = setup_logger('rss_worker')
console = Console()

def job():
    """Run the RSS generator job"""
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        console.print(Panel.fit(
            f"[bold blue]RSS Feed Generator Worker[/bold blue]\n"
            f"[cyan]Starting job at: {current_time}[/cyan]"
        ))
        
        # Run the RSS generator
        rss_generator()
        
        console.print("[bold green]✓ Job completed successfully![/bold green]\n")
        
    except Exception as e:
        logger.error(f"Error in worker job: {str(e)}", exc_info=True)
        console.print(f"[bold red]✗ Job failed: {str(e)}[/bold red]\n")

def main():
    """Main worker function"""
    console.print(Panel.fit(
        "[bold blue]RSS Feed Generator Worker[/bold blue]\n"
        "[cyan]Worker started. Will run every minute.[/cyan]"
    ))
    
    # Schedule the job to run every minute
    schedule.every(1).minutes.do(job)
    
    # Run the job immediately on startup
    job()
    
    # Keep the script running
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]Worker stopped by user[/yellow]")
            break
        except Exception as e:
            logger.error(f"Error in main worker loop: {str(e)}", exc_info=True)
            console.print(f"[bold red]Worker error: {str(e)}[/bold red]")
            time.sleep(60)  # Wait a minute before retrying

if __name__ == "__main__":
    main() 