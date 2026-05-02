# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "beautifulsoup4>=4.14.3",
#     "pandas>=3.0.2",
#     "playwright>=1.49.0",
#     "playwright-stealth>=1.0.6",
# ]
# ///

import asyncio
import json
import os
import re
import time

import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from playwright_stealth import Stealth


# ---------------------------------------------------------------------------
# Browser helpers
# ---------------------------------------------------------------------------

async def get_page(playwright):
    """Launch a stealth Chromium page matching index.mjs config."""
    browser = await playwright.chromium.launch(
        channel='chrome', 
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ],
    )
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    )
    
    # Stealth: Hide automation fingerprint
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    """)
    
    page = await context.new_page()
    # Keeping playwright-stealth as it's usually better than manual if it works, 
    # but aligning the core config first.
    await Stealth().apply_stealth_async(page)
    return browser, context, page


async def safe_goto(page, url: str, wait: float = 5.0):
    """Navigate and wait for page to load, matching index.mjs behavior."""
    await page.goto(url, wait_until="domcontentloaded", timeout=90_000)
    
    # Ensure product cards are rendered if it's a category/search page
    if "/c/" in url or "/cari/" in url or "/p/" in url:
        try:
            await page.wait_for_selector(".elf-product-card", timeout=30_000)
        except Exception:
            pass
            
    await asyncio.sleep(wait)


async def smooth_scroll(page, steps: int = 5, step_px: int = 800, delay: float = 1.5):
    """Scroll down gradually to trigger lazy-loading."""
    for _ in range(steps):
        await page.mouse.wheel(0, step_px)
        await asyncio.sleep(delay)


# ---------------------------------------------------------------------------
# Category discovery
# ---------------------------------------------------------------------------

async def get_categories(page) -> list[dict]:
    """Scrape Level-2 categories from the Blibli categories page."""
    try:
        await safe_goto(page, "https://www.blibli.com/categories", wait=8)
        content = await page.content()
    except Exception as e:
        print(f"Error fetching categories page: {e}")
        return []

    soup = BeautifulSoup(content, "html.parser")
    all_links = soup.select('a[class*="category__"]')

    hierarchy: list[dict] = []
    l2_categories: list[dict] = []

    current_l1 = current_l2 = current_l3 = current_l4 = None

    for link in all_links:
        name = link.get_text(strip=True)
        href = link.get("href", "")
        if href.startswith("/"):
            href = "https://www.blibli.com" + href

        classes = link.get("class", [])
        class_str = " ".join(classes)
        node = {"name": name, "url": href, "children": []}

        if "category__item-header" in class_str:
            current_l1 = node
            hierarchy.append(current_l1)
            current_l2 = current_l3 = current_l4 = None
        elif "level-2" in class_str and current_l1:
            current_l1["children"].append(node)
            current_l2 = node
            l2_categories.append({"name": name, "url": href, "parent": current_l1["name"], "level": 2})
            current_l3 = current_l4 = None
        elif "level-3" in class_str and current_l2:
            current_l2["children"].append(node)
            current_l3 = node
            current_l4 = None
        elif "level-4" in class_str and current_l3:
            current_l3["children"].append(node)
            current_l4 = node
        elif "level-5" in class_str and current_l4:
            current_l4["children"].append(node)

    output_dir = "data/blibli"
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "categories.json"), "w", encoding="utf-8") as f:
        json.dump(hierarchy, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(hierarchy)} main categories to {output_dir}/categories.json")
    print(f"Extracted {len(l2_categories)} Level 2 categories.")
    return l2_categories


# ---------------------------------------------------------------------------
# Product scraping
# ---------------------------------------------------------------------------

def _extract_clean_name(soup: BeautifulSoup, category_name: str) -> str:
    """Derive a clean display name from the page, falling back to the raw label."""
    clean_name = re.sub(r"^Hingga\s+\d+%\s*", "", category_name)

    breadcrumb = soup.find("div", class_="breadcrumb-wrapper") or soup.find(
        "ul", class_="breadcrumb"
    )
    if breadcrumb:
        items = breadcrumb.find_all(["a", "span"])
        if items:
            last = items[-1].get_text(strip=True)
            if last and len(last) < 30:
                return last
    else:
        active = soup.select_one("a.link-active")
        if active:
            return active.get_text(strip=True)

    return clean_name


def _parse_products(soup: BeautifulSoup, clean_name: str, category_url: str, level: int) -> list[dict]:
    """Extract product cards from parsed HTML."""
    boxes = soup.find_all("div", class_="product-list__card")
    if not boxes:
        boxes = soup.find_all("a", class_="elf-product-card")
    if not boxes:
        boxes = [
            a
            for a in soup.find_all("a", href=True)
            if "/p/" in a["href"] and a.find("span")
        ]

    print(f"Found {len(boxes)} products in '{clean_name}'")

    products = []
    for box in boxes:
        item: dict = {}
        try:
            # Get URL first as it helps with naming fallbacks
            product_url = ""
            if box.name == 'a' and box.get('href'):
                product_url = box['href']
            else:
                a_tag = box.find('a', href=True)
                if a_tag:
                    product_url = a_tag['href']
            
            if product_url and product_url.startswith('/'):
                product_url = 'https://www.blibli.com' + product_url
            
            item['productUrl'] = product_url

            # --- Name ---
            title_el = (
                box.find("span", class_="els-product__title")
                or box.find("div", class_="els-product__title")
                or box.find("div", class_="product-title-wrapper")
            )
            name = title_el.get_text(strip=True) if title_el else "N/A"
            
            # Fallback if name is N/A or looks like location (from index.mjs logic)
            if not name or name == "N/A" or name.startswith("Kota ") or name.startswith("Kab. "):
                if product_url:
                    match = re.search(r'/p/([^/?#]+)', product_url)
                    if match:
                        name = " ".join([w.capitalize() for w in match.group(1).split('-')])
            
            item["productName"] = name

            # --- Price ---
            price_el = (
                box.find("div", class_="els-product__fixed-price")
                or box.find("span", class_="els-product__fixed-price")
                or box.find("div", class_="price-container")
            )
            price_raw = "Rp 0"
            if price_el:
                price_raw = price_el.get_text(strip=True)
            else:
                rp_text = box.find(string=lambda t: "Rp" in str(t))
                if rp_text:
                    price_raw = rp_text.strip()
            
            item["priceRaw"] = price_raw
            
            # Numeric Price
            price_numeric = 0
            if price_raw:
                digits = re.sub(r'[^0-9]', '', price_raw)
                if digits:
                    price_numeric = int(digits)
            item['priceNumeric'] = price_numeric

            item["category"] = clean_name
            item["categoryLevel"] = level

            # --- Seller & Location ---
            seller_spans = box.find_all("span", class_="els-product__seller-name")
            seller_texts = [s.get_text(strip=True) for s in seller_spans if s.get_text(strip=True)]
            
            seller = "Unknown"
            location = "N/A"
            
            if len(seller_texts) >= 2:
                location = seller_texts[-1]
                seller = seller_texts[-2]
            elif seller_texts:
                seller = seller_texts[0]
                
            item["seller"] = seller.replace("Disediakan", "").strip()
            item["location"] = location

            # Installment (Extra Mile from index.mjs)
            full_text = box.get_text().lower()
            item['installmentAvailable'] = "Yes" if ("cicilan" in full_text or "0%" in full_text) else "No"

            # --- Sales & Rating ---
            sold_el = box.find("div", class_="els-product__sold")
            item["soldCount"] = sold_el.get_text(strip=True) if sold_el else "0"

            rating_wrapper = box.find("div", class_="els-product__rating-wrapper")
            rating = "0"
            if rating_wrapper:
                rating_val = rating_wrapper.find_next("span")
                if rating_val:
                    rating = rating_val.get_text(strip=True)
            
            # Fallback rating regex from index.mjs
            if rating == "0":
                rating_match = re.search(r'([0-5][,.][0-9])', full_text)
                if rating_match:
                    rating = rating_match.group(1)
            
            item["rating"] = rating

            products.append(item)
        except Exception:
            continue

    return products


async def scrape_category(page, category_url: str, category_name: str, level: int) -> list[dict]:
    """Navigate to a category page and scrape product listings."""
    print(f"\nScraping category: {category_name} -> {category_url}")
    await safe_goto(page, category_url, wait=8)
    await smooth_scroll(page, steps=5, step_px=800, delay=1.5)

    soup = BeautifulSoup(await page.content(), "html.parser")
    clean_name = _extract_clean_name(soup, category_name)
    return _parse_products(soup, clean_name, category_url, level)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    all_data: list[dict] = []

    async with async_playwright() as playwright:
        browser, context, page = await get_page(playwright)
        try:
            categories = await get_categories(page)

            # Use top 5 Level-2 categories for a quick test run
            test_categories = categories[:5]
            if not test_categories:
                print("\nNo categories found. Falling back to a hardcoded category.")
                test_categories = [
                    {
                        "name": "Handphone & Tablet",
                        "url": "https://www.blibli.com/c/handphone-tablet/54593",
                    }
                ]

            print(f"\nScraping {len(test_categories)} sample Level 2 categories:")
            for i, cat in enumerate(test_categories, 1):
                print(f"{i}. {cat['name']} (Parent: {cat.get('parent', 'N/A')})")

            for cat in test_categories:
                products = await scrape_category(page, cat["url"], cat["name"], cat.get("level", 2))
                all_data.extend(products)

        finally:
            await context.close()
            await browser.close()

    df = pd.DataFrame(all_data)
    if not df.empty:
        output_file = "blibli_holistic_test_data.csv"
        df.to_csv(output_file, index=False, encoding="utf-8")
        print(f"\nScraping finished. Data saved to {output_file}.")
        print(df.head())
    else:
        print("\nNo data collected.")


if __name__ == "__main__":
    asyncio.run(main())