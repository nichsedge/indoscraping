/**
 * Blibli Category Hierarchy Scraper
 * =================================
 * 
 * This script extracts the complete hierarchical category tree from Blibli.
 * Useful for mapping out the platform's product taxonomy for structured crawling.
 */

import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

async function scrapeCategories() {
  console.log('🚀 Starting Blibli Category Scraper...');
  
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

  // Hide automation fingerprint
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
  });
  const url = 'https://www.blibli.com/categories';
  
  console.log(`🔗 Navigating to ${url}`);
  
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 });
    
    // Wait for the main category headers to render
    console.log('⏳ Waiting for category elements...');
    await page.waitForSelector('.category__item-header', { timeout: 30000 });
    
    console.log('📊 Extracting category hierarchy...');
    
    const hierarchy = await page.evaluate(() => {
      const results = [];
      // Grab all level tags in order
      const allLinks = Array.from(document.querySelectorAll('a[class*="category__"]'));
      
      let currentL1 = null;
      let currentL2 = null;
      let currentL3 = null;
      let currentL4 = null;

      allLinks.forEach(link => {
        const name = link.innerText.trim();
        const url = link.href;
        const className = link.className;

        const node = { name, url, children: [] };

        if (className.includes('category__item-header')) {
          currentL1 = node;
          results.push(currentL1);
          currentL2 = currentL3 = currentL4 = null;
        } else if (className.includes('level-2') && currentL1) {
          currentL1.children.push(node);
          currentL2 = node;
          currentL3 = currentL4 = null;
        } else if (className.includes('level-3') && currentL2) {
          currentL2.children.push(node);
          currentL3 = node;
          currentL4 = null;
        } else if (className.includes('level-4') && currentL3) {
          currentL3.children.push(node);
          currentL4 = node;
        } else if (className.includes('level-5') && currentL4) {
          currentL4.children.push(node);
        }
      });
      
      return results;
    });

    // Save results
    const outputDir = path.join(process.cwd(), 'data', 'blibli');
    if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });
    
    const outputPath = path.join(outputDir, 'categories.json');
    fs.writeFileSync(outputPath, JSON.stringify(hierarchy, null, 2));
    
    console.log(`✅ Success! Extracted ${hierarchy.length} main categories.`);
    console.log(`📁 Saved to: ${outputPath}`);
    
    await browser.close();
    return hierarchy;

  } catch (error) {
    console.error(`❌ Error: ${error.message}`);
    await browser.close();
    return [];
  }
}

scrapeCategories().catch(console.error);
