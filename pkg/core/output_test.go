package core

import (
	"testing"
)

func TestCleanText(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"<p>Hello   world</p>", "Hello world"},
		{"  Indomaret   \t\n  Special\u00a0Promo  ", "Indomaret Special Promo"},
		{"<div><b>Bold</b> & <i>Italic</i></div>", "Bold & Italic"},
		{"Normal Text", "Normal Text"},
		{"", ""},
		{"<br/><hr/>", ""},
	}

	for _, tc := range tests {
		got := CleanText(tc.input)
		if got != tc.expected {
			t.Errorf("CleanText(%q) = %q; want %q", tc.input, got, tc.expected)
		}
	}
}

func TestParseNumericPrice(t *testing.T) {
	tests := []struct {
		input    string
		expected int
	}{
		{"Rp 15.000", 15000},
		{"Rp15.000,00", 15000},
		{"Rp 1.250.000", 1250000},
		{"45000", 45000},
		{"Gratis", 0},
		{"", 0},
	}

	for _, tc := range tests {
		got := ParseNumericPrice(tc.input)
		if got != tc.expected {
			t.Errorf("ParseNumericPrice(%q) = %d; want %d", tc.input, got, tc.expected)
		}
	}
}

func TestFormatIDR(t *testing.T) {
	tests := []struct {
		input    int
		expected string
	}{
		{0, "0"},
		{500, "500"},
		{15000, "15.000"},
		{1250000, "1.250.000"},
		{2630000, "2.630.000"},
	}

	for _, tc := range tests {
		got := FormatIDR(tc.input)
		if got != tc.expected {
			t.Errorf("FormatIDR(%d) = %q; want %q", tc.input, got, tc.expected)
		}
	}
}

func BenchmarkCleanText(b *testing.B) {
	input := `<div class="product-card"><h3> Indomaret Super   Promo </h3>\n\t<span>Rp 25.000\u00a0disc</span></div>`
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = CleanText(input)
	}
}

func BenchmarkParseNumericPrice(b *testing.B) {
	input := "Rp 1.250.000,00"
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = ParseNumericPrice(input)
	}
}

func BenchmarkFormatIDR(b *testing.B) {
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = FormatIDR(2630000)
	}
}
