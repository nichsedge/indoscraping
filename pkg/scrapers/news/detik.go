package news

import (
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/PuerkitoBio/goquery"
	"github.com/nichsedge/indoscraping/pkg/core"
)

type Article struct {
	Title       string `json:"title"`
	URL         string `json:"url"`
	Category    string `json:"category"`
	PublishedAt string `json:"published_at"`
	ScrapedAt   string `json:"scraped_at"`
}

type DetikOptions struct {
	Date            string // Format: MM/DD/YYYY
	LimitCategories int
	LimitArticles   int
	OutputPath      string
}

func ScrapeDetik(opts DetikOptions) ([]Article, error) {
	if opts.LimitArticles <= 0 {
		opts.LimitArticles = 10
	}
	if opts.Date == "" {
		opts.Date = time.Now().Format("01/02/2006")
	}
	if opts.OutputPath == "" {
		opts.OutputPath = "data/news/detik/latest.json"
	}

	client := core.HTTPClient()
	startURL := fmt.Sprintf("https://news.detik.com/indeks?date=%s", opts.Date)

	req, err := http.NewRequest("GET", startURL, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36")

	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch Detik index: %w", err)
	}
	defer resp.Body.Close()

	doc, err := goquery.NewDocumentFromReader(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to parse Detik HTML: %w", err)
	}

	var allArticles []Article
	seenURLs := make(map[string]bool)
	scrapedAt := time.Now().UTC().Format(time.RFC3339)

	doc.Find("article, .list-content__item").Each(func(i int, s *goquery.Selection) {
		if len(allArticles) >= opts.LimitArticles {
			return
		}

		titleTag := s.Find(".media__title a, h3 a, h2 a").First()
		if titleTag.Length() == 0 {
			return
		}

		href, exists := titleTag.Attr("href")
		if !exists || href == "" || strings.HasSuffix(href, "/indeks") || seenURLs[href] {
			return
		}

		title := core.CleanText(titleTag.Text())
		if title == "" {
			return
		}

		seenURLs[href] = true
		dateTag := s.Find(".media__date span, .media__date, .date").First()
		dateText := core.CleanText(dateTag.AttrOr("title", dateTag.Text()))

		allArticles = append(allArticles, Article{
			Title:       title,
			URL:         href,
			Category:    "News",
			PublishedAt: dateText,
			ScrapedAt:   scrapedAt,
		})
	})

	historyPath := fmt.Sprintf("data/news/detik/history/%s.json", time.Now().Format("2006-01-02"))
	meta := map[string]interface{}{
		"scraper":     "detik-go",
		"items_count": len(allArticles),
		"scraped_at":  scrapedAt,
		"target_date": opts.Date,
	}

	if err := core.WriteLatestAndHistory(opts.OutputPath, historyPath, allArticles, meta); err != nil {
		return allArticles, err
	}

	return allArticles, nil
}
