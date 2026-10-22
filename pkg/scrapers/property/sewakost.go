package property

import (
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/PuerkitoBio/goquery"
	"github.com/nichsedge/indoscraping/pkg/core"
)

type KostListing struct {
	Title        string   `json:"title"`
	PriceRaw     string   `json:"priceRaw"`
	PriceNumeric int      `json:"priceNumeric"`
	Area         string   `json:"area"`
	Type         string   `json:"type"` // Campur, Putri, Putra
	Tags         []string `json:"tags"`
	URL          string   `json:"url"`
	ScrapedAt    string   `json:"scraped_at"`
}

type SewaKostOptions struct {
	Area       string // e.g. "jakarta/jakarta-barat/palmerah"
	MaxPages   int
	OutputPath string
}

func ScrapeSewaKost(opts SewaKostOptions) ([]KostListing, error) {
	if opts.Area == "" {
		opts.Area = "jakarta/jakarta-barat/palmerah"
	}
	if opts.MaxPages <= 0 {
		opts.MaxPages = 1
	}
	if opts.OutputPath == "" {
		opts.OutputPath = "data/property/sewakost/latest.json"
	}

	client := &http.Client{Timeout: 30 * time.Second}
	var allListings []KostListing
	seenURLs := make(map[string]bool)
	scrapedAt := time.Now().UTC().Format(time.RFC3339)

	for page := 1; page <= opts.MaxPages; page++ {
		targetURL := fmt.Sprintf("https://www.sewakost.com/kost/%s/", strings.Trim(opts.Area, "/"))
		if page > 1 {
			targetURL = fmt.Sprintf("https://www.sewakost.com/kost/%s/page/%d/", strings.Trim(opts.Area, "/"), page)
		}

		req, err := http.NewRequest("GET", targetURL, nil)
		if err != nil {
			continue
		}
		req.Header.Set("User-Agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
		req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")

		resp, err := client.Do(req)
		if err != nil {
			continue
		}

		doc, err := goquery.NewDocumentFromReader(resp.Body)
		resp.Body.Close()
		if err != nil {
			continue
		}

		doc.Find("article.item, .listing-item, article").Each(func(i int, s *goquery.Selection) {
			titleLink := s.Find("li.title a, .title a, a.link-large").First()
			if titleLink.Length() == 0 {
				titleLink = s.Find("h2 a, h3 a").First()
			}
			href, exists := titleLink.Attr("href")
			if !exists || href == "" || seenURLs[href] || !strings.Contains(href, "/kost/") {
				return
			}

			title := core.CleanText(titleLink.Text())
			if title == "" {
				title, _ = titleLink.Attr("title")
			}
			if title == "" {
				return
			}

			seenURLs[href] = true

			priceTag := s.Find("li.system .price-tag, .price-tag, .price").First()
			priceRaw := core.CleanText(priceTag.Text())
			priceNum := core.ParseNumericPrice(priceRaw)

			var tags []string
			s.Find("li.fields span, .tags span").Each(func(j int, tag *goquery.Selection) {
				t := core.CleanText(tag.Text())
				if t != "" {
					tags = append(tags, t)
				}
			})

			kostType := "Kost"
			for _, t := range tags {
				if strings.Contains(strings.ToLower(t), "putri") {
					kostType = "Kost Putri"
					break
				}
				if strings.Contains(strings.ToLower(t), "putra") {
					kostType = "Kost Putra"
					break
				}
				if strings.Contains(strings.ToLower(t), "campur") {
					kostType = "Kost Campur"
					break
				}
			}

			allListings = append(allListings, KostListing{
				Title:        title,
				PriceRaw:     priceRaw,
				PriceNumeric: priceNum,
				Area:         opts.Area,
				Type:         kostType,
				Tags:         tags,
				URL:          href,
				ScrapedAt:    scrapedAt,
			})
		})
	}

	historyPath := fmt.Sprintf("data/property/sewakost/history/%s.json", time.Now().Format("2006-01-02"))
	meta := map[string]interface{}{
		"scraper":     "sewakost-go",
		"items_count": len(allListings),
		"scraped_at":  scrapedAt,
		"area":        opts.Area,
	}

	if err := core.WriteLatestAndHistory(opts.OutputPath, historyPath, allListings, meta); err != nil {
		return allListings, err
	}

	return allListings, nil
}
