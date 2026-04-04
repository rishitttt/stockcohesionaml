"""
rolling_correlation.py — 52-week rolling pairwise correlation engine.

Computes a rolling 200×200 Pearson correlation matrix of weekly returns,
then extracts baseline correlation, same-sector excess, and same-group
excess correlations using boolean masking.

Vectorized NumPy implementation — no nested Python loops over stock pairs.

Functions:
    compute_rolling_correlations(aligned_df, window, min_pairs) -> pd.DataFrame
    load_or_compute_correlations(...) -> pd.DataFrame
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd
from tqdm import tqdm

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ROLLING_CORR_PATH, ROLLING_WINDOW_WEEKS, MIN_PAIRS_THRESHOLD

logger = logging.getLogger(__name__)


def _build_masks(
    tickers: list,
    promoter_map: dict,
    sector_map: dict,
) -> tuple:
    """
    Build boolean masks for the upper triangle of the N×N correlation matrix.

    Args:
        tickers: Ordered list of ticker symbols.
        promoter_map: {ticker: promoter_group}
        sector_map: {ticker: nse_sector}

    Returns:
        Tuple of (upper_tri_mask, same_sector_diff_promoter, same_promoter_diff_sector)
        Each is a 2D boolean numpy array of shape (N, N).
    """
    n = len(tickers)

    promoter_arr = np.array([promoter_map.get(t, "Independent") for t in tickers])
    sector_arr = np.array([sector_map.get(t, "Other") for t in tickers])

    # NxN comparison matrices (broadcasting)
    same_promoter = promoter_arr[:, None] == promoter_arr[None, :]
    same_sector = sector_arr[:, None] == sector_arr[None, :]

    # Upper triangle (excluding diagonal) — unique pairs only
    upper_tri = np.triu(np.ones((n, n), dtype=bool), k=1)

    # Mask 1: Same sector but different promoter
    same_sector_diff_promoter = upper_tri & same_sector & ~same_promoter

    # Mask 2: Same promoter but different sector
    # Exclude "Independent" from same-promoter analysis (they're not actually
    # related — "Independent" is the default catch-all bucket)
    independent_mask = promoter_arr == "Independent"
    both_independent = independent_mask[:, None] & independent_mask[None, :]
    same_promoter_diff_sector = upper_tri & same_promoter & ~same_sector & ~both_independent

    return upper_tri, same_sector_diff_promoter, same_promoter_diff_sector


def compute_rolling_correlations(
    aligned_df: pd.DataFrame,
    window: int = ROLLING_WINDOW_WEEKS,
    min_pairs: int = MIN_PAIRS_THRESHOLD,
) -> pd.DataFrame:
    """
    Compute rolling pairwise correlations and extract excess correlations
    for sector and promoter group subsets.

    Algorithm:
        1. Pivot the aligned panel to wide format: (date × ticker) returns
        2. For each rolling window endpoint t:
           - Extract [t-window : t] returns sub-matrix
           - Compute N×N Pearson correlation via pandas .corr()
           - Extract upper-triangle means for baseline, sector mask, group mask
           - Apply noise filter (min_pairs threshold)
           - Excess = subset_mean - baseline

    Args:
        aligned_df: Long-format panel with columns
                    [date, ticker, weekly_return, promoter_group, nse_sector].
        window: Rolling window size in weeks.
        min_pairs: Minimum valid pairs required for a subset mean;
                   below this the mean is set to NaN.

    Returns:
        pd.DataFrame with columns:
            - date: Window end date
            - baseline: Mean of all unique pairwise correlations
            - sector_excess: Same-sector, different-promoter mean - baseline
            - group_excess: Same-promoter, different-sector mean - baseline
            - n_tickers: Number of tickers with valid data in this window
            - n_sector_pairs: Count of valid same-sector, diff-promoter pairs
            - n_group_pairs: Count of valid same-promoter, diff-sector pairs
    """
    logger.info(f"Computing rolling correlations (window={window}, min_pairs={min_pairs})...")

    # ── Step 1: Pivot to wide returns matrix ──
    returns_wide = aligned_df.pivot_table(
        index="date", columns="ticker", values="weekly_return"
    )
    returns_wide.sort_index(inplace=True)

    dates = returns_wide.index
    all_tickers = returns_wide.columns.tolist()
    n_dates = len(dates)

    logger.info(f"Returns matrix shape: {returns_wide.shape} ({n_dates} weeks × {len(all_tickers)} tickers)")

    # ── Step 2: Build label lookup dicts (use latest snapshot) ──
    # For static labels, every date has the same mapping
    latest = aligned_df.drop_duplicates(subset=["ticker"], keep="last")
    promoter_map = dict(zip(latest["ticker"], latest["promoter_group"]))
    sector_map = dict(zip(latest["ticker"], latest["nse_sector"]))

    # ── Step 3: Pre-build masks ──
    upper_tri, mask_sd, mask_pd = _build_masks(all_tickers, promoter_map, sector_map)

    # ── Step 4: Rolling computation ──
    results = []

    for end_idx in tqdm(range(window, n_dates), desc="Rolling correlations"):
        start_idx = end_idx - window
        window_data = returns_wide.iloc[start_idx:end_idx]
        end_date = dates[end_idx]

        # Drop tickers that are entirely NaN in this window
        valid_cols = window_data.columns[window_data.notna().sum() >= window // 2]
        if len(valid_cols) < 3:
            continue  # Need at least 3 tickers

        window_subset = window_data[valid_cols]

        # Compute correlation matrix
        corr_matrix = window_subset.corr().values  # NumPy array

        # Map valid columns back to mask indices
        col_indices = [all_tickers.index(c) for c in valid_cols]
        idx = np.array(col_indices)

        # Extract sub-masks for the valid tickers
        ix = np.ix_(idx, idx)
        sub_upper = upper_tri[ix]
        sub_mask_sd = mask_sd[ix]
        sub_mask_pd = mask_pd[ix]

        # ── Baseline: mean of all upper-tri correlations ──
        baseline_vals = corr_matrix[sub_upper]
        baseline_vals = baseline_vals[np.isfinite(baseline_vals)]

        if len(baseline_vals) == 0:
            continue

        baseline = np.mean(baseline_vals)

        # ── Same-sector, different-promoter ──
        sd_vals = corr_matrix[sub_mask_sd]
        sd_vals = sd_vals[np.isfinite(sd_vals)]
        n_sd = len(sd_vals)
        sector_mean = np.mean(sd_vals) if n_sd >= min_pairs else np.nan
        sector_excess = (sector_mean - baseline) if not np.isnan(sector_mean) else np.nan

        # ── Same-promoter, different-sector ──
        pd_vals = corr_matrix[sub_mask_pd]
        pd_vals = pd_vals[np.isfinite(pd_vals)]
        n_pd = len(pd_vals)
        group_mean = np.mean(pd_vals) if n_pd >= min_pairs else np.nan
        group_excess = (group_mean - baseline) if not np.isnan(group_mean) else np.nan

        results.append({
            "date": end_date,
            "baseline": baseline,
            "sector_excess": sector_excess,
            "group_excess": group_excess,
            "n_tickers": len(valid_cols),
            "n_sector_pairs": n_sd,
            "n_group_pairs": n_pd,
        })

    result_df = pd.DataFrame(results)
    if not result_df.empty:
        result_df.set_index("date", inplace=True)

    logger.info(
        f"Rolling correlation output: {len(result_df)} windows. "
        f"Baseline range: [{result_df['baseline'].min():.4f}, {result_df['baseline'].max():.4f}]"
    )

    return result_df


def load_or_compute_correlations(
    aligned_df: pd.DataFrame,
    window: int = ROLLING_WINDOW_WEEKS,
    min_pairs: int = MIN_PAIRS_THRESHOLD,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """
    Load rolling correlations from cache or compute from aligned panel.

    Args:
        aligned_df: Aligned panel DataFrame.
        window: Rolling window size in weeks.
        min_pairs: Minimum valid pairs for noise filter.
        force_refresh: If True, recompute even if cache exists.

    Returns:
        Rolling correlations DataFrame.
    """
    if not force_refresh and ROLLING_CORR_PATH.exists():
        logger.info(f"Loading cached correlations from {ROLLING_CORR_PATH}")
        return pd.read_parquet(ROLLING_CORR_PATH)

    result = compute_rolling_correlations(aligned_df, window, min_pairs)
    result.to_parquet(ROLLING_CORR_PATH, engine="pyarrow")
    logger.info(f"Saved correlations to {ROLLING_CORR_PATH}")
    return result


# ─── CLI Entry Point ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    from config import ALIGNED_PANEL_PATH
    if ALIGNED_PANEL_PATH.exists():
        panel = pd.read_parquet(ALIGNED_PANEL_PATH)
        result = load_or_compute_correlations(panel, force_refresh=True)
        print(f"\nResult shape: {result.shape}")
        print(result.head(10))
    else:
        print("No aligned panel found. Run main.py first.")
