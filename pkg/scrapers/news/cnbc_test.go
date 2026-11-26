package news

import (
	"strings"
	"testing"

	"github.com/PuerkitoBio/goquery"
)

func TestParseCNBCArticle(t *testing.T) {
	html := `
	<html>
	  <head>
	    <meta property="og:description" content="Ringkasan berita CNBC." />
	    <meta property="og:image" content="https://example.com/thumb.jpg" />
	  </head>
	  <body>
	    <h1>Judul Artikel CNBC</h1>
	    <div class="text-cm text-gray">26 November 2026 07:30</div>
	    <div class="mb-1 text-base font-semibold">Reporter CNBC</div>
	    <div class="detail-text">
	      <p>Paragraf pertama artikel.</p>
	      <p>Paragraf kedua artikel.</p>
	    </div>
	    <div class="flex flex-wrap gap-2">
	      <a href="https://www.cnbcindonesia.com/tag/ekonomi">#ekonomi</a>
	      <a href="https://www.cnbcindonesia.com/tag/ihsg">#ihsg</a>
	      <a href="https://www.cnbcindonesia.com/tag/ekonomi">#ekonomi</a>
	    </div>
	  </body>
	</html>`

	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		t.Fatalf("failed to parse HTML: %v", err)
	}

	article := Article{URL: "https://www.cnbcindonesia.com/market/sample"}
	parseCNBCArticle(doc, &article)

	if article.Title != "Judul Artikel CNBC" {
		t.Errorf("unexpected title: %q", article.Title)
	}
	if article.PublishedAt != "26 November 2026 07:30" {
		t.Errorf("unexpected published_at: %q", article.PublishedAt)
	}
	if article.Author != "Reporter CNBC" {
		t.Errorf("unexpected author: %q", article.Author)
	}
	if article.Summary != "Ringkasan berita CNBC." {
		t.Errorf("unexpected summary: %q", article.Summary)
	}
	if article.Image != "https://example.com/thumb.jpg" {
		t.Errorf("unexpected image: %q", article.Image)
	}
	wantContent := "Paragraf pertama artikel.\n\nParagraf kedua artikel."
	if article.Content != wantContent {
		t.Errorf("unexpected content: got %q, want %q", article.Content, wantContent)
	}
	if len(article.Tags) != 2 || article.Tags[0] != "ekonomi" || article.Tags[1] != "ihsg" {
		t.Errorf("unexpected tags: %#v", article.Tags)
	}
}

func TestNormalizeCNBCDate(t *testing.T) {
	urlDate, isoDate := normalizeCNBCDate("2026-11-25")
	if urlDate != "2026/11/25" || isoDate != "2026-11-25" {
		t.Errorf("unexpected date normalization: url=%q iso=%q", urlDate, isoDate)
	}

	urlDateSlash, isoDateSlash := normalizeCNBCDate("2026/11/25")
	if urlDateSlash != "2026/11/25" || isoDateSlash != "2026-11-25" {
		t.Errorf("unexpected slash normalization: url=%q iso=%q", urlDateSlash, isoDateSlash)
	}

	defaultURL, defaultISO := normalizeCNBCDate("")
	if len(defaultURL) != 10 || len(defaultISO) != 10 || strings.ReplaceAll(defaultURL, "/", "-") != defaultISO {
		t.Errorf("unexpected default D-1 date: url=%q iso=%q", defaultURL, defaultISO)
	}
}
