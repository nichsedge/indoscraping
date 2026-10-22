package news

import (
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/PuerkitoBio/goquery"
	"github.com/nichsedge/indoscraping/pkg/core"
)

type CNNOptions struct {
	Date          string // YYYY/MM/DD
	LimitArticles int
	OutputPath    string
}

func ScrapeCNN(opts CNNOptions) ([]Article, error) {
	if opts.LimitArticles <= 0 {
		opts.LimitArticles = 10
	}
	if opts.Date == "" {
		opts.Date = time.Now().Format("2006/01/02")
	}
	if opts.OutputPath == "" {
		opts.OutputPath = "data/news/cnn/latest.json"
	}

	targetURL := fmt.Sprintf("https://www.cnnindonesia.com/indeks?date=%s", opts.Date)
	client := &http.Client{Timeout: 30 * time.Second}

	req, err := http.NewRequest("GET", targetURL, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36")

	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch CNN index: %w", err)
	}
	defer resp.Body.Close()

	doc, err := goquery.NewDocumentFromReader(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to parse CNN HTML: %w", err)
	}

	var articles []Article
	seenURLs := make(map[string]bool)
	scrapedAt := time.Now().UTC().Format(time.RFC3339)

	doc.Find("article, a.flex, [class*='media']").Each(func(i int, s *goquery.Selection) {
		if len(articles) >= opts.LimitArticles {
			return
		}

		link := s
		if link.Nodes[0].Data != "a" {
			link = s.Find("a[href*='cnnindonesia.com']").First()
		}

		href, _ := link.Attr("href")
		if href == "" || strings.HasSuffix(href, "/indeks") || strings.Count(href, "/") < 4 || seenURLs[href] {
			return
		}

		title := core.CleanText(s.Find("h2, h3, [class*='title']").First().Text())
		if title == "" {
			title = core.CleanText(link.Text())
		}
		if title == "" {
			return
		}

		seenURLs[href] = true
		rawDate := s.Find("span[class*='text-cnn_black_light'], [class*='date'], time").First().Text()
		dateText := strings.TrimSpace(strings.TrimPrefix(strings.TrimSpace(rawDate), "•"))

		categoryTag := s.Find("span[class*='text-cnn_red']").First().Text()
		category := core.CleanText(categoryTag)
		if category == "" {
			parts := strings.Split(strings.TrimPrefix(href, "https://www.cnnindonesia.com/"), "/")
			if len(parts) > 0 && parts[0] != "" {
				category = strings.Title(parts[0])
			} else {
				category = "News"
			}
		}

		articles = append(articles, Article{
			Title:       title,
			URL:         href,
			Category:    category,
			PublishedAt: dateText,
			ScrapedAt:   scrapedAt,
		})
	})

	historyPath := fmt.Sprintf("data/news/cnn/history/%s.json", time.Now().Format("2006-01-02"))
	meta := map[string]interface{}{
		"scraper":     "cnn-go",
		"items_count": len(articles),
		"scraped_at":  scrapedAt,
		"target_date": opts.Date,
	}

	if err := core.WriteLatestAndHistory(opts.OutputPath, historyPath, articles, meta); err != nil {
		return articles, err
	}

	return articles, nil
}
