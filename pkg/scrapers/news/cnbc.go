package news

import (
	"fmt"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/PuerkitoBio/goquery"
	"github.com/nichsedge/indoscraping/pkg/core"
)

type CNBCOptions struct {
	Date          string   // YYYY/MM/DD or YYYY-MM-DD (default: D-1 Asia/Jakarta)
	Categories    []string // Category slugs, e.g. ["market", "research", "news"]
	LimitArticles int      // < 0 means unlimited (all articles for the date)
	OutputPath    string
}

var cnbcCategoryIDs = map[string]string{
	"market":         "5",
	"news":           "3",
	"entrepreneur":   "9",
	"syariah":        "10",
	"sharia":         "10",
	"tech":           "12",
	"lifestyle":      "11",
	"opini":          "13",
	"mymoney":        "71",
	"cuap-cuap-cuan": "78",
	"research":       "127",
}

func normalizeCNBCDate(raw string) (urlDate string, isoDate string) {
	loc, err := time.LoadLocation("Asia/Jakarta")
	if err != nil {
		loc = time.FixedZone("WIB", 7*3600)
	}
	trimmed := strings.TrimSpace(raw)
	if trimmed == "" {
		d1 := time.Now().In(loc).AddDate(0, 0, -1)
		return d1.Format("2006/01/02"), d1.Format("2006-01-02")
	}
	isoDate = strings.ReplaceAll(trimmed, "/", "-")
	urlDate = strings.ReplaceAll(trimmed, "-", "/")
	return urlDate, isoDate
}

func ScrapeCNBC(opts CNBCOptions) ([]Article, error) {
	if opts.LimitArticles == 0 {
		opts.LimitArticles = 10
	}
	urlDate, isoDate := normalizeCNBCDate(opts.Date)
	opts.Date = urlDate
	if opts.OutputPath == "" {
		opts.OutputPath = "data/news/cnbc/latest.json"
	}

	client := core.HTTPClient()
	var articles []Article
	seenURLs := make(map[string]struct{})
	scrapedAt := time.Now().UTC().Format(time.RFC3339)

	var indexURLs []struct {
		url      string
		category string
	}
	if len(opts.Categories) == 0 {
		indexURLs = append(indexURLs, struct {
			url      string
			category string
		}{
			url: fmt.Sprintf("https://www.cnbcindonesia.com/indeks?date=%s", opts.Date),
		})
	} else {
		for _, rawCat := range opts.Categories {
			slug := strings.ToLower(strings.TrimSpace(rawCat))
			if slug == "" {
				continue
			}
			if catID, ok := cnbcCategoryIDs[slug]; ok {
				indexURLs = append(indexURLs, struct {
					url      string
					category string
				}{
					url:      fmt.Sprintf("https://www.cnbcindonesia.com/%s/indeks/%s?date=%s", slug, catID, opts.Date),
					category: strings.ToUpper(slug),
				})
			}
		}
	}

	for _, target := range indexURLs {
		for page := 1; ; page++ {
			if opts.LimitArticles > 0 && len(articles) >= opts.LimitArticles {
				break
			}
			pageURL := fmt.Sprintf("%s&page=%d", target.url, page)
			req, err := http.NewRequest("GET", pageURL, nil)
			if err != nil {
				return nil, err
			}
			req.Header.Set("User-Agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36")

			resp, err := client.Do(req)
			if err != nil {
				return nil, fmt.Errorf("failed to fetch CNBC index: %w", err)
			}

			if resp.StatusCode == http.StatusNotFound {
				resp.Body.Close()
				break
			}
			if resp.StatusCode != http.StatusOK {
				resp.Body.Close()
				return nil, fmt.Errorf("unexpected status %d fetching %s", resp.StatusCode, pageURL)
			}

			doc, err := goquery.NewDocumentFromReader(resp.Body)
			resp.Body.Close()
			if err != nil {
				return nil, fmt.Errorf("failed to parse CNBC HTML: %w", err)
			}

			addedOnPage := 0
			doc.Find("article, .media_rows li, .list li").Each(func(_ int, s *goquery.Selection) {
				if opts.LimitArticles > 0 && len(articles) >= opts.LimitArticles {
					return
				}

				link := s.Find("a[href*='cnbcindonesia.com']").First()
				if link.Length() == 0 {
					return
				}

				href, _ := link.Attr("href")
				if href == "" || strings.Contains(href, "/indeks") {
					return
				}
				if _, dup := seenURLs[href]; dup {
					return
				}

				title := core.CleanText(s.Find("h2, h3, .sub_judul").First().Text())
				if title == "" {
					title = core.CleanText(link.Text())
				}
				if title == "" {
					return
				}

				dateText := core.CleanText(s.Find("[class*='text-gray'], .date, .sub_date, time").First().Text())

				category := target.category
				if category == "" {
					catBadge := s.Find("span.uppercase, span.sub_label").First()
					if catBadge.Length() > 0 && len(catBadge.Text()) < 25 {
						category = core.CleanText(catBadge.Text())
					}
				}
				if category == "" {
					parts := strings.Split(strings.TrimPrefix(href, "https://www.cnbcindonesia.com/"), "/")
					if len(parts) > 0 && parts[0] != "" {
						category = strings.Title(parts[0])
					} else {
						category = "News"
					}
				}

				seenURLs[href] = struct{}{}
				articles = append(articles, Article{
					Title:       title,
					URL:         href,
					Category:    category,
					PublishedAt: dateText,
					ScrapedAt:   scrapedAt,
				})
				addedOnPage++
			})

			if addedOnPage == 0 || len(opts.Categories) == 0 {
				break
			}
			time.Sleep(300 * time.Millisecond)
		}
	}

	// Enrich each article with full content, author, summary, image, and tags concurrently.
	var wg sync.WaitGroup
	sem := make(chan struct{}, 5)
	for i := range articles {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()
			_ = enrichCNBCArticle(client, &articles[idx])
		}(i)
	}
	wg.Wait()

	historyPath := fmt.Sprintf("data/news/cnbc/history/%s.json", isoDate)
	meta := map[string]interface{}{
		"scraper":     "cnbc-go",
		"items_count": len(articles),
		"scraped_at":  scrapedAt,
		"target_date": opts.Date,
		"categories":  opts.Categories,
	}

	if err := core.WriteLatestAndHistory(opts.OutputPath, historyPath, articles, meta); err != nil {
		return articles, err
	}

	return articles, nil
}

