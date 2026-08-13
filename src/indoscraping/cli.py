import argparse
import os
import sys
import subprocess
import time
from datetime import datetime
from typing import Dict, Any, List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

# Initialize console
console = Console()

# Unified list of scrapers
SCRAPERS: Dict[str, Dict[str, Any]] = {
    # News Category
    "detik": {
        "name": "Detik.com News Scraper",
        "category": "News",
        "lang": "Python",
        "cmd": ["python", "src/indoscraping/scraper/news/detik.py"],
        "desc": "Scrapes general & financial news articles from Detik Indeks.",
        "output_path": "data/news/detik/latest.json"
    },
    "bisnis": {
        "name": "Bisnis.com Scraper",
        "category": "News",
        "lang": "Python",
        "cmd": ["python", "src/indoscraping/scraper/news/bisnis.py"],
        "desc": "Extracts economics and business articles from Bisnis.com Index.",
        "output_path": "data/news/bisnis/latest.json"
    },
    "cnbc": {
        "name": "CNBC Indonesia Scraper",
        "category": "News",
        "lang": "Python",
        "cmd": ["python", "src/indoscraping/scraper/news/cnbc.py"],
        "desc": "Extracts news, timestamps, and tags from CNBC Indonesia.",
        "output_path": "data/news/cnbc/latest.json"
    },
    "cnn": {
        "name": "CNN Indonesia Scraper",
        "category": "News",
        "lang": "Python",
        "cmd": ["python", "src/indoscraping/scraper/news/cnn.py"],
        "desc": "Scrapes national and international news from CNN Indonesia.",
        "output_path": "data/news/cnn/latest.json"
    },
    "kompas": {
        "name": "Kompas.com Scraper",
        "category": "News",
        "lang": "Python",
        "cmd": ["python", "src/indoscraping/scraper/news/kompas.py"],
        "desc": "Extracts national and regional articles from Kompas Indeks.",
        "output_path": "data/news/kompas/latest.json"
    },
    "narasi": {
        "name": "Narasi.tv Scraper",
        "category": "News",
        "lang": "Python",
        "cmd": ["python", "src/indoscraping/scraper/news/narasi.py"],
        "desc": "Queries the Narasi API to fetch spotlight articles and tags using curl-cffi.",
        "output_path": "data/news/narasi/latest.json"
    },
    # E-Commerce Category
    "alfagift": {
        "name": "Alfagift Scraper",
        "category": "E-Commerce",
        "lang": "Python",
        "cmd": ["alfagift-scraper"],
        "desc": "Scrapes categories and products from the Alfamart Alfagift app.",
        "output_path": "data/ecommerce/alfagift/latest.json"
    },
    "indomaret": {
        "name": "Klik Indomaret Scraper",
        "category": "E-Commerce",
        "lang": "Python",
        "cmd": ["indomaret-scraper"],
        "desc": "Scrapes products and catalog details from KlikIndomaret.",
        "output_path": "data/ecommerce/indomaret/latest.json"
    },
    "blibli-search": {
        "name": "Blibli Search Scraper",
        "category": "E-Commerce",
        "lang": "Python (Playwright)",
        "cmd": ["blibli-scraper"],
        "desc": "Scrapes search results from Blibli using Playwright.",
        "output_path": "data/ecommerce/blibli/latest.json",
        "env": {"PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD": "1"}
    },
    "tokped": {
        "name": "Tokopedia Holistic Scraper",
        "category": "E-Commerce",
        "lang": "Python (Selenium)",
        "cmd": ["tokopedia-scraper"],
        "desc": "Scrapes Tokopedia category tree and product details using Undetected ChromeDriver.",
        "output_path": "data/ecommerce/tokopedia/latest.json"
    },
    # Finance Category
    "banks": {
        "name": "Digital Bank Rates Scraper",
        "category": "Finance",
        "lang": "Python (Playwright)",
        "cmd": ["python", "-m", "src.indoscraping.scraper.finance.rates"],
        "desc": "Scrapes interest rates of Jenius, Jago, SeaBank, blu, LineBank, Neo, Krom, Superbank.",
        "output_path": "data/latest.json",
        "env": {"PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD": "1"}
    }
}


def print_banner() -> None:
    banner_text = r"""
.___           .___                                   
|   | ____   __| _/____  ______ ___________ ___.__.   
|   |/    \ / __ |/  _ \/  ___//  ___/\_  __ <   |  |   
|   |   |  Y /_/ (  <_> )___ \ \___ \  |  | \/\___  |   
|___|___|  /\____ \____/____  >____  > |__|   / ____|   
         \/      \/         \/     \/         \/        
      Indonesian Web Scrapers Interactive Collection
"""
    console.print(Panel(Align.center(Text(banner_text, style="bold cyan")), border_style="cyan"))


