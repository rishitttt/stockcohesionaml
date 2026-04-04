"""
price_fetcher.py — Weekly closing price extraction via yfinance.

Downloads weekly closing prices for all Nifty 200 constituents,
with batching, retry/backoff, and parquet caching.

Functions:
    fetch_weekly_prices(tickers, start, end, ...) -> pd.DataFrame
    load_or_fetch_prices() -> pd.DataFrame
"""

import time
import logging
from typing import List, Optional

import numpy as np
import pandas as pd
import yfinance as yf
from tqdm import tqdm

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    YAHOO_TICKERS, NIFTY_200_TICKERS, START_DATE, END_DATE,
    YFINANCE_BATCH_SIZE, YFINANCE_BATCH_DELAY_SEC, YFINANCE_MAX_RETRIES,
    WEEKLY_PRICES_PATH,
)

logger = logging.getLogger(__name__)


def fetch_weekly_prices(
    tickers: Optional[List[str]] = None,
    start: str = START_DATE,
    end: str = END_DATE,
    batch_size: int = YFINANCE_BATCH_SIZE,
    batch_delay: float = YFINANCE_BATCH_DELAY_SEC,
    max_retries: int = YFINANCE_MAX_RETRIES,
) -> pd.DataFrame:
    """
    Fetch weekly closing prices for a list of Yahoo Finance tickers.

    Args:
        tickers: List of Yahoo Finance tickers (e.g., ["RELIANCE.NS", ...]).
                 Defaults to the full Nifty 200 list from config.
        start: Start date string (YYYY-MM-DD).
        end: End date string (YYYY-MM-DD).
        batch_size: Number of tickers to fetch per batch.
        batch_delay: Seconds to sleep between batches.
        max_retries: Max retries per batch on failure (exponential backoff).

    Returns:
        pd.DataFrame with DatetimeIndex (weekly Fridays) and one column
        per NSE ticker symbol (without '.NS' suffix). Values are weekly
        closing prices; NaN where data is unavailable.
    """
    if tickers is None:
        tickers = YAHOO_TICKERS

    all_frames: List[pd.DataFrame] = []
    batches = [tickers[i:i + batch_size] for i in range(0, len(tickers), batch_size)]

    logger.info(
        f"Fetching weekly prices for {len(tickers)} tickers in "
        f"{len(batches)} batches of {batch_size}..."
    )

    for batch_idx, batch in enumerate(tqdm(batches, desc="Downloading prices")):
        batch_str = " ".join(batch)
        success = False

        for attempt in range(1, max_retries + 1):
            try:
                df = yf.download(
                    batch_str,
                    start=start,
                    end=end,
                    interval="1wk",
                    auto_adjust=True,
                    progress=False,
                    threads=True,
                )

                # yf.download returns MultiIndex columns (field, ticker) for multi-ticker
                if isinstance(df.columns, pd.MultiIndex):
                    close_df = df["Close"] if "Close" in df.columns.get_level_values(0) else df
                else:
                    # single ticker case
                    close_df = df[["Close"]].rename(columns={"Close": batch[0]})

                all_frames.append(close_df)
                success = True
                break

            except Exception as e:
                wait_time = batch_delay * (2 ** (attempt - 1))
                logger.warning(
                    f"Batch {batch_idx + 1} attempt {attempt}/{max_retries} failed: {e}. "
                    f"Retrying in {wait_time:.1f}s..."
                )
                time.sleep(wait_time)

        if not success:
            logger.error(
                f"Batch {batch_idx + 1} failed after {max_retries} retries. "
                f"Tickers: {batch}. Skipping."
            )

        # Delay between batches to avoid throttling
        if batch_idx < len(batches) - 1:
            time.sleep(batch_delay)

    if not all_frames:
        raise RuntimeError("No price data was fetched. Check network and tickers.")

    # Concatenate all batches column-wise
    prices = pd.concat(all_frames, axis=1)

    # Strip '.NS' suffix from column names to get clean NSE symbols
    prices.columns = [col.replace(".NS", "") if isinstance(col, str) else col
                      for col in prices.columns]

    # Remove duplicate columns (in case of overlap between batches)
    prices = prices.loc[:, ~prices.columns.duplicated()]

    # Sort by date
    prices.sort_index(inplace=True)

    # Log summary
    valid_tickers = prices.columns[prices.notna().any()].tolist()
    all_nan_tickers = prices.columns[prices.isna().all()].tolist()
    logger.info(
        f"Fetched {len(prices)} weekly observations for {len(valid_tickers)} tickers. "
        f"{len(all_nan_tickers)} tickers returned all NaN."
    )
    if all_nan_tickers:
        logger.warning(f"All-NaN tickers: {all_nan_tickers}")

    return prices


def load_or_fetch_prices(force_refresh: bool = False) -> pd.DataFrame:
    """
    Load prices from cache if available, otherwise fetch and cache.

    Args:
        force_refresh: If True, re-download even if cache exists.

    Returns:
        pd.DataFrame of weekly closing prices.
    """
    if not force_refresh and WEEKLY_PRICES_PATH.exists():
        logger.info(f"Loading cached prices from {WEEKLY_PRICES_PATH}")
        return pd.read_parquet(WEEKLY_PRICES_PATH)

    prices = fetch_weekly_prices()
    prices.to_parquet(WEEKLY_PRICES_PATH, engine="pyarrow")
    logger.info(f"Saved prices to {WEEKLY_PRICES_PATH}")
    return prices


# ─── CLI Entry Point ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    df = load_or_fetch_prices(force_refresh=True)
    print(f"\nPrice DataFrame shape: {df.shape}")
    print(f"Date range: {df.index.min()} → {df.index.max()}")
    print(f"Sample:\n{df.iloc[:3, :5]}")
