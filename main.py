"""
main.py — Orchestrator for the Market Microstructure Pipeline.

Runs the full pipeline sequentially:
    1. Fetch weekly prices (or load from cache)
    2. Load static promoter group labels
    3. Load static sector classifications
    4. Align timeline (merge + forward-fill)
    5. Run rolling correlation engine
    6. Save final results

Usage:
    python main.py [--refresh]     # --refresh forces re-download/recompute
"""

import argparse
import logging
import time

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ROLLING_CORR_PATH
from phase1.price_fetcher import load_or_fetch_prices
from phase1.promoter_mapping import get_promoter_labels
from phase1.sector_mapping import get_sector_labels
from phase1.timeline_aligner import load_or_align
from phase2.rolling_correlation import load_or_compute_correlations


def main(force_refresh: bool = False):
    """
    Execute the full market microstructure pipeline.

    Args:
        force_refresh: If True, re-download prices and recompute all stages.
    """
    pipeline_start = time.time()

    # ── Phase 1: Data Extraction & Alignment ──
    print("=" * 70)
    print("PHASE 1: Data Extraction & Alignment")
    print("=" * 70)

    # Step 1: Weekly prices
    print("\n[1/4] Fetching weekly prices...")
    prices_df = load_or_fetch_prices(force_refresh=force_refresh)
    print(f"  → Shape: {prices_df.shape} | "
          f"Date range: {prices_df.index.min().date()} → {prices_df.index.max().date()}")

    # Step 2: Promoter labels
    print("\n[2/4] Loading promoter group labels...")
    promoter_df = get_promoter_labels()
    print(f"  → {len(promoter_df)} tickers classified")

    # Step 3: Sector labels
    print("\n[3/4] Loading sector classifications...")
    sector_df = get_sector_labels()
    print(f"  → {len(sector_df)} tickers classified")

    # Step 4: Timeline alignment
    print("\n[4/4] Aligning timeline...")
    aligned_df = load_or_align(prices_df, promoter_df, sector_df, force_refresh=force_refresh)
    print(f"  → Panel shape: {aligned_df.shape}")
    print(f"  → Unique dates: {aligned_df['date'].nunique()}")
    print(f"  → Unique tickers: {aligned_df['ticker'].nunique()}")
    print(f"  → Valid returns: {aligned_df['weekly_return'].notna().sum():,}")

    # ── Phase 2: Rolling Correlation Engine ──
    print("\n" + "=" * 70)
    print("PHASE 2: Rolling Correlation Engine")
    print("=" * 70)

    print("\nComputing 52-week rolling correlations...")
    result_df = load_or_compute_correlations(aligned_df, force_refresh=force_refresh)

    # ── Summary ──
    elapsed = time.time() - pipeline_start
    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)
    print(f"  Total time: {elapsed:.1f}s")
    print(f"  Result shape: {result_df.shape}")
    print(f"  Output saved to: {ROLLING_CORR_PATH}")
    print(f"\n  Summary statistics:")
    print(result_df[["baseline", "sector_excess", "group_excess"]].describe().to_string())
    print(f"\n  First 5 rows:")
    print(result_df.head().to_string())
    print(f"\n  Last 5 rows:")
    print(result_df.tail().to_string())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Market Microstructure Pipeline")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force re-download prices and recompute all stages",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    main(force_refresh=args.refresh)
