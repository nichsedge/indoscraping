package ecommerce

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"regexp"
	"strings"
	"time"

	"github.com/nichsedge/indoscraping/pkg/core"
)

type TokopediaOptions struct {
	Query         string
	LimitProducts int
	OutputPath    string
}

var tokpedCacheRegex = regexp.MustCompile(`window\.__cache\s*=\s*(\{.*?\});\s*</script>`)

func ScrapeTokopedia(opts TokopediaOptions) ([]Product, error) {
	if opts.Query == "" {
		opts.Query = "kopi"
	}
	if opts.LimitProducts <= 0 {
		opts.LimitProducts = 20
	}
	if opts.OutputPath == "" {
		opts.OutputPath = "data/ecommerce/tokopedia/latest.json"
	}

	targetURL := fmt.Sprintf("https://www.tokopedia.com/find/%s", url.PathEscape(opts.Query))
	client := &http.Client{Timeout: 30 * time.Second}

	req, err := http.NewRequest("GET", targetURL, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
	req.Header.Set("Accept-Language", "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7")

	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch Tokopedia find page: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("tokopedia returned status %d", resp.StatusCode)
	}

	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response body: %w", err)
	}

	htmlContent := string(bodyBytes)
	match := tokpedCacheRegex.FindStringSubmatch(htmlContent)
	if len(match) < 2 {
		return nil, fmt.Errorf("could not locate window.__cache in Tokopedia response")
	}

	var cacheData map[string]interface{}
	if err := json.Unmarshal([]byte(match[1]), &cacheData); err != nil {
		return nil, fmt.Errorf("failed to parse Tokopedia cache JSON: %w", err)
	}

	var products []Product
	scrapedAt := time.Now().UTC().Format(time.RFC3339)

	for key, val := range cacheData {
		if !strings.HasPrefix(key, "searchProductV5Product") {
			continue
		}
		itemMap, ok := val.(map[string]interface{})
		if !ok {
			continue
		}

		name, _ := itemMap["name"].(string)
		if name == "" {
			continue
		}

		prodURL, _ := itemMap["url"].(string)

		// Resolve price
		var priceRaw string
		var priceNum int
		if priceRef, ok := itemMap["price"].(map[string]interface{}); ok {
			if id, ok := priceRef["id"].(string); ok {
				if priceObj, ok := cacheData[id].(map[string]interface{}); ok {
					priceRaw, _ = priceObj["text"].(string)
					if num, ok := priceObj["number"].(float64); ok {
						priceNum = int(num)
					}
				}
			} else {
				priceRaw, _ = priceRef["text"].(string)
				if num, ok := priceRef["number"].(float64); ok {
					priceNum = int(num)
				}
			}
		}

		if priceRaw == "" {
			priceRaw = fmt.Sprintf("Rp %s", core.FormatIDR(priceNum))
		}

		// Resolve shop
		seller := "Tokopedia Merchant"
		if shopRef, ok := itemMap["shop"].(map[string]interface{}); ok {
			if id, ok := shopRef["id"].(string); ok {
				if shopObj, ok := cacheData[id].(map[string]interface{}); ok {
					sName, _ := shopObj["name"].(string)
					sCity, _ := shopObj["city"].(string)
					if sName != "" {
						if sCity != "" {
							seller = fmt.Sprintf("%s (%s)", sName, sCity)
						} else {
							seller = sName
						}
					}
				}
			} else {
				sName, _ := shopRef["name"].(string)
				sCity, _ := shopRef["city"].(string)
				if sName != "" {
					if sCity != "" {
						seller = fmt.Sprintf("%s (%s)", sName, sCity)
					} else {
						seller = sName
					}
				}
			}
		}

		products = append(products, Product{
			ProductName:  core.CleanText(name),
			PriceRaw:     priceRaw,
			PriceNumeric: priceNum,
			Seller:       seller,
			ProductURL:   prodURL,
			Category:     "Tokopedia Discovery",
			ScrapedAt:    scrapedAt,
		})

		if len(products) >= opts.LimitProducts {
			break
		}
	}

	historyPath := fmt.Sprintf("data/ecommerce/tokopedia/history/%s.json", time.Now().Format("2006-01-02"))
	meta := map[string]interface{}{
		"scraper":     "tokopedia-go-ssr",
		"items_count": len(products),
		"scraped_at":  scrapedAt,
		"query":       opts.Query,
	}

	if err := core.WriteLatestAndHistory(opts.OutputPath, historyPath, products, meta); err != nil {
		return products, err
	}

	return products, nil
}
