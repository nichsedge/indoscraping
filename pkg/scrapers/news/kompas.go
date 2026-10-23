package news

import (
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/PuerkitoBio/goquery"
	"github.com/nichsedge/indoscraping/pkg/core"
)

type KompasOptions struct {
	Date          string // YYYY-MM-DD
	LimitArticles int
	OutputPath    string
}

func ScrapeKompas(opts KompasOptions) ([]Article, error) {
	if opts.LimitArticles <= 0 {
		opts.LimitArticles = 10
	}
	if opts.Date == "" {
		opts.Date = time.Now().Format("2006-01-02")
	}
	if opts.OutputPath == "" {
		opts.OutputPath = "data/news/kompas/latest.json"
	}

	targetURL := fmt.Sprintf("https://indeks.kompas.com/?site=news&date=%s", opts.Date)
	client := core.HTTPClient()

	req, err := http.NewRequest("GET", targetURL, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36")

	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch Kompas index: %w", err)
	}
	defer resp.Body.Close()

	doc, err := goquery.NewDocumentFromReader(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to parse Kompas HTML: %w", err)
	}

	var articles []Article
	seenURLs := make(map[string]bool)
	scrapedAt := time.Now().UTC().Format(time.RFC3339)

	doc.Find(".articleList, .article__list, .articleItem, article, div.article__list__title").Each(func(i int, s *goquery.Selection) {
		if len(articles) >= opts.LimitArticles {
			return
		}

		link := s.Find("a").First()
		if s.Nodes[0].Data == "a" {
			link = s
		}
		href, exists := link.Attr("href")
		if !exists || href == "" || seenURLs[href] || strings.Contains(href, "/indeks") {
			return
		}

		titleTag := s.Find("h2.articleTitle, .articleTitle, h2, h3").First()
		title := core.CleanText(titleTag.Text())
		if title == "" {
			title = core.CleanText(link.Text())
		}
		if title == "" {
			return
		}

		seenURLs[href] = true
		dateText := core.CleanText(s.Find(".articlePost-date, .article__date, time").First().Text())
		category := core.CleanText(s.Find(".articlePost-subtitle, .article__subtitle").First().Text())
		if category == "" {
			category = "News"
		}

		articles = append(articles, Article{
			Title:       title,
			URL:         href,
			Category:    category,
			PublishedAt: dateText,
			ScrapedAt:   scrapedAt,
		})
	})

	historyPath := fmt.Sprintf("data/news/kompas/history/%s.json", time.Now().Format("2006-01-02"))
	meta := map[string]interface{}{
		"scraper":     "kompas-go",
		"items_count": len(articles),
		"scraped_at":  scrapedAt,
		"target_date": opts.Date,
	}

	if err := core.WriteLatestAndHistory(opts.OutputPath, historyPath, articles, meta); err != nil {
		return articles, err
	}

	return articles, nil
}
