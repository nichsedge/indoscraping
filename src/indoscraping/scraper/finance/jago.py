from bs4 import BeautifulSoup

from .base import BaseScraper, EmptyParseError, clean_text, parse_rate
from .models import BankData, RateDetail


class JagoScraper(BaseScraper):
    mode = "browser"

    def __init__(self):
        super().__init__("Bank Jago", "https://www.jago.com/id/jago/rates")

    async def scrape_browser(self, page, html: str) -> list[BankData]:
        soup = BeautifulSoup(html, "html.parser")
        results: list[BankData] = []

        for table in soup.select("table"):
            heading = table.find_previous(["h2", "h3", "h4"])
            title = clean_text(heading.get_text(" ", strip=True)) if heading else "Jago Product"
            if "limit" in title.lower():
                continue

            rates: list[RateDetail] = []
            for row in table.select("tr"):
                cells = [clean_text(cell.get_text(" ", strip=True)) for cell in row.select("th, td")]
                if len(cells) < 2:
                    continue
                label = cells[0]
                value = " ".join(cells[1:])
                rate = parse_rate(value)
                if rate is None:
                    continue
                rates.append(RateDetail(tenor=label, rate=rate))

            if rates:
                results.append(
                    BankData(
                        bank_name=self.name,
                        product_name=title,
                        rates=rates,
                        source_url=self.url,
                    )
                )

        if not results:
            raise EmptyParseError("No Jago rates were parsed from browser content", source_url=self.url)

        return results
