from __future__ import annotations

from pathlib import Path

import pandas as pd

from .membership import build_membership_history
from .pricing import build_weekly_prices
from .promoters import build_promoter_history
from .sectors import build_sector_map
from .util import ensure_dir


def forward_join_promoters(panel: pd.DataFrame, promoter_history: pd.DataFrame) -> pd.DataFrame:
    if promoter_history.empty:
        panel["Promoter_Group"] = None
        return panel
    left = panel.copy()
    right = promoter_history.copy()
    left["Date"] = pd.to_datetime(left["Date"])
    right["Quarter_End"] = pd.to_datetime(right["Quarter_End"])

    stitched: list[pd.DataFrame] = []
    for ticker, ticker_panel in left.groupby("Ticker", sort=False):
        promoter_slice = right[right["Ticker"] == ticker][["Quarter_End", "Promoter_Group"]].sort_values("Quarter_End")
        ticker_panel = ticker_panel.sort_values("Date")
        if promoter_slice.empty:
            ticker_panel["Promoter_Group"] = None
            stitched.append(ticker_panel)
            continue
        merged = pd.merge_asof(
            ticker_panel,
            promoter_slice,
            left_on="Date",
            right_on="Quarter_End",
            direction="backward",
        )
        stitched.append(merged.drop(columns=["Quarter_End"]))
    merged = pd.concat(stitched, ignore_index=True)
    merged["Date"] = merged["Date"].dt.date
    return merged


def build_final_dataset(project_root: Path) -> dict[str, Path]:
    raw_dir = ensure_dir(project_root / "data" / "raw")
    processed_dir = ensure_dir(project_root / "data" / "processed")

    print("Stage 1/5: rebuilding membership history", flush=True)
    master_universe, monthly_membership, weekly_membership, reconciliation, snapshots = build_membership_history(raw_dir)
    raw_master_universe = master_universe.copy()
    raw_monthly_membership = monthly_membership.copy()
    raw_weekly_membership = weekly_membership.copy()
    print(f"  master universe size: {len(master_universe)}", flush=True)

    print("Stage 2/5: sector mapping", flush=True)
    sectors = build_sector_map(master_universe, snapshots, raw_dir)

    print("Stage 3/5: promoter history", flush=True)
    promoter_history, unresolved = build_promoter_history(master_universe, raw_dir)
    unresolved_tickers = set(unresolved["Ticker"].unique()) if not unresolved.empty else set()
    eligible_tickers = set(master_universe["Ticker"]) - unresolved_tickers
    filtered_master_universe = master_universe[master_universe["Ticker"].isin(eligible_tickers)].copy()
    filtered_monthly_membership = monthly_membership[monthly_membership["Ticker"].isin(eligible_tickers)].copy()
    filtered_weekly_membership = weekly_membership[weekly_membership["Ticker"].isin(eligible_tickers)].copy()
    filtered_sectors = sectors[sectors["Ticker"].isin(eligible_tickers)].copy()

    print("Stage 4/5: prices and weekly returns", flush=True)
    prices = build_weekly_prices(sorted(eligible_tickers), raw_dir)
    panel = filtered_weekly_membership.merge(prices, on=["Date", "Ticker"], how="left")
    panel = panel.merge(filtered_sectors, on="Ticker", how="left")
    panel = forward_join_promoters(panel, promoter_history)
    panel = panel[panel["In_Nifty200"]].copy()
    panel = panel[panel["Promoter_Group"].notna()].sort_values(["Date", "Ticker"]).reset_index(drop=True)
    final_tickers = set(panel["Ticker"].unique())
    filtered_master_universe = filtered_master_universe[filtered_master_universe["Ticker"].isin(final_tickers)].copy()
    filtered_monthly_membership = filtered_monthly_membership[filtered_monthly_membership["Ticker"].isin(final_tickers)].copy()
    filtered_weekly_membership = filtered_weekly_membership[filtered_weekly_membership["Ticker"].isin(final_tickers)].copy()

    print("Stage 5/5: writing outputs", flush=True)

    outputs = {
        "master_universe": processed_dir / "master_universe.csv",
        "master_universe_filtered": processed_dir / "master_universe_filtered.csv",
        "monthly_membership": processed_dir / "monthly_membership.csv",
        "monthly_membership_filtered": processed_dir / "monthly_membership_filtered.csv",
        "weekly_membership": processed_dir / "weekly_membership.csv",
        "weekly_membership_filtered": processed_dir / "weekly_membership_filtered.csv",
        "weekly_panel": processed_dir / "weekly_panel.csv",
        "reconciliation": processed_dir / "membership_reconciliation.csv",
        "promoter_history": processed_dir / "promoter_history.csv",
        "unresolved_promoters": processed_dir / "unresolved_promoters.csv",
        "sector_map": processed_dir / "sector_map.csv",
    }
    raw_master_universe.to_csv(outputs["master_universe"], index=False)
    filtered_master_universe.to_csv(outputs["master_universe_filtered"], index=False)
    raw_monthly_membership.to_csv(outputs["monthly_membership"], index=False)
    filtered_monthly_membership.to_csv(outputs["monthly_membership_filtered"], index=False)
    raw_weekly_membership.to_csv(outputs["weekly_membership"], index=False)
    filtered_weekly_membership.to_csv(outputs["weekly_membership_filtered"], index=False)
    panel.to_csv(outputs["weekly_panel"], index=False)
    reconciliation.to_csv(outputs["reconciliation"], index=False)
    promoter_history.to_csv(outputs["promoter_history"], index=False)
    unresolved.to_csv(outputs["unresolved_promoters"], index=False)
    sectors.to_csv(outputs["sector_map"], index=False)
    return outputs
