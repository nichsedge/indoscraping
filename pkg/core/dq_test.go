package core

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestDataQualityPriceParsingEdgeCases(t *testing.T) {
	testCases := []struct {
		input    string
		expected int
	}{
		{"Rp 0", 0},
		{"Rp 100", 100},
		{"Rp. 99.900,-", 99900},
		{"IDR 50.000", 50000},
		{"   Rp   1.500.000   ", 1500000},
		{"Free", 0},
		{"Hubungi Kami", 0},
		{"Invalid", 0},
	}

	for _, tc := range testCases {
		got := ParseNumericPrice(tc.input)
		if got != tc.expected {
			t.Errorf("ParseNumericPrice(%q) = %d; want %d", tc.input, got, tc.expected)
		}
	}
}

func TestDataQualityTextSanitization(t *testing.T) {
	testCases := []struct {
		input    string
		expected string
	}{
		{"<h1>Header</h1><p>Paragraph with <a href='#'>link</a></p>", "Header Paragraph with link"},
		{"&quot;Double Quotes&quot; &amp; &lt;brackets&gt;", "\"Double Quotes\" & <brackets>"},
		{"Multiple   spaces   and\n\nnewlines\t\tpreserved as single space", "Multiple spaces and newlines preserved as single space"},
	}

	for _, tc := range testCases {
		got := CleanText(tc.input)
		if got != tc.expected {
			t.Errorf("CleanText(%q) = %q; want %q", tc.input, got, tc.expected)
		}
	}
}

func TestDataQualityAtomicOutputAndMetadata(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "indoscraping_dq_*")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tmpDir)

	latestPath := filepath.Join(tmpDir, "test_category", "latest.json")
	historyPath := filepath.Join(tmpDir, "test_category", "history", "2026-11-11.json")

	type sampleItem struct {
		ID    int    `json:"id"`
		Title string `json:"title"`
		Price int    `json:"price"`
	}

	payload := []sampleItem{
		{ID: 1, Title: "Item A", Price: 10000},
		{ID: 2, Title: "Item B", Price: 20000},
	}

	meta := map[string]interface{}{
		"scraper":     "test-scraper",
		"items_count": len(payload),
	}

	if err := WriteLatestAndHistory(latestPath, historyPath, payload, meta); err != nil {
		t.Fatalf("WriteLatestAndHistory failed: %v", err)
	}

	// 1. Verify latest.json
	latestBytes, err := os.ReadFile(latestPath)
	if err != nil {
		t.Fatalf("Failed to read latest.json: %v", err)
	}
	var readItems []sampleItem
	if err := json.Unmarshal(latestBytes, &readItems); err != nil {
		t.Fatalf("Failed to unmarshal latest.json: %v", err)
	}
	if len(readItems) != 2 || readItems[0].Title != "Item A" {
		t.Errorf("Unexpected latest.json payload: %+v", readItems)
	}

	// 2. Verify history/YYYY-MM-DD.json
	if _, err := os.Stat(historyPath); os.IsNotExist(err) {
		t.Fatalf("History file not created: %s", historyPath)
	}

	// 3. Verify .meta.json lineage sidecar
	metaPath := filepath.Join(tmpDir, "test_category", "latest.meta.json")
	metaBytes, err := os.ReadFile(metaPath)
	if err != nil {
		t.Fatalf("Failed to read .meta.json: %v", err)
	}
	var readMeta map[string]interface{}
	if err := json.Unmarshal(metaBytes, &readMeta); err != nil {
		t.Fatalf("Failed to unmarshal .meta.json: %v", err)
	}
	if readMeta["scraper"] != "test-scraper" {
		t.Errorf("Unexpected meta content: %+v", readMeta)
	}
}
