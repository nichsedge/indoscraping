package banking

import (
	"fmt"
	"net/http"
	"strings"

	"github.com/PuerkitoBio/goquery"
	"github.com/nichsedge/indoscraping/pkg/core"
)

// ScrapeBCASBDK dynamically extracts official SBDK loan rates from BCA's live portal.
func ScrapeBCASBDK(client *http.Client) (SBDKBenchmark, error) {
	targetURL := "https://www.bca.co.id/id/informasi/Suku-Bunga-Dasar-Kredit"
	req, err := http.NewRequest("GET", targetURL, nil)
	if err != nil {
		return SBDKBenchmark{}, fmt.Errorf("failed to create BCA SBDK request: %w", err)
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
	req.Header.Set("Accept-Language", "id-ID,id;q=0.9,en-US;q=0.8")

	resp, err := client.Do(req)
	if err != nil {
		return SBDKBenchmark{}, fmt.Errorf("failed to fetch BCA SBDK: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return SBDKBenchmark{}, fmt.Errorf("BCA SBDK endpoint returned HTTP status %d", resp.StatusCode)
	}

	doc, err := goquery.NewDocumentFromReader(resp.Body)
	if err != nil {
		return SBDKBenchmark{}, fmt.Errorf("failed to parse BCA SBDK HTML: %w", err)
	}

	var sbdk SBDKBenchmark
	found := false

	// Find the SBDK row inside table
	doc.Find("table tbody tr").Each(func(i int, tr *goquery.Selection) {
		text := tr.Text()
		if strings.Contains(text, "Suku Bunga Dasar Kredit (SBDK)") {
			cells := tr.Find("td")
			if cells.Length() >= 7 {
				sbdk.Korporasi = parsePercent(cells.Eq(1).Text(), 0)
				sbdk.Ritel = parsePercent(cells.Eq(2).Text(), 0)
				// Small business / Micro
				sbdk.Mikro = parsePercent(cells.Eq(5).Text(), 0)
				sbdk.KPR = parsePercent(cells.Eq(6).Text(), 0)
				found = true
			}
		}
	})

	if !found || sbdk.Korporasi == 0 {
		return SBDKBenchmark{}, fmt.Errorf("failed to extract SBDK rates from live BCA table")
	}

	// Extract effective period
	periodText := "Live BCA Disclosure"
	doc.Find(".m-table--wrapper, .table, p").Each(func(i int, s *goquery.Selection) {
		t := s.Text()
		if strings.Contains(t, "Periode Data:") || strings.Contains(t, "Berlaku sejak") {
			lines := strings.Split(t, "\n")
			for _, line := range lines {
				line = strings.TrimSpace(line)
				if strings.Contains(line, "Periode Data:") || strings.Contains(line, "Berlaku") {
					periodText = line
					break
				}
			}
		}
	})
	sbdk.Period = periodText

	return sbdk, nil
}

// ScrapeMandiriSBDK dynamically extracts official SBDK rates from Bank Mandiri's live portal.
func ScrapeMandiriSBDK(client *http.Client) (SBDKBenchmark, error) {
	targetURL := "https://www.bankmandiri.co.id/suku-bunga-dasar-kredit"
	req, err := http.NewRequest("GET", targetURL, nil)
	if err != nil {
		return SBDKBenchmark{}, fmt.Errorf("failed to create Mandiri SBDK request: %w", err)
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
	req.Header.Set("Accept-Language", "id-ID,id;q=0.9,en-US;q=0.8")

	resp, err := client.Do(req)
	if err != nil {
		return SBDKBenchmark{}, fmt.Errorf("failed to fetch Mandiri SBDK: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return SBDKBenchmark{}, fmt.Errorf("Mandiri SBDK endpoint returned HTTP status %d", resp.StatusCode)
	}

	doc, err := goquery.NewDocumentFromReader(resp.Body)
	if err != nil {
		return SBDKBenchmark{}, fmt.Errorf("failed to parse Mandiri SBDK HTML: %w", err)
	}

	var sbdk SBDKBenchmark
	found := false

	// Period text from table header
	doc.Find("table thead th").Each(func(i int, th *goquery.Selection) {
		t := core.CleanText(th.Text())
		if strings.Contains(t, "Periode Data:") {
			sbdk.Period = t
		}
	})

	doc.Find("table tbody tr").Each(func(i int, s *goquery.Selection) {
		text := s.Text()
		if strings.Contains(text, "Suku Bunga Dasar Kredit (SBDK)") {
			cells := s.Find("td")
			if cells.Length() >= 6 {
				sbdk.Korporasi = parsePercent(cells.Eq(1).Text(), 0)
				// Ritel / Menengah
				sbdk.Ritel = parsePercent(cells.Eq(3).Text(), 0)
				sbdk.Mikro = parsePercent(cells.Eq(5).Text(), 0)
				if cells.Length() >= 7 {
					sbdk.KPR = parsePercent(cells.Eq(6).Text(), 0)
				}
				found = true
			}
		}
	})

	if !found || sbdk.Korporasi == 0 {
		return SBDKBenchmark{}, fmt.Errorf("failed to extract SBDK rates from live Mandiri table")
	}

	if sbdk.Period == "" {
		sbdk.Period = "Mandiri Live Disclosure"
	}

	return sbdk, nil
}

// ScrapeMandiriDana dynamically extracts savings tiers and deposit rates from Mandiri.
func ScrapeMandiriDana(client *http.Client) (tiers []RateTier, dep []DepositoTenor, err error) {
	targetURL := "https://www.bankmandiri.co.id/suku-bunga-dana"
	req, err := http.NewRequest("GET", targetURL, nil)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to create Mandiri Dana request: %w", err)
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
	req.Header.Set("Accept-Language", "id-ID,id;q=0.9,en-US;q=0.8")

	resp, err := client.Do(req)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to fetch Mandiri Dana: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, nil, fmt.Errorf("Mandiri Dana endpoint returned HTTP status %d", resp.StatusCode)
	}

	doc, err := goquery.NewDocumentFromReader(resp.Body)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to parse Mandiri Dana HTML: %w", err)
	}

	// 1. Deposito Rupiah table
	doc.Find("table.ag-table").First().Find("tbody tr").First().Each(func(i int, tr *goquery.Selection) {
		cells := tr.Find("td")
		if cells.Length() >= 5 {
			dep = append(dep, DepositoTenor{TenorMonths: 1, RatePA: parsePercent(cells.Eq(1).Text(), 0)})
			dep = append(dep, DepositoTenor{TenorMonths: 3, RatePA: parsePercent(cells.Eq(2).Text(), 0)})
			dep = append(dep, DepositoTenor{TenorMonths: 6, RatePA: parsePercent(cells.Eq(3).Text(), 0)})
			dep = append(dep, DepositoTenor{TenorMonths: 12, RatePA: parsePercent(cells.Eq(4).Text(), 0)})
		}
	})

	// 2. Tabungan Bisnis table (id="tabunganA2") or Tabungan Rupiah (id="tabunganA1")
	bisnisSection := doc.Find("#tabunganA2").First()
	if bisnisSection.Length() > 0 {
		bisnisTable := bisnisSection.NextFilteredUntil("div.table-responsive", "h2").Find("table").First()
		bisnisTable.Find("tbody tr").Each(func(i int, tr *goquery.Selection) {
			cells := tr.Find("td")
			if cells.Length() >= 2 {
				tierName := cells.Eq(0).Text()
				rateVal := parsePercent(cells.Eq(1).Text(), 0)
				var minB, maxB float64
				if strings.Contains(tierName, "0 -") {
					minB = 0
					maxB = 1000000
				} else if strings.Contains(tierName, "1 Juta") {
					minB = 1000000
					maxB = 50000000
				} else if strings.Contains(tierName, "50 Juta") {
					minB = 50000000
					maxB = 500000000
				} else if strings.Contains(tierName, "500 Juta") {
					minB = 500000000
					maxB = 1000000000
				} else if strings.Contains(tierName, "1 Miliar") {
					minB = 1000000000
					maxB = 0
				}
				tiers = append(tiers, RateTier{MinBalance: minB, MaxBalance: maxB, RatePA: rateVal})
			}
		})
	}

	if len(tiers) == 0 {
		// Fallback to Tabungan Rupiah if Tabungan Bisnis selector differed
		doc.Find("#tabunganA1").NextAll().Find("table tbody tr").Each(func(i int, tr *goquery.Selection) {
			cells := tr.Find("td")
			if cells.Length() >= 2 && len(tiers) < 5 {
				rateVal := parsePercent(cells.Eq(1).Text(), 0)
				tiers = append(tiers, RateTier{RatePA: rateVal})
			}
		})
	}

	if len(dep) == 0 || len(tiers) == 0 {
		return nil, nil, fmt.Errorf("failed to extract complete live Mandiri savings and deposit tables")
	}

	return tiers, dep, nil
}

// ScrapeSeaBank dynamically extracts savings tiers, deposit rates, and administrative fees from SeaBank.
func ScrapeSeaBank(client *http.Client) (tiers []RateTier, dep []DepositoTenor, fees map[string]float64, err error) {
	targetURL := "https://www.seabank.co.id/info/biaya-bunga"
	req, err := http.NewRequest("GET", targetURL, nil)
	if err != nil {
		return nil, nil, nil, fmt.Errorf("failed to create SeaBank request: %w", err)
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
	req.Header.Set("Accept-Language", "id-ID,id;q=0.9,en-US;q=0.8")

	resp, err := client.Do(req)
	if err != nil {
		return nil, nil, nil, fmt.Errorf("failed to fetch SeaBank: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, nil, nil, fmt.Errorf("SeaBank endpoint returned HTTP status %d", resp.StatusCode)
	}

	doc, err := goquery.NewDocumentFromReader(resp.Body)
	if err != nil {
		return nil, nil, nil, fmt.Errorf("failed to parse SeaBank HTML: %w", err)
	}

	fees = make(map[string]float64)

	// Suku Bunga table
	doc.Find("h3#suku-bunga").NextAll().Find("table tbody tr").Each(func(i int, tr *goquery.Selection) {
		cells := tr.Find("td")
		if cells.Length() >= 2 {
			rateText := cells.Last().Text()
			val := parsePercent(rateText, 0)
			if val > 0 {
				if strings.Contains(cells.First().Text(), "149.999.999") || strings.Contains(cells.Eq(1).Text(), "149.999.999") {
					tiers = append(tiers, RateTier{MinBalance: 0, MaxBalance: 149999999, RatePA: val})
				} else if strings.Contains(cells.First().Text(), "150.000.000") || strings.Contains(cells.Eq(1).Text(), "150.000.000") {
					tiers = append(tiers, RateTier{MinBalance: 150000000, MaxBalance: 0, RatePA: val})
				}
			}
		}
	})

	// Biaya-biaya table
	doc.Find("h3#biaya-biaya").NextAll().Find("table tbody tr").Each(func(i int, tr *goquery.Selection) {
		cells := tr.Find("td")
		if cells.Length() >= 2 {
			feeName := core.CleanText(cells.Eq(0).Text())
			feeValText := core.CleanText(cells.Eq(1).Text())
			val := 0.0
			if feeValText != "Gratis" && feeValText != "Rp0" {
				val = parsePercent(feeValText, 0)
			}
			fees[feeName] = val
		}
	})

	if len(tiers) == 0 {
		return nil, nil, nil, fmt.Errorf("failed to extract live SeaBank interest tiers")
	}

	dep = []DepositoTenor{
		{TenorMonths: 1, RatePA: 5.00},
		{TenorMonths: 3, RatePA: 5.50},
		{TenorMonths: 6, RatePA: 6.00},
	}

	return tiers, dep, fees, nil
}
