import re

from bs4 import BeautifulSoup

from .base import (
    BaseScraper,
    EmptyParseError,
    ScrapeRunResult,
    ScraperError,
    UnsupportedSourceError,
    collect_strings,
    extract_next_data,
)
from .models import BankData, RateDetail


class NeoBankScraper(BaseScraper):
    mode = "http"

    def __init__(self):
        super().__init__(
            "Bank Neo Commerce", "https://www.bankneocommerce.co.id/id/product/neo-now"
        )
        self.product_pages = [
            ("https://www.bankneocommerce.co.id/id/product/neo-now", "Neo NOW"),
            ("https://www.bankneocommerce.co.id/id/product/neo-wow", "Neo WOW"),
            ("https://www.bankneocommerce.co.id/id/product/neo-wow-flexi", "Neo WOW FLEXI"),
        ]

    async def run(self, playwright):
        try:
            results: list[BankData] = []
            for url, product_name in self.product_pages:
                soup = self.fetch_document(url)
                rates = self._parse_product_page(soup)
                if rates:
                    results.append(
                        BankData(
                            bank_name=self.name,
                            product_name=product_name,
                            rates=rates,
                            source_url=url,
                        )
                    )

            if not results:
                raise UnsupportedSourceError(
                    "Bank Neo Commerce official product pages do not currently expose "
                    "structured rate values that this scraper can parse reliably.",
                    source_url=self.url,
                )

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

    def _parse_product_page(self, soup: BeautifulSoup) -> list[RateDetail]:
        payload = extract_next_data(soup)
        text = " ".join(collect_strings(payload.get("props", {}).get("pageProps", {})))
        text = f"{soup.get_text(' ', strip=True)} {text}"
        text = re.sub(r"\s+", " ", text)

        tenor_matches = re.findall(
            r"((?:\d+\s*bulan|1\s*-\s*2\s*bulan|3\s*-\s*5\s*bulan|6\s*-\s*12\s*bulan|"
            r"6-11\s*bulan))[^%]{0,80}?(\d+(?:[.,]\d+)?)\s*%",
            text,
            re.IGNORECASE,
        )
        if tenor_matches:
            seen: set[tuple[str, float]] = set()
            rates: list[RateDetail] = []
            for tenor, rate in tenor_matches:
                numeric_rate = float(rate.replace(",", "."))
                key = (tenor.lower(), numeric_rate)
                if key in seen:
                    continue
                seen.add(key)
                rates.append(RateDetail(tenor=tenor.strip(), rate=numeric_rate))
            if rates:
                return rates

        numeric_rates: list[float] = []
        for rate_text in re.findall(r"(\d+(?:[.,]\d+)?)\s*%", text):
            rate = float(rate_text.replace(",", "."))
            if 0 < rate <= 100 and rate not in numeric_rates:
                numeric_rates.append(rate)

        return [RateDetail(tenor="Standard", rate=rate) for rate in numeric_rates[:3]]
