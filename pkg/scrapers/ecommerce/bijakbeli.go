package ecommerce

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/nichsedge/indoscraping/pkg/core"
)

// StapleItem represents a consumer staple price observation for Bijak-Beli.
type StapleItem struct {
	StapleCategory string `json:"stapleCategory"` // e.g. "minyak", "beras", "susu", "gula", "telur", "mie"
	Source         string `json:"source"`         // "alfagift" or "indomaret"
	ProductName    string `json:"productName"`
	PriceRaw       string `json:"priceRaw"`
	PriceNumeric   int    `json:"priceNumeric"`
	ProductURL     string `json:"productUrl"`
	Seller         string `json:"seller"`
	ScrapedAt      string `json:"scrapedAt"`
}

// BijakBeliSummary provides comparative stats between Alfamart and Indomaret.
type BijakBeliSummary struct {
	Category      string  `json:"category"`
	AlfaMinPrice  int     `json:"alfaMinPrice"`
	AlfaAvgPrice  float64 `json:"alfaAvgPrice"`
	IndoMinPrice  int     `json:"indoMinPrice"`
	IndoAvgPrice  float64 `json:"indoAvgPrice"`
	CheapestStore string  `json:"cheapestStore"`
}

type BijakBeliOptions struct {
	Queries      []string
	LimitPerItem int
	OutputPath   string
}

// RunBijakBeli executes cross-retailer consumer staple price ingestion.
func RunBijakBeli(opts BijakBeliOptions) ([]StapleItem, []BijakBeliSummary, error) {
	if len(opts.Queries) == 0 {
		opts.Queries = []string{"minyak", "beras", "susu", "gula", "telur", "mie"}
	}
	if opts.LimitPerItem <= 0 {
		opts.LimitPerItem = 3
	}
	if opts.OutputPath == "" {
		opts.OutputPath = "data/bijak_beli/latest.json"
	}

	scrapedAt := time.Now().UTC().Format(time.RFC3339)
	var allItems []StapleItem
	var summaries []BijakBeliSummary

	for _, query := range opts.Queries {
		q := strings.TrimSpace(query)
		if q == "" {
			continue
		}

		// 1. Scrape Alfagift
		alfaProducts, err := ScrapeAlfagift(AlfagiftOptions{
			Query:         q,
			LimitProducts: opts.LimitPerItem,
			OutputPath:    filepath.Join("data/ecommerce/alfagift", fmt.Sprintf("staple_%s.json", q)),
		})
		if err != nil {
			fmt.Printf("⚠️  [BijakBeli] Warning: failed to fetch Alfagift for '%s': %v\n", q, err)
		}

		// 2. Scrape Indomaret
		indoProducts, err := ScrapeIndomaret(IndomaretOptions{
			Query:         q,
			LimitProducts: opts.LimitPerItem,
			OutputPath:    filepath.Join("data/ecommerce/indomaret", fmt.Sprintf("staple_%s.json", q)),
		})
		if err != nil {
			fmt.Printf("⚠️  [BijakBeli] Warning: failed to fetch Indomaret for '%s': %v\n", q, err)
		}

		var alfaTotal, alfaCount, alfaMin int
		for i, p := range alfaProducts {
			allItems = append(allItems, StapleItem{
				StapleCategory: q,
				Source:         "alfagift",
				ProductName:    p.ProductName,
				PriceRaw:       p.PriceRaw,
				PriceNumeric:   p.PriceNumeric,
				ProductURL:     p.ProductURL,
				Seller:         p.Seller,
				ScrapedAt:      scrapedAt,
			})
			if p.PriceNumeric > 0 {
				alfaTotal += p.PriceNumeric
				alfaCount++
				if i == 0 || p.PriceNumeric < alfaMin {
					alfaMin = p.PriceNumeric
				}
			}
		}

		var indoTotal, indoCount, indoMin int
		for i, p := range indoProducts {
			allItems = append(allItems, StapleItem{
				StapleCategory: q,
				Source:         "indomaret",
				ProductName:    p.ProductName,
				PriceRaw:       p.PriceRaw,
				PriceNumeric:   p.PriceNumeric,
				ProductURL:     p.ProductURL,
				Seller:         p.Seller,
				ScrapedAt:      scrapedAt,
			})
			if p.PriceNumeric > 0 {
				indoTotal += p.PriceNumeric
				indoCount++
				if i == 0 || p.PriceNumeric < indoMin {
					indoMin = p.PriceNumeric
				}
			}
		}

		var alfaAvg, indoAvg float64
		if alfaCount > 0 {
			alfaAvg = float64(alfaTotal) / float64(alfaCount)
		}
		if indoCount > 0 {
			indoAvg = float64(indoTotal) / float64(indoCount)
		}

		cheapest := "equal"
		if alfaMin > 0 && indoMin > 0 {
			if alfaMin < indoMin {
				cheapest = "alfamart"
			} else if indoMin < alfaMin {
				cheapest = "indomaret"
			}
		} else if alfaMin > 0 {
			cheapest = "alfamart"
		} else if indoMin > 0 {
			cheapest = "indomaret"
		}

		summaries = append(summaries, BijakBeliSummary{
			Category:      q,
			AlfaMinPrice:  alfaMin,
			AlfaAvgPrice:  alfaAvg,
			IndoMinPrice:  indoMin,
			IndoAvgPrice:  indoAvg,
			CheapestStore: cheapest,
		})
	}

	historyPath := fmt.Sprintf("data/bijak_beli/history/%s.json", time.Now().Format("2006-01-02"))
	meta := map[string]interface{}{
		"initiative":  "bijak-beli",
		"items_count": len(allItems),
		"categories":  len(summaries),
		"scraped_at":  scrapedAt,
	}

	if err := core.WriteLatestAndHistory(opts.OutputPath, historyPath, allItems, meta); err != nil {
		return allItems, summaries, err
	}

	// Also write summary JSON
	summaryPath := "data/bijak_beli/summary.json"
	summaryBytes, _ := json.MarshalIndent(summaries, "", "  ")
	_ = os.WriteFile(summaryPath, summaryBytes, 0644)

	return allItems, summaries, nil
}
