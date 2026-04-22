import re

from bs4 import BeautifulSoup
from playwright_stealth import Stealth

from .base import (
    BaseScraper,
    EmptyParseError,
    ScrapeRunResult,
    ScraperError,
    SourceChangedError,
    DEFAULT_USER_AGENT,
    clean_text,
    extract_next_data,
    parse_rate,
)
from .models import BankData, RateDetail


class SeaBankScraper(BaseScraper):
    mode = "http"

    def __init__(self):
        super().__init__("SeaBank", "https://www.seabank.co.id/info/biaya-bunga")
        self.deposito_url = (
            "https://www.seabank.co.id/pusat-bantuan/artikel/"
            "10080-berapa-bunga-dan-tenor-deposito-yang-ditawarkan-oleh-seabank"
        )

    async def run(self, playwright):
        try:
            savings_doc = self.fetch_document(self.url)
            results = self.scrape_http(savings_doc)
            try:
                deposito_doc = self.fetch_document(self.deposito_url)
                results.extend(self.scrape_deposito_document(deposito_doc))
            except (SourceChangedError, EmptyParseError):
                results.extend(await self.scrape_deposito_with_browser(playwright))
            if not results:
                raise EmptyParseError("SeaBank returned no data", source_url=self.url)

            return ScrapeRunResult(
                scraper_name=self.name,
                source_url=self.url,
                mode=self.mode,
                bank_data=results,
            )
        except Exception as exc:
            error = exc if isinstance(exc, ScraperError) else ScraperError(str(exc))
            return ScrapeRunResult(
                scraper_name=self.name,
                source_url=getattr(error, "source_url", self.url) or self.url,
                mode=self.mode,
                error=error,
            )

    def scrape_http(self, soup: BeautifulSoup) -> list[BankData]:
        next_data = extract_next_data(soup)
        page_schema = next_data.get("props", {}).get("pageProps", {}).get("pageSchema", {})
        components_tree = page_schema.get("view", {}).get("componentsTree", [])

        rich_text = None
        for component in components_tree:
            if component.get("title") != "RichTextEditor":
                continue
            rich_text = component.get("props", {}).get("richContent", {}).get("textId")
            if rich_text:
                break

        if not rich_text:
            raise SourceChangedError("SeaBank savings rich text payload not found", source_url=self.url)

        rates = self._parse_savings_rates(rich_text)
        if not rates:
            raise EmptyParseError("SeaBank savings table did not contain rates", source_url=self.url)

        return [
            BankData(
                bank_name=self.name,
                product_name="SeaBank Tabungan",
                rates=rates,
                source_url=self.url,
            )
        ]

    def scrape_deposito_document(self, soup: BeautifulSoup) -> list[BankData]:
        next_data = extract_next_data(soup)
        content = (
            next_data.get("props", {})
            .get("pageProps", {})
            .get("preFetchData", {})
            .get("articleData", {})
            .get("content")
        )
        if not content:
            raise SourceChangedError(
                "SeaBank deposito article payload not found", source_url=self.deposito_url
            )

        text = clean_text(BeautifulSoup(content, "html.parser").get_text(" ", strip=True))
        rate = parse_rate(text)
        if rate is None:
            raise EmptyParseError(
                "SeaBank deposito article did not contain a rate", source_url=self.deposito_url
            )

        tenors = re.findall(r"\b(1|3|6|12)\s*bulan\b", text, re.IGNORECASE)
        unique_tenors = []
        for tenor in tenors:
            label = f"{tenor} bulan"
            if label not in unique_tenors:
                unique_tenors.append(label)
        if not unique_tenors:
            unique_tenors = ["Deposito"]

        return [
            BankData(
                bank_name=self.name,
                product_name="SeaBank Deposito",
                rates=[RateDetail(tenor=tenor, rate=rate) for tenor in unique_tenors],
                source_url=self.deposito_url,
            )
        ]

    async def scrape_deposito_with_browser(self, playwright) -> list[BankData]:
        browser = await playwright.chromium.launch(channel="chrome", headless=True)
        context = await browser.new_context(
            locale="id-ID",
            timezone_id="Asia/Jakarta",
            viewport={"width": 1440, "height": 900},
            user_agent=DEFAULT_USER_AGENT,
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        try:
            await page.goto(self.deposito_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(4000)
            text = clean_text(await page.locator("body").inner_text())
            rate = parse_rate(text)
            if rate is None:
                raise EmptyParseError(
                    "SeaBank deposito browser fallback did not contain a rate",
                    source_url=self.deposito_url,
                )

            tenors = re.findall(r"\b(1|3|6|12)\s*bulan\b", text, re.IGNORECASE)
            unique_tenors = []
            for tenor in tenors:
                label = f"{tenor} bulan"
                if label not in unique_tenors:
                    unique_tenors.append(label)
            if not unique_tenors:
                unique_tenors = ["Deposito"]

            return [
                BankData(
                    bank_name=self.name,
                    product_name="SeaBank Deposito",
                    rates=[RateDetail(tenor=tenor, rate=rate) for tenor in unique_tenors],
                    source_url=self.deposito_url,
                )
            ]
        finally:
            await context.close()
            await browser.close()

    def _parse_savings_rates(self, html: str) -> list[RateDetail]:
        soup = BeautifulSoup(html, "html.parser")
        rates: list[RateDetail] = []
        seen: set[tuple[str, float]] = set()

        for row in soup.select("tr"):
            cells = [clean_text(cell.get_text(" ", strip=True)) for cell in row.select("th, td")]
            if len(cells) < 2:
                continue
            label = cells[0]
            value = " ".join(cells[1:])
            rate = parse_rate(value)
            if rate is None or "tabungan" not in label.lower():
                continue
            key = ("Tabungan", rate)
            if key in seen:
                continue
            seen.add(key)
            rates.append(RateDetail(tenor="Tabungan", rate=rate))

        return rates
