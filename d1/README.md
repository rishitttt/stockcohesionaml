# Nifty 200 Historical Panel Pipeline

This project builds a point-in-time weekly panel for the Nifty 200 from 2015 to 2025 using only open-source data sources and web scraping.

## What it builds

- Historical Nifty 200 membership without survivorship bias
- Weekly adjusted close and week-over-week returns from `yfinance`
- Coarse sector mapping from official Nifty index sources with fallbacks
- Fine industry mapping from `yfinance`
- Point-in-time promoter-group labels from NSE shareholding pattern disclosures
- A final long-format weekly panel filtered to rows where the stock was actually in the Nifty 200 that week

## Key design choices

- Monthly Nifty archive PDFs are used as authoritative constituent checkpoints through December 2021.
- Official Nifty press releases are replayed as dated change events to capture intra-period additions and exclusions.
- Quarterly promoter labels are joined forward from the disclosure date field in NSE shareholding data.
- All network responses are cached locally under `data/raw/` so reruns are incremental.

## Project layout

- `docs/PLAN.md`: plan, assumptions, and diagrams
- `src/nifty200_pipeline/`: pipeline code
- `tests/`: parser and classification regression tests
- `scripts/run_app.py`: main entrypoint

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run

```bash
.venv/bin/python scripts/run_app.py
```

Outputs are written to `data/processed/`.

## Verify

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```
