# MD1 Report: Rolling Correlation Study

This notebook section reproduces the original 52-week rolling-correlation study from the first project note, on the repaired historical panel.

## Q1. Is same-group co-movement larger than same-sector co-movement?

- Coarse sectors with PSU: same-group excess `0.104` vs same-sector excess `0.094`.
- Fine sectors with PSU: same-group excess `0.110` vs same-sector excess `0.147`.
- Same-group excess is above same-sector excess in `52.1%` of coarse-sector windows and `27.0%` of fine-sector windows.

Inference: ownership produces a persistent second layer of co-movement, but the strong claim that it cleanly dominates sector is not supported once sector controls become fine.

## Q2. What changes when PSUs are excluded?

- Coarse same-group excess falls from `0.104` to `0.094`.
- Fine same-group excess falls from `0.110` to `0.103`.

Inference: PSU co-movement is a real part of the ownership-style concentration story, but the private-group signal remains even after removing PSUs.

## Q3. Which blocks are most cohesive?

- `Reliance (ADAG)` (Private) average cohesion excess `0.458` with average concurrent membership `3.3`.
- `Adani` (Private) average cohesion excess `0.229` with average concurrent membership `4.4`.
- `Bajaj` (Private) average cohesion excess `0.158` with average concurrent membership `3.7`.
- `Reliance (RIL)` (Private) average cohesion excess `0.147` with average concurrent membership `2.0`.
- `PSU` (PSU) average cohesion excess `0.136` with average concurrent membership `31.4`.
- `Birla` (Private) average cohesion excess `0.117` with average concurrent membership `5.3`.
- `Tata` (Private) average cohesion excess `0.065` with average concurrent membership `10.6`.
- `Mahindra` (Private) average cohesion excess `-0.006` with average concurrent membership `4.5`.

## Q4. Effective number of bets

- Fine-sector, with-PSU average effective entity bets: `10.9` out of `126.0` active entities.
- This remains a heuristic because historical market-cap weights are not available in the local panel.