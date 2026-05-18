import asyncio
import json
import os
from datetime import datetime
from typing import Iterable

from playwright.async_api import async_playwright
from rich.console import Console
from rich.table import Table

from src.indoscraping.scraper.finance import ALL_SCRAPERS
from src.indoscraping.scraper.finance.base import ScrapeRunResult
from src.indoscraping.scraper.finance.models import BankData, ScrapeResult

console = Console()


async def run_scrapers() -> list[ScrapeRunResult]:
    scrapers = [scraper_cls() for scraper_cls in ALL_SCRAPERS]

    async with async_playwright() as playwright:
        results: list[ScrapeRunResult] = []
        for scraper in scrapers:
            results.append(await scraper.run(playwright))
        return results


def detect_changes(new_data: list[BankData], old_data: list[BankData]) -> list[str]:
    changes = []
    old_map = {(bank.bank_name, bank.product_name): bank for bank in old_data}
    new_map = {(bank.bank_name, bank.product_name): bank for bank in new_data}

    for key, new_bank in new_map.items():
        if key not in old_map:
            changes.append(f"NEW Product: {key[0]} - {key[1]}")
            continue
        old_bank = old_map[key]
        if new_bank.rates != old_bank.rates:
            changes.append(f"CHANGED Rates: {key[0]} - {key[1]}")

    for key in old_map:
        if key not in new_map:
            changes.append(f"REMOVED Product: {key[0]} - {key[1]}")

    return changes


def flatten_bank_data(results: Iterable[ScrapeRunResult]) -> list[BankData]:
    data: list[BankData] = []
    for result in results:
        data.extend(result.bank_data)
    return data


def load_previous_data(latest_file: str) -> list[BankData]:
    if not os.path.exists(latest_file):
        return []
    with open(latest_file, "r") as handle:
        old_data = json.load(handle)
    return [BankData(**bank) for bank in old_data.get("banks", [])]


def print_statuses(results: list[ScrapeRunResult]) -> None:
    table = Table(title="Scraper Status")
    table.add_column("Bank", style="cyan")
    table.add_column("Mode", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Details", style="yellow")

    for result in results:
        if result.success:
            table.add_row(
                result.scraper_name,
                result.mode,
                "ok",
                f"{len(result.bank_data)} products",
            )
            continue
        table.add_row(
            result.scraper_name,
            result.mode,
            result.error.code,
            result.error.message,
        )

    console.print(table)


def print_rates(banks: list[BankData]) -> None:
    table = Table(title="Current Interest Rates")
    table.add_column("Bank", style="cyan")
    table.add_column("Product", style="magenta")
    table.add_column("Tenor", style="green")
    table.add_column("Rate (%)", justify="right", style="yellow")

    for bank in banks:
        for rate in bank.rates:
            table.add_row(bank.bank_name, bank.product_name, rate.tenor, f"{rate.rate:.2f}%")

    console.print(table)


def save_data(result: ScrapeResult) -> tuple[str, str]:
    latest_file = "data/latest.json"
    timestamp = datetime.now().strftime("%Y-%m-%d")
    history_file = f"data/history/{timestamp}.json"
    os.makedirs("data/history", exist_ok=True)
    payload = result.model_dump(mode="json")

    with open(latest_file, "w") as latest_handle:
        json.dump(payload, latest_handle, indent=2)

    with open(history_file, "w") as history_handle:
        json.dump(payload, history_handle, indent=2)

    return latest_file, history_file


async def main() -> None:
    console.print("[bold blue]Starting Digital Bank Indonesia Rate Scraper...[/bold blue]")

    results = await run_scrapers()
    print_statuses(results)

    successful_banks = flatten_bank_data(result for result in results if result.success)
    failed_results = [result for result in results if not result.success]

    if not successful_banks:
        raise SystemExit("No bank data was scraped successfully.")

    old_banks = []
    try:
        old_banks = load_previous_data("data/latest.json")
    except Exception as exc:
        console.print(f"[yellow]Could not load old data: {exc}[/yellow]")

    changes = detect_changes(successful_banks, old_banks)
    if changes:
        console.print("[bold yellow]Changes Detected:[/bold yellow]")
        for change in changes:
            console.print(f" - {change}")
    else:
        console.print("[green]No changes detected since last run.[/green]")

    result = ScrapeResult(banks=successful_banks)
    latest_file, history_file = save_data(result)
    console.print(f"[green]Data saved to {latest_file} and {history_file}[/green]")
    print_rates(successful_banks)

    blocking_failures = [
        result for result in failed_results if result.error.code != "unsupported"
    ]

    if blocking_failures:
        failed_codes = ", ".join(
            f"{result.scraper_name}={result.error.code}" for result in blocking_failures
        )
        raise SystemExit(f"Some scrapers failed: {failed_codes}")


if __name__ == "__main__":
    asyncio.run(main())
