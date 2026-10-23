package news

import (
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/PuerkitoBio/goquery"
	"github.com/nichsedge/indoscraping/pkg/core"
)

type CNBCOptions struct {
	Date          string // YYYY/MM/DD
	LimitArticles int
	OutputPath    string
}

func ScrapeCNBC(opts CNBCOptions) ([]Article, error) {
	if opts.LimitArticles <= 0 {
		opts.LimitArticles = 10
	}
	if opts.Date == "" {
		opts.Date = time.Now().Format("2006/01/02")
	}
	if opts.OutputPath == "" {
		opts.OutputPath = "data/news/cnbc/latest.json"
	}

	targetURL := fmt.Sprintf("https://www.cnbcindonesia.com/indeks?date=%s", opts.Date)
	client := core.HTTPClient()

	req, err := http.NewRequest("GET", targetURL, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36")

	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch CNBC index: %w", err)
	}
	defer resp.Body.Close()

	doc, err := goquery.NewDocumentFromReader(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to parse CNBC HTML: %w", err)
	}

	var articles []Article
	scrapedAt := time.Now().UTC().Format(time.RFC3339)

	doc.Find("article, .media_rows li, .list li").Each(func(i int, s *goquery.Selection) {
		if len(articles) >= opts.LimitArticles {
			return
		}

		link := s.Find("a[href*='cnbcindonesia.com']").First()
		if link.Length() == 0 {
			return
		}

		href, _ := link.Attr("href")
		title := core.CleanText(s.Find("h2, h3, .sub_judul").First().Text())
		if title == "" {
			title = core.CleanText(link.Text())
		}
		if title == "" || strings.Contains(href, "/indeks") {
			return
		}

		dateText := core.CleanText(s.Find("[class*='text-gray'], .date, .sub_date, time").First().Text())

		category := ""
		catBadge := s.Find("span.uppercase, span.sub_label").First()
		if catBadge.Length() > 0 && len(catBadge.Text()) < 25 {
			category = core.CleanText(catBadge.Text())
		}
		if category == "" {
			parts := strings.Split(strings.TrimPrefix(href, "https://www.cnbcindonesia.com/"), "/")
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

	historyPath := fmt.Sprintf("data/news/cnbc/history/%s.json", time.Now().Format("2006-01-02"))
	meta := map[string]interface{}{
		"scraper":     "cnbc-go",
		"items_count": len(articles),
		"scraped_at":  scrapedAt,
		"target_date": opts.Date,
	}

	if err := core.WriteLatestAndHistory(opts.OutputPath, historyPath, articles, meta); err != nil {
		return articles, err
	}

	return articles, nil
}
