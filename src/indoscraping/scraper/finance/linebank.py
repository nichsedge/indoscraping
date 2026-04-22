import re

from bs4 import BeautifulSoup

from .base import BaseScraper, EmptyParseError, clean_text, find_table_after_label
from .models import BankData, RateDetail


class LineBankScraper(BaseScraper):
    mode = "http"

    def __init__(self):
        super().__init__("LINE Bank", "https://linebank.co.id/id/rates")

    def scrape_http(self, soup: BeautifulSoup) -> list[BankData]:
        text = clean_text(soup.get_text("\n", strip=True))
        savings_rates = self._parse_tabungan_rates(text)
        deposito_rates = self._parse_deposito_rates(text)

        results: list[BankData] = []
        if savings_rates:
            results.append(
                BankData(
                    bank_name=self.name,
                    product_name="LINE Bank Tabungan",
                    rates=savings_rates,
                    source_url=self.url,
                )
            )
        if deposito_rates:
            results.append(
                BankData(
                    bank_name=self.name,
                    product_name="Deposito Reguler",
                    rates=deposito_rates,
                    source_url=self.url,
                )
            )

        flexi_rates = self._parse_flexi_deposit_rates(text)
        if flexi_rates:
            results.append(
                BankData(
                    bank_name=self.name,
                    product_name="Flexi Deposit",
                    rates=flexi_rates,
                    source_url=self.url,
                )
            )

        if not results:
            raise EmptyParseError("LINE Bank rates page returned no data", source_url=self.url)

        return results

    def _parse_tabungan_rates(self, text: str) -> list[RateDetail]:
        section = find_table_after_label(text, "1) Tabungan Regular")
        matches = re.findall(
            r"(<\s*1 juta|1 Juta\s*-\s*10 Juta|>10 Juta\s*-\s*100 Juta|"
            r">100 Juta\s*-\s*1 Miliar|>\s*1 Miliar)\s+(\d+(?:[.,]\d+)?)%\s*p\.a",
            section,
            re.IGNORECASE,
        )
        rates: list[RateDetail] = []
        seen: set[tuple[str, float]] = set()
        for balance_range, rate in matches:
            parsed = float(rate.replace(",", "."))
            key = (clean_text(balance_range), parsed)
            if key in seen:
                continue
            seen.add(key)
            rates.append(RateDetail(tenor=key[0], rate=parsed))
        return rates

    def _parse_deposito_rates(self, text: str) -> list[RateDetail]:
        section = find_table_after_label(text, "4) Deposito Reguler")
        matches = re.findall(
            r"(1\s*-\s*2 Bulan|3\s*-\s*5 Bulan|6\s*-\s*12 Bulan)\s+"
            r"(\d+(?:[.,]\d+)?)%\s*p\.a",
            section,
            re.IGNORECASE,
        )
        return [
            RateDetail(tenor=clean_text(tenor), rate=float(rate.replace(",", ".")))
            for tenor, rate in matches
        ]

    def _parse_flexi_deposit_rates(self, text: str) -> list[RateDetail]:
        section = find_table_after_label(text, "5) Flexi Deposit")
        matches = re.findall(
            r"(1 Bulan|3 Bulan|6-11 Bulan|12 Bulan)\s+(\d+(?:[.,]\d+)?)%\s*p\.a",
            section,
            re.IGNORECASE,
        )
        return [
            RateDetail(tenor=clean_text(tenor), rate=float(rate.replace(",", ".")))
            for tenor, rate in matches
        ]
