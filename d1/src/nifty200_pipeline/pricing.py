from __future__ import annotations

from pathlib import Path

import pandas as pd
import yfinance as yf

from .util import chunked, ensure_dir


def build_weekly_prices(tickers: list[str], raw_dir: Path) -> pd.DataFrame:
    ensure_dir(raw_dir / "prices")
    frames: list[pd.DataFrame] = []
    for batch in chunked(sorted(tickers), 40):
        yf_tickers = [f"{ticker}.NS" for ticker in batch]
        history = yf.download(
            tickers=yf_tickers,
            start="2014-12-01",
            end="2026-01-10",
            progress=False,
            auto_adjust=False,
            group_by="ticker",
            threads=True,
        )
        if history.empty:
            continue
        if isinstance(history.columns, pd.MultiIndex):
            if "Adj Close" in history.columns.get_level_values(0):
                adj_close = history["Adj Close"].copy()
                adj_close.columns = [str(col).replace(".NS", "") for col in adj_close.columns]
            else:
                pieces = []
                for symbol in batch:
                    key = f"{symbol}.NS"
                    if key in history.columns.get_level_values(0):
                        series = history[key]["Adj Close"].rename(symbol)
                        pieces.append(series)
                adj_close = pd.concat(pieces, axis=1) if pieces else pd.DataFrame()
        else:
            adj_close = history[["Adj Close"]].rename(columns={"Adj Close": batch[0]})
        frames.append(adj_close)
    daily = pd.concat(frames, axis=1).sort_index()
    daily = daily.loc[:, ~daily.columns.duplicated()].sort_index(axis=1)
    weekly = daily.resample("W-FRI").last()
    returns = weekly.pct_change(fill_method=None)
    long_prices = weekly.stack(dropna=False).rename("Adj_Close").reset_index()
    long_prices.columns = ["Date", "Ticker", "Adj_Close"]
    long_returns = returns.stack(dropna=False).rename("Weekly_Return").reset_index()
    long_returns.columns = ["Date", "Ticker", "Weekly_Return"]
    merged = long_prices.merge(long_returns, on=["Date", "Ticker"], how="left")
    merged["Date"] = pd.to_datetime(merged["Date"]).dt.date
    return merged
