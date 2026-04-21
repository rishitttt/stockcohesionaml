# Results

## Output artifacts

- `data/processed/master_universe.csv`: raw decade-wide master universe before promoter-history filtering
- `data/processed/master_universe_filtered.csv`: subset retained after unresolved promoter histories were dropped
- `data/processed/monthly_membership.csv`: raw month-end Nifty 200 membership map
- `data/processed/monthly_membership_filtered.csv`: month-end membership after promoter-history filtering
- `data/processed/weekly_membership.csv`: raw Friday membership map
- `data/processed/weekly_membership_filtered.csv`: Friday membership after promoter-history filtering
- `data/processed/weekly_panel.csv`: final long-format panel with verified promoter labels only
- `data/processed/promoter_history.csv`: quarter-end promoter labels
- `data/processed/unresolved_promoters.csv`: unresolved promoter-history fetch/classification cases
- `data/processed/sector_map.csv`: coarse and fine sector map
- `data/processed/membership_reconciliation.csv`: differences between replayed event state and monthly official archive checkpoints

## Coverage summary

- Raw master universe: `378` unique tickers
- Tickers with at least one classified promoter quarter: `343`
- Tickers dropped for unresolved promoter-history gaps: `34`
- Tickers dropped because NSE returned no usable promoter-history rows: `35`
- Promoter-verified subset retained for final panel: `309` unique tickers
- Raw monthly membership rows: `26,475` across `132` month-end snapshots
- Raw weekly membership rows: `115,105` across `574` Friday snapshots
- Filtered monthly membership rows: `21,935`
- Filtered weekly membership rows: `95,300`
- Final weekly panel rows: `95,300`
- Final panel date range: `2015-01-02` to `2025-12-26`

## Raw universe quality checks

- Average raw month-end constituent count: `200.57`
- Min raw month-end constituent count: `197`
- Max raw month-end constituent count: `207`
- Average raw Friday constituent count: `200.53`
- Min raw Friday constituent count: `197`
- Max raw Friday constituent count: `207`

These counts are close to the intended `200`, with temporary deviations driven by corporate-action handling and the event-replay layer before monthly checkpoint reconciliation.

## Filtered panel quality checks

- Average filtered month-end constituent count: `166.17`
- Min filtered month-end constituent count: `155`
- Max filtered month-end constituent count: `180`
- Average filtered Friday constituent count: `166.03`
- Min filtered Friday constituent count: `155`
- Max filtered Friday constituent count: `180`

The filtered cross-section is materially smaller because the final panel applies the instruction to drop any ticker whose ownership chain could not be verified end to end.

## Final panel completeness

- Missing `Promoter_Group` rows in final panel: `0`
- Unresolved-promoter tickers surviving into final panel: `0`
- Missing `Sector_Coarse` rows in final panel: `0`
- Missing `Adj_Close` rows in final panel: `3,483`
- Missing `Weekly_Return` rows in final panel: `3,483`
- Missing `Sector_Fine` rows in final panel: `3,787`

The missing price rows are concentrated in `19` retained legacy Yahoo symbols:

- `HDFC`
- `PEL`
- `MINDTREE`
- `HEXAWARE`
- `DHANI`
- `GRUH`
- `TV18BRDCST`
- `GSKCONS`
- `SYNDIBANK`
- `IDFC`
- `BHARATFIN`
- `ALBK`
- `ABIRLANUVO`
- `AMTEKAUTO`
- `GDL`
- `SINTEX`
- `CMC`
- `INGVYSYABK`
- `ISEC`

The missing fine-sector rows are concentrated in the same delisted or renamed symbols plus a small metadata-only tail such as `RELCAPITAL`, `DALMIABHA`, and `VIDEOIND`.

## Promoter-group distribution in the final panel

- `Independent`: `68,719` rows
- `GOI_PSU`: `16,055` rows
- `Birla`: `2,862` rows
- `Tata`: `2,812` rows
- `Bajaj`: `1,976` rows
- `Adani`: `1,180` rows
- `Reliance`: `1,174` rows
- `Mahindra`: `522` rows

## Reconciliation diagnostics

- Official monthly archive checkpoints checked: `93`
- Checkpoints with any replay difference before reset-to-official reconciliation: `54`

Largest replay drifts before monthly reset:

- `2016-04-29`: missing `36`, extra `35`
- `2016-05-31`: missing `36`, extra `35`
- `2018-06-29`: missing `16`, extra `17`
- `2015-05-29`: missing `13`, extra `13`
- `2015-10-30`: missing `11`, extra `12`

This means the event-replay layer is useful for intra-period timing, but the monthly archive checkpoints remain the authoritative state anchor through 2021.

## Important caveats

1. The original request suggested AMC portfolio disclosures as the base-universe source. In practice, the official Nifty archive PDFs were materially more complete and authoritative for 2015-2021, so they were used as the primary source. This avoids survivorship bias more reliably than sparse AMC history.
2. Promoter-history verification is the strictest filter in the final panel. `69` tickers were excluded: `35` because NSE did not return any usable promoter timeline for the legacy symbol, and `34` because at least one quarter remained unresolved after scraping and classification.
3. Yahoo ticker continuity is imperfect for delisted, merged, and renamed NSE symbols, so `19` retained constituents still carry missing price and return rows.
4. Fine industry mapping depends on `yfinance` metadata. `22` retained symbols still have missing `Sector_Fine`, concentrated in delisted or renamed names where Yahoo no longer exposes industry metadata.
5. The `membership_reconciliation.csv` file should be treated as a health-check artifact. It shows where the press-release replay diverged from the official month-end archive before the pipeline reset the state back to the official snapshot.
