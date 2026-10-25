"""KPK LHKPN (Laporan Harta Kekayaan Penyelenggara Negara) Scraper.

Extracts state official asset announcements, declaration history, and itemized
wealth breakdowns (property, vehicles, securities, cash, debts) from the KPK portal.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright
from playwright_stealth import Stealth

from indoscraping_core.lineage import collect_lineage
from indoscraping_core.output import write_latest_and_history

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("lhkpn")

CATEGORY_MAP: Dict[str, str] = {
    "TANAH DAN BANGUNAN": "tanah_bangunan",
    "ALAT TRANSPORTASI DAN MESIN": "transportasi",
    "HARTA BERGERAK LAINNYA": "bergerak_lainnya",
    "SURAT BERHARGA": "surat_berharga",
    "KAS DAN SETARA KAS": "kas",
    "HARTA LAINNYA": "harta_lainnya",
    "HUTANG": "hutang",
}


def parse_detail(html: str) -> Dict[str, List[Dict[str, str]]]:
    """Parse the comparison/detail modal HTML using BeautifulSoup.

    Args:
        html: HTML content of the modal dialog.

    Returns:
        Categorized dictionary containing asset entries and values.
    """
    soup = BeautifulSoup(html, "html.parser")
    data: Dict[str, List[Dict[str, str]]] = {
        "tanah_bangunan": [],
        "transportasi": [],
        "bergerak_lainnya": [],
        "surat_berharga": [],
        "kas": [],
        "harta_lainnya": [],
        "hutang": [],
    }

    tbody = soup.find("tbody", class_="data_perbandingan_lhkpn")
    if not tbody:
        return data

    rows = tbody.find_all("tr")
    current_cat: Optional[str] = None

    for row in rows:
        cells = row.find_all(["td", "th"])
        new_cat_found = False

        if len(cells) >= 3:
            c1_text = cells[1].get_text(strip=True).upper()
            c2_text = cells[2].get_text(strip=True).upper()

            for cat_name, key in CATEGORY_MAP.items():
                if cat_name in c2_text or cat_name in row.get_text(" ", strip=True).upper()[:50]:
                    header_indicators = ["A.", "B.", "C.", "D.", "E.", "F.", "II.", "III."]
                    if any(ind in c1_text or ind in cells[0].get_text(strip=True).upper() for ind in header_indicators):
                        current_cat = key
                        new_cat_found = True
                        break

        if new_cat_found:
            continue

        if current_cat:
            found_index = False
            desc = ""
            val = ""

            for j in range(min(len(cells), 4)):
                cell_text = cells[j].get_text(strip=True)
                if cell_text and cell_text[0].isdigit() and cell_text.endswith("."):
                    found_index = True
                    if j + 1 < len(cells):
                        desc = cells[j + 1].get_text(strip=True)
                        for k in range(j + 2, len(cells)):
                            k_text = cells[k].get_text(strip=True)
                            if k_text and (k_text[0].isdigit() or (len(k_text) > 1 and k_text[0] in "0123456789")):
                                val = k_text
                                break
                    break

            if found_index and desc and val:
                data[current_cat].append({
                    "description": desc,
                    "value": val,
                })

    # Fallback for category totals if individual line items were not matched
    for key, val_list in data.items():
        if not val_list:
            cat_name_search = [k for k, v in CATEGORY_MAP.items() if v == key][0]
            for row in rows:
                row_text = row.get_text(" ", strip=True).upper()
                if cat_name_search in row_text:
                    cells = row.find_all(["td", "th"])
                    for cell in cells:
                        cell_text = cell.get_text(strip=True)
                        clean_num = cell_text.replace("Rp.", "").replace("Rp", "").strip().replace(".", "").replace(",", "")
                        if clean_num and clean_num.isdigit():
                            data[key].append({
                                "description": "Total",
                                "value": cell_text.replace("Rp.", "").replace("Rp", "").strip(),
                            })
                            break
                    if data[key]:
                        break

    return data


class LHKPNScraper:
    """Scraper for the KPK LHKPN State Official Wealth Portal."""

    BASE_URL = "https://elhkpn.kpk.go.id"
    SEARCH_PAGE = f"{BASE_URL}/portal/user/login#announ"

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def init_browser(self, playwright: Playwright) -> None:
        """Initialize browser with stealth and anti-bot evasions."""
        logger.info("Initializing Playwright browser...")
        launch_args = ["--disable-blink-features=AutomationControlled", "--no-sandbox"]

        try:
            self.browser = await playwright.chromium.launch(
                channel="chrome",
                headless=self.headless,
                args=launch_args,
            )
        except Exception as e:
            logger.warning(f"Could not launch system Chrome ({e}), falling back to bundled Chromium...")
            self.browser = await playwright.chromium.launch(
                headless=self.headless,
                args=launch_args,
            )

        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        )
        self.page = await self.context.new_page()

        try:
            await Stealth().apply_stealth_async(self.page)
        except Exception as e:
            logger.warning(f"Failed to apply playwright stealth: {e}")

    async def handle_popups(self) -> None:
        """Dismiss common initial announcement modals on KPK portal."""
        if not self.page:
            return
        logger.info("Checking and handling popups...")
        try:
            for _ in range(5):
                await self.page.evaluate("""() => {
                    const closeButtons = document.querySelectorAll('.remodal-close');
                    closeButtons.forEach(btn => btn.click());
                    
                    const wrappers = document.querySelectorAll('.remodal-wrapper.remodal-is-opened');
                    wrappers.forEach(w => w.style.display = 'none');
                    
                    const backdrop = document.querySelector('.remodal-overlay');
                    if (backdrop) backdrop.remove();
                    
                    document.body.classList.remove('remodal-is-active');
                    
                    const bootstrapModals = document.querySelectorAll('.modal.in, .modal.show');
                    bootstrapModals.forEach(m => {
                        const close = m.querySelector('button.close, .btn-close');
                        if (close) close.click();
                        else m.style.display = 'none';
                    });
                }""")
                await asyncio.sleep(1)
                active = await self.page.query_selector(".remodal-is-opened, .modal.in, .modal.show")
                if not active:
                    break
        except Exception as e:
            logger.warning(f"Note on popup handling: {e}")

    async def search(self, name: str) -> None:
        """Navigate to KPK announcement portal and search by official name."""
        if not self.page:
            return
        logger.info(f"Navigating to LHKPN portal and searching for '{name}'...")
        try:
            await self.page.goto(self.SEARCH_PAGE, timeout=60000, wait_until="load")
        except Exception as e:
            logger.warning(f"Initial goto timeout or notice: {e}. Retrying with domcontentloaded...")
            await self.page.goto(self.SEARCH_PAGE, timeout=60000, wait_until="domcontentloaded")

        await self.handle_popups()

        try:
            announ_tab = self.page.locator("a.page-scroll[href='#announ'], a.anchor-eannoun").first
            await announ_tab.scroll_into_view_if_needed()
            await announ_tab.click()
            await asyncio.sleep(2)
        except Exception as e:
            logger.warning(f"Could not click announcement tab directly ({e}), navigating via hash...")
            await self.page.evaluate("window.location.hash = '#announ'")
            await asyncio.sleep(1)

        input_selector = "#CARI_NAMA, input[name='CARI_NAMA']"
        try:
            await self.page.wait_for_selector(input_selector, timeout=20000)
        except Exception:
            logger.warning("Search input selector not immediately found, resetting hash...")
            await self.page.evaluate("window.location.hash = '#announ'")
            await self.page.wait_for_selector(input_selector, timeout=20000)

        input_field = self.page.locator(input_selector).first
        await input_field.scroll_into_view_if_needed()
        await input_field.click()
        await self.page.keyboard.press("Control+A")
        await self.page.keyboard.press("Backspace")
        await input_field.fill(name)

        search_btn = self.page.locator("button[type='submit'].btn-success")
        await search_btn.scroll_into_view_if_needed()
        await search_btn.click()

        logger.info("Waiting for search results table...")
        try:
            table_row_selector = "#table-pengumuman tbody tr, table.table-striped tbody tr"
            await self.page.wait_for_selector(table_row_selector, timeout=30000)
            logger.info("Found search results table.")
        except Exception as e:
            logger.warning(f"Results table did not appear within timeout: {e}")
            if await self.page.locator("text='Data Tidak Ditemukan'").is_visible():
                logger.info("Search returned no results from KPK portal.")

        await asyncio.sleep(2)

    async def extract_and_detail(self, max_results: Union[int, float] = float("inf")) -> List[Dict[str, Any]]:
        """Extract summary records and detailed asset breakdowns from modals."""
        if not self.page:
            return []

        logger.info(f"Extracting results (max limit: {max_results})...")
        all_data: List[Dict[str, Any]] = []
        page_num = 1

        while len(all_data) < max_results:
            logger.info(f"Processing result page {page_num}...")
            row_selector = "table.table-striped tbody tr, #table-pengumuman tbody tr"

            try:
                await self.page.wait_for_selector(row_selector, timeout=10000)
            except Exception:
                logger.info(f"No table rows found on page {page_num}.")
                break

            rows = self.page.locator(row_selector)
            count = await rows.count()

            if count > 0:
                first_row_cells = await rows.nth(0).locator("td").count()
                if first_row_cells < 5:
                    logger.info("Page contains placeholder or loading message.")
                    break

            logger.info(f"Found {count} rows on page {page_num}.")

            for i in range(count):
                if len(all_data) >= max_results:
                    break

                row = rows.nth(i)
                cells = row.locator("td")

                try:
                    async def get_cell_text(idx: int) -> str:
                        try:
                            if await cells.nth(idx).count() > 0:
                                return await cells.nth(idx).inner_text()
                        except Exception:
                            pass
                        return ""

                    name = await get_cell_text(6)
                    lembaga = await get_cell_text(7)
                    unit_kerja = await get_cell_text(8)
                    jabatan = await get_cell_text(9)
                    tanggal_lapor = await get_cell_text(10)
                    total_harta = await get_cell_text(12)
                    jenis_laporan = await get_cell_text(11)

                    if not name.strip() or "Rp." not in total_harta:
                        name = await get_cell_text(1)
                        lembaga = await get_cell_text(2)
                        unit_kerja = await get_cell_text(3)
                        jabatan = await get_cell_text(4)
                        tanggal_lapor = await get_cell_text(5)
                        total_harta = await get_cell_text(7)
                        jenis_laporan = await get_cell_text(6)

                    data: Dict[str, Any] = {
                        "name": name.strip(),
                        "lembaga": lembaga.strip(),
                        "unit_kerja": unit_kerja.strip(),
                        "jabatan": jabatan.strip(),
                        "tanggal_lapor": tanggal_lapor.strip(),
                        "jenis_laporan": jenis_laporan.strip(),
                        "total_harta": total_harta.strip(),
                        "tanah_bangunan": [],
                        "transportasi": [],
                        "bergerak_lainnya": [],
                        "surat_berharga": [],
                        "kas": [],
                        "harta_lainnya": [],
                        "hutang": [],
                    }

                    action_link = row.locator(".perbandingan-announcement, i.fa-history, i.fa-file-text-o")
                    if await action_link.count() > 0:
                        history_btn = row.locator(
                            "a.perbandingan-announcement, a[data-toggle='modal'][data-target='#modal-perbandingan-announcement-lhkpn']"
                        ).first
                        if await history_btn.count() > 0 and await history_btn.is_visible():
                            logger.info(f"Opening details for {name.strip()} ({tanggal_lapor.strip()})...")
                            await history_btn.click()

                            modal_selector = "#modal-perbandingan-announcement-lhkpn"
                            try:
                                await self.page.wait_for_selector(f"{modal_selector} table", timeout=15000)
                                await asyncio.sleep(1.5)

                                modal_html = await self.page.inner_html(modal_selector)
                                details = parse_detail(modal_html)
                                data.update(details)

                                close_btn = self.page.locator(
                                    f"{modal_selector} .remodal-close, {modal_selector} .btn-danger, button[data-dismiss='modal']"
                                ).first
                                if await close_btn.is_visible():
                                    await close_btn.click()
                                    await self.page.wait_for_selector(modal_selector, state="hidden", timeout=5000)
                                else:
                                    await self.page.keyboard.press("Escape")
                                    await asyncio.sleep(1)
                            except Exception as e:
                                logger.warning(f"Could not extract modal details for {name}: {e}")
                                await self.page.keyboard.press("Escape")
                                await asyncio.sleep(1)

                    all_data.append(data)
                except Exception as e:
                    logger.error(f"Error processing row {i}: {e}")

            next_btn = self.page.locator(
                "#table-pengumuman_next, li.next a, .paginate_button.next a, a:has-text('Next'), a:has-text('>>')"
            ).first

            if await next_btn.count() > 0:
                is_visible = await next_btn.is_visible()
                is_disabled = await self.page.evaluate(
                    """(btn) => {
                    const parent = btn.parentElement;
                    return btn.classList.contains('disabled') || 
                           (parent && parent.classList.contains('disabled')) ||
                           btn.getAttribute('aria-disabled') === 'true' ||
                           btn.disabled;
                }""",
                    await next_btn.element_handle(),
                )

                if is_visible and not is_disabled:
                    logger.info("Navigating to next page...")
                    await next_btn.scroll_into_view_if_needed()
                    await next_btn.click()
                    page_num += 1
                    await asyncio.sleep(5)
                else:
                    logger.info("Reached the last available page.")
                    break
            else:
                break

        return all_data

    async def run(self, query: str, max_results: Union[int, float] = float("inf")) -> List[Dict[str, Any]]:
        """Run full LHKPN scraper session."""
        async with async_playwright() as p:
            await self.init_browser(p)
            try:
                await self.search(query)
                data = await self.extract_and_detail(max_results=max_results)
                return data
            finally:
                if self.browser:
                    await self.browser.close()


def save_lhkpn_results(
    data: List[Dict[str, Any]],
    output_path: str,
    format_type: str = "json",
    date_str: Optional[str] = None,
) -> None:
    """Save scraped LHKPN data adhering to Indoscraping atomic output and lineage standards."""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    out_file = Path(output_path)
    out_dir = out_file.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    history_dir = out_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    history_path = str(history_dir / f"{date_str}.json")

    lineage = collect_lineage("lhkpn")
    meta = {
        "scraper": "lhkpn",
        "category": "Governance",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "total_records": len(data),
        "date": date_str,
        "lineage": lineage,
    }

    # Save canonical latest.json and history snapshot
    write_latest_and_history(
        latest_path=str(out_file),
        history_path=history_path,
        payload=data,
        meta=meta,
    )
    logger.info(f"Saved latest snapshot to: {out_file} ({len(data)} records)")
    logger.info(f"Saved history snapshot to: {history_path}")

    # If CSV requested, write flattened table
    if format_type == "csv":
        csv_path = str(out_file.with_suffix(".csv"))
        df = pd.DataFrame(data)
        cols = ["name", "lembaga", "unit_kerja", "jabatan", "tanggal_lapor", "jenis_laporan", "total_harta"]
        ordered_cols = [c for c in cols if c in df.columns]
        other_cols = [c for c in df.columns if c not in cols]
        df = df[ordered_cols + other_cols]
        df.to_csv(csv_path, index=False)
        logger.info(f"Saved CSV export to: {csv_path}")


def parse_max_results(value: str) -> Union[int, float]:
    """Parse max results integer or allow 'inf' for unlimited."""
    if value.lower() == "inf":
        return float("inf")
    try:
        return int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid max-results value: '{value}'")


def main() -> None:
    """CLI entry point for standalone or Indoscraping execution."""
    parser = argparse.ArgumentParser(description="KPK LHKPN State Official Wealth Scraper.")
    parser.add_argument("query_pos", nargs="?", default=None, help="State official name to query (positional)")
    parser.add_argument("--query", "-q", default=None, help="State official name to query")
    parser.add_argument(
        "--limit-articles",
        "--max-results",
        "--limit",
        dest="max_results",
        type=parse_max_results,
        default=10,
        help="Maximum records to scrape (default: 10, or 'inf' for unlimited)",
    )
    parser.add_argument("--headless", action="store_true", default=True, help="Run browser headless (default: True)")
    parser.add_argument("--no-headless", action="store_false", dest="headless", help="Run browser in visible mode")
    parser.add_argument("--output", type=str, default="data/governance/lhkpn/latest.json", help="Output JSON path")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format (default: json)")
    parser.add_argument("--date", default=None, help="Snapshot date (YYYY-MM-DD)")

    args = parser.parse_args()
    query = args.query or args.query_pos or "PRABOWO SUBIANTO"

    logger.info(f"Starting LHKPN scrape for '{query}' (limit: {args.max_results})...")
    scraper = LHKPNScraper(headless=args.headless)

    try:
        data = asyncio.run(scraper.run(query=query, max_results=args.max_results))
        if not data:
            logger.warning(f"No records returned for '{query}'.")
            return

        save_lhkpn_results(data, output_path=args.output, format_type=args.format, date_str=args.date)
    except Exception as e:
        logger.error(f"Error during LHKPN scraping session: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
