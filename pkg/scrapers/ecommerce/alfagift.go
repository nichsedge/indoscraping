package ecommerce

import (
	"encoding/json"
	"fmt"
	"math/rand"
	"net/http"
	"net/url"
	"strconv"
	"time"

	"github.com/nichsedge/indoscraping/pkg/core"
)

type AlfagiftOptions struct {
	Query         string
	LimitProducts int
	OutputPath    string
	Latitude      string
	Longitude     string
}

func ScrapeAlfagift(opts AlfagiftOptions) ([]Product, error) {
	if opts.Query == "" {
		opts.Query = "minyak"
	}
	if opts.LimitProducts <= 0 {
		opts.LimitProducts = 20
	}
	if opts.OutputPath == "" {
		opts.OutputPath = "data/ecommerce/alfagift/latest.json"
	}
	if opts.Latitude == "" {
		opts.Latitude = "-6.1753924"
	}
	if opts.Longitude == "" {
		opts.Longitude = "106.8271528"
	}

	client := core.HTTPClient()

	setHeaders := func(req *http.Request) {
		trxID := strconv.FormatInt(rand.Int63n(9999999999), 10)
		req.Header.Set("accept", "application/json")
		req.Header.Set("accept-language", "id")
		req.Header.Set("devicemodel", "chrome")
		req.Header.Set("devicetype", "Web")
		req.Header.Set("fingerprint", "hNvsXdRTVhrqH5gGgHkI8OnvtKOGC8E/vIk1u9NwkKyV1i1yorHlQQr52UMqtait")
		req.Header.Set("latitude", opts.Latitude)
		req.Header.Set("longitude", opts.Longitude)
		req.Header.Set("priority", "u=1, i")
		req.Header.Set("Referer", "https://alfagift.id/")
		req.Header.Set("User-Agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36")
		req.Header.Set("trxid", trxID)
	}

	searchURL := fmt.Sprintf(
		"https://webcommerce-gw.alfagift.id/v2/products/searches?keyword=%s&start=0&limit=%d",
		url.QueryEscape(opts.Query),
		opts.LimitProducts,
	)

	req, err := http.NewRequest("GET", searchURL, nil)
	if err != nil {
		return nil, err
	}
	setHeaders(req)

	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch Alfagift searches API: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("alfagift API returned HTTP %d", resp.StatusCode)
	}

	var pData struct {
		Products []struct {
			ProductID    string  `json:"productId"`
			ProductName  string  `json:"productName"`
			BasePrice    float64 `json:"basePrice"`
			FinalPrice   float64 `json:"finalPrice"`
			ProductCode  string  `json:"productCode"`
			SKU          string  `json:"sku"`
			Stock        int     `json:"stock"`
			CategoryName string  `json:"categoryNameLvl0"`
			SellerAlias  string  `json:"sellerAlias"`
			URL          string  `json:"url"`
		} `json:"products"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&pData); err != nil {
		return nil, fmt.Errorf("failed to decode Alfagift JSON: %w", err)
	}

	var products []Product
	scrapedAt := time.Now().UTC().Format(time.RFC3339)

	for _, item := range pData.Products {
		if len(products) >= opts.LimitProducts {
			break
		}

		price := int(item.FinalPrice)
		if price == 0 {
			price = int(item.BasePrice)
		}

		prodURL := item.URL
		if prodURL == "" {
			code := item.SKU
			if code == "" {
				code = item.ProductID
			}
			prodURL = fmt.Sprintf("https://alfagift.id/p/%s", code)
		}

		seller := "Alfamart"
		if item.SellerAlias != "" {
			seller = fmt.Sprintf("Alfamart (%s)", item.SellerAlias)
		}

		category := item.CategoryName
		if category == "" {
			category = "Search"
		}

		products = append(products, Product{
			ProductName:  core.CleanText(item.ProductName),
			PriceRaw:     fmt.Sprintf("Rp %s", core.FormatIDR(price)),
			PriceNumeric: price,
			Seller:       seller,
			ProductURL:   prodURL,
			Category:     category,
			ScrapedAt:    scrapedAt,
		})
	}

	historyPath := fmt.Sprintf("data/ecommerce/alfagift/history/%s.json", time.Now().Format("2006-01-02"))
	meta := map[string]interface{}{
		"scraper":     "alfagift-go-searches-api",
		"items_count": len(products),
		"scraped_at":  scrapedAt,
		"query":       opts.Query,
	}

	if err := core.WriteLatestAndHistory(opts.OutputPath, historyPath, products, meta); err != nil {
		return products, err
	}

	return products, nil
}
