# MD2 Report: Weekly Variance Decomposition

This notebook section reproduces the original weekly cross-sectional variance-decomposition study from the second project note, on the repaired historical panel.

## Q1. How much weekly cross-sectional variance does sector explain?

- Coarse sectors average `R²`: `0.255`.
- Fine sectors average `R²`: `0.463`.

## Q2. How much incremental variance does promoter-group identity explain after sector?

- Coarse sectors with PSU: group `R²` `0.065`.
- Coarse sectors ex PSU: group `R²` `0.060`.
- Fine sectors with PSU: group `R²` `0.064`.
- Fine sectors ex PSU: group `R²` `0.058`.

Inference: the group factor is real but smaller than sector. It should be interpreted as an incremental structural layer, not the main market partition.

## Q3. Is the group factor growing over time?

- Coarse with PSU: `2015-2019` mean `0.061` vs `2020-2025` mean `0.069`; change `0.008`.
- Fine with PSU: `2015-2019` mean `0.074` vs `2020-2025` mean `0.056`; change `-0.019`.
- Fine ex PSU trend slope per year `-0.0024` with p-value `0.000`.

Inference: the strong upward-growth story is not robust. It weakens and turns negative under the stricter fine-sector specification.

## Q4. Which groups drive the factor?

- `Reliance (ADAG)` average contribution `0.021`, average share of factor `19.7%`, average group size `3.0`.
- `Adani` average contribution `0.013`, average share of factor `17.3%`, average group size `4.4`.
- `PSU` average contribution `0.010`, average share of factor `17.9%`, average group size `32.5`.
- `Bajaj` average contribution `0.007`, average share of factor `12.3%`, average group size `3.7`.
- `Reliance (RIL)` average contribution `0.007`, average share of factor `12.2%`, average group size `1.4`.
- `Birla` average contribution `0.006`, average share of factor `10.9%`, average group size `5.3`.