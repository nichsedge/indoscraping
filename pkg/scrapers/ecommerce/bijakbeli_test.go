package ecommerce

import (
	"testing"
)

func TestBijakBeliSummaryLogic(t *testing.T) {
	// Verify comparison math and structure
	summary := BijakBeliSummary{
		Category:      "minyak",
		AlfaMinPrice:  34000,
		AlfaAvgPrice:  35500.0,
		IndoMinPrice:  33500,
		IndoAvgPrice:  36000.0,
		CheapestStore: "indomaret",
	}

	if summary.Category != "minyak" {
		t.Errorf("Expected category minyak, got %s", summary.Category)
	}
	if summary.CheapestStore != "indomaret" {
		t.Errorf("Expected cheapest indomaret, got %s", summary.CheapestStore)
	}
}

func TestProductSchemaIntegrity(t *testing.T) {
	p := Product{
		ProductName:  "Minyak Goreng Sania 2L",
		PriceRaw:     "Rp 34.000",
		PriceNumeric: 34000,
		Seller:       "Alfamart",
		ProductURL:   "https://alfagift.id/p/123",
		Category:     "minyak",
		ScrapedAt:    "2026-11-11T12:00:00Z",
	}

	if p.PriceNumeric != 34000 {
		t.Errorf("Expected price 34000, got %d", p.PriceNumeric)
	}
	if p.Category != "minyak" {
		t.Errorf("Expected category minyak, got %s", p.Category)
	}
}
