import fs from 'fs';

const headers = {
  "accept": "application/json",
  "accept-language": "id",
  "devicemodel": "chrome",
  "devicetype": "Web",
  "fingerprint": "hNvsXdRTVhrqH5gGgHkI8OnvtKOGC8E/vIk1u9NwkKyV1i1yorHlQQr52UMqtait",
  "latitude": "0",
  "longitude": "0",
  "priority": "u=1, i",
  "sec-ch-ua": "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\", \"Google Chrome\";v=\"138\"",
  "sec-ch-ua-mobile": "?0",
  "sec-ch-ua-platform": "\"Linux\"",
  "sec-fetch-dest": "empty",
  "sec-fetch-mode": "cors",
  "sec-fetch-site": "same-site",
  "trxid": Math.floor(Math.random() * 10000000000).toString(),
  "Referer": "https://alfagift.id/"
};

async function getCategories() {
  const requestHeaders = {
    ...headers,
    "trxid": Math.floor(Math.random() * 10000000000).toString()
  };
  
  const response = await fetch("https://webcommerce-gw.alfagift.id/v2/categories", { headers: requestHeaders });
  const data = await response.json();
  
  const subCategoryIds = [];
  data.categories.forEach(category => {
    if (category.subCategories) {
      category.subCategories.forEach(sub => {
        subCategoryIds.push(sub.categoryId);
      });
    }
  });
  
  return subCategoryIds;
}

async function getProducts(categoryId, page = 0, limit = 60) {  
  const start = page;
  const url = `https://webcommerce-gw.alfagift.id/v2/products/category/${categoryId}?sortDirection=asc&start=${start}&limit=${limit}`;
  
  // Generate new trxid for each request
  const requestHeaders = {
    ...headers,
    "trxid": Math.floor(Math.random() * 10000000000).toString()
  };
  
  const response = await fetch(url, { headers: requestHeaders });
  return await response.json();
}

async function scrapeAllProducts() {
  const categoryIds = await getCategories();
  const allProducts = [];
  
  for (const categoryId of categoryIds) {
    console.log(`Scraping category: ${categoryId}`);
    
    // Get first page to determine total pages
    const firstPage = await getProducts(categoryId);
    const totalPages = firstPage.totalPage;
    
    // Collect products from all pages
    for (let page = 0; page <= totalPages; page++) {
      const data = page === 0 ? firstPage : await getProducts(categoryId, page);
      allProducts.push(...data.products);
      console.log(`  Page ${page}/${totalPages}: ${data.products.length} products`);
    }
    
    // Small delay to avoid rate limiting
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  
  // Export to JSON
  fs.writeFileSync('alfagift_products.json', JSON.stringify(allProducts, null, 2));
  console.log(`Total products scraped: ${allProducts.length}`);
}

scrapeAllProducts().catch(console.error);