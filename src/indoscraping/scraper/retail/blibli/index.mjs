/**
 * Krom Bank: Blibli Scraper Prototype (Final Version)
 * =================================================
 * 
 * Developed for: Data Quality Engineer Role - Case Study
 * 
 * This prototype demonstrates a robust e-commerce crawler using Node.js and Playwright.
 * It captures mandatory product data and adds business intelligence layers crucial
 * for consumer financing decisions at Krom Bank.
 * 
 * Business Rationale for Extra Fields:
 * ------------------------------------
 * 1. Rating & Sold Count: Validates asset quality and market liquidity.
 * 2. Seller Trust: Identifies Official Stores for partnership opportunities.
 * 3. Installment Status: Monitors competitive financing landscapes (0% BNPL).
 */

import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { createObjectCsvWriter } from 'csv-writer';

async function scrapeBlibli(query = 'xiaomi note 15 pro') {
  console.log(`\n🚀 [START] Scraping Blibli for: "${query}"`);
  
  // Launching system-installed Chrome with stealth settings
  const browser = await chromium.launch({ 
    channel: 'chrome', 
    headless: true,
    args: ['--disable-blink-features=AutomationControlled', '--no-sandbox']
  });
  
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    viewport: { width: 1920, height: 1080 }
  });
  
  const page = await context.newPage();
  
  // Stealth: Hide automation fingerprint
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
  });

  const searchUrl = `https://www.blibli.com/cari/${encodeURIComponent(query)}`;
  console.log(`🔗 [NAVIGATE] ${searchUrl}`);
  
  try {
    // Navigate and wait for initial content
    await page.goto(searchUrl, { waitUntil: 'domcontentloaded', timeout: 90000 });
    
    // Ensure product cards are rendered
    console.log('⏳ [WAIT] Waiting for product cards to render...');
    const cardSelector = '.elf-product-card';
    await page.waitForSelector(cardSelector, { timeout: 60000 });
    
    // Small scroll to trigger lazy-loaded images/prices
    await page.evaluate(() => window.scrollBy(0, 1500));
    await page.waitForTimeout(2000);

    console.log('📊 [EXTRACT] Processing data from DOM...');
    
    const products = await page.evaluate((categoryName) => {
      const items = Array.from(document.querySelectorAll('.elf-product-card'));
      
      return items.map((item) => {
        try {
          const text = item.innerText || '';
          const url = item.href || '';
          
          // --- PRODUCT NAME EXTRACTION ---
          // Prioritize specific selectors, fallback to URL slug if masked by location badges
          let name = item.querySelector('[class*="name-text"]')?.innerText?.trim() || 
                     item.querySelector('[class*="product-title"]')?.innerText?.trim();
          
          if (!name || name === 'N/A' || name.startsWith('Kota ') || name.startsWith('Kab. ')) {
            const urlMatch = url.match(/\/p\/([^/?#]+)/);
            if (urlMatch) {
              name = urlMatch[1].split('-').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
            }
          }

          // --- MANDATORY FIELDS ---
          const priceMatch = text.match(/Rp\s?([0-9.]+)/);
          const priceRaw = priceMatch ? priceMatch[0] : 'Rp 0';
          const priceNumeric = parseInt(priceRaw.replace(/[^0-9]/g, '')) || 0;
          
          // --- EXTRA MILE FIELDS ---
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
    }, query);

    await browser.close();
    return products;

  } catch (error) {
    console.error(`❌ [ERROR] Scraping failed: ${error.message}`);
    await browser.close();
    return [];
  }
}

async function saveResults(data) {
  if (data.length === 0) {
    console.log('⚠️ [WARN] No data collected.');
    return;
  }

  const dataDir = path.join(process.cwd(), 'data', 'blibli');
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
  }

  // Save as JSON
  const jsonPath = path.join(dataDir, 'blibli_results.json');
  fs.writeFileSync(jsonPath, JSON.stringify(data, null, 2));

  // Save as CSV
  const csvPath = path.join(dataDir, 'blibli_results.csv');
  const csvWriter = createObjectCsvWriter({
    path: csvPath,
    header: [
      { id: 'productName', title: 'Product Name' },
      { id: 'category', title: 'Category' },
      { id: 'priceRaw', title: 'Price (Raw)' },
      { id: 'priceNumeric', title: 'Price (Numeric)' },
      { id: 'rating', title: 'Rating' },
      { id: 'soldCount', title: 'Sold Count' },
      { id: 'seller', title: 'Seller' },
      { id: 'installmentAvailable', title: 'Installment' },
      { id: 'productUrl', title: 'URL' }
    ]
  });

  await csvWriter.writeRecords(data);
  console.log(`✅ [SUCCESS] Captured ${data.length} products.`);
  console.log(`📁 JSON: ${jsonPath}`);
  console.log(`📁 CSV: ${csvPath}`);
}

async function main() {
  const query = 'xiaomi note 15 pro';
  const results = await scrapeBlibli(query);
  await saveResults(results);
}

main().catch(console.error);