def list_scrapers_table() -> Table:
    table = Table(title="Available Scrapers", border_style="cyan", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="bold yellow", width=15)
    table.add_column("Scraper Name", style="bold white", width=30)
    table.add_column("Category", style="bold green", width=12)
    table.add_column("Tech Stack", style="bold blue", width=20)
    table.add_column("Status / Output File", style="dim white")

    for sid, info in SCRAPERS.items():
        # Check if output file exists to show status
        out_path = info["output_path"]
        if os.path.exists(out_path):
            size = os.path.getsize(out_path)
            # Format size nicely
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size/1024:.1f} KB"
            else:
                size_str = f"{size/(1024*1024):.1f} MB"
            
            mtime = os.path.getmtime(out_path)
            mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
            status_text = f"[green]Ready[/green] ({size_str}, updated {mtime_str})"
        else:
            status_text = "[red]No crawl data[/red] (never run)"

        table.add_row(
            sid,
            info["name"],
            info["category"],
            info["lang"],
            status_text
        )
    return table


def run_scraper_subprocess(sid: str, extra_args: List[str] = None) -> bool:
    if sid not in SCRAPERS:
        console.print(f"[bold red]Error: Scraper '{sid}' not found![/bold red]")
        return False

    info = SCRAPERS[sid]
    cmd = list(info["cmd"])
    if cmd[0] == "python":
        cmd[0] = sys.executable

    if extra_args:
        cmd.extend(extra_args)

    console.print(Panel(
        f"[bold green]Starting Scraper:[/bold green] {info['name']}\n"
        f"[bold blue]Command:[/bold blue] {' '.join(cmd)}\n"
        f"[bold yellow]Description:[/bold yellow] {info['desc']}",
        border_style="green",
        title="Execution Details"
    ))

    # Prepare environment variables
    env = os.environ.copy()
    if "env" in info:
        for k, v in info["env"].items():
            env[k] = v

    start_time = time.time()

    # We use rich progress spinner for executions that might take time
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=20),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task_id = progress.add_task(description=f"Running {sid}...", total=None)

        try:
            # Run the process and capture logs
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                bufsize=1
            )

            # Stream output
            while True:
                line = process.stdout.readline() if process.stdout else None
                if not line and process.poll() is not None:
                    break
                if line:
                    clean_line = line.strip()
                    if clean_line:
                        # Periodically update progress label to reflect live status
                        progress.update(task_id, description=f"[{sid}] {clean_line[:50]}...")

            return_code = process.wait()
            progress.update(task_id, completed=100)

            elapsed = time.time() - start_time
            if return_code == 0:
                console.print(f"\n[bold green]✓ Scraper {sid} completed successfully in {elapsed:.2f}s![/bold green]")
                
                # Check output file details
                out_path = info["output_path"]
                if os.path.exists(out_path):
                    size = os.path.getsize(out_path)
                    console.print(f"[green]Data successfully written to: {out_path} ({size} bytes)[/green]")
                else:
                    console.print(f"[yellow]Expected output at {out_path} was not found, check script logs.[/yellow]")
                return True
            else:
                console.print(f"\n[bold red]✗ Scraper {sid} failed with return code {return_code} (Duration: {elapsed:.2f}s).[/bold red]")
                return False

        except Exception as e:
            console.print(f"[bold red]Exception during execution: {e}[/bold red]")
            return False


def view_output_statistics() -> None:
    console.print(Panel("[bold cyan]Data Storage & Volume Metrics[/bold cyan]", border_style="cyan"))
    
    table = Table(border_style="cyan", show_header=True, header_style="bold magenta")
    table.add_column("Scraper / Path", style="bold white")
    table.add_column("Size", style="bold green", justify="right")
    table.add_column("Last Modified", style="bold blue")
    table.add_column("Format", style="bold yellow")

    total_size = 0
    total_files = 0

    for sid, info in SCRAPERS.items():
        out_path = info["output_path"]
        if os.path.exists(out_path):
            size = os.path.getsize(out_path)
            total_size += size
            total_files += 1

            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size/1024:.1f} KB"
            else:
                size_str = f"{size/(1024*1024):.1f} MB"

            mtime = os.path.getmtime(out_path)
            mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            fmt = os.path.splitext(out_path)[1].upper().replace(".", "")

            table.add_row(out_path, size_str, mtime_str, fmt)
        else:
            table.add_row(out_path, "[red]Missing[/red]", "-", "-")

    console.print(table)
    
    # Render total volume summary
    if total_size < 1024:
        total_size_str = f"{total_size} B"
    elif total_size < 1024 * 1024:
        total_size_str = f"{total_size/1024:.2f} KB"
    else:
        total_size_str = f"{total_size/(1024*1024):.2f} MB"

    console.print(Panel(
        f"[bold white]Total Scraped Files:[/bold white] [green]{total_files}[/green]\n"
        f"[bold white]Total Active Volume:[/bold white] [cyan]{total_size_str}[/cyan]",
        title="Volume Summary",
        border_style="white"
    ))


