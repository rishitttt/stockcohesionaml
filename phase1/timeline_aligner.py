"""
timeline_aligner.py — Merge weekly prices with promoter & sector labels.

Produces an aligned panel DataFrame with forward-filled promoter labels
and computed weekly log-returns.

Functions:
    compute_weekly_returns(prices_df) -> pd.DataFrame
    align_timeline(prices_df, promoter_df, sector_df) -> pd.DataFrame
    load_or_align(...) -> pd.DataFrame
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ALIGNED_PANEL_PATH

logger = logging.getLogger(__name__)


def compute_weekly_returns(prices_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute weekly log-returns from a wide-format closing price DataFrame.

    Args:
        prices_df: DataFrame with DatetimeIndex and ticker columns.

    Returns:
        DataFrame of same shape with log-returns. First row is NaN.
    """
    returns = np.log(prices_df / prices_df.shift(1))
    return returns


def align_timeline(
    prices_df: pd.DataFrame,
    promoter_df: pd.DataFrame,
    sector_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Merge weekly price data with promoter and sector labels into a
    long-format panel DataFrame.

    The promoter labels are static (no quarterly variation in this version),
    so they are simply joined. When quarterly promoter data is available,
    this function handles forward-filling within each quarter.

    Args:
        prices_df: Wide-format DataFrame (index=Date, columns=tickers)
                   with weekly closing prices.
        promoter_df: DataFrame with columns ['ticker', 'promoter_group'].
        sector_df: DataFrame with columns ['ticker', 'nse_sector', 'gics_sub_industry'].

    Returns:
        Long-format DataFrame with columns:
            - date (DatetimeIndex)
            - ticker
            - close
            - weekly_return
            - promoter_group
            - nse_sector
            - gics_sub_industry
        Saved to parquet at ALIGNED_PANEL_PATH.
    """
    logger.info("Aligning timeline...")

    # 1. Compute returns (wide format)
    returns_df = compute_weekly_returns(prices_df)

    # 2. Melt prices and returns to long format
    prices_long = prices_df.reset_index().melt(
        id_vars=prices_df.index.name or "Date",
        var_name="ticker",
        value_name="close",
    )
    date_col = prices_df.index.name or "Date"
    prices_long.rename(columns={date_col: "date"}, inplace=True)

    returns_long = returns_df.reset_index().melt(
        id_vars=returns_df.index.name or "Date",
        var_name="ticker",
        value_name="weekly_return",
    )
    returns_long.rename(columns={returns_df.index.name or "Date": "date"}, inplace=True)

    # 3. Merge prices and returns
    panel = prices_long.merge(returns_long, on=["date", "ticker"], how="left")

    # 4. Merge promoter labels
    panel = panel.merge(promoter_df[["ticker", "promoter_group"]], on="ticker", how="left")

    # 5. Merge sector labels
    panel = panel.merge(
        sector_df[["ticker", "nse_sector", "gics_sub_industry"]],
        on="ticker",
        how="left",
    )

    # 6. Fill missing labels with defaults
    panel["promoter_group"] = panel["promoter_group"].fillna("Independent")
    panel["nse_sector"] = panel["nse_sector"].fillna("Other")
    panel["gics_sub_industry"] = panel["gics_sub_industry"].fillna("Unclassified")

    # 7. Sort for clean output
    panel.sort_values(["date", "ticker"], inplace=True)
    panel.reset_index(drop=True, inplace=True)

    # 8. Summary
    n_dates = panel["date"].nunique()
    n_tickers = panel["ticker"].nunique()
    n_valid = panel["weekly_return"].notna().sum()
    logger.info(
        f"Aligned panel: {n_dates} dates × {n_tickers} tickers = "
        f"{len(panel)} rows ({n_valid} valid returns)."
    )

    return panel


def load_or_align(
    prices_df: pd.DataFrame,
    promoter_df: pd.DataFrame,
    sector_df: pd.DataFrame,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """
    Load aligned panel from cache or build from inputs.

    Args:
        prices_df, promoter_df, sector_df: Input DataFrames.
        force_refresh: If True, rebuild even if cache exists.

    Returns:
        Aligned panel DataFrame.
    """
    if not force_refresh and ALIGNED_PANEL_PATH.exists():
        logger.info(f"Loading cached aligned panel from {ALIGNED_PANEL_PATH}")
        return pd.read_parquet(ALIGNED_PANEL_PATH)

    panel = align_timeline(prices_df, promoter_df, sector_df)
    panel.to_parquet(ALIGNED_PANEL_PATH, engine="pyarrow", index=False)
    logger.info(f"Saved aligned panel to {ALIGNED_PANEL_PATH}")
    return panel


# ─── CLI Entry Point ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    from price_fetcher import load_or_fetch_prices
    from promoter_mapping import get_promoter_labels
    from sector_mapping import get_sector_labels

    prices = load_or_fetch_prices()
    promoters = get_promoter_labels()
    sectors = get_sector_labels()

    panel = load_or_align(prices, promoters, sectors, force_refresh=True)
    print(f"\nPanel shape: {panel.shape}")
    print(panel.head(10))
