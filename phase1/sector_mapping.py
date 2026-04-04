"""
sector_mapping.py — Static NSE broad sector and GICS sub-industry mapping.

Assigns each Nifty 200 ticker to:
    1. NSE Broad Sector (e.g., "Financial Services", "IT", "Energy")
    2. GICS Sub-Industry (e.g., "IT Services", "Oil & Gas Refining")

Functions:
    get_sector_labels() -> pd.DataFrame
"""

import pandas as pd

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import NIFTY_200_TICKERS


# ─── Sector Mapping Dictionary ───────────────────────────────────────────────
# Format: "TICKER": ("NSE_Broad_Sector", "GICS_Sub_Industry")
# NSE Broad Sectors follow NSE's classification system.
# GICS Sub-Industries are approximations based on company activities.

_SECTOR_MAP = {
    # ── Financial Services ──
    "HDFCBANK":     ("Financial Services", "Diversified Banks"),
    "ICICIBANK":    ("Financial Services", "Diversified Banks"),
    "SBIN":         ("Financial Services", "Diversified Banks"),
    "KOTAKBANK":    ("Financial Services", "Diversified Banks"),
    "AXISBANK":     ("Financial Services", "Diversified Banks"),
    "INDUSINDBK":   ("Financial Services", "Diversified Banks"),
    "BANKBARODA":   ("Financial Services", "Diversified Banks"),
    "CANBK":        ("Financial Services", "Diversified Banks"),
    "PNB":          ("Financial Services", "Diversified Banks"),
    "IDFCFIRSTB":   ("Financial Services", "Diversified Banks"),
    "FEDERALBNK":   ("Financial Services", "Regional Banks"),
    "RBLBANK":      ("Financial Services", "Regional Banks"),
    "AUBANK":       ("Financial Services", "Regional Banks"),
    "BANDHANBNK":   ("Financial Services", "Regional Banks"),
    "CUB":          ("Financial Services", "Regional Banks"),
    "CENTRALBK":    ("Financial Services", "Diversified Banks"),
    "UNIONBANK":    ("Financial Services", "Diversified Banks"),
    "INDIANB":      ("Financial Services", "Diversified Banks"),
    "IDBI":         ("Financial Services", "Diversified Banks"),
    "BAJFINANCE":   ("Financial Services", "Consumer Finance"),
    "BAJAJFINSV":   ("Financial Services", "Multi-Sector Holdings"),
    "CHOLAFIN":     ("Financial Services", "Consumer Finance"),
    "SHRIRAMFIN":   ("Financial Services", "Consumer Finance"),
    "MUTHOOTFIN":   ("Financial Services", "Consumer Finance"),
    "MANAPPURAM":   ("Financial Services", "Consumer Finance"),
    "LTF":          ("Financial Services", "Consumer Finance"),
    "L&TFH":        ("Financial Services", "Consumer Finance"),
    "CANFINHOME":   ("Financial Services", "Thrifts & Mortgage Finance"),
    "LICHSGFIN":    ("Financial Services", "Thrifts & Mortgage Finance"),
    "PFC":          ("Financial Services", "Specialized Finance"),
    "RECLTD":       ("Financial Services", "Specialized Finance"),
    "IRFC":         ("Financial Services", "Specialized Finance"),
    "HUDCO":        ("Financial Services", "Specialized Finance"),
    "SBILIFE":      ("Financial Services", "Life & Health Insurance"),
    "HDFCLIFE":     ("Financial Services", "Life & Health Insurance"),
    "ICICIPRULI":   ("Financial Services", "Life & Health Insurance"),
    "STARHEALTH":   ("Financial Services", "Life & Health Insurance"),
    "ICICIGI":      ("Financial Services", "Property & Casualty Insurance"),
    "NIACL":        ("Financial Services", "Property & Casualty Insurance"),
    "SBICARD":      ("Financial Services", "Consumer Finance"),
    "ABCAPITAL":    ("Financial Services", "Diversified Capital Markets"),
    "MFSL":         ("Financial Services", "Diversified Capital Markets"),
    "SUNDARMFIN":   ("Financial Services", "Consumer Finance"),
    "UJJIVANSFB":   ("Financial Services", "Regional Banks"),
    "MCX":          ("Financial Services", "Financial Exchanges & Data"),
    "CDSL":         ("Financial Services", "Financial Exchanges & Data"),
    "CAMS":         ("Financial Services", "Financial Exchanges & Data"),
    "FIVESTAR":     ("Financial Services", "Consumer Finance"),
    "POLICYBZR":    ("Financial Services", "Insurance Brokers"),
    "NAM-INDIA":    ("Financial Services", "Asset Management"),
    "IIFL":         ("Financial Services", "Diversified Capital Markets"),

    # ── Information Technology ──
    "TCS":          ("IT", "IT Services"),
    "INFY":         ("IT", "IT Services"),
    "HCLTECH":      ("IT", "IT Services"),
    "WIPRO":        ("IT", "IT Services"),
    "TECHM":        ("IT", "IT Services"),
    "LTIM":         ("IT", "IT Services"),
    "MPHASIS":      ("IT", "IT Services"),
    "PERSISTENT":   ("IT", "IT Services"),
    "COFORGE":      ("IT", "IT Services"),
    "KPITTECH":     ("IT", "IT Services"),
    "TATAELXSI":    ("IT", "IT Services"),
    "HAPPSTMNDS":   ("IT", "IT Services"),
    "ROUTE":        ("IT", "IT Services"),
    "OFSS":         ("IT", "Application Software"),
    "NAUKRI":       ("IT", "Internet Services & Infrastructure"),
    "INDIAMART":    ("IT", "Internet Services & Infrastructure"),
    "ZOMATO":       ("IT", "Internet Services & Infrastructure"),
    "PAYTM":        ("IT", "Internet Services & Infrastructure"),
    "AFFLE":        ("IT", "Application Software"),

    # ── Oil, Gas & Energy ──
    "RELIANCE":     ("Energy", "Integrated Oil & Gas"),
    "ONGC":         ("Energy", "Integrated Oil & Gas"),
    "BPCL":         ("Energy", "Oil & Gas Refining"),
    "IOC":          ("Energy", "Oil & Gas Refining"),
    "HINDPETRO":    ("Energy", "Oil & Gas Refining"),
    "GAIL":         ("Energy", "Oil & Gas Storage & Transportation"),
    "PETRONET":     ("Energy", "Oil & Gas Storage & Transportation"),
    "IGL":          ("Energy", "Gas Utilities"),
    "GSPL":         ("Energy", "Gas Utilities"),
    "GUJGASLTD":    ("Energy", "Gas Utilities"),
    "ATGL":         ("Energy", "Gas Utilities"),

    # ── Power ──
    "NTPC":         ("Power", "Electric Utilities"),
    "POWERGRID":    ("Power", "Electric Utilities"),
    "TATAPOWER":    ("Power", "Electric Utilities"),
    "ADANIGREEN":   ("Power", "Renewable Electricity"),
    "ADANIPOWER":   ("Power", "Electric Utilities"),
    "NHPC":         ("Power", "Electric Utilities"),
    "TORNTPOWER":   ("Power", "Electric Utilities"),
    "NLCINDIA":     ("Power", "Electric Utilities"),
    "JSWENERGY":    ("Power", "Electric Utilities"),

    # ── Metals & Mining ──
    "TATASTEEL":    ("Metals & Mining", "Steel"),
    "JSWSTEEL":     ("Metals & Mining", "Steel"),
    "HINDALCO":     ("Metals & Mining", "Aluminum"),
    "VEDL":         ("Metals & Mining", "Diversified Metals & Mining"),
    "COALINDIA":    ("Metals & Mining", "Coal & Consumable Fuels"),
    "NMDC":         ("Metals & Mining", "Steel"),
    "SAIL":         ("Metals & Mining", "Steel"),
    "NATIONALUM":   ("Metals & Mining", "Aluminum"),
    "JINDALSTEL":   ("Metals & Mining", "Steel"),

    # ── Automobile ──
    "MARUTI":       ("Automobile", "Automobile Manufacturers"),
    "TATAMOTORS":   ("Automobile", "Automobile Manufacturers"),
    "M&M":          ("Automobile", "Automobile Manufacturers"),
    "BAJAJ-AUTO":   ("Automobile", "Motorcycle Manufacturers"),
    "HEROMOTOCO":   ("Automobile", "Motorcycle Manufacturers"),
    "EICHERMOT":    ("Automobile", "Motorcycle Manufacturers"),
    "TVSMOTOR":     ("Automobile", "Motorcycle Manufacturers"),
    "ESCORTS":      ("Automobile", "Agricultural Machinery"),
    "BHARATFORG":   ("Automobile", "Auto Parts & Equipment"),
    "EXIDEIND":     ("Automobile", "Auto Parts & Equipment"),
    "BALKRISIND":   ("Automobile", "Auto Parts & Equipment"),
    "MOTHERSON":    ("Automobile", "Auto Parts & Equipment"),
    "ENDURANCE":    ("Automobile", "Auto Parts & Equipment"),
    "SONACOMS":     ("Automobile", "Auto Parts & Equipment"),
    "UNOMINDA":     ("Automobile", "Auto Parts & Equipment"),

    # ── Pharma & Healthcare ──
    "SUNPHARMA":    ("Pharma", "Pharmaceuticals"),
    "DRREDDY":      ("Pharma", "Pharmaceuticals"),
    "CIPLA":        ("Pharma", "Pharmaceuticals"),
    "DIVISLAB":     ("Pharma", "Pharmaceuticals"),
    "LUPIN":        ("Pharma", "Pharmaceuticals"),
    "AUROPHARMA":   ("Pharma", "Pharmaceuticals"),
    "BIOCON":       ("Pharma", "Biotechnology"),
    "TORNTPHARM":   ("Pharma", "Pharmaceuticals"),
    "IPCALAB":      ("Pharma", "Pharmaceuticals"),
    "ZYDUSLIFE":    ("Pharma", "Pharmaceuticals"),
    "GLENMARK":     ("Pharma", "Pharmaceuticals"),
    "LAURUSLABS":   ("Pharma", "Life Sciences Tools & Services"),
    "SYNGENE":      ("Pharma", "Life Sciences Tools & Services"),
    "SUVENPHAR":    ("Pharma", "Pharmaceuticals"),
    "APOLLOHOSP":   ("Pharma", "Health Care Facilities"),
    "MAXHEALTH":    ("Pharma", "Health Care Facilities"),
    "FORTIS":       ("Pharma", "Health Care Facilities"),
    "LALPATHLAB":   ("Pharma", "Health Care Services"),
    "METROPOLIS":   ("Pharma", "Health Care Services"),
    "GLAXO":        ("Pharma", "Pharmaceuticals"),

    # ── FMCG ──
    "HINDUNILVR":   ("FMCG", "Household Products"),
    "ITC":          ("FMCG", "Tobacco"),
    "NESTLEIND":    ("FMCG", "Packaged Foods & Meats"),
    "BRITANNIA":    ("FMCG", "Packaged Foods & Meats"),
    "DABUR":        ("FMCG", "Personal Products"),
    "GODREJCP":     ("FMCG", "Personal Products"),
    "MARICO":       ("FMCG", "Personal Products"),
    "COLPAL":       ("FMCG", "Household Products"),
    "TATACONSUM":   ("FMCG", "Packaged Foods & Meats"),
    "EMAMILTD":     ("FMCG", "Personal Products"),
    "JUBLFOOD":     ("FMCG", "Restaurants"),
    "UBL":          ("FMCG", "Brewers"),
    "MCDOWELL-N":   ("FMCG", "Distillers & Vintners"),
    "RADICO":       ("FMCG", "Distillers & Vintners"),
    "EIDPARRY":     ("FMCG", "Agricultural Products"),
    "BATAINDIA":    ("FMCG", "Footwear"),
    "PAGEIND":      ("FMCG", "Apparel & Accessories"),
    "RELAXO":       ("FMCG", "Footwear"),
    "HATSUN":       ("FMCG", "Packaged Foods & Meats"),
    "RAJESHEXPO":   ("FMCG", "Packaged Foods & Meats"),

    # ── Construction & Infrastructure ──
    "LT":           ("Construction", "Construction & Engineering"),
    "ADANIENT":     ("Construction", "Industrial Conglomerates"),
    "ADANIPORTS":   ("Construction", "Marine Ports & Services"),
    "DLF":          ("Construction", "Real Estate Development"),
    "OBEROIRLTY":   ("Construction", "Real Estate Development"),
    "GODREJPROP":   ("Construction", "Real Estate Development"),
    "PRESTIGE":     ("Construction", "Real Estate Development"),
    "PHOENIX":      ("Construction", "Real Estate Development"),
    "CONCOR":       ("Construction", "Marine Ports & Services"),
    "GMRAIRPORT":   ("Construction", "Airport Services"),
    "IRB":          ("Construction", "Highways & Railtracks"),
    "DELHIVERY":    ("Construction", "Air Freight & Logistics"),

    # ── Cement ──
    "ULTRACEMCO":   ("Cement", "Cement"),
    "AMBUJACEM":    ("Cement", "Cement"),
    "ACC":          ("Cement", "Cement"),
    "GRASIM":       ("Cement", "Cement"),  # Grasim's main value is via UltraTech
    "JKCEMENT":     ("Cement", "Cement"),
    "RAMCOCEM":     ("Cement", "Cement"),
    "DALBHARAT":    ("Cement", "Cement"),

    # ── Consumer Durables ──
    "TITAN":        ("Consumer Durables", "Apparel & Accessories"),
    "HAVELLS":      ("Consumer Durables", "Electrical Components & Equipment"),
    "VOLTAS":       ("Consumer Durables", "Building Products"),
    "CROMPTON":     ("Consumer Durables", "Electrical Components & Equipment"),
    "WHIRLPOOL":    ("Consumer Durables", "Household Appliances"),
    "SYMPHONY":     ("Consumer Durables", "Household Appliances"),
    "KAJARIACER":   ("Consumer Durables", "Building Products"),
    "TRENT":        ("Consumer Durables", "Apparel Retail"),
    "ABFRL":        ("Consumer Durables", "Apparel Retail"),

    # ── Chemicals ──
    "PIIND":        ("Chemicals", "Specialty Chemicals"),
    "SRF":          ("Chemicals", "Specialty Chemicals"),
    "DEEPAKNTR":    ("Chemicals", "Specialty Chemicals"),
    "NAVINFLUOR":   ("Chemicals", "Specialty Chemicals"),
    "CLEAN":        ("Chemicals", "Specialty Chemicals"),
    "TATACHEM":     ("Chemicals", "Commodity Chemicals"),
    "COROMANDEL":   ("Chemicals", "Fertilizers & Agricultural Chemicals"),
    "SUMICHEM":     ("Chemicals", "Fertilizers & Agricultural Chemicals"),
    "UPL":          ("Chemicals", "Fertilizers & Agricultural Chemicals"),
    "NOCIL":        ("Chemicals", "Specialty Chemicals"),

    # ── Paints ──
    "ASIANPAINT":   ("Consumer Durables", "Specialty Chemicals"),
    "BERGEPAINT":   ("Consumer Durables", "Specialty Chemicals"),
    "KANSAINER":    ("Consumer Durables", "Specialty Chemicals"),
    "PIDILITIND":   ("Consumer Durables", "Specialty Chemicals"),

    # ── Telecom ──
    "BHARTIARTL":   ("Telecom", "Wireless Telecommunication Services"),
    "IDEA":         ("Telecom", "Wireless Telecommunication Services"),
    "TATACOMM":     ("Telecom", "Integrated Telecommunication Services"),

    # ── Media ──
    "SUNTV":        ("Media", "Broadcasting"),
    "ZEEL":         ("Media", "Broadcasting"),
    "PVRINOX":      ("Media", "Movies & Entertainment"),

    # ── Capital Goods / Industrial ──
    "SIEMENS":      ("Capital Goods", "Heavy Electrical Equipment"),
    "BOSCHLTD":     ("Capital Goods", "Auto Parts & Equipment"),
    "CUMMINSIND":   ("Capital Goods", "Industrial Machinery"),
    "HONAUT":       ("Capital Goods", "Industrial Machinery"),
    "THERMAX":      ("Capital Goods", "Industrial Machinery"),
    "SCHAEFFLER":   ("Capital Goods", "Industrial Machinery"),
    "TIMKEN":       ("Capital Goods", "Industrial Machinery"),
    "KEI":          ("Capital Goods", "Electrical Components & Equipment"),
    "POLYCAB":      ("Capital Goods", "Electrical Components & Equipment"),
    "ASTRAL":       ("Capital Goods", "Building Products"),
    "SUPREMEIND":   ("Capital Goods", "Building Products"),
    "SUNDRMFAST":   ("Capital Goods", "Industrial Machinery"),
    "TRIDENT":      ("Capital Goods", "Textile Manufacturing"),
    "MRF":          ("Capital Goods", "Tires & Rubber"),

    # ── Miscellaneous ──
    "BEL":          ("Capital Goods", "Aerospace & Defense"),
    "HAL":          ("Capital Goods", "Aerospace & Defense"),
    "INDHOTEL":     ("FMCG", "Hotels & Resorts"),
    "IRCTC":        ("Construction", "Railroads"),
}


def get_sector_labels() -> pd.DataFrame:
    """
    Return a DataFrame mapping each Nifty 200 ticker to its sector classifications.

    Returns:
        pd.DataFrame with columns ['ticker', 'nse_sector', 'gics_sub_industry'].
        Tickers without explicit mapping receive 'Other' / 'Unclassified'.
    """
    records = []
    unmapped = []

    for ticker in NIFTY_200_TICKERS:
        if ticker in _SECTOR_MAP:
            nse_sector, gics_sub = _SECTOR_MAP[ticker]
        else:
            nse_sector, gics_sub = "Other", "Unclassified"
            unmapped.append(ticker)

        records.append({
            "ticker": ticker,
            "nse_sector": nse_sector,
            "gics_sub_industry": gics_sub,
        })

    df = pd.DataFrame(records)

    if unmapped:
        print(f"WARNING: {len(unmapped)} tickers unmapped to sectors: {unmapped}")

    # Summary
    print(f"\nSector distribution:")
    print(df["nse_sector"].value_counts().to_string())

    return df


# ─── CLI Entry Point ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    labels = get_sector_labels()
    print(f"\nTotal tickers: {len(labels)}")
    print(labels.head(20))
