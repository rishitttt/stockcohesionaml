from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import yfinance as yf

from .util import curl_download

CURRENT_CONSTITUENT_URL = "https://www.niftyindices.com/IndexConstituent/ind_nifty200list.csv"
MANUAL_SECTOR_OVERRIDES = {
    "ISEC": "FINANCE",
}


def build_sector_map(master_universe: pd.DataFrame, snapshots: pd.DataFrame, raw_dir: Path) -> pd.DataFrame:
    current_csv = raw_dir / "ind_nifty200list.csv"
    curl_download(CURRENT_CONSTITUENT_URL, current_csv)
    current = pd.read_csv(current_csv)
    current = current.rename(columns={"Symbol": "Ticker", "Industry": "Sector_Coarse_Current"})

    coarse_from_snapshots = (
        snapshots[["ticker", "sector_coarse_pdf"]]
        .dropna()
        .rename(columns={"ticker": "Ticker", "sector_coarse_pdf": "Sector_Coarse"})
        .drop_duplicates(subset=["Ticker"], keep="last")
    )

    sector_frame = master_universe.merge(coarse_from_snapshots, on="Ticker", how="left")
    sector_frame = sector_frame.merge(current[["Ticker", "Sector_Coarse_Current"]], on="Ticker", how="left")
    sector_frame["Sector_Coarse"] = sector_frame["Sector_Coarse"].fillna(sector_frame["Sector_Coarse_Current"])

    def fetch_info(ticker: str) -> dict[str, object]:
        try:
            info = yf.Ticker(f"{ticker}.NS").info
        except Exception:
            info = {}
        return {
            "Ticker": ticker,
            "Sector_Fine": info.get("industry"),
            "Sector_Coarse_YF": info.get("sector"),
        }

    fine_rows: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_map = {executor.submit(fetch_info, ticker): ticker for ticker in master_universe["Ticker"].tolist()}
        for future in as_completed(future_map):
            fine_rows.append(future.result())
    fine = pd.DataFrame.from_records(fine_rows)
    sector_frame = sector_frame.merge(fine, on="Ticker", how="left")
    sector_frame["Sector_Coarse"] = sector_frame["Sector_Coarse"].fillna(sector_frame["Sector_Coarse_YF"])
    sector_frame["Sector_Coarse"] = sector_frame.apply(
        lambda row: MANUAL_SECTOR_OVERRIDES.get(row["Ticker"], row["Sector_Coarse"]),
        axis=1,
    )
    return sector_frame[["Ticker", "Sector_Coarse", "Sector_Fine"]].drop_duplicates()
