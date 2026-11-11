package banking

import (
	"testing"
)

func TestCalculateEffectiveAPY(t *testing.T) {
	tiers := []RateTier{
		{MinBalance: 0, MaxBalance: 50000000, RatePA: 0.0},
		{MinBalance: 50000000, MaxBalance: 500000000, RatePA: 1.0},
	}

	// Below tier 1: 0%
	if apy := CalculateEffectiveAPY(tiers, 25000000); apy != 0.0 {
		t.Errorf("expected 0.0, got %f", apy)
	}

	// In tier 2: Rp 100M total. Rp 50M at 0%, Rp 50M at 1.0% -> total yield Rp 500k -> 0.5% APY
	apy := CalculateEffectiveAPY(tiers, 100000000)
	expected := 0.50
	if apy < expected-0.01 || apy > expected+0.01 {
		t.Errorf("expected ~%f, got %f", expected, apy)
	}

	// Flat tier test (e.g. digital bank)
	flatTiers := []RateTier{
		{MinBalance: 0, MaxBalance: 0, RatePA: 3.0},
	}
	if apy := CalculateEffectiveAPY(flatTiers, 10000000); apy != 3.0 {
		t.Errorf("expected 3.0, got %f", apy)
	}
}

func TestEvaluateRetailerScores(t *testing.T) {
	banks := []BankAccountProfile{
		{
			BankID:              "trad_bank",
			BankName:            "Traditional Bank",
			BankType:            "KBMI 4 Commercial",
			AccountName:         "Business Checking",
			MonthlyAdminFee:     15000,
			MonthlyDebitCardFee: 0,
			BiFastFee:           2500,
			FreeTransferQuota:   0,
			QRISSettlementSpeed: "T+0",
			CashDepositNetwork:  "Nationwide CRM",
			DailyBiFastLimit:    250000000,
			SavingsTiers: []RateTier{
				{MinBalance: 0, MaxBalance: 0, RatePA: 0.1},
			},
		},
		{
			BankID:              "digital_bank",
			BankName:            "Digital Bank",
			BankType:            "Digital Bank",
			AccountName:         "High Yield Digital",
			MonthlyAdminFee:     0,
			MonthlyDebitCardFee: 0,
			BiFastFee:           0,
			FreeTransferQuota:   50,
			QRISSettlementSpeed: "T+1",
			CashDepositNetwork:  "Partner",
			DailyBiFastLimit:    100000000,
			SavingsTiers: []RateTier{
				{MinBalance: 0, MaxBalance: 0, RatePA: 3.5},
			},
		},
	}

	scenario := RetailerScenario{
		ProfileName:         "Micro Merchant",
		AverageIdleBalance:  20000000, // Rp 20M
		MonthlyTransfersOut: 20,
		MonthlyCardSpend:    1000000,
	}

	results := EvaluateRetailerScores(banks, scenario)
	if len(results) != 2 {
		t.Fatalf("expected 2 results, got %d", len(results))
	}

	// Ranks should be 1 and 2
	if results[0].Rank != 1 || results[1].Rank != 2 {
		t.Errorf("incorrect ranks: %d, %d", results[0].Rank, results[1].Rank)
	}

	// Digital bank should have significantly higher net annual benefit
	var digitalRes, tradRes RetailerEvaluationResult
	for _, r := range results {
		if r.BankID == "digital_bank" {
			digitalRes = r
		} else {
			tradRes = r
		}
	}

	if digitalRes.NetAnnualBenefit <= tradRes.NetAnnualBenefit {
		t.Errorf("expected digital bank net benefit (%f) to exceed traditional (%f)",
			digitalRes.NetAnnualBenefit, tradRes.NetAnnualBenefit)
	}
}
