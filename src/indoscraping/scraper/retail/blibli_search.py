import argparse
import os
import json
import time
import random
from datetime import datetime
from playwright.sync_api import sync_playwright

def scrape_blibli(query, output_path, output_format="json", max_retries=3, initial_delay=2.0):
    """Scrapes Blibli search results using system-installed Chrome via Playwright."""
    print(f"\n🚀 [START] Scraping Blibli for: '{query}'")
    
    products = []
    
    with sync_playwright() as p:
        for attempt in range(max_retries):
            try:
                # Launch system Chrome channel
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
                
                # Hide automation fingerprint
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
                break # Success, exit retry loop
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
                
    # Save the output
    if products:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        if output_format == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(products, f, ensure_ascii=False, indent=2)
        elif output_format == "jsonl":
            with open(output_path, "w", encoding="utf-8") as f:
                for p in products:
                    f.write(json.dumps(p, ensure_ascii=False) + '\n')
        elif output_format == "csv":
            import csv
            keys = ["productName", "category", "priceRaw", "priceNumeric", "rating", "soldCount", "seller", "installmentAvailable", "productUrl"]
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                for p in products:
                    row = {k: p.get(k, "") for k in keys}
                    writer.writerow(row)
                    
        print(f"✅ [SUCCESS] Captured {len(products)} products.")
    else:
        print("⚠️ [WARN] No data collected.")
        
    return products

def main():
    default_date = datetime.now().strftime("%Y-%m-%d")
    
    parser = argparse.ArgumentParser(description="Blibli Search Scraper using Playwright")
    parser.add_argument("--query", default="xiaomi note 15 pro", help="Search query (default: 'xiaomi note 15 pro')")
    parser.add_argument("--date", default=default_date, help="Date to scrape in YYYY-MM-DD format (default: today)")
    parser.add_argument("--output", default="data/retail/blibli/latest.json", help="Output path for the latest scraping results")
    parser.add_argument("--format", choices=["json", "jsonl", "csv"], default="json", help="Output format (default: json)")
    args = parser.parse_args()
    
    # Adjust output file extension based on format
    output_path = args.output
    if args.format != "json":
        base, _ = os.path.splitext(output_path)
        output_path = f"{base}.{args.format}"
        
    products = scrape_blibli(
        query=args.query,
        output_path=output_path,
        output_format=args.format
    )
    
    if products:
        # Save historical snapshot of the merged final output
        date_str = args.date
        history_ext = args.format
        history_path = f"data/retail/blibli/history/{date_str}.{history_ext}"
        os.makedirs(os.path.dirname(history_path), exist_ok=True)
        
        # Read/Copy content directly to historical file
        try:
            if args.format == "json":
                with open(output_path, "r", encoding="utf-8") as f:
                    final_merged = json.load(f)
            else:
                with open(output_path, "rb") as f:
                    final_merged_content = f.read()
        except Exception:
            final_merged = products
            final_merged_content = None
            
        if args.format == "json" or not final_merged_content:
            with open(history_path, "w", encoding="utf-8") as f:
                json.dump(final_merged, f, ensure_ascii=False, indent=2)
        else:
            with open(history_path, "wb") as f:
                f.write(final_merged_content)
                
        print(f"Saved latest to {output_path}")
        print(f"Saved historical snapshot to {history_path}")
    else:
        print("No products crawled or error occurred.")

if __name__ == "__main__":
    main()
