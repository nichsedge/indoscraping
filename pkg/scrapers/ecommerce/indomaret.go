package ecommerce

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"time"

	"github.com/nichsedge/indoscraping/pkg/core"
)

// IndomaretOptions defines configurable parameters for Klik Indomaret scraping.
type IndomaretOptions struct {
	Query         string
	LimitProducts int
	OutputPath    string
	StoreCode     string
	Latitude      string
	Longitude     string
	DistrictID    string
}

type indomaretResponse struct {
	Status  string `json:"status"`
	Message string `json:"message"`
	Data    struct {
		Content []struct {
			ProductID   int     `json:"productId"`
			PLU         string  `json:"plu"`
			Permalink   string  `json:"permalink"`
			ProductName string  `json:"productName"`
			Price       float64 `json:"price"`
			FinalPrice  float64 `json:"finalPrice"`
			BrandName   string  `json:"brandName"`
			ImageURL    string  `json:"imageUrl"`
			UOM         string  `json:"uom"`
		} `json:"content"`
	} `json:"data"`
}

func generateDeviceID() string {
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}

// ScrapeIndomaret extracts live grocery catalog and prices from Klik Indomaret API.
func ScrapeIndomaret(opts IndomaretOptions) ([]Product, error) {
	if opts.Query == "" {
		opts.Query = "susu"
	}
	if opts.LimitProducts <= 0 {
		opts.LimitProducts = 10
	}
	if opts.OutputPath == "" {
		opts.OutputPath = "data/ecommerce/indomaret/latest.json"
	}
	if opts.StoreCode == "" {
		opts.StoreCode = "TJKT"
	}
	if opts.Latitude == "" {
		opts.Latitude = "-6.1763897"
	}
	if opts.Longitude == "" {
		opts.Longitude = "106.82667"
	}
	if opts.DistrictID == "" {
		opts.DistrictID = "141100100"
	}

	baseURL := "https://ap-mc.klikindomaret.com/assets-klikidmgroceries/api/get/catalog-xpress/api/webapp/search/result"
	var allProducts []Product
	page := 0
	pageSize := 20
	if opts.LimitProducts < pageSize {
		pageSize = opts.LimitProducts
	}

	client := &http.Client{
		Timeout: 15 * time.Second,
	}

	appsJSON := fmt.Sprintf(`{"app_version":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36","device_class":"browser|browser","device_family":"none","device_id":"%s","os_name":"Linux","os_version":"x86_64"}`, generateDeviceID())

	for len(allProducts) < opts.LimitProducts {
		reqURL, err := url.Parse(baseURL)
		if err != nil {
			return nil, fmt.Errorf("invalid indomaret url: %w", err)
		}

		q := reqURL.Query()
		q.Set("storeCode", opts.StoreCode)
		q.Set("latitude", opts.Latitude)
		q.Set("longitude", opts.Longitude)
		q.Set("mode", "DELIVERY")
		q.Set("districtId", opts.DistrictID)
		q.Set("key", opts.Query)
		q.Set("keyword", opts.Query)
		q.Set("page", fmt.Sprintf("%d", page))
		q.Set("size", fmt.Sprintf("%d", pageSize))
		reqURL.RawQuery = q.Encode()

		req, err := http.NewRequest("GET", reqURL.String(), nil)
		if err != nil {
			return nil, fmt.Errorf("failed to create indomaret request: %w", err)
		}

		req.Header.Set("accept", "application/json, text/plain, */*")
		req.Header.Set("accept-language", "en-US,en;q=0.9,id;q=0.8")
		req.Header.Set("apps", appsJSON)
		req.Header.Set("page", "unpage")
		req.Header.Set("Referer", "https://www.klikindomaret.com/")
		req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

		resp, err := client.Do(req)
		if err != nil {
			return nil, fmt.Errorf("indomaret request error: %w", err)
		}

		bodyBytes, err := io.ReadAll(resp.Body)
		resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			return nil, fmt.Errorf("indomaret API returned HTTP %d: %s", resp.StatusCode, string(bodyBytes))
		}

		var apiResp indomaretResponse
		if err := json.Unmarshal(bodyBytes, &apiResp); err != nil {
			return nil, fmt.Errorf("indomaret json unmarshal error: %w", err)
		}

		if len(apiResp.Data.Content) == 0 {
			break
		}

		nowStr := time.Now().UTC().Format(time.RFC3339)
		for _, item := range apiResp.Data.Content {
			if len(allProducts) >= opts.LimitProducts {
				break
			}

			price := item.FinalPrice
			if price <= 0 {
				price = item.Price
			}
			priceNumeric := int(price)

			sellerName := "Klik Indomaret"
			if item.BrandName != "" {
				sellerName = fmt.Sprintf("Klik Indomaret (%s)", item.BrandName)
			}

			productURL := fmt.Sprintf("https://www.klikindomaret.com/product/%s", item.Permalink)

			prod := Product{
				ProductName:  core.CleanText(item.ProductName),
				PriceRaw:     fmt.Sprintf("Rp %s", core.FormatIDR(priceNumeric)),
				PriceNumeric: priceNumeric,
				Seller:       sellerName,
				ProductURL:   productURL,
				Category:     "Groceries",
				ScrapedAt:    nowStr,
			}

			allProducts = append(allProducts, prod)
		}

		page++
	}

	meta := map[string]interface{}{
		"scraper":      "indomaret-go-api",
		"query":        opts.Query,
		"store_code":   opts.StoreCode,
		"items_count":  len(allProducts),
		"scraped_at":   time.Now().UTC().Format(time.RFC3339),
	}

	historyPath := fmt.Sprintf("data/ecommerce/indomaret/history/%s.json", time.Now().Format("2006-01-02"))
	if err := core.WriteLatestAndHistory(opts.OutputPath, historyPath, allProducts, meta); err != nil {
		return nil, fmt.Errorf("failed to save indomaret dataset: %w", err)
	}

	return allProducts, nil
}
