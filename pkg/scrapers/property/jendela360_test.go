package property

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestJendela360UnmarshalingWithFloatUnitArea(t *testing.T) {
	mockJSON := `{
		"current_page": 1,
		"last_page": 1,
		"total": 1,
		"data": [
			{
				"id": 46486,
				"code": "URKB245",
				"name": "Strategic Location 1BR Apartment",
				"price": 6380000,
				"bedroom": 1,
				"bathroom": 1,
				"unit_area": 60.64,
				"tower": "5 (Bizloft)",
				"apartment_name": "U Residence Karawaci",
				"apartment_slug": "u-residence-karawaci"
			}
		]
	}`

	var apiResp struct {
		Data []struct {
			ID            int     `json:"id"`
			Code          string  `json:"code"`
			Name          string  `json:"name"`
			Price         int     `json:"price"`
			Bedroom       int     `json:"bedroom"`
			Bathroom      int     `json:"bathroom"`
			UnitArea      float64 `json:"unit_area"`
			Tower         string  `json:"tower"`
			ApartmentName string  `json:"apartment_name"`
			ApartmentSlug string  `json:"apartment_slug"`
		} `json:"data"`
	}

	err := json.Unmarshal([]byte(mockJSON), &apiResp)
	if err != nil {
		t.Fatalf("Failed to unmarshal JSON with float unit_area: %v", err)
	}

	if len(apiResp.Data) != 1 {
		t.Fatalf("Expected 1 item, got %d", len(apiResp.Data))
	}
	item := apiResp.Data[0]
	if item.UnitArea != 60.64 {
		t.Errorf("Expected unit_area 60.64, got %f", item.UnitArea)
	}
	if item.Code != "URKB245" {
		t.Errorf("Expected code URKB245, got %s", item.Code)
	}
}

func TestJendela360MockServer(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{
			"current_page": 1,
			"data": [
				{
					"id": 101,
					"code": "TEST01",
					"name": "Test Apt",
					"price": 5000000,
					"bedroom": 2,
					"bathroom": 1,
					"unit_area": 45.5,
					"tower": "A",
					"apartment_name": "Test Residence",
					"apartment_slug": "test-residence"
				}
			]
		}`))
	}))
	defer ts.Close()

	// Direct unmarshal test against server payload
	resp, err := http.Get(ts.URL)
	if err != nil {
		t.Fatalf("Failed request to mock server: %v", err)
	}
	defer resp.Body.Close()

	var apiResp struct {
		Data []struct {
			ID       int     `json:"id"`
			Code     string  `json:"code"`
			UnitArea float64 `json:"unit_area"`
		} `json:"data"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&apiResp); err != nil {
		t.Fatalf("Decode failed: %v", err)
	}
	if len(apiResp.Data) != 1 || apiResp.Data[0].UnitArea != 45.5 {
		t.Errorf("Unexpected result: %+v", apiResp)
	}
}
