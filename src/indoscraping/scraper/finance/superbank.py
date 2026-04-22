from playwright.async_api import Page
from typing import List
import re
from .base import BaseScraper
from .models import BankData, RateDetail

class SuperbankScraper(BaseScraper):
    mode = "browser"

    def __init__(self):
        super().__init__("Superbank", "https://superbank.id/")

    async def scrape_browser(self, page: Page, html: str) -> List[BankData]:
        # Using evaluate because the structure might be complex
        body_text = await page.evaluate("document.body.innerText")
        
        rates = []
        
        # Deposito is extracted from the specific page later, but if we wanted the "up to" rate we could grab it here.
        # We will grab the detailed tenors below.
            
        # Look for Celengan rate
        celengan_match = re.search(r"Celengan by Superbank.*?(\d+(?:[,.]\d+)?)%\s*p\.a", body_text, re.IGNORECASE | re.DOTALL)
        if celengan_match:
            rate = float(celengan_match.group(1).replace(",", "."))
            rates.append(RateDetail(tenor="Celengan", rate=rate))
            
        # Look for OVO Nabung rate
        ovo_match = re.search(r"OVO Nabung.*?(\d+(?:[,.]\d+)?)%\s*p\.a", body_text, re.IGNORECASE | re.DOTALL)
        if ovo_match:
            rate = float(ovo_match.group(1).replace(",", "."))
            rates.append(RateDetail(tenor="OVO Nabung", rate=rate))

        # Navigate to Deposito page to get the table
        try:
            await page.goto("https://www.superbank.id/produk-layanan/tabungan/deposito", wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            table_text = await page.evaluate('''() => {
                let t = document.querySelector("table");
                return t ? t.innerText : "";
            }''')
            
            if table_text:
                lines = table_text.split("\n")
                tenors = []
                for line in lines:
                    if "7 Hari" in line and "1 Bulan" in line:
                        tenors = line.split("\t")
                    elif "Rp500.000" in line and tenors:
                        vals = line.split("\t")
                        for i in range(1, min(len(vals), len(tenors))):
                            match = re.search(r"(\d+(?:[,.]\d+)?)%", vals[i])
                            if match:
                                rate = float(match.group(1).replace(",", "."))
                                rates.append(RateDetail(tenor=f"Deposito {tenors[i].strip()}", rate=rate))
        except Exception as e:
            print(f"Failed to fetch Superbank Deposito details: {e}")
            
        if rates:
            return [BankData(
                bank_name=self.name,
                product_name="Superbank Savings & Deposito",
                rates=rates,
                source_url=self.url
            )]
            
        return []
