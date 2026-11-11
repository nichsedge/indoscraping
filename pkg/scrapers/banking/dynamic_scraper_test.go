package banking

import (
	"testing"

	"github.com/nichsedge/indoscraping/pkg/core"
)

func TestLiveBCASBDKScraper(t *testing.T) {
	client := core.HTTPClient()
	sbdk, err := ScrapeBCASBDK(client)
	if err != nil {
		t.Fatalf("Live BCA SBDK scrape failed: %v", err)
	}

	if sbdk.Korporasi <= 0 || sbdk.Ritel <= 0 {
		t.Errorf("Invalid scraped BCA SBDK values: %+v", sbdk)
	}

	t.Logf("✅ Successfully scraped live BCA SBDK: Korporasi=%.2f%%, Ritel=%.2f%%, Mikro=%.2f%% (Period: %s)",
		sbdk.Korporasi, sbdk.Ritel, sbdk.Mikro, sbdk.Period)
}

func TestLiveMandiriSBDKScraper(t *testing.T) {
	client := core.HTTPClient()
	sbdk, err := ScrapeMandiriSBDK(client)
	if err != nil {
		t.Fatalf("Live Mandiri SBDK scrape failed: %v", err)
	}

	if sbdk.Korporasi <= 0 || sbdk.Ritel <= 0 {
		t.Errorf("Invalid scraped Mandiri SBDK values: %+v", sbdk)
	}

	t.Logf("✅ Successfully scraped live Mandiri SBDK: Korporasi=%.2f%%, Ritel=%.2f%%, Mikro=%.2f%% (Period: %s)",
		sbdk.Korporasi, sbdk.Ritel, sbdk.Mikro, sbdk.Period)
}

func TestLiveMandiriDanaScraper(t *testing.T) {
	client := core.HTTPClient()
	tiers, dep, err := ScrapeMandiriDana(client)
	if err != nil {
		t.Fatalf("Live Mandiri Dana scrape failed: %v", err)
	}

	if len(tiers) == 0 || len(dep) == 0 {
		t.Errorf("Empty Mandiri tiers or deposit tenors: tiers=%d, dep=%d", len(tiers), len(dep))
	}

	t.Logf("✅ Successfully scraped live Mandiri Dana: %d savings tiers, %d deposit tenors", len(tiers), len(dep))
}

func TestLiveSeaBankScraper(t *testing.T) {
	client := core.HTTPClient()
	tiers, dep, fees, err := ScrapeSeaBank(client)
	if err != nil {
		t.Fatalf("Live SeaBank scrape failed: %v", err)
	}

	if len(tiers) == 0 {
		t.Errorf("Expected SeaBank tiers, got 0")
	}

	t.Logf("✅ Successfully scraped live SeaBank: %d savings tiers, %d deposit tenors, %d fee types",
		len(tiers), len(dep), len(fees))
}
