package hardware

import (
	"fmt"
	"net/http"
	"regexp"
	"strconv"
	"time"

	"github.com/PuerkitoBio/goquery"
	"github.com/nichsedge/indoscraping/pkg/core"
)

type BenchmarkItem struct {
	Name      string `json:"name"`
	Category  string `json:"category"` // "GPU" or "CPU"
	Segment   string `json:"segment"`  // "High-End", "Mid-Range"
	Score     int    `json:"score"`
	Benchmark string `json:"benchmark"`
	Source    string `json:"source"`
	URL       string `json:"url"`
	ScrapedAt string `json:"scraped_at"`
}

type PassMarkOptions struct {
	OutputPath string
}

var digitRe = regexp.MustCompile(`[^\d]`)

func fetchChart(client *http.Client, urlStr, category, segment, scrapedAt string) ([]BenchmarkItem, error) {
	req, err := http.NewRequest("GET", urlStr, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request for %s: %w", urlStr, err)
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36")

	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch %s: %w", urlStr, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("HTTP error %d fetching %s", resp.StatusCode, urlStr)
	}

	doc, err := goquery.NewDocumentFromReader(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to parse HTML for %s: %w", urlStr, err)
	}

	benchName := "PassMark G3D Mark"
	if category == "CPU" {
		benchName = "PassMark CPU Mark"
	}

	var items []BenchmarkItem
	doc.Find("ul.chartlist li").Each(func(i int, s *goquery.Selection) {
		name := core.CleanText(s.Find("span.prdname").Text())
		countRaw := s.Find("span.count").Text()
		digits := digitRe.ReplaceAllString(countRaw, "")

		if name == "" || digits == "" {
			return
		}

		score, err := strconv.Atoi(digits)
		if err != nil || score <= 0 {
			return
		}

		items = append(items, BenchmarkItem{
			Name:      name,
			Category:  category,
			Segment:   segment,
			Score:     score,
			Benchmark: benchName,
			Source:    "passmark",
			URL:       urlStr,
			ScrapedAt: scrapedAt,
		})
	})

	return items, nil
}

// ScrapePassMark retrieves live GPU and CPU benchmark ratings from PassMark.
func ScrapePassMark(opts PassMarkOptions) ([]BenchmarkItem, error) {
	if opts.OutputPath == "" {
		opts.OutputPath = "data/benchmarks/passmark/latest.json"
	}

	client := core.HTTPClient()
	scrapedAt := time.Now().UTC().Format(time.RFC3339)

	targets := []struct {
		url      string
		category string
		segment  string
	}{
		{"https://www.videocardbenchmark.net/high_end_gpus.html", "GPU", "High-End"},
		{"https://www.videocardbenchmark.net/mid_range_gpus.html", "GPU", "Mid-Range"},
		{"https://www.cpubenchmark.net/high_end_cpus.html", "CPU", "High-End"},
		{"https://www.cpubenchmark.net/mid_range_cpus.html", "CPU", "Mid-Range"},
	}

	var allItems []BenchmarkItem
	for _, target := range targets {
		items, err := fetchChart(client, target.url, target.category, target.segment, scrapedAt)
		if err != nil {
			return nil, fmt.Errorf("passmark: error scraping %s %s: %w", target.category, target.segment, err)
		}
		allItems = append(allItems, items...)
	}

	historyPath := fmt.Sprintf("data/benchmarks/passmark/history/%s.json", time.Now().Format("2006-01-02"))
	meta := map[string]interface{}{
		"scraper":     "passmark-go",
		"items_count": len(allItems),
		"scraped_at":  scrapedAt,
	}

	if err := core.WriteLatestAndHistory(opts.OutputPath, historyPath, allItems, meta); err != nil {
		return allItems, err
	}

	return allItems, nil
}
