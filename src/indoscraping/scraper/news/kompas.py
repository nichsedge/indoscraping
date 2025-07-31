import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

BASE_URL = "https://indeks.kompas.com/"
DATE = "2025-07-23"

def get_categories():
    response = requests.get(BASE_URL)
    soup = BeautifulSoup(response.text, "html.parser")
    select = soup.find("select", class_="form__select dropdown_sites")
    categories = [option.get("value") for option in select.find_all("option") if option.get("value") != "all"]
    return list(set(categories))

def get_article_links(category, date):
    page = 1
    links = []
    
    while True:
        url = f"{BASE_URL}?site={category}&date={date}&page={page}"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        articles = soup.find_all("div", class_="articleItem")
        
        if not articles:
            break
            
        for article in articles:
            a_tag = article.find("a", class_="article-link")
            if a_tag and a_tag.get("href"):
                links.append(a_tag["href"])
        
        page += 1
    
    return links

def scrape_kompas_article(url):
    try:
        soup = BeautifulSoup(requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).content, "html.parser")
        
        title = soup.title.get_text(strip=True) if soup.title else ""
        
        raw_date = soup.select_one(".read__time")
        date = raw_date.get_text(strip=True).split("-", 1)[-1].strip() if raw_date else ""
        
        journalists = [j.get_text(strip=True).rstrip(",") for j in soup.select(".credit-title-nameEditor")]
        
        tags = [t.get_text(strip=True) for t in soup.select("ul.tag__article__wrap li a")]
        
        img = soup.select_one(".cover-photo img")
        image_url = img["src"] if img else ""
        
        paragraphs = soup.select(".read__content p")
        content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        
        return {
            "url": url,
            "title": title,
            "date": date,
            "journalists": journalists,
            "tags": tags,
            "image_url": image_url,
            "content": content
        }
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

def main():
    categories = get_categories()
    all_articles = []
    
    for category in categories[:1]:
        print(f"Processing category: {category}")
        article_links = get_article_links(category, DATE)
        
        for link in article_links[:2]:
            article_data = scrape_kompas_article(link)
            if article_data:
                article_data["category"] = category
                all_articles.append(article_data)
    
    # Export to JSON
    filename = f"kompas_articles_{DATE}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)
    
    print(f"Exported {len(all_articles)} articles to {filename}")

if __name__ == "__main__":
    main()