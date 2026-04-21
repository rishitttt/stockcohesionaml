from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from .util import curl_download, ensure_dir, parse_human_date, parse_number, read_json

NSE_MASTER_URL = "https://www.nseindia.com/api/corporate-share-holdings-master?index=equities&symbol={symbol}"
NSE_PROMOTER_URL = "https://www.nseindia.com/api/corporate-share-holdings-equities?ndsId={record_id}&index=promoter"

GROUP_PATTERNS: dict[str, tuple[str, ...]] = {
    "Tata": ("TATA", "TATA SONS"),
    "Adani": ("ADANI", "ENDEAVOUR TRADE AND INVESTMENT", "MUNDRA", "AMBUJA CEMENTS LIMITED"),
    "Bajaj": ("BAJAJ",),
    "Birla": ("ADITYA BIRLA", "BIRLA", "GRASIM", "HINDALCO", "ULTRATECH"),
    "Mahindra": ("MAHINDRA",),
    "Reliance": ("RELIANCE", "JIO", "RIL", "AMBANI", "PETROLEUM TRUST"),
    "GOI_PSU": ("PRESIDENT OF INDIA", "GOVERNMENT OF INDIA", "MINISTRY OF", "UNION OF INDIA", "STATE GOVERNMENT"),
}

SUMMARY_LABELS = {
    "INDIAN",
    "FOREIGN",
    "INDIVIDUALS/HINDU UNDIVIDED FAMILY",
    "INDIVIDUALS (NON-RESIDENT INDIVIDUALS/ FOREIGN INDIVIDUALS)",
    "CENTRAL GOVERNMENT/ STATE GOVERNMENT(S)",
    "FINANCIAL INSTITUTIONS/ BANKS",
    "ANY OTHER (SPECIFY)",
    "GOVERNMENT",
    "INSTITUTIONS",
    "FOREIGN PORTFOLIO INVESTOR",
    "BODIES CORPORATE",
    "TRUSTS",
    "OVERSEAS CORPORATE BODIES",
}


def classifier_for_name(name: str) -> str:
    upper = name.upper()
    if "AMBUJA CEMENTS LIMITED" in upper and "ENDEAVOUR" not in upper:
        return "Independent"
    for label, patterns in GROUP_PATTERNS.items():
        if any(pattern in upper for pattern in patterns):
            return label
    return "Independent"


