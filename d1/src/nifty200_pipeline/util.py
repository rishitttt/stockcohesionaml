from __future__ import annotations

import calendar
import json
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Iterator, Sequence

from pypdf import PdfReader

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def month_end(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def month_range(start_year: int, start_month: int, end_year: int, end_month: int) -> Iterator[tuple[int, int]]:
    year = start_year
    month = start_month
    while (year, month) <= (end_year, end_month):
        yield year, month
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1


def month_token(year: int, month: int) -> str:
    return f"{calendar.month_abbr[month]}{year}"


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def curl_download(url: str, dest: Path, force: bool = False) -> Path:
    if dest.exists() and not force:
        return dest
    ensure_dir(dest.parent)
    command = [
        "curl",
        "-L",
        "--retry",
        "3",
        "--retry-all-errors",
        "--retry-delay",
        "1",
        "--connect-timeout",
        "15",
        "--max-time",
        "60",
        "-A",
        USER_AGENT,
        url,
        "-o",
        str(dest),
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"curl failed for {url}: {completed.stderr.strip()}")
    return dest


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> object:
    return json.loads(read_text(path))


def write_json(path: Path, payload: object) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def parse_human_date(value: str) -> date:
    cleaned = normalize_space(value.replace("w.e.f.", "").replace("effective from", ""))
    cleaned = cleaned.replace("(close of", "").replace(")", "").strip()
    for fmt in ("%B %d, %Y", "%d-%b-%Y", "%d-%B-%Y", "%d %B %Y"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {value}")


def parse_number(value: str | None) -> float:
    if value in (None, "", "-"):
        return 0.0
    return float(str(value).replace(",", ""))


def chunked(values: Sequence[str], size: int) -> Iterator[list[str]]:
    for index in range(0, len(values), size):
        yield list(values[index : index + size])


def add_venv_site_packages(project_root: Path) -> None:
    versions = [
        f"python{sys.version_info.major}.{sys.version_info.minor}",
        f"python{sys.version_info.major}.{sys.version_info.minor - 1}",
    ]
    for version in versions:
        candidate = project_root / ".venv" / "lib" / version / "site-packages"
        if candidate.exists():
            sys.path.insert(0, str(candidate))
            return


def daterange_weekly(start: date, end: date) -> list[date]:
    current = start
    values: list[date] = []
    while current <= end:
        values.append(current)
        current = current.fromordinal(current.toordinal() + 7)
    return values


def daterange_month_end(start_year: int, start_month: int, end_year: int, end_month: int) -> list[date]:
    return [month_end(year, month) for year, month in month_range(start_year, start_month, end_year, end_month)]


def best_symbol_match(symbol_text: str) -> str:
    return normalize_space(symbol_text).split()[-1].upper()