func enrichCNBCArticle(client *http.Client, article *Article) error {
	req, err := http.NewRequest("GET", article.URL, nil)
	if err != nil {
		return err
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36")

	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("unexpected status %d for %s", resp.StatusCode, article.URL)
	}

	doc, err := goquery.NewDocumentFromReader(resp.Body)
	if err != nil {
		return err
	}

	parseCNBCArticle(doc, article)
	return nil
}

func parseCNBCArticle(doc *goquery.Document, article *Article) {
	if h1 := core.CleanText(doc.Find("h1").First().Text()); h1 != "" {
		article.Title = h1
	}

	if dateText := core.CleanText(doc.Find("div.text-cm.text-gray").First().Text()); dateText != "" {
		article.PublishedAt = dateText
	}

	author := core.CleanText(doc.Find("div.mb-1.text-base.font-semibold").First().Text())
	if author == "" {
		if val, ok := doc.Find("meta[name='author']").Attr("content"); ok {
			author = core.CleanText(val)
		}
	}
	article.Author = author

	if val, ok := doc.Find("meta[property='og:description']").Attr("content"); ok {
		article.Summary = core.CleanText(val)
	} else if val, ok := doc.Find("meta[name='description']").Attr("content"); ok {
		article.Summary = core.CleanText(val)
	}

	if val, ok := doc.Find("meta[property='og:image']").Attr("content"); ok {
		article.Image = strings.TrimSpace(val)
	}

	var paragraphs []string
	doc.Find("div.detail-text p, div.detail_text p").Each(func(_ int, s *goquery.Selection) {
		if text := core.CleanText(s.Text()); text != "" {
			paragraphs = append(paragraphs, text)
		}
	})
	article.Content = strings.Join(paragraphs, "\n\n")

	seen := make(map[string]struct{})
	var tags []string
	doc.Find("a[href*='/tag/']").Each(func(_ int, s *goquery.Selection) {
		tag := strings.TrimSpace(strings.TrimPrefix(core.CleanText(s.Text()), "#"))
		if tag == "" {
			return
		}
		key := strings.ToLower(tag)
		if _, exists := seen[key]; exists {
			return
		}
		seen[key] = struct{}{}
		tags = append(tags, tag)
	})
	article.Tags = tags
}
