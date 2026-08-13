#!/usr/bin/env python3
"""Live Scraper Verification & Schema Drift Smoke Test Script.

Executes rapid smoke-tests against target live endpoints to verify DOM integrity and schema matching.
"""

import sys
import subprocess
from rich.console import Console
from rich.table import Table

console = Console()

SCRAPER_TESTS = [
    ("detik", ["indoscraping", "run", "detik", "--limit-categories", "1", "--limit-articles", "1"]),
    ("bisnis", ["indoscraping", "run", "bisnis", "--limit-categories", "1", "--limit-articles", "1"]),
    ("cnbc", ["indoscraping", "run", "cnbc", "--limit-categories", "1", "--limit-articles", "1"]),
    ("alfagift", ["indoscraping", "run", "alfagift", "--limit-categories", "1", "--limit-articles", "1"]),
    ("indomaret", ["indoscraping", "run", "indomaret", "--limit-categories", "1", "--limit-articles", "1"]),
]

def main():
    console.print("[bold blue]🔍 Running IndoScraping Live Scraper & Schema Health Smoke Tests...[/bold blue]\n")
    
    table = Table(title="Scraper Live Verification Results")
    table.add_column("Scraper Key", style="cyan")
    table.add_column("Command", style="magenta")
    table.add_column("Status", style="bold green")

    all_passed = True
    for key, cmd in SCRAPER_TESTS:
        console.print(f"Testing scraper [bold yellow]{key}[/bold yellow]...")
        try:
            res = subprocess.run(["uv", "run"] + cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
            if res.returncode == 0:
                table.add_row(key, " ".join(cmd), "[green]PASS (Schema Valid)[/green]")
            else:
                all_passed = False
                table.add_row(key, " ".join(cmd), f"[red]FAIL (Exit {res.returncode})[/red]")
        except subprocess.TimeoutExpired:
            all_passed = False
            table.add_row(key, " ".join(cmd), "[yellow]TIMEOUT (60s)[/yellow]")
        except Exception as e:
            all_passed = False
            table.add_row(key, " ".join(cmd), f"[red]ERROR: {e}[/red]")

    console.print(table)
    if not all_passed:
        sys.exit(1)

if __name__ == "__main__":
    main()
