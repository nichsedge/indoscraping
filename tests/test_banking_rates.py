"""Tests for the Indonesian Banking Rates scraper and retailer evaluation model."""

import unittest
from indoscraping.scraper.banking.rates import (
    calculate_effective_apy,
    evaluate_retailers,
    format_idr,
    get_bank_profiles,
)


class TestBankingRates(unittest.TestCase):
    def test_format_idr(self):
        self.assertEqual(format_idr(25000000), "25.000.000")
        self.assertEqual(format_idr(0), "0")
        self.assertEqual(format_idr(-1250000), "-1.250.000")

    def test_calculate_effective_apy(self):
        tiers = [
            {"min_balance": 0, "max_balance": 50000000, "rate_pa": 0.0},
            {"min_balance": 50000000, "max_balance": 500000000, "rate_pa": 1.0},
        ]

        # Balance below threshold
        self.assertEqual(calculate_effective_apy(tiers, 25000000), 0.0)

        # Rp 100M: Rp 50M at 0%, Rp 50M at 1% -> Rp 500k yield / 100M = 0.5%
        apy = calculate_effective_apy(tiers, 100000000)
        self.assertAlmostEqual(apy, 0.50, delta=0.01)

        # Flat tier
        flat = [{"min_balance": 0, "max_balance": 0, "rate_pa": 3.0}]
        self.assertEqual(calculate_effective_apy(flat, 10000000), 3.0)

    def test_evaluate_retailers(self):
        banks = [
            {
                "bank_id": "trad",
                "bank_name": "Trad Bank",
                "bank_type": "KBMI 4 Commercial",
                "account_name": "Trad Checking",
                "monthly_admin_fee": 15000,
                "monthly_debit_card_fee": 0,
                "min_balance_required": 50000,
                "below_min_penalty": 0,
                "bi_fast_fee": 2500,
                "free_transfer_quota": 0,
                "daily_bi_fast_limit": 250000000,
                "qris_settlement_speed": "T+0",
                "cash_deposit_network": "Nationwide ATM",
                "cashback_debit_pct": 0.1,
                "savings_tiers": [{"min_balance": 0, "max_balance": 0, "rate_pa": 0.1}],
            },
            {
                "bank_id": "digi",
                "bank_name": "Digi Bank",
                "bank_type": "Digital Bank",
                "account_name": "Digi Yield",
                "monthly_admin_fee": 0,
                "monthly_debit_card_fee": 0,
                "min_balance_required": 0,
                "below_min_penalty": 0,
                "bi_fast_fee": 0,
                "free_transfer_quota": 50,
                "daily_bi_fast_limit": 100000000,
                "qris_settlement_speed": "T+1",
                "cash_deposit_network": "Partner",
                "cashback_debit_pct": 0.2,
                "savings_tiers": [{"min_balance": 0, "max_balance": 0, "rate_pa": 3.5}],
            },
        ]

        results = evaluate_retailers(banks, idle_balance=20000000, transfers_out=25, card_spend=1000000)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["rank"], 1)
        self.assertEqual(results[1]["rank"], 2)

        # Digital bank has higher net benefit
        digi_res = next(r for r in results if r["bank_id"] == "digi")
        trad_res = next(r for r in results if r["bank_id"] == "trad")
        self.assertGreater(digi_res["net_annual_benefit"], trad_res["net_annual_benefit"])

    def test_bank_profiles_integrity(self):
        profiles = get_bank_profiles()
        self.assertGreaterEqual(len(profiles), 7)
        required_keys = {"bank_id", "bank_name", "bank_type", "account_name", "monthly_admin_fee", "savings_tiers", "sbdk"}
        for p in profiles:
            self.assertTrue(required_keys.issubset(p.keys()))
            self.assertGreater(len(p["savings_tiers"]), 0)
            self.assertIn("ritel_pa", p["sbdk"])


if __name__ == "__main__":
    unittest.main()
