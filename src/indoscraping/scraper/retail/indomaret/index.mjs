import { writeFile } from 'fs/promises';

const BASE_URL = "https://ap-mc.klikindomaret.com/assets-klikidmgroceries/api/get/catalog-xpress/api/webapp";

const STORE_CONFIG = {
  storeCode: "TJKT",
  latitude: -6.1763897,
  longitude: 106.82667,
  mode: "DELIVERY",
  districtId: 141100100
};

const HEADERS = {
  "accept": "application/json, text/plain, */*",
  "accept-language": "en-US,en;q=0.9",
  "apps": "{\"app_version\":\"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36\",\"device_class\":\"browser|browser\",\"device_family\":\"none\",\"device_id\":\"e97a1210-e2aa-4908-9ddd-12d4ac58afa6\",\"os_name\":\"Linux\",\"os_version\":\"x86_64\"}",
  "page": "unpage",
  "priority": "u=1, i",
  "sec-ch-ua": "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\", \"Google Chrome\";v=\"138\"",
  "sec-ch-ua-mobile": "?0",
  "sec-ch-ua-platform": "\"Linux\"",
  "sec-fetch-dest": "empty",
  "sec-fetch-mode": "cors",
  "sec-fetch-site": "same-site",
  "x-correlation-id": "ce59e39f-5b13-4b89-a501-06dd911d67ac",
  "Referer": "https://www.klikindomaret.com/"
};

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function fetchCategories() {
  const params = new URLSearchParams(STORE_CONFIG);
  const url = `${BASE_URL}/category/meta?${params}`;
  
  await delay(1000); // Add delay
  const response = await fetch(url, { headers: HEADERS });
  
  const text = await response.text();
  console.log('Response status:', response.status);
  console.log('First 200 chars:', text.substring(0, 200));
  
  if (!response.ok || text.startsWith('<!DOCTYPE')) {
    throw new Error(`API returned HTML instead of JSON. Status: ${response.status}`);
  }
  
  return JSON.parse(text);
}

async function getProducts(page, metaCategories, categories, subCategories) {
  const params = new URLSearchParams({
    metaCategories,
    categories,
    page: page.toString(),
    size: "20",
    ...STORE_CONFIG
  });
  
  if (subCategories) {
    params.set('subCategories', subCategories);
  }
  
  const url = `${BASE_URL}/search/result?${params}`;
  console.log('Fetching:', Object.fromEntries(params));
  
  const response = await fetch(url, { headers: HEADERS });
  const data = await response.json();
  
  return data.data;
}

async function getAllProducts(metaCategories, categories, subCategories) {
  let page = 0;
  let arr = [];
  let products = await getProducts(page, metaCategories, categories, subCategories);
  
  while (products.content && products.content.length > 0) {
    arr.push(...products.content);
    page++;
    products = await getProducts(page, metaCategories, categories, subCategories);
  }
  
  // Add category info to each product
  for (const product of arr) {
    Object.assign(product, {
      metaCategories,
      categories,
      subCategories
    });
  }
  
  return arr;
}

async function main() {
  try {
    console.log('Fetching categories...');
    const response = await fetchCategories();
    
    if (!response.data) {
      console.error('No category data received');
      return;
    }
    
    console.log('Response received successfully.');
    
    let allArr = [];
    
    for (const data of response.data) {
      const categories = data.categories;
      console.log(`num categories of ${data.name}: ${categories.length}`);
      
      for (const category of categories) {
        const subCategories = category.subCategories;
        console.log(`num subCategories of ${category.name}: ${subCategories.length}`);
        
        if (subCategories.length === 0) {
          const resArr = await getAllProducts(data.permalink, category.permalink, null);
          console.log(`Retrieved ${resArr.length} products`);
          allArr.push(...resArr);
        }
        
        for (const subCategory of subCategories) {
          console.log(subCategory.name);
          const resArr = await getAllProducts(data.permalink, category.permalink, subCategory.permalink);
          console.log(`Retrieved ${resArr.length} products`);
          allArr.push(...resArr);
        }
      }
    }
    
    console.log(`\nTotal products collected: ${allArr.length}`);
    await writeFile('klikindomaret_products.json', JSON.stringify(allArr, null, 2));
    console.log('Products saved to klikindomaret_products.json');
    
  } catch (error) {
    console.error('Error:', error);
  }
}

main();