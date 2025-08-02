

const fs = require('fs');

async function scrapeNarasi() {
  const apiUrl = 'https://gateway.narasi.tv/core/api/tags/special/1';

  try {
    const response = await fetch(apiUrl);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();

    // Save the raw JSON response to a file
    fs.writeFile('response.json', JSON.stringify(data, null, 2), (err) => {
      if (err) {
        console.error('Error writing JSON to file:', err);
      } else {
        console.log('Raw JSON response saved to response.json');
      }
    });

    console.log('--- Articles from Narasi.tv API ---');
    if (data.data.articles && data.data.articles.length > 0) {
      data.data.articles.forEach((article, index) => {
        console.log(`\nArticle ${index + 1}:`);
        console.log(`Title: ${article.title}`);
        console.log(`Short Description: ${article.short}`);
        console.log(`Publish Date: ${article.publishDate}`);
        console.log(`Link: https://narasi.tv/${article.slug}`);
      });
    } else {
      console.log('No articles found.');
    }

  } catch (error) {
    console.error('Error scraping Narasi.tv API:', error);
  }
}

scrapeNarasi();
