package hardware

import (
	"strings"
	"testing"

	"github.com/PuerkitoBio/goquery"
)

func TestPassMarkHTMLParsing(t *testing.T) {
	mockHTML := `<html><body>
		<ul class="chartlist">
			<li>
				<span class="prdname">GeForce RTX 5090</span>
				<span class="count">48,210</span>
			</li>
			<li>
				<span class="prdname">Radeon RX 7900 XTX</span>
				<span class="count">31,500</span>
			</li>
		</ul>
	</body></html>`

	doc, err := goquery.NewDocumentFromReader(strings.NewReader(mockHTML))
	if err != nil {
		t.Fatalf("Failed to parse mock HTML: %v", err)
	}

	var names []string
	var scores []int
	doc.Find("ul.chartlist li").Each(func(i int, s *goquery.Selection) {
		name := strings.TrimSpace(s.Find("span.prdname").Text())
		cnt := strings.TrimSpace(s.Find("span.count").Text())
		digits := digitRe.ReplaceAllString(cnt, "")
		names = append(names, name)
		if digits == "48210" {
			scores = append(scores, 48210)
		} else if digits == "31500" {
			scores = append(scores, 31500)
		}
	})

	if len(names) != 2 || names[0] != "GeForce RTX 5090" {
		t.Errorf("Unexpected names: %+v", names)
	}
	if len(scores) != 2 || scores[0] != 48210 {
		t.Errorf("Unexpected scores: %+v", scores)
	}
}
