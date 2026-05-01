"""
Krom Bank: Tokopedia Scraper (Advanced GQL Version)
==================================================

This version uses httpx with HTTP/2 support to bypass Tokopedia's 
connection-level blocking of standard Python requests.

Author: Antigravity
Date: 2026-05-01
"""

import asyncio
import json
import os
import pandas as pd
import httpx
from rich.console import Console
from rich.table import Table

console = Console()

async def scrape_tokopedia_gql(query="iphone 15", rows=20):
    """
    Fetches product data using HTTP/2 to avoid connection resets.
    """
    url = "https://gql.tokopedia.com/graphql/SearchProductV5Query"
    
    # Advanced headers to mimic a real browser perfectly
    headers = {
        "authority": "gql.tokopedia.com",
        "accept": "*/*",
        "accept-language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "content-type": "application/json",
        "origin": "https://www.tokopedia.com",
        "referer": f"https://www.tokopedia.com/search?q={query.replace(' ', '+')}",
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Linux"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "x-source": "tokopedia-lite",
        "x-tkpd-ak-gql-source": "zeus",
        "x-device": "desktop-0.0",
    }

    gql_query = """
    query SearchProductV5Query($params: String!) {
      searchProductV5(params: $params) {
        data {
          products {
            id
            name
            url
            price {
              text
              number
            }
            shop {
              id
              name
              city
              tier
            }
            rating
            countReview
          }
        }
      }
    }
    """

    payload = [
        {
            "operationName": "SearchProductV5Query",
            "variables": {"params": f"q={query}&source=search&st=product&rows={rows}&page=1&ob=23"},
            "query": gql_query
        }
    ]

    console.print(f"[bold green]Fetching Tokopedia data via HTTP/2 GQL...[/bold green]")
    
    try:
        # Using HTTP/2 is critical for bypassing Tokopedia's connection-level blocks
        async with httpx.AsyncClient(http2=True, timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            products_raw = data[0].get('data', {}).get('searchProductV5', {}).get('data', {}).get('products', [])
            
            if not products_raw:
                console.print("[bold red]No products found. Tokopedia might be serving a challenge page.[/bold red]")
                return []

            products = []
            for p in products_raw:
                products.append({
                    "Product Name": p.get('name'),
                    "Category": query.title(),
                    "Price (Raw)": p.get('price', {}).get('text'),
                    "Price (Numeric)": p.get('price', {}).get('number'),
                    "Rating": p.get('rating'),
                    "Sold Count": p.get('countReview'),
                    "Store Name": p.get('shop', {}).get('name'),
                    "Location": p.get('shop', {}).get('city'),
                    "Store Tier": p.get('shop', {}).get('tier')
                })
                
            return products

    except Exception as e:
        console.print(f"[bold red]Advanced GQL Request Failed:[/bold red] {e}")
        return []

async def main():
    console.print("[bold magenta]==========================================[/bold magenta]")
    console.print("[bold white] Krom Bank: Tokopedia Advanced Scraper [/bold white]")
    console.print("[bold magenta]==========================================[/bold magenta]\n")
    
    query = "iphone 15"
    products = await scrape_tokopedia_gql(query)
    
    if products:
        # Save results
        os.makedirs("data", exist_ok=True)
        df = pd.DataFrame(products)
        df.to_csv("data/tokopedia_results.csv", index=False)
        df.to_json("data/tokopedia_results.json", orient="records", indent=4)
        
        console.print(f"[bold green]Successfully saved {len(products)} products to data/tokopedia_results.csv[/bold green]")
        
        # Show small summary
        table = Table(title="Scraped Data Preview")
        table.add_column("Product", style="cyan")
        table.add_column("Price", style="green")
        for p in products[:3]:
            table.add_row(p['Product Name'][:40] + "...", p['Price (Raw)'])
        console.print(table)
    else:
        console.print("[bold red]Failed to scrape Tokopedia. They are actively blocking this IP.[/bold red]")

if __name__ == "__main__":
    asyncio.run(main())
