from bs4 import BeautifulSoup
from typing import List
import re
from .base import BaseScraper
from .models import BankData, RateDetail

class KromScraper(BaseScraper):
    mode = "http"

    def __init__(self):
        super().__init__("Krom Bank", "https://krom.id/")

    def scrape_http(self, soup: BeautifulSoup) -> List[BankData]:
        body_text = soup.get_text(separator=" ")
        
        rates = []
        
        # Look for Deposito rate
        deposito_match = re.search(r"deposito hingga (\d+[,.]\d+)%\s*per", body_text, re.IGNORECASE)
        if deposito_match:
            rate = float(deposito_match.group(1).replace(",", "."))
            rates.append(RateDetail(tenor="Deposito Krom", rate=rate))
            
        # Look for Kantong Tabungan rate
        tabungan_match = re.search(r"bunga (\d+[,.]\d+)%\s*per tahun", body_text, re.IGNORECASE)
        if tabungan_match:
            rate = float(tabungan_match.group(1).replace(",", "."))
            rates.append(RateDetail(tenor="Tabungan Krom", rate=rate))
        elif "6%" in body_text:
            rates.append(RateDetail(tenor="Tabungan Krom", rate=6.0))
            
        if rates:
            return [BankData(
                bank_name=self.name,
                product_name="Krom Savings & Deposito",
                rates=rates,
                source_url=self.url
            )]
            
        return []
