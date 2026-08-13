import argparse
import os
import json
import time
import random
from datetime import datetime
from playwright.sync_api import sync_playwright
from indoscraping_core import write_latest_and_history, collect_lineage, validate_and_clean_ecommerce, detect_schema_drift, EcommerceProductModel

def scrape_blibli(query, output_path, output_format="json", max_retries=3, initial_delay=2.0):
    """Scrapes Blibli search results using system-installed Chrome via Playwright."""
    print(f"\n🚀 [START] Scraping Blibli for: '{query}'")
    
    products = []
    
    with sync_playwright() as p:
        for attempt in range(max_retries):
            try:
                browser = p.chromium.launch(
                    channel="chrome",
                    headless=True,
                    args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
                )
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080}
                )
                page = context.new_page()
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined })")
                
                search_url = f"https://www.blibli.com/cari/{query}"
                print(f"🔗 [NAVIGATE] {search_url}")
                
                page.goto(search_url, wait_until='domcontentloaded', timeout=90000)
                print('⏳ [WAIT] Waiting for product cards to render...')
                card_selector = '.elf-product-card'
                page.wait_for_selector(card_selector, timeout=60000)
                
                page.evaluate("window.scrollBy(0, 1500)")
                page.wait_for_timeout(2000)
                
                print('📊 [EXTRACT] Evaluating DOM...')
                products = page.evaluate(r"""(categoryName) => {
                  const items = Array.from(document.querySelectorAll('.elf-product-card'));
                  return items.map((item) => {
                    try {
                      const text = item.innerText || '';
                      const url = item.href || '';
                      
                      let name = item.querySelector('[class*="name-text"]')?.innerText?.trim() || 
                                 item.querySelector('[class*="product-title"]')?.innerText?.trim();
                      
                      if (!name || name === 'N/A' || name.startsWith('Kota ') || name.startsWith('Kab. ')) {
                        const urlMatch = url.match(/\/p\/([^/?#]+)/);
                        if (urlMatch) {
                          name = urlMatch[1].split('-').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
                        }
                      }

                      const priceMatch = text.match(/Rp\s?([0-9.]+)/);
                      const priceRaw = priceMatch ? priceMatch[0] : 'Rp 0';
                      const priceNumeric = parseInt(priceRaw.replace(/[^0-9]/g, '')) || 0;
                      
                      const ratingMatch = text.match(/([0-5][,.][0-9])/);
                      const rating = ratingMatch ? ratingMatch[1] : '0';
                      
                      const soldMatch = text.match(/Terjual\s+([0-9,.]+k?)/i);
                      const soldCount = soldMatch ? soldMatch[1] : '0';
                      
                      const seller = item.querySelector('[class*="seller"], [class*="merchant"]')?.innerText?.split('\n')[0] || 'Unknown';
                      const hasInstallment = text.toLowerCase().includes('cicilan') || text.toLowerCase().includes('0%');

                      return {
                        productName: name,
                        category: categoryName,
                        priceRaw: priceRaw,
                        priceNumeric: priceNumeric,
                        rating: rating,
                        soldCount: soldCount,
                        seller: seller.replace('Disediakan', '').trim(),
                        installmentAvailable: hasInstallment ? 'Yes' : 'No',
                        productUrl: url
                      };
                    } catch (e) {
                      return null;
                    }
                  }).filter(p => p !== null && p.productName);
                }""", query)
                
                browser.close()
                break
            except Exception as e:
                try:
                    browser.close()
                except Exception:
                    pass
                if attempt == max_retries - 1:
                    print(f"❌ [ERROR] Scraping failed after {max_retries} attempts: {e}")
                    raise e
                delay = initial_delay * (2 ** attempt) + random.uniform(0.1, 0.5)
                print(f"  [Attempt {attempt + 1}/{max_retries}] Playwright failed: {e}. Retrying in {delay:.2f}s...")
                time.sleep(delay)
                
    if products:
        products = validate_and_clean_ecommerce(products)
        detect_schema_drift(products, EcommerceProductModel, "blibli", strict_raise=False)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        if output_format == "json":
            meta = collect_lineage("blibli-search")
            write_latest_and_history(latest_path=output_path, history_path=None, payload=products, meta=meta)
        print(f"✅ [SUCCESS] Captured {len(products)} products.")
    else:
        print("⚠️ [WARN] No data collected.")
        
    return products
