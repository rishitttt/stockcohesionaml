# Build Plan

## Objective

Construct a weekly long-format panel for the Nifty 200 covering 2015-01-02 through 2025-12-26 with point-in-time membership, prices, sector mappings, and promoter-group labels.

## Source strategy

1. Use monthly Nifty archive PDFs as authoritative constituent snapshots through 2021.
2. Use official Nifty press releases as dated event logs for additions, exclusions, and demerger-related changes.
3. Use NSE shareholding-pattern APIs for quarter-end promoter entities and map them into group labels.
4. Use `yfinance` for price history and fine industry labels.

## Traceable task list

1. Build historical constituent extraction from archive PDFs.
2. Build press-release event extraction and replay state changes.
3. Compute monthly and weekly membership states.
4. Download price history and compute weekly returns.
5. Build sector mapping with official-source-first fallbacks.
6. Build promoter classification with point-in-time quarter joins.
7. Assemble final long panel and a written report.

## Architecture

```mermaid
flowchart TD
    A["Monthly Nifty archive PDFs"] --> B["Authoritative monthly constituent snapshots"]
    C["Nifty press releases"] --> D["Dated add/remove events"]
    B --> E["Membership state engine"]
    D --> E
    F["Master ticker universe"] --> G["yfinance prices"]
    F --> H["yfinance industry metadata"]
    F --> I["NSE shareholding master + promoter tables"]
    E --> J["Weekly membership grid"]
    G --> K["Weekly price + return grid"]
    H --> L["Sector map"]
    I --> M["Quarterly promoter map"]
    J --> N["Final weekly panel"]
    K --> N
    L --> N
    M --> N
```

## Membership reconstruction logic

```mermaid
flowchart TD
    A["Seed state from Dec 2014 archive PDF"] --> B["Replay dated Nifty 200 events forward"]
    B --> C["At each monthly PDF through 2021: reconcile to official snapshot"]
    C --> D["Carry reconciled state forward"]
    D --> E["Sample month-end state for monthly mapping"]
    D --> F["Sample Friday state for weekly panel"]
```

## Promoter classification logic

```mermaid
flowchart TD
    A["NSE shareholding master rows by symbol"] --> B["Quarterly record IDs"]
    B --> C["Promoter detail rows"]
    C --> D["Largest promoter entity by share count"]
    D --> E["Keyword-based group mapping"]
    E --> F["Quarter-end label timeline"]
    F --> G["Forward join to weekly dates"]
```

## Assumptions

- The official Nifty archive PDFs are more authoritative than AMC portfolio disclosures for constituent history and are used because plain Nifty 200 index-fund disclosure history is sparse for parts of the requested window.
- Membership changes are applied on the effective date stated in the press release.
- Quarterly promoter labels take effect on the shareholding pattern date reported by NSE.
- If promoter history cannot be fetched or classified consistently for a ticker, that ticker is dropped from the final panel.
