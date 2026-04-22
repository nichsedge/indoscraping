from bs4 import BeautifulSoup

from .base import BaseScraper, EmptyParseError, SourceChangedError, clean_text, parse_rate
from .models import BankData, RateDetail


class JeniusScraper(BaseScraper):
    mode = "http"

    def __init__(self):
        super().__init__("Jenius", "https://www.jenius.com/id/rates-and-limits")

    def scrape_http(self, soup: BeautifulSoup) -> list[BankData]:
        sections = [
            ("dmaxisaver-rates", "Maxi Saver"),
            ("dflexisaver-rates", "Flexi Saver"),
            ("ddreamsaver-rates", "Dream Saver"),
        ]
        results: list[BankData] = []

        for section_id, product_name in sections:
            container = soup.select_one(f"#{section_id}")
            if not container:
                continue

            rates = self._parse_section_rates(container, product_name)
            if rates:
                results.append(
                    BankData(
                        bank_name=self.name,
                        product_name=product_name,
                        rates=rates,
                        source_url=self.url,
                    )
                )

        if not results:
            raise EmptyParseError("No Jenius rate sections were parsed", source_url=self.url)

        return results

    def _parse_section_rates(
        self, container: BeautifulSoup, product_name: str
    ) -> list[RateDetail]:
        rates: list[RateDetail] = []
        seen: set[tuple[str, float]] = set()

        for row in container.select("table tr"):
            cells = [clean_text(cell.get_text(" ", strip=True)) for cell in row.select("th, td")]
            if len(cells) < 2:
                continue

            if product_name == "Maxi Saver":
                tenor = cells[0]
                for value in cells[1:]:
                    rate = parse_rate(value)
                    if rate is None:
                        continue
                    key = (tenor, rate)
                    if key not in seen:
                        seen.add(key)
                        rates.append(RateDetail(tenor=tenor, rate=rate))
                continue

            label = cells[0]
            value = " ".join(cells[1:])
            rate = parse_rate(value)
            if rate is None:
                continue
            key = (label, rate)
            if key in seen:
                continue
            seen.add(key)
            rates.append(RateDetail(tenor=label, rate=rate))

        return rates