def interactive_dashboard() -> None:
    while True:
        console.clear()
        print_banner()

        console.print(Align.center("[bold white]====== MAIN MENU ======[/bold white]\n"))
        console.print("  1. [bold cyan]List & Run Scrapers[/bold cyan] (Individual / Batch Execution)")
        console.print("  2. [bold cyan]View Output Data & Statistics[/bold cyan]")
        console.print("  3. [bold cyan]Help & Documentation[/bold cyan]")
        console.print("  q. [bold red]Quit / Exit[/bold red]")
        console.print()

        choice = console.input("[bold yellow]Choose option: [/bold yellow]").strip().lower()

        if choice == "1":
            while True:
                console.clear()
                print_banner()
                table = list_scrapers_table()
                console.print(table)
                console.print()
                console.print("[dim]Enter the Scraper ID to start running, or 'b' to go back.[/dim]")
                console.print("[dim]Or run multiple: 'all', 'all:news', 'all:ecommerce', 'all:finance'[/dim]")
                scraper_choice = console.input("[bold yellow]Run Scraper ID: [/bold yellow]").strip()

                if scraper_choice.lower() == "b":
                    break
                
                if scraper_choice.lower() == "all" or scraper_choice.lower().startswith("all:"):
                    # Batch execution
                    category_filter = None
                    if ":" in scraper_choice:
                        category_filter = scraper_choice.split(":")[1].strip().lower()
                    
                    scrapers_to_run = []
                    for sid, info in SCRAPERS.items():
                        if category_filter and info["category"].lower() != category_filter:
                            continue
                        scrapers_to_run.append((sid, info))
                    
                    if not scrapers_to_run:
                        console.print(f"[bold red]No scrapers found matching category filter '{category_filter}'.[/bold red]")
                        time.sleep(1.5)
                        continue
                    
                    console.clear()
                    console.print(Panel(
                        f"[bold cyan]Starting batch execution of {len(scrapers_to_run)} scrapers...[/bold cyan]",
                        border_style="cyan"
                    ))
                    
                    success_count = 0
                    failed_scrapers = []
                    
                    for sid, info in scrapers_to_run:
                        console.print(f"\n[bold yellow]>>> [{info['category']}] Executing {info['name']} ({sid})...[/bold yellow]")
                        # For batch interactive run, we add brief smoketest parameters to news crawlers so they complete rapidly.
                        extra_args = []
                        if info["category"] == "News" or sid in ["alfagift", "indomaret"]:
                            extra_args.extend(["--limit-categories", "1", "--limit-articles", "2"])
                        elif sid in ["detik", "narasi", "bisnis", "cnn", "kompas", "cnbc"]:
                            extra_args.extend(["--limit-articles", "2"])
                            
                        success = run_scraper_subprocess(sid, extra_args)
                        if success:
                            success_count += 1
                        else:
                            failed_scrapers.append(sid)
                    
                    console.print(Panel(
                        f"[bold green]Batch run complete.[/bold green]\n"
                        f"[bold white]Success Rate:[/bold white] [green]{success_count}/{len(scrapers_to_run)}[/green]\n"
                        f"[bold white]Failed Scrapers:[/bold white] {', '.join(failed_scrapers) if failed_scrapers else '[green]None[/green]'}",
                        border_style="green",
                        title="Batch Run Summary"
                    ))
                    console.input("\n[dim]Press Enter to continue...[/dim]")
                    continue

                if scraper_choice in SCRAPERS:
                    console.clear()
                    run_scraper_subprocess(scraper_choice)
                    console.input("\n[dim]Press Enter to continue...[/dim]")
                else:
                    console.print(f"[bold red]Invalid ID: '{scraper_choice}'. Please select a valid ID from the table.[/bold red]")
                    time.sleep(1.5)

        elif choice == "2":
            console.clear()
            print_banner()
            view_output_statistics()
            console.input("\n[dim]Press Enter to continue...[/dim]")

        elif choice == "3":
            console.clear()
            print_banner()
            help_text = (
                "[bold cyan]Indoscraping Scraper Suite[/bold cyan]\n\n"
                "This collection aggregates various crawlers focused on Indonesian data:\n"
                "  - [magenta]News[/magenta]: Detik, Bisnis.com, CNBC, CNN, Kompas, Narasi\n"
                "  - [magenta]E-Commerce[/magenta]: Alfagift, Klik Indomaret, Blibli, Tokopedia\n"
                "  - [magenta]Finance[/magenta]: Digital bank rates (Jago, SeaBank, Jenius, etc.)\n\n"
                "Dependencies are managed efficiently using [green]uv[/green].\n"
                "Playwright crawls automatically bypass runtime browser downloads and use local system-installed binaries."
            )
            console.print(Panel(help_text, border_style="cyan", title="Help & Information"))
            console.input("\n[dim]Press Enter to continue...[/dim]")

        elif choice == "q":
            console.print("[bold green]Thank you for using Indoscraping! Goodbye.[/bold green]")
            break
        else:
            console.print("[bold red]Invalid choice, please select 1, 2, 3 or q.[/bold red]")
            time.sleep(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Indoscraping Scraper Suite CLI Dashboard")
    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    # List command
    subparsers.add_parser("list", help="List all available scrapers and status")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run a specific scraper")
    run_parser.add_argument("scraper_id", choices=list(SCRAPERS.keys()), help="ID of the scraper to run")
    run_parser.add_argument("scraper_args", nargs=argparse.REMAINDER, help="Additional optional arguments for the scraper script")

    # Run-all command
    run_all_parser = subparsers.add_parser("run-all", help="Run all scrapers sequentially")
    run_all_parser.add_argument("--category", choices=["news", "ecommerce", "finance"], type=str.lower, help="Filter scrapers by category")
    run_all_parser.add_argument("--limit-categories", type=int, help="Override --limit-categories argument for news scrapers")
    run_all_parser.add_argument("--limit-articles", type=int, help="Override --limit-articles argument for news/ecommerce scrapers")

    # Status command
    subparsers.add_parser("status", help="Show scraped output files and data metrics")

    args = parser.parse_args()

    if args.command == "list":
        table = list_scrapers_table()
        console.print(table)
    elif args.command == "run":
        success = run_scraper_subprocess(args.scraper_id, args.scraper_args)
        sys.exit(0 if success else 1)
    elif args.command == "run-all":
        # Identify scrapers to run
        scrapers_to_run = []
        for sid, info in SCRAPERS.items():
            if args.category and info["category"].lower() != args.category.lower():
                continue
            scrapers_to_run.append((sid, info))

        if not scrapers_to_run:
            console.print("[bold red]No scrapers found matching the category filter.[/bold red]")
            sys.exit(1)

        console.print(Panel(
            f"[bold cyan]Running {len(scrapers_to_run)} scrapers sequentially...[/bold cyan]",
            border_style="cyan"
        ))

        success_count = 0
        failed_scrapers = []

        for sid, info in scrapers_to_run:
            extra_args = []
            if args.limit_categories and (info["category"] == "News" or sid in ["alfagift", "indomaret"]):
                extra_args.extend(["--limit-categories", str(args.limit_categories)])
            if args.limit_articles:
                if info["category"] == "News" or sid in ["detik", "narasi", "bisnis", "cnn", "kompas", "cnbc", "alfagift", "indomaret"]:
                    extra_args.extend(["--limit-articles", str(args.limit_articles)])
            
            console.print(f"\n[bold yellow]>>> [{info['category']}] Executing {info['name']} ({sid})...[/bold yellow]")
            success = run_scraper_subprocess(sid, extra_args)
            if success:
                success_count += 1
            else:
                failed_scrapers.append(sid)

        console.print(Panel(
            f"[bold green]Batch run complete.[/bold green]\n"
            f"[bold white]Success Rate:[/bold white] [green]{success_count}/{len(scrapers_to_run)}[/green]\n"
            f"[bold white]Failed Scrapers:[/bold white] {', '.join(failed_scrapers) if failed_scrapers else '[green]None[/green]'}",
            border_style="green",
            title="Batch Run Summary"
        ))
        sys.exit(0 if len(failed_scrapers) == 0 else 1)
    elif args.command == "status":
        view_output_statistics()
    else:
        # Launch beautiful interactive dashboard
        interactive_dashboard()


if __name__ == "__main__":
    main()
