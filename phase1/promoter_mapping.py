"""
promoter_mapping.py — Static promoter group classification for Nifty 200 stocks.

Maps each ticker to one of the defined promoter buckets:
    Tata, Adani, Bajaj, Birla, Mahindra, Reliance, PSU, Independent

Functions:
    get_promoter_labels() -> pd.DataFrame
"""

import pandas as pd

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import NIFTY_200_TICKERS


# ─── Promoter Group Definitions ──────────────────────────────────────────────
# Each group maps to a set of NSE ticker symbols whose dominant promoter
# belongs to that business house. Sources: BSE shareholding patterns,
# annual reports, NSE group indices.

_TATA_GROUP = {
    "TCS", "TATAMOTORS", "TATASTEEL", "TITAN", "TATACONSUM",
    "TATAPOWER", "TATACHEM", "TATAELXSI", "TATACOMM", "TRENT",
    "VOLTAS", "INDHOTEL",
}

_ADANI_GROUP = {
    "ADANIENT", "ADANIPORTS", "ADANIGREEN", "ADANIPOWER", "ATGL",
    "AMBUJACEM", "ACC",  # Adani acquired Ambuja & ACC in 2022
}

_BAJAJ_GROUP = {
    "BAJFINANCE", "BAJAJFINSV", "BAJAJ-AUTO",
}

_BIRLA_GROUP = {
    # Aditya Birla Group
    "GRASIM", "ULTRACEMCO", "HINDALCO", "ABCAPITAL", "ABFRL",
    "IDEA",  # Vodafone Idea — Birla is co-promoter
}

_MAHINDRA_GROUP = {
    "M&M", "TECHM", "MFSL",  # Mahindra & Mahindra Financial Services → MFSL
    "ESCORTS",  # Mahindra acquired majority stake
}

_RELIANCE_GROUP = {
    "RELIANCE",
}

# PSU: Government of India (central or state govt) is the dominant promoter
_PSU_GROUP = {
    "SBIN", "ONGC", "NTPC", "POWERGRID", "COALINDIA", "BPCL",
    "IOC", "GAIL", "NMDC", "SAIL", "BEL", "HAL",
    "BANKBARODA", "CANBK", "PNB", "CONCOR", "IRCTC",
    "PFC", "RECLTD", "NHPC", "NLCINDIA", "NATIONALUM",
    "HINDPETRO", "PETRONET", "IRFC", "HUDCO", "IDBI",
    "INDIANB", "CENTRALBK", "UNIONBANK", "NIACL",
    "IRB",  # Not technically PSU but government-linked infra
}


def _build_ticker_to_group() -> dict:
    """Build a dictionary mapping each ticker to its promoter group."""
    mapping = {}

    group_sets = {
        "Tata": _TATA_GROUP,
        "Adani": _ADANI_GROUP,
        "Bajaj": _BAJAJ_GROUP,
        "Birla": _BIRLA_GROUP,
        "Mahindra": _MAHINDRA_GROUP,
        "Reliance": _RELIANCE_GROUP,
        "PSU": _PSU_GROUP,
    }

    for group_name, tickers in group_sets.items():
        for ticker in tickers:
            if ticker in mapping:
                raise ValueError(
                    f"Ticker '{ticker}' assigned to both '{mapping[ticker]}' "
                    f"and '{group_name}'. Fix the mapping."
                )
            mapping[ticker] = group_name

    return mapping


def get_promoter_labels() -> pd.DataFrame:
    """
    Return a DataFrame mapping each Nifty 200 ticker to its promoter group.

    Returns:
        pd.DataFrame with columns ['ticker', 'promoter_group'].
        All tickers not explicitly mapped to a business house are
        classified as 'Independent'.
    """
    group_map = _build_ticker_to_group()

    records = []
    for ticker in NIFTY_200_TICKERS:
        records.append({
            "ticker": ticker,
            "promoter_group": group_map.get(ticker, "Independent"),
        })

    df = pd.DataFrame(records)

    # Summary log
    counts = df["promoter_group"].value_counts()
    print(f"Promoter group distribution:\n{counts.to_string()}\n")

    return df


# ─── CLI Entry Point ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    labels = get_promoter_labels()
    print(labels.head(20))
    print(f"\nTotal tickers: {len(labels)}")
