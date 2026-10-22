package property

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/nichsedge/indoscraping/pkg/core"
)

type PropertyListing struct {
	ID            int    `json:"id"`
	Code          string `json:"code"`
	Name          string `json:"name"`
	ApartmentName string `json:"apartment_name"`
	PriceRaw      string `json:"priceRaw"`
	PriceNumeric  int    `json:"priceNumeric"`
	Bedroom       int    `json:"bedroom"`
	Bathroom      int    `json:"bathroom"`
	UnitArea      int    `json:"unit_area"`
	Tower         string `json:"tower"`
	URL           string `json:"url"`
	ScrapedAt     string `json:"scraped_at"`
}

type Jendela360Options struct {
	LimitPages int
	OutputPath string
}

func ScrapeJendela360(opts Jendela360Options) ([]PropertyListing, error) {
	if opts.LimitPages <= 0 {
		opts.LimitPages = 1
	}
	if opts.OutputPath == "" {
		opts.OutputPath = "data/property/jendela360/latest.json"
	}

	client := &http.Client{Timeout: 30 * time.Second}
	var allListings []PropertyListing
	scrapedAt := time.Now().UTC().Format(time.RFC3339)

	for page := 1; page <= opts.LimitPages; page++ {
		apiURL := fmt.Sprintf("https://api.jendela360.com/api/site/search-list?listing_type_id=1&type=0&page=%d&duration_filter=yearly", page)
		req, err := http.NewRequest("GET", apiURL, nil)
		if err != nil {
			continue
		}
		req.Header.Set("origin", "https://jendela360.com")
		req.Header.Set("referer", "https://jendela360.com/")
		req.Header.Set("user-agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36")

		resp, err := client.Do(req)
		if err != nil {
			continue
		}

		var apiResp struct {
			Data []struct {
				ID            int    `json:"id"`
				Code          string `json:"code"`
				Name          string `json:"name"`
				Price         int    `json:"price"`
				Bedroom       int    `json:"bedroom"`
				Bathroom      int    `json:"bathroom"`
				UnitArea      int    `json:"unit_area"`
				Tower         string `json:"tower"`
				ApartmentName string `json:"apartment_name"`
				ApartmentSlug string `json:"apartment_slug"`
			} `json:"data"`
		}

		err = json.NewDecoder(resp.Body).Decode(&apiResp)
		resp.Body.Close()
		if err != nil {
			continue
		}

		for _, item := range apiResp.Data {
			propURL := fmt.Sprintf("https://jendela360.com/sewa-apartemen/%s/%s", item.ApartmentSlug, strings.ToLower(item.Code))
			if item.ApartmentSlug == "" {
				propURL = fmt.Sprintf("https://jendela360.com/detail/%s", item.Code)
			}

			allListings = append(allListings, PropertyListing{
				ID:            item.ID,
				Code:          item.Code,
				Name:          core.CleanText(item.Name),
				ApartmentName: core.CleanText(item.ApartmentName),
				PriceRaw:      fmt.Sprintf("Rp %s", core.FormatIDR(item.Price)),
				PriceNumeric:  item.Price,
				Bedroom:       item.Bedroom,
				Bathroom:      item.Bathroom,
				UnitArea:      item.UnitArea,
				Tower:         item.Tower,
				URL:           propURL,
				ScrapedAt:     scrapedAt,
			})
		}
	}

	historyPath := fmt.Sprintf("data/property/jendela360/history/%s.json", time.Now().Format("2006-01-02"))
	meta := map[string]interface{}{
		"scraper":     "jendela360-go",
		"items_count": len(allListings),
		"scraped_at":  scrapedAt,
	}

	if err := core.WriteLatestAndHistory(opts.OutputPath, historyPath, allListings, meta); err != nil {
		return allListings, err
	}

	return allListings, nil
}
