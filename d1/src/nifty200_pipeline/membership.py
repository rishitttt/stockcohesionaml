from __future__ import annotations

import io
import re
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

import pandas as pd
from bs4 import BeautifulSoup

from .util import (
    curl_download,
    daterange_month_end,
    daterange_weekly,
    ensure_dir,
    extract_pdf_text,
    month_end,
    month_range,
    month_token,
    normalize_space,
    parse_human_date,
)

ARCHIVE_BASE = "https://www.niftyindices.com/Indices_-_Market_Capitalisation_and_Weightage"
PRESS_RELEASE_BASE = "https://www.niftyindices.com"
PRESS_RELEASE_PAGE = "https://www.niftyindices.com/press-release?date={year}"

MONTHLY_HEADER_MARKERS = {
    "Symbol Security Name Industry",
    "Constituents of CNX 200",
    "Constituents of NIFTY 200",
}

NON_SYMBOL_PREFIXES = {
    "SYMBOL",
    "CONSTITUENTS",
    "WEIGHTAGE",
    "INDEX",
    "SR.",
    "COMPANY",
    "SECURITY",
    "JANUARY",
    "FEBRUARY",
    "MARCH",
    "APRIL",
    "MAY",
    "JUNE",
    "JULY",
    "AUGUST",
    "SEPTEMBER",
    "OCTOBER",
    "NOVEMBER",
    "DECEMBER",
}

EVENT_KEYWORDS = ("replacement", "replacements", "exclusion", "inclusion", "corporate adjustment", "demerger")


@dataclass(frozen=True)
class ChangeEvent:
    effective_date: date
    symbol: str
    action: str
    source_title: str
    source_url: str


def archive_zip_url(year: int, month: int) -> str:
    return f"{ARCHIVE_BASE}/indices_data{month_token(year, month)}.zip"


def press_release_path(title_href: str) -> str:
    return urljoin(PRESS_RELEASE_BASE, title_href)


def is_symbol_token(token: str) -> bool:
    token = token.strip()
    return bool(re.fullmatch(r"[A-Z0-9&._-]+", token))


def is_industry_token(token: str) -> bool:
    stripped = token.strip("(),.")
    return bool(stripped) and bool(re.fullmatch(r"[A-Z0-9/&-]+", stripped))


def split_company_and_industry(rest: str) -> tuple[str, str]:
    tokens = rest.split()
    industry_tokens: list[str] = []
    idx = len(tokens) - 1
    while idx >= 0 and is_industry_token(tokens[idx]):
        industry_tokens.insert(0, tokens[idx])
        idx -= 1
    company = " ".join(tokens[: idx + 1]).strip()
    industry = " ".join(industry_tokens).strip()
    return company, industry


def row_complete(text: str) -> bool:
    return bool(re.search(r"\d[\d,]*\.\d+\s+\d[\d,]*\.\d+$", text))


def parse_constituent_row(text: str) -> dict[str, str] | None:
    match = re.match(
        r"^(?P<symbol>[A-Z0-9&._-]+)\s+(?P<rest>.+?)\s+(?P<close>\d[\d,]*\.\d+)\s+(?P<weight>\d[\d,]*\.\d+)$",
        normalize_space(text),
    )
    if not match:
        return None
    company, industry = split_company_and_industry(match.group("rest"))
    return {
        "ticker": match.group("symbol"),
        "company_name": company,
        "sector_coarse_pdf": industry,
    }


def extract_snapshot_date(text: str, default_date: date) -> date:
    date_match = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}", text)
    if date_match:
        return parse_human_date(date_match.group(0))
    return default_date