def promoter_rows_from_payload(payload: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    for row in payload:
        name = str(row.get("COL_I") or "").strip()
        entity_type = str(row.get("ENTITY_TYPE") or "").strip()
        category = str(row.get("category") or "").strip()
        shares = parse_number(row.get("COL_IX_Total"))
        if not name or shares <= 0:
            continue
        upper_name = name.upper()
        if upper_name.startswith("SUB-TOTAL") or upper_name.startswith("TOTAL SHAREHOLDING"):
            continue
        if entity_type in {"Promoter", "Promoter Group"}:
            rows.append({"name": name, "shares": shares, "entity_type": entity_type, "category": row.get("category")})
            continue
        if upper_name in {"CENTRAL GOVERNMENT/ STATE GOVERNMENT(S)", "GOVERNMENT"}:
            rows.append({"name": name, "shares": shares, "entity_type": entity_type, "category": row.get("category")})
            continue
        # Older NSE payloads often omit ENTITY_TYPE on the detail rows but keep
        # promoter entities in indented rows with blank category markers.
        if category == "" and upper_name not in SUMMARY_LABELS:
            rows.append({"name": name, "shares": shares, "entity_type": entity_type, "category": row.get("category")})
    return rows


def classify_promoter_payload(payload: list[dict[str, object]]) -> tuple[str | None, str | None, float]:
    rows = promoter_rows_from_payload(payload)
    if not rows:
        return None, None, 0.0
    named_group_rows = [
        row
        for row in rows
        if classifier_for_name(row["name"]) not in {None, "Independent"}
    ]
    if named_group_rows:
        grouped: dict[str, list[dict[str, object]]] = {}
        for row in named_group_rows:
            grouped.setdefault(classifier_for_name(row["name"]), []).append(row)
        best_group = max(
            grouped.items(),
            key=lambda item: (
                sum(float(member["shares"]) for member in item[1]),
                max(float(member["shares"]) for member in item[1]),
            ),
        )
        dominant = sorted(best_group[1], key=lambda row: (-row["shares"], row["name"]))[0]
        return best_group[0], dominant["name"], dominant["shares"]
    dominant = sorted(rows, key=lambda row: (-row["shares"], row["name"]))[0]
    label = classifier_for_name(dominant["name"])
    return label, dominant["name"], dominant["shares"]


def process_promoter_record(ticker: str, row: dict[str, object], symbol_dir: Path) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    if "date" not in row or "recordId" not in row:
        return None, None
    quarter_date = parse_human_date(str(row["date"]))
    if quarter_date.year < 2014 or quarter_date.year > 2025:
        return None, None
    total_promoter = parse_number(row.get("pr_and_prgrp"))
    if total_promoter == 0:
        return (
            {
                "Ticker": ticker,
                "Quarter_End": quarter_date,
                "Promoter_Group": "Independent",
                "Dominant_Promoter_Entity": None,
                "Dominant_Promoter_Shares": 0.0,
            },
            None,
        )
    promoter_path = symbol_dir / f"promoter_{row['recordId']}.json"
    curl_download(NSE_PROMOTER_URL.format(record_id=row["recordId"]), promoter_path)
    promoter_payload = read_json(promoter_path)
    if not isinstance(promoter_payload, list):
        return None, {"Ticker": ticker, "Reason": f"promoter payload invalid for {row['recordId']}"}
    group, entity_name, entity_shares = classify_promoter_payload(promoter_payload)
    if group is None:
        return None, {"Ticker": ticker, "Reason": f"could not classify promoter rows for {row['recordId']}"}
    return (
        {
            "Ticker": ticker,
            "Quarter_End": quarter_date,
            "Promoter_Group": group,
            "Dominant_Promoter_Entity": entity_name,
            "Dominant_Promoter_Shares": entity_shares,
        },
        None,
    )


def build_promoter_history(master_universe: pd.DataFrame, raw_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    base_dir = ensure_dir(raw_dir / "nse_shareholding")
    history_rows: list[dict[str, object]] = []
    unresolved_rows: list[dict[str, object]] = []
    jobs: list[tuple[str, dict[str, object], Path]] = []
    for ticker in master_universe["Ticker"]:
        symbol_dir = ensure_dir(base_dir / ticker)
        master_path = symbol_dir / "master.json"
        try:
            curl_download(NSE_MASTER_URL.format(symbol=ticker), master_path)
            master_payload = read_json(master_path)
        except Exception as exc:
            unresolved_rows.append({"Ticker": ticker, "Reason": f"master fetch failed: {exc}"})
            continue
        if not isinstance(master_payload, list):
            unresolved_rows.append({"Ticker": ticker, "Reason": "master payload was not a list"})
            continue
        for row in master_payload:
            jobs.append((ticker, row, symbol_dir))
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_map = {
            executor.submit(process_promoter_record, ticker, row, symbol_dir): (ticker, row.get("recordId"))
            for ticker, row, symbol_dir in jobs
        }
        for future in as_completed(future_map):
            ticker, record_id = future_map[future]
            try:
                history_row, unresolved_row = future.result()
            except Exception as exc:
                unresolved_rows.append({"Ticker": ticker, "Reason": f"promoter fetch failed for {record_id}: {exc}"})
                continue
            if history_row:
                history_rows.append(history_row)
            if unresolved_row:
                unresolved_rows.append(unresolved_row)
    history = pd.DataFrame.from_records(history_rows)
    if history.empty:
        return history, pd.DataFrame.from_records(unresolved_rows)
    history = history.sort_values(["Ticker", "Quarter_End"]).drop_duplicates(subset=["Ticker", "Quarter_End"], keep="last")
    unresolved = pd.DataFrame.from_records(unresolved_rows)
    return history, unresolved
