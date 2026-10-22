package ecommerce

// Product represents a standardized e-commerce product schema.
type Product struct {
	ProductName  string `json:"productName"`
	PriceRaw     string `json:"priceRaw"`
	PriceNumeric int    `json:"priceNumeric"`
	Seller       string `json:"seller"`
	ProductURL   string `json:"productUrl"`
	Category     string `json:"category"`
	ScrapedAt    string `json:"scrapedAt,omitempty"`
}
