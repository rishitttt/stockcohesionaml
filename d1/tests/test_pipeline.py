import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from nifty200_pipeline.pipeline import build_final_dataset


class FinalDatasetAssemblyTests(unittest.TestCase):
    def test_unresolved_tickers_are_excluded_from_filtered_outputs(self) -> None:
        master_universe = pd.DataFrame({"Ticker": ["AAA", "BBB"]})
        monthly_membership = pd.DataFrame(
            {
                "Month_End": pd.to_datetime(["2025-01-31", "2025-01-31"]),
                "Ticker": ["AAA", "BBB"],
                "In_Nifty200": [True, True],
            }
        )
        weekly_membership = pd.DataFrame(
            {
                "Date": pd.to_datetime(["2025-01-03", "2025-01-03"]),
                "Ticker": ["AAA", "BBB"],
                "In_Nifty200": [True, True],
            }
        )
        reconciliation = pd.DataFrame(
            {
                "snapshot_date": pd.to_datetime(["2025-01-31"]),
                "official_count": [2],
                "replayed_count": [2],
                "missing_from_replay": [0],
                "extra_in_replay": [0],
            }
        )
        sectors = pd.DataFrame(
            {
                "Ticker": ["AAA", "BBB"],
                "Sector_Coarse": ["FINANCE", "ENERGY"],
                "Sector_Fine": ["Banks", "Oil & Gas"],
            }
        )
        promoter_history = pd.DataFrame(
            {
                "Ticker": ["AAA", "BBB"],
                "Quarter_End": pd.to_datetime(["2024-12-31", "2024-12-31"]),
                "Promoter_Group": ["Independent", "Adani"],
                "Dominant_Promoter_Entity": ["Alpha Holdings", "Beta Holdings"],
                "Dominant_Promoter_Shares": [100.0, 200.0],
            }
        )
        unresolved = pd.DataFrame({"Ticker": ["BBB"], "Reason": ["quarter parse failed"]})
        prices = pd.DataFrame(
            {
                "Date": pd.to_datetime(["2025-01-03", "2025-01-03"]),
                "Ticker": ["AAA", "BBB"],
                "Adj_Close": [101.0, 202.0],
                "Weekly_Return": [0.01, 0.02],
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("nifty200_pipeline.pipeline.build_membership_history") as build_membership_history:
                with patch("nifty200_pipeline.pipeline.build_sector_map", return_value=sectors):
                    with patch("nifty200_pipeline.pipeline.build_promoter_history", return_value=(promoter_history, unresolved)):
                        with patch("nifty200_pipeline.pipeline.build_weekly_prices", return_value=prices):
                            build_membership_history.return_value = (
                                master_universe,
                                monthly_membership,
                                weekly_membership,
                                reconciliation,
                                [],
                            )
                            outputs = build_final_dataset(Path(tmpdir))

            filtered_universe = pd.read_csv(outputs["master_universe_filtered"])
            filtered_weekly_membership = pd.read_csv(outputs["weekly_membership_filtered"])
            panel = pd.read_csv(outputs["weekly_panel"])

            self.assertEqual(filtered_universe["Ticker"].tolist(), ["AAA"])
            self.assertEqual(filtered_weekly_membership["Ticker"].tolist(), ["AAA"])
            self.assertEqual(panel["Ticker"].tolist(), ["AAA"])


if __name__ == "__main__":
    unittest.main()
