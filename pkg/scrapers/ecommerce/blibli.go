package ecommerce

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/nichsedge/indoscraping/pkg/core"
)

type BlibliOptions struct {
	Query         string
	LimitProducts int
	OutputPath    string
	TimeoutSec    int
}

func ScrapeBlibli(opts BlibliOptions) ([]Product, error) {
	if opts.Query == "" {
		opts.Query = "susu"
	}
	if opts.LimitProducts <= 0 {
		opts.LimitProducts = 20
	}
	if opts.OutputPath == "" {
		opts.OutputPath = "data/ecommerce/blibli/latest.json"
	}
	if opts.TimeoutSec <= 0 {
		opts.TimeoutSec = 30
	}

	apiURL := fmt.Sprintf(
		"https://www.blibli.com/backend/search/products?page=1&start=0&searchTerm=%s&intent=false&merchantSearch=true&multiCategory=true&customUrl=&sort=0&channelId=mobile-web&catIntent=false&showFacet=false",
		url.QueryEscape(opts.Query),
	)

	req, err := http.NewRequest("GET", apiURL, nil)
	if err != nil {
		return nil, err
	}

	req.Header.Set("accept", "application/json, text/plain, */*")
	req.Header.Set("accept-language", "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7")
	req.Header.Set("user-agent", "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36")
	req.Header.Set("referer", "https://www.blibli.com/")
	req.Header.Set("origin", "https://www.blibli.com")
	req.Header.Set("sec-fetch-dest", "empty")
	req.Header.Set("sec-fetch-mode", "cors")
	req.Header.Set("sec-fetch-site", "same-origin")

	client := &http.Client{
		Transport: core.DefaultTransport,
		Timeout:   time.Duration(opts.TimeoutSec) * time.Second,
	}
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch Blibli search API: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("blibli API returned HTTP %d", resp.StatusCode)
	}

	var blibliResp struct {
		Code   int    `json:"code"`
		Status string `json:"status"`
		Data   struct {
			Products []struct {
				ID           string `json:"id"`
				Name         string `json:"name"`
				MerchantName string `json:"merchantName"`
				Location     string `json:"location"`
				Brand        string `json:"brand"`
				URL          string `json:"url"`
				Price        struct {
					PriceDisplay string  `json:"priceDisplay"`
					MinPrice     float64 `json:"minPrice"`
					SalePrice    float64 `json:"salePrice"`
				} `json:"price"`
				RootCategory struct {
					Name string `json:"name"`
				} `json:"rootCategory"`
			} `json:"products"`
		} `json:"data"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&blibliResp); err != nil {
		return nil, fmt.Errorf("failed to decode Blibli JSON: %w", err)
	}

	var products []Product
	scrapedAt := time.Now().UTC().Format(time.RFC3339)

	for _, item := range blibliResp.Data.Products {
		if len(products) >= opts.LimitProducts {
			break
		}

		priceNum := int(item.Price.MinPrice)
		if priceNum == 0 {
			priceNum = int(item.Price.SalePrice)
		}

		priceRaw := item.Price.PriceDisplay
		if priceRaw == "" {
			priceRaw = fmt.Sprintf("Rp %s", core.FormatIDR(priceNum))
		}

		prodURL := item.URL
		if !strings.HasPrefix(prodURL, "http") {
			prodURL = "https://www.blibli.com" + prodURL
		}

		seller := item.MerchantName
		if item.Location != "" {
			seller = fmt.Sprintf("%s (%s)", seller, item.Location)
		}

		category := item.RootCategory.Name
		if category == "" {
			category = "Search"
		}

		products = append(products, Product{
			ProductName:  core.CleanText(item.Name),
			PriceRaw:     priceRaw,
			PriceNumeric: priceNum,
			Seller:       seller,
			ProductURL:   prodURL,
			Category:     category,
			ScrapedAt:    scrapedAt,
		})
	}

	historyPath := fmt.Sprintf("data/ecommerce/blibli/history/%s.json", time.Now().Format("2006-01-02"))
	meta := map[string]interface{}{
		"scraper":     "blibli-go-mobile-api",
		"items_count": len(products),
		"scraped_at":  scrapedAt,
		"query":       opts.Query,
	}

	if err := core.WriteLatestAndHistory(opts.OutputPath, historyPath, products, meta); err != nil {
		return products, err
	}

	return products, nil
}
