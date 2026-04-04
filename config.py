"""
config.py — Central configuration for the Market Microstructure Pipeline.

Contains:
    - Nifty 200 constituents (NSE symbols)
    - Date range parameters
    - Promoter group bucket definitions
    - File paths for cached data outputs
"""

import os
from pathlib import Path

# ─── Project Paths ───────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# Cached data file paths
WEEKLY_PRICES_PATH = DATA_DIR / "weekly_prices.parquet"
PROMOTER_LABELS_PATH = DATA_DIR / "promoter_labels.parquet"
SECTOR_LABELS_PATH = DATA_DIR / "sector_labels.parquet"
ALIGNED_PANEL_PATH = DATA_DIR / "aligned_panel.parquet"
ROLLING_CORR_PATH = DATA_DIR / "rolling_correlations.parquet"

# ─── Date Range ──────────────────────────────────────────────────────────────
START_DATE = "2020-01-01"
END_DATE = "2025-12-31"

# ─── yfinance Settings ───────────────────────────────────────────────────────
YFINANCE_BATCH_SIZE = 20        # tickers per batch to avoid throttling
YFINANCE_BATCH_DELAY_SEC = 2.0  # seconds between batches
YFINANCE_MAX_RETRIES = 3        # retries per batch on failure
YFINANCE_SUFFIX = ".NS"         # Yahoo Finance suffix for NSE stocks

# ─── Rolling Correlation Settings ────────────────────────────────────────────
ROLLING_WINDOW_WEEKS = 52       # 1-year rolling window
MIN_PAIRS_THRESHOLD = 10        # noise filter: min valid pairs for a mean

# ─── Promoter Group Buckets ──────────────────────────────────────────────────
PROMOTER_GROUPS = [
    "Tata",
    "Adani",
    "Bajaj",
    "Birla",
    "Mahindra",
    "Reliance",
    "PSU",
    "Independent",
]

# ─── Nifty 200 Constituents (NSE Symbols) ───────────────────────────────────
# Approximately 200 tickers representing the Nifty 200 index as of early 2025.
# Yahoo Finance tickers are formed by appending `.NS` to these symbols.
NIFTY_200_TICKERS = [
    # ── Large Cap (Nifty 50 core) ──
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
    "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "HCLTECH",
    "SUNPHARMA", "TITAN", "BAJFINANCE", "WIPRO", "ULTRACEMCO",
    "ONGC", "NTPC", "POWERGRID", "M&M", "TATAMOTORS",
    "TATASTEEL", "ADANIENT", "ADANIPORTS", "TECHM", "JSWSTEEL",
    "COALINDIA", "BAJAJFINSV", "BAJAJ-AUTO", "NESTLEIND", "GRASIM",
    "INDUSINDBK", "HINDALCO", "DRREDDY", "DIVISLAB", "CIPLA",
    "APOLLOHOSP", "BRITANNIA", "EICHERMOT", "HEROMOTOCO", "BPCL",
    "TATACONSUM", "SBILIFE", "HDFCLIFE", "VEDL", "SHRIRAMFIN",

    # ── Large Cap (Nifty Next 50) ──
    "ADANIGREEN", "ADANIPOWER", "AMBUJACEM", "ACC", "ATGL",
    "BANKBARODA", "BEL", "BERGEPAINT", "BIOCON", "BOSCHLTD",
    "CANBK", "CHOLAFIN", "COLPAL", "CONCOR", "DABUR",
    "DLF", "GAIL", "GODREJCP", "HAVELLS", "HAL",
    "ICICIPRULI", "ICICIGI", "IDFCFIRSTB", "IGL", "INDHOTEL",
    "IOC", "IRCTC", "JINDALSTEL", "JUBLFOOD", "LTF",
    "LTIM", "LUPIN", "MARICO", "MCDOWELL-N", "MPHASIS",
    "MUTHOOTFIN", "NAUKRI", "NMDC", "OBEROIRLTY", "OFSS",
    "PAGEIND", "PERSISTENT", "PETRONET", "PFC", "PIDILITIND",
    "PNB", "RECLTD", "SAIL", "SBICARD", "SIEMENS",

    # ── Mid Cap (Nifty Midcap 100 — representative set) ──
    "TRENT", "TATAPOWER", "TATACHEM", "TATAELXSI", "TATACOMM",
    "ZOMATO", "POLICYBZR", "PAYTM", "DELHIVERY", "CUMMINSIND",
    "GODREJPROP", "PIIND", "ASTRAL", "AUROPHARMA", "BALKRISIND",
    "BHARATFORG", "CANFINHOME", "COFORGE", "CROMPTON", "DEEPAKNTR",
    "ESCORTS", "EXIDEIND", "FEDERALBNK", "GMRAIRPORT", "GSPL",
    "HONAUT", "IPCALAB", "IRFC", "JKCEMENT", "KPITTECH",
    "L&TFH", "LALPATHLAB", "LICHSGFIN", "MANAPPURAM", "MAXHEALTH",
    "MRF", "MFSL", "NAM-INDIA", "NATIONALUM", "NAVINFLUOR",
    "NHPC", "NLCINDIA", "POLYCAB", "PVRINOX", "RAMCOCEM",
    "RBLBANK", "SCHAEFFLER", "SRF", "STARHEALTH", "SUNDARMFIN",
    "SUNTV", "SUPREMEIND", "SYNGENE", "TORNTPHARM", "TORNTPOWER",
    "TVSMOTOR", "UBL", "UNIONBANK", "UPL", "VOLTAS",
    "ZYDUSLIFE", "ABCAPITAL", "ABFRL", "IDEA", "INDIAMART",
    "AUBANK", "BANDHANBNK", "BATAINDIA", "CENTRALBK", "CLEAN",
    "COROMANDEL", "CUB", "DALBHARAT", "EIDPARRY", "EMAMILTD",
    "ENDURANCE", "FORTIS", "GLENMARK", "GLAXO", "GUJGASLTD",
    "HATSUN", "HINDPETRO", "HUDCO", "IDBI", "IIFL",
    "INDIANB", "IRB", "JSWENERGY", "KAJARIACER", "KEI",
    "KANSAINER", "LAURUSLABS", "MCX", "METROPOLIS", "MOTHERSON",
    "NIACL", "NOCIL", "PRESTIGE", "RADICO", "RAJESHEXPO",
    "RELAXO", "SONACOMS", "SUMICHEM", "SUNDRMFAST", "SUVENPHAR",
    "SYMPHONY", "THERMAX", "TIMKEN", "TRIDENT", "UJJIVANSFB",
    "UNOMINDA", "WHIRLPOOL", "ZEEL", "PHOENIX", "AFFLE",
    "CDSL", "HAPPSTMNDS", "ROUTE", "CAMS", "FIVESTAR",
]

# Convert to Yahoo Finance tickers
YAHOO_TICKERS = [f"{t}{YFINANCE_SUFFIX}" for t in NIFTY_200_TICKERS]
