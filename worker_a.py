import asyncio
import time
from datetime import datetime
from a import main as article_processor
from logger_config import setup_logger
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Initialize logger and console
logger = setup_logger('article_worker')
console = Console()

async def job():
    """Run the article processor job"""
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        console.print(Panel.fit(
            f"[bold blue]Article Processor Worker[/bold blue]\n"
            f"[cyan]Starting job at: {current_time}[/cyan]"
        ))
        
        # Run the article processor
        await article_processor()
        
        console.print("[bold green]✓ Job cycle completed successfully![/bold green]\n")
        
    except Exception as e:
        logger.error(f"Error in worker job: {str(e)}", exc_info=True)
        console.print(f"[bold red]✗ Job cycle failed: {str(e)}[/bold red]\n")

async def main():
    """Main worker function"""
    console.print(Panel.fit(
        "[bold blue]Article Processor Worker[/bold blue]\n"
        "[cyan]Worker started. Will run continuously.[/cyan]"
    ))
    
    cycle_count = 0
    
    while True:
        try:
            cycle_count += 1
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]Status:"),
                console=console
            ) as progress:
                progress.add_task(f"[cyan]Starting cycle #{cycle_count}...")
                
                # Run the job
                await job()
                
                # Add a small delay between cycles
                progress.add_task("[yellow]Waiting 5 seconds before next cycle...")
                await asyncio.sleep(5)
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Worker stopped by user[/yellow]")
            break
        except Exception as e:
            logger.error(f"Error in main worker loop: {str(e)}", exc_info=True)
            console.print(f"[bold red]Worker error: {str(e)}[/bold red]")
            # Wait a minute before retrying on error
            console.print("[yellow]Waiting 60 seconds before retry...[/yellow]")
            await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Worker stopped by user[/yellow]") 