def extract_constituents_from_pdf_text(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    buffer = ""
    for raw_line in text.splitlines():
        line = normalize_space(raw_line)
        if not line:
            continue
        if line in MONTHLY_HEADER_MARKERS:
            continue
        if re.fullmatch(r"\d+", line):
            continue
        first_token = line.split()[0]
        if first_token.upper() in NON_SYMBOL_PREFIXES:
            continue
        if not buffer and is_symbol_token(first_token):
            buffer = line
        elif buffer:
            buffer = f"{buffer} {line}"
        else:
            continue
        if row_complete(buffer):
            parsed = parse_constituent_row(buffer)
            if parsed:
                rows.append(parsed)
            buffer = ""
    unique: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        if row["ticker"] not in seen:
            unique.append(row)
            seen.add(row["ticker"])
    return unique


def locate_nifty200_pdf(zf: zipfile.ZipFile) -> str:
    candidates = []
    for name in zf.namelist():
        normalized = name.upper().replace(" ", "").replace("-", "").replace("_", "")
        if "NIFTY200" in normalized or "CNX200" in normalized:
            candidates.append(name)
    if not candidates:
        raise FileNotFoundError("No Nifty 200 PDF found in archive zip")
    return sorted(candidates)[0]


def load_monthly_snapshot_from_zip(zip_path: Path, fallback_date: date) -> tuple[date, list[dict[str, str]]]:
    with zipfile.ZipFile(zip_path) as archive:
        pdf_name = locate_nifty200_pdf(archive)
        pdf_bytes = archive.read(pdf_name)
    temp_pdf = zip_path.with_suffix(".pdf")
    temp_pdf.write_bytes(pdf_bytes)
    text = extract_pdf_text(temp_pdf)
    temp_pdf.unlink(missing_ok=True)
    snapshot_date = extract_snapshot_date(text, fallback_date)
    rows = extract_constituents_from_pdf_text(text)
    if len(rows) < 150:
        raise ValueError(f"Too few constituents parsed from {zip_path.name}: {len(rows)}")
    return snapshot_date, rows


def build_monthly_archive_snapshots(raw_dir: Path) -> pd.DataFrame:
    archive_dir = ensure_dir(raw_dir / "nifty_archives")
    records: list[dict[str, object]] = []
    for year, month in month_range(2014, 12, 2021, 12):
        token = month_token(year, month)
        zip_path = archive_dir / f"indices_data{token}.zip"
        curl_download(archive_zip_url(year, month), zip_path)
        snapshot_date, rows = load_monthly_snapshot_from_zip(zip_path, month_end(year, month))
        for row in rows:
            records.append(
                {
                    "snapshot_date": snapshot_date,
                    "month_token": token,
                    "ticker": row["ticker"],
                    "company_name": row["company_name"],
                    "sector_coarse_pdf": row["sector_coarse_pdf"],
                    "source_url": archive_zip_url(year, month),
                }
            )
    frame = pd.DataFrame.from_records(records)
    return frame.sort_values(["snapshot_date", "ticker"]).reset_index(drop=True)


def parse_press_release_archive(html_text: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html_text, "html.parser")
    results: list[dict[str, str]] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        title = normalize_space(anchor.get_text(" ", strip=True))
        if "/Press_Release/" not in href or not title:
            continue
        results.append({"title": title, "url": press_release_path(href)})
    return results


def relevant_press_release(title: str) -> bool:
    lowered = title.lower()
    skip_markers = (
        "fixed income",
        "g-sec",
        "bond",
        "sdl",
        "ipo",
        "sme emerge",
        "shariah",
        "aif",
    )
    if any(marker in lowered for marker in skip_markers):
        return False
    if not any(keyword in lowered for keyword in EVENT_KEYWORDS):
        return False
    return any(marker in lowered for marker in ("indices", "index", "nifty"))


def extract_effective_date(text: str, title: str) -> date:
    patterns = [
        r"effective from\s+([A-Za-z]+ \d{1,2}, \d{4})",
        r"w\.e\.f\.\s+([A-Za-z]+ \d{1,2}, \d{4})",
        r"effective from\s+(\d{1,2}-[A-Za-z]+-\d{4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return parse_human_date(match.group(1))
        match = re.search(pattern, title, flags=re.IGNORECASE)
        if match:
            return parse_human_date(match.group(1))
    raise ValueError(f"Unable to find effective date in release: {title}")


def extract_symbol_rows(block: str) -> list[str]:
    symbols: list[str] = []
    for line in block.splitlines():
        normalized = normalize_space(line)
        if not normalized or normalized.lower().startswith("sr. no"):
            continue
        match = re.match(r"^\d+\s+.+?\s+([A-Z0-9&._-]+)$", normalized)
        if match:
            symbols.append(match.group(1))
    return symbols


def extract_nifty200_section(text: str) -> str | None:
    match = re.search(
        r"(?:(?:(?:\d+|[a-z])\)\s+)?)Nifty 200\b(?P<section>.*?)(?=\n(?:\d+|[a-z])\)\s+Nifty |\n[A-Z]\.\s|\Z)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match:
        return match.group("section")
    if "Nifty 200" in text:
        index = text.index("Nifty 200")
        return text[index : index + 4000]
    return None


def parse_nifty200_section_events(section: str, title: str, url: str, effective_date: date) -> list[ChangeEvent]:
    events: list[ChangeEvent] = []
    excluded_block = re.search(
        r"The following companies are being excluded:(?P<body>.*?)(?=The following companies are being included:|$)",
        section,
        flags=re.DOTALL | re.IGNORECASE,
    )
    included_block = re.search(
        r"The following companies are being included:(?P<body>.*?)(?=$)",
        section,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if excluded_block:
        for symbol in extract_symbol_rows(excluded_block.group("body")):
            events.append(ChangeEvent(effective_date, symbol, "exclude", title, url))
    if included_block:
        for symbol in extract_symbol_rows(included_block.group("body")):
            events.append(ChangeEvent(effective_date, symbol, "include", title, url))
    return events


def parse_one_off_index_list_event(text: str, title: str, url: str, effective_date: date) -> list[ChangeEvent]:
    title_lower = title.lower()
    if not any(marker in title_lower for marker in ("exclusion", "inclusion", "corporate adjustment", "demerger")):
        return []
    table_match = re.search(r"Sr\. No\. Index Name(?P<body>.*?)(?:About NSE Indices Limited|For detailed guidelines|\Z)", text, flags=re.DOTALL)
    if not table_match or "Nifty 200" not in table_match.group("body"):
        return []
    symbol_match = re.search(r"\(([A-Z0-9&._-]+)(?:\s+or\s+[^)]*)?\)", text)
    if not symbol_match:
        symbol_match = re.search(r"(?:exclude|include)\s+([A-Z0-9&._-]+)\s+from various indices", text, flags=re.IGNORECASE)
    if not symbol_match:
        return []
    symbol = symbol_match.group(1)
    if "exclusion" in title_lower or "exclude" in text.lower():
        action = "exclude"
    elif "inclusion" in title_lower or "include" in text.lower():
        action = "include"
    else:
        return []
    return [ChangeEvent(effective_date, symbol, action, title, url)]


def extract_events_from_press_release(text: str, title: str, url: str) -> list[ChangeEvent]:
    effective_date = extract_effective_date(text, title)
    section = extract_nifty200_section(text)
    if section:
        parsed = parse_nifty200_section_events(section, title, url, effective_date)
        if parsed:
            return parsed
    return parse_one_off_index_list_event(text, title, url, effective_date)


def build_press_release_events(raw_dir: Path) -> pd.DataFrame:
    archive_dir = ensure_dir(raw_dir / "press_release_pages")
    pdf_dir = ensure_dir(raw_dir / "press_release_pdfs")
    all_events: list[dict[str, object]] = []
    releases_to_process: list[dict[str, str]] = []
    for year in range(2015, 2026):
        html_path = archive_dir / f"press_release_{year}.html"
        curl_download(PRESS_RELEASE_PAGE.format(year=year), html_path)
        releases = parse_press_release_archive(html_path.read_text(encoding="utf-8"))
        for release in releases:
            if not relevant_press_release(release["title"]):
                continue
            releases_to_process.append(release)

    def process_release(release: dict[str, str]) -> list[dict[str, object]]:
        pdf_name = release["url"].rsplit("/", 1)[-1]
        pdf_path = pdf_dir / pdf_name
        curl_download(release["url"], pdf_path)
        text = extract_pdf_text(pdf_path)
        try:
            events = extract_events_from_press_release(text, release["title"], release["url"])
        except ValueError:
            return []
        return [
            {
                "effective_date": event.effective_date,
                "ticker": event.symbol,
                "action": event.action,
                "source_title": event.source_title,
                "source_url": event.source_url,
            }
            for event in events
        ]

    with ThreadPoolExecutor(max_workers=8) as executor:
        future_map = {executor.submit(process_release, release): release["title"] for release in releases_to_process}
        for future in as_completed(future_map):
            try:
                all_events.extend(future.result())
            except Exception:
                continue
    frame = pd.DataFrame.from_records(all_events).drop_duplicates()
    return frame.sort_values(["effective_date", "ticker", "action"]).reset_index(drop=True)


def build_membership_history(raw_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    snapshots = build_monthly_archive_snapshots(raw_dir)
    events = build_press_release_events(raw_dir)

    snapshot_sets = {
        pd.Timestamp(snapshot_date).date(): set(group["ticker"])
        for snapshot_date, group in snapshots.groupby("snapshot_date")
    }
    current_set = set(snapshot_sets[min(snapshot_sets)])
    event_rows = events.to_dict("records")
    event_index = 0
    weekly_dates = daterange_weekly(date(2015, 1, 2), date(2025, 12, 26))
    month_end_dates = daterange_month_end(2015, 1, 2025, 12)

    weekly_records: list[dict[str, object]] = []
    monthly_records: list[dict[str, object]] = []
    reconciliation_rows: list[dict[str, object]] = []

    def advance_state(target_date: date) -> None:
        nonlocal current_set, event_index
        while event_index < len(event_rows) and event_rows[event_index]["effective_date"] <= target_date:
            row = event_rows[event_index]
            if row["action"] == "include":
                current_set.add(row["ticker"])
            elif row["action"] == "exclude":
                current_set.discard(row["ticker"])
            event_index += 1
        if target_date in snapshot_sets:
            official = snapshot_sets[target_date]
            missing = sorted(official - current_set)
            extra = sorted(current_set - official)
            reconciliation_rows.append(
                {
                    "snapshot_date": target_date,
                    "official_count": len(official),
                    "replayed_count": len(current_set),
                    "missing_from_replay": ",".join(missing),
                    "extra_in_replay": ",".join(extra),
                }
            )
            current_set = set(official)

    for week_date in weekly_dates:
        advance_state(week_date)
        for ticker in sorted(current_set):
            weekly_records.append({"Date": week_date, "Ticker": ticker, "In_Nifty200": True})

    current_set = set(snapshot_sets[min(snapshot_sets)])
    event_index = 0
    for month_date in month_end_dates:
        advance_state(month_date)
        for ticker in sorted(current_set):
            monthly_records.append({"Month_End": month_date, "Ticker": ticker, "In_Nifty200": True})

    weekly_frame = pd.DataFrame.from_records(weekly_records)
    monthly_frame = pd.DataFrame.from_records(monthly_records)
    reconciliation_frame = pd.DataFrame.from_records(reconciliation_rows)
    master_universe = pd.DataFrame({"Ticker": sorted(weekly_frame["Ticker"].unique())})
    return master_universe, monthly_frame, weekly_frame, reconciliation_frame, snapshots
