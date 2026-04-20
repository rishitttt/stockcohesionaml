from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from tqdm import tqdm


TEXT_COLOR = "#0f172a"
GRID_COLOR = "#cbd5e1"
SECTOR_COLOR = "#1d4ed8"
GROUP_COLOR = "#b45309"
WITH_PSU_COLOR = "#0f766e"
EX_PSU_COLOR = "#dc2626"
MUTED_COLOR = "#94a3b8"

DISPLAY_GROUPS = {
    "GOI_PSU": "PSU",
    "Reliance_RIL": "Reliance (RIL)",
    "Reliance_ADAG": "Reliance (ADAG)",
}

GROUP_ORDER = [
    "Tata",
    "Adani",
    "Bajaj",
    "Birla",
    "Mahindra",
    "Reliance_RIL",
    "Reliance_ADAG",
    "GOI_PSU",
]


@dataclass(frozen=True)
class StudySpec:
    name: str
    sector_col: str
    exclude_psu: bool = False

    @property
    def label(self) -> str:
        sector = "Coarse" if self.sector_col == "Sector_Coarse" else "Fine"
        psu = "Ex PSU" if self.exclude_psu else "With PSU"
        return f"{sector} | {psu}"


@dataclass(frozen=True)
class Phase4Spec:
    input_path: Path = Path("data/completed/weekly_panel_completed.csv")
    output_dir: Path = Path("phase4/results")
    rolling_window: int = 52
    rolling_min_obs: int = 26
    min_stocks: int = 100
    permutations: int = 1000
    seed: int = 42
    newey_west_lags: int = 6
    smooth_weeks: int = 26


DEFAULT_SPECS = [
    StudySpec("coarse_all", "Sector_Coarse", False),
    StudySpec("coarse_ex_psu", "Sector_Coarse", True),
    StudySpec("fine_all", "Sector_Fine", False),
    StudySpec("fine_ex_psu", "Sector_Fine", True),
]


def _display_group(group: str) -> str:
    return DISPLAY_GROUPS.get(group, group)


def _style_axis(ax: plt.Axes) -> None:
    ax.set_facecolor("white")
    ax.grid(axis="y", color=GRID_COLOR, alpha=0.4, linewidth=0.8)
    ax.tick_params(colors=TEXT_COLOR, labelsize=10)
    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)
        spine.set_alpha(0.6)


def _period_mask(dates: pd.Series | pd.Index, period: str) -> pd.Series:
    dates = pd.to_datetime(dates)
    if period == "2015_2019":
        return (dates >= pd.Timestamp("2015-01-01")) & (dates < pd.Timestamp("2020-01-01"))
    if period == "2020_2025":
        return dates >= pd.Timestamp("2020-01-01")
    if period == "2015_2017":
        return (dates >= pd.Timestamp("2015-01-01")) & (dates < pd.Timestamp("2018-01-01"))
    if period == "2018_2021":
        return (dates >= pd.Timestamp("2018-01-01")) & (dates < pd.Timestamp("2022-01-01"))
    if period == "2022_2025":
        return dates >= pd.Timestamp("2022-01-01")
    raise ValueError(period)


def _ordered_groups(groups: list[str]) -> list[str]:
    ordered = [group for group in GROUP_ORDER if group in groups]
    ordered.extend(sorted(group for group in groups if group not in ordered))
    return ordered


def _mean_off_diagonal(corr: pd.DataFrame) -> tuple[float, int]:
    if corr.shape[0] < 2:
        return np.nan, 0
    arr = corr.to_numpy(dtype=float)
    tri = arr[np.triu_indices_from(arr, k=1)]
    tri = tri[np.isfinite(tri)]
    if len(tri) == 0:
        return np.nan, 0
    return float(tri.mean()), int(len(tri))


def _participation_ratio(corr: pd.DataFrame) -> float:
    if corr.shape[0] < 2:
        return np.nan
    arr = corr.to_numpy(dtype=float)
    arr = np.where(np.isfinite(arr), arr, 0.0)
    np.fill_diagonal(arr, 1.0)
    eigvals = np.linalg.eigvalsh(arr)
    denom = float(np.square(eigvals).sum())
    if denom <= 0:
        return np.nan
    return float((eigvals.sum() ** 2) / denom)


def load_panel(path: str | Path) -> pd.DataFrame:
    panel = pd.read_csv(path, parse_dates=["Date"])
    required = {
        "Date",
        "Ticker",
        "In_Nifty200",
        "Adj_Close",
        "Weekly_Return",
        "Sector_Coarse",
        "Sector_Fine",
        "Promoter_Group",
    }
    missing = required.difference(panel.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    panel = panel.copy()
    panel = panel.loc[panel["In_Nifty200"].astype(bool)].copy()
    panel["Weekly_Return"] = pd.to_numeric(panel["Weekly_Return"], errors="coerce")
    panel["Adj_Close"] = pd.to_numeric(panel["Adj_Close"], errors="coerce")
    panel["Sector_Coarse"] = panel["Sector_Coarse"].fillna("Unknown")
    panel["Sector_Fine"] = panel["Sector_Fine"].fillna(panel["Sector_Coarse"]).fillna("Unknown")
    panel["Promoter_Group"] = panel["Promoter_Group"].fillna("Independent")
    return panel.sort_values(["Date", "Ticker"]).reset_index(drop=True)


def compute_md1_rolling(
    panel: pd.DataFrame,
    specs: list[StudySpec],
    rolling_window: int,
    min_obs: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metric_frames: list[pd.DataFrame] = []
    cohesion_frames: list[pd.DataFrame] = []
    effective_frames: list[pd.DataFrame] = []
    summary_rows: list[dict] = []

    for spec in specs:
        spec_panel = panel.copy()
        if spec.exclude_psu:
            spec_panel = spec_panel.loc[spec_panel["Promoter_Group"] != "GOI_PSU"].copy()

        returns_wide = spec_panel.pivot_table(index="Date", columns="Ticker", values="Weekly_Return").sort_index()
        snapshots = {
            date: cross.set_index("Ticker")[[spec.sector_col, "Promoter_Group"]]
            for date, cross in spec_panel.groupby("Date", sort=True)
        }
        dates = list(returns_wide.index)

        metric_rows: list[dict] = []
        cohesion_rows: list[dict] = []
        effective_rows: list[dict] = []

        for end_idx in tqdm(range(rolling_window - 1, len(dates)), desc=f"MD1 [{spec.name}]"):
            end_date = dates[end_idx]
            window_dates = dates[end_idx + 1 - rolling_window : end_idx + 1]
            window_data = returns_wide.loc[window_dates]
            snapshot = snapshots.get(end_date)
            if snapshot is None or snapshot.empty:
                continue

            valid_cols = [
                ticker
                for ticker in window_data.columns
                if window_data[ticker].notna().sum() >= min_obs and ticker in snapshot.index
            ]
            if len(valid_cols) < 3:
                continue

            labels = snapshot.loc[valid_cols]
            sector_vals = labels[spec.sector_col].fillna("Unknown").astype(str).to_numpy()
            group_vals = labels["Promoter_Group"].fillna("Independent").astype(str).to_numpy()
            corr = window_data[valid_cols].corr(min_periods=min_obs)
            baseline, n_baseline_pairs = _mean_off_diagonal(corr)
            if not np.isfinite(baseline):
                continue

            same_sector = sector_vals[:, None] == sector_vals[None, :]
            same_group = group_vals[:, None] == group_vals[None, :]
            upper = np.triu(np.ones((len(valid_cols), len(valid_cols)), dtype=bool), k=1)
            independent = group_vals == "Independent"
            both_independent = independent[:, None] & independent[None, :]
            sector_mask = upper & same_sector & ~same_group
            group_mask = upper & same_group & ~same_sector & ~both_independent

            corr_arr = corr.to_numpy(dtype=float)
            sector_corrs = corr_arr[sector_mask]
            sector_corrs = sector_corrs[np.isfinite(sector_corrs)]
            group_corrs = corr_arr[group_mask]
            group_corrs = group_corrs[np.isfinite(group_corrs)]

            sector_mean = float(sector_corrs.mean()) if len(sector_corrs) else np.nan
            group_mean = float(group_corrs.mean()) if len(group_corrs) else np.nan

            metric_rows.append(
                {
                    "Date": end_date,
                    "spec": spec.name,
                    "label": spec.label,
                    "sector_col": spec.sector_col,
                    "exclude_psu": spec.exclude_psu,
                    "baseline_corr": baseline,
                    "same_sector_mean": sector_mean,
                    "same_sector_excess": sector_mean - baseline if np.isfinite(sector_mean) else np.nan,
                    "same_group_mean": group_mean,
                    "same_group_excess": group_mean - baseline if np.isfinite(group_mean) else np.nan,
                    "n_tickers": len(valid_cols),
                    "n_baseline_pairs": n_baseline_pairs,
                    "n_sector_pairs": int(len(sector_corrs)),
                    "n_group_pairs": int(len(group_corrs)),
                }
            )

            active_groups = _ordered_groups(sorted(set(group_vals).intersection(GROUP_ORDER)))
            for group in active_groups:
                members = [ticker for ticker, value in zip(valid_cols, group_vals) if value == group]
                if len(members) < 2:
                    continue
                cohesion, n_pairs = _mean_off_diagonal(corr.loc[members, members])
                cohesion_rows.append(
                    {
                        "Date": end_date,
                        "spec": spec.name,
                        "label": spec.label,
                        "group": group,
                        "group_display": _display_group(group),
                        "group_type": "PSU" if group == "GOI_PSU" else "Private",
                        "n_members": len(members),
                        "group_corr_mean": cohesion,
                        "group_cohesion_excess": cohesion - baseline if np.isfinite(cohesion) else np.nan,
                        "baseline_corr": baseline,
                        "n_pairs": n_pairs,
                    }
                )

            entity_labels = [group if group != "Independent" else ticker for ticker, group in zip(valid_cols, group_vals)]
            entity_returns = window_data[valid_cols].T.groupby(entity_labels).mean().T
            entity_cols = [col for col in entity_returns.columns if entity_returns[col].notna().sum() >= min_obs]
            entity_corr = entity_returns[entity_cols].corr(min_periods=min_obs) if len(entity_cols) >= 2 else pd.DataFrame()
            effective_rows.append(
                {
                    "Date": end_date,
                    "spec": spec.name,
                    "label": spec.label,
                    "n_active_stocks": len(valid_cols),
                    "n_active_entities": len(entity_cols),
                    "effective_entity_bets": _participation_ratio(entity_corr) if not entity_corr.empty else np.nan,
                }
            )

        metrics = pd.DataFrame(metric_rows).sort_values("Date").reset_index(drop=True)
        cohesion = pd.DataFrame(cohesion_rows).sort_values(["group", "Date"]).reset_index(drop=True)
        effective = pd.DataFrame(effective_rows).sort_values("Date").reset_index(drop=True)
        metric_frames.append(metrics)
        cohesion_frames.append(cohesion)
        effective_frames.append(effective)

        if metrics.empty:
            continue

        early = metrics.loc[_period_mask(metrics["Date"], "2015_2019")]
        late = metrics.loc[_period_mask(metrics["Date"], "2020_2025")]
        summary_rows.append(
            {
                "spec": spec.name,
                "label": spec.label,
                "avg_baseline_corr": float(metrics["baseline_corr"].mean()),
                "avg_same_sector_excess": float(metrics["same_sector_excess"].mean()),
                "avg_same_group_excess": float(metrics["same_group_excess"].mean()),
                "avg_group_minus_sector": float((metrics["same_group_excess"] - metrics["same_sector_excess"]).mean()),
                "share_weeks_group_gt_sector": float((metrics["same_group_excess"] > metrics["same_sector_excess"]).mean()),
                "avg_n_sector_pairs": float(metrics["n_sector_pairs"].mean()),
                "avg_n_group_pairs": float(metrics["n_group_pairs"].mean()),
                "mean_group_excess_2015_2019": float(early["same_group_excess"].mean()) if not early.empty else np.nan,
                "mean_group_excess_2020_2025": float(late["same_group_excess"].mean()) if not late.empty else np.nan,
                "diff_group_excess_late_minus_early": (
                    float(late["same_group_excess"].mean() - early["same_group_excess"].mean())
                    if not early.empty and not late.empty
                    else np.nan
                ),
                "avg_effective_entity_bets": float(effective["effective_entity_bets"].mean()) if not effective.empty else np.nan,
                "avg_active_entities": float(effective["n_active_entities"].mean()) if not effective.empty else np.nan,
            }
        )

    metric_df = pd.concat(metric_frames, ignore_index=True)
    cohesion_df = pd.concat(cohesion_frames, ignore_index=True)
    effective_df = pd.concat(effective_frames, ignore_index=True)
    summary_df = pd.DataFrame(summary_rows).sort_values("spec").reset_index(drop=True)
    return metric_df, cohesion_df, effective_df, summary_df


def compute_md2_variance(
    panel: pd.DataFrame,
    specs: list[StudySpec],
    min_stocks: int,
    permutations: int,
    seed: int,
    newey_west_lags: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    weekly_frames: list[pd.DataFrame] = []
    group_frames: list[pd.DataFrame] = []
    summary_frames: list[pd.DataFrame] = []

    for idx, spec in enumerate(specs):
        data = panel.dropna(subset=["Weekly_Return", spec.sector_col]).copy()
        if spec.exclude_psu:
            data = data.loc[data["Promoter_Group"] != "GOI_PSU"].copy()

        rng = np.random.default_rng(seed + idx)
        weekly_rows: list[dict] = []
        group_rows: list[dict] = []

        for date, cross in tqdm(data.groupby("Date", sort=True), desc=f"MD2 [{spec.name}]"):
            cross = cross.copy()
            n_stocks = len(cross)
            if n_stocks < min_stocks:
                continue

            returns = cross["Weekly_Return"].to_numpy(dtype=float)
            overall_mean = float(returns.mean())
            total_ss = float(np.sum((returns - overall_mean) ** 2))
            if total_ss <= 0:
                continue

            sector_means = cross.groupby(spec.sector_col)["Weekly_Return"].transform("mean").to_numpy(dtype=float)
            sector_residual = returns - sector_means
            sector_resid_ss = float(np.sum(sector_residual ** 2))
            sector_r2 = 1.0 - (sector_resid_ss / total_ss)

            promoter = cross["Promoter_Group"].astype(str).to_numpy()
            named_groups = _ordered_groups([group for group in pd.unique(promoter) if group != "Independent"])

            contribution_records: list[dict] = []
            actual_group_ss = 0.0
            for group in named_groups:
                mask = promoter == group
                if not np.any(mask):
                    continue
                group_mean = float(sector_residual[mask].mean())
                group_count = int(mask.sum())
                group_ss = float(group_count * (group_mean ** 2))
                actual_group_ss += group_ss
                contribution_records.append(
                    {
                        "Date": date,
                        "spec": spec.name,
                        "label": spec.label,
                        "sector_col": spec.sector_col,
                        "exclude_psu": spec.exclude_psu,
                        "Promoter_Group": group,
                        "group_display": _display_group(group),
                        "n_stocks": group_count,
                        "group_mean_sector_residual": group_mean,
                        "group_ss": group_ss,
                    }
                )

            group_r2 = actual_group_ss / sector_resid_ss if sector_resid_ss > 0 and contribution_records else np.nan
            perm_mean = np.nan
            perm95 = np.nan
            perm_pvalue = np.nan
            if pd.notna(group_r2) and contribution_records and permutations > 0:
                indicator_groups = [record["Promoter_Group"] for record in contribution_records]
                indicator = np.column_stack([(promoter == group) for group in indicator_groups]).astype(float)
                counts = indicator.sum(axis=0)
                permuted_index = np.argsort(rng.random((permutations, n_stocks)), axis=1)
                permuted_residuals = sector_residual[permuted_index]
                group_sums = permuted_residuals @ indicator
                perm_r2 = (((group_sums ** 2) / counts).sum(axis=1)) / sector_resid_ss
                perm_mean = float(perm_r2.mean())
                perm95 = float(np.quantile(perm_r2, 0.95))
                perm_pvalue = float((1 + np.sum(perm_r2 >= group_r2)) / (permutations + 1))

            weekly_rows.append(
                {
                    "Date": date,
                    "spec": spec.name,
                    "label": spec.label,
                    "sector_col": spec.sector_col,
                    "exclude_psu": spec.exclude_psu,
                    "n_stocks": n_stocks,
                    "n_sectors": int(cross[spec.sector_col].astype(str).nunique()),
                    "n_named_groups": len(contribution_records),
                    "n_non_independent_stocks": int(np.sum(promoter != "Independent")),
                    "sector_r2": sector_r2,
                    "sector_resid_ss": sector_resid_ss,
                    "group_r2": group_r2,
                    "perm_mean_group_r2": perm_mean,
                    "perm95_group_r2": perm95,
                    "perm_pvalue": perm_pvalue,
                    "group_r2_gap_vs_null": group_r2 - perm_mean if pd.notna(group_r2) and pd.notna(perm_mean) else np.nan,
                }
            )

            total_group_ss = actual_group_ss if actual_group_ss > 0 else np.nan
            for record in contribution_records:
                record["group_r2_contribution"] = record["group_ss"] / sector_resid_ss if sector_resid_ss > 0 else np.nan
                record["share_of_group_r2"] = record["group_ss"] / total_group_ss if pd.notna(total_group_ss) else np.nan
                group_rows.append(record)

        weekly = pd.DataFrame(weekly_rows).sort_values("Date").reset_index(drop=True)
        groups = pd.DataFrame(group_rows).sort_values(["Date", "Promoter_Group"]).reset_index(drop=True)
        weekly_frames.append(weekly)
        group_frames.append(groups)

        if weekly.empty:
            continue

        valid = weekly.dropna(subset=["group_r2"]).copy()
        summary = {
            "spec": spec.name,
            "label": spec.label,
            "sector_col": spec.sector_col,
            "exclude_psu": spec.exclude_psu,
            "weeks_total": int(len(weekly)),
            "weeks_with_group_r2": int(len(valid)),
            "avg_n_stocks": float(weekly["n_stocks"].mean()),
            "avg_sector_r2": float(weekly["sector_r2"].mean()),
            "avg_group_r2": float(valid["group_r2"].mean()) if not valid.empty else np.nan,
            "avg_group_gap_vs_null": float(valid["group_r2_gap_vs_null"].mean()) if not valid.empty else np.nan,
            "share_weeks_above_perm95": float((valid["group_r2"] > valid["perm95_group_r2"]).mean()) if not valid.empty else np.nan,
            "mean_2015_2019": float(valid.loc[_period_mask(valid["Date"], "2015_2019"), "group_r2"].mean()) if not valid.empty else np.nan,
            "mean_2020_2025": float(valid.loc[_period_mask(valid["Date"], "2020_2025"), "group_r2"].mean()) if not valid.empty else np.nan,
            "mean_2015_2017": float(valid.loc[_period_mask(valid["Date"], "2015_2017"), "group_r2"].mean()) if not valid.empty else np.nan,
            "mean_2018_2021": float(valid.loc[_period_mask(valid["Date"], "2018_2021"), "group_r2"].mean()) if not valid.empty else np.nan,
            "mean_2022_2025": float(valid.loc[_period_mask(valid["Date"], "2022_2025"), "group_r2"].mean()) if not valid.empty else np.nan,
            "trend_slope_per_year": np.nan,
            "trend_pvalue": np.nan,
            "trend_tstat": np.nan,
            "newey_west_lags": newey_west_lags,
        }
        summary["diff_2020_2025_minus_2015_2019"] = (
            summary["mean_2020_2025"] - summary["mean_2015_2019"]
            if pd.notna(summary["mean_2020_2025"]) and pd.notna(summary["mean_2015_2019"])
            else np.nan
        )
        if len(valid) >= 20:
            trend_years = (valid["Date"] - valid["Date"].min()).dt.days / 365.25
            model = sm.OLS(valid["group_r2"], sm.add_constant(trend_years)).fit(
                cov_type="HAC",
                cov_kwds={"maxlags": newey_west_lags},
            )
            summary["trend_slope_per_year"] = float(model.params.iloc[1])
            summary["trend_pvalue"] = float(model.pvalues.iloc[1])
            summary["trend_tstat"] = float(model.tvalues.iloc[1])
        summary_frames.append(pd.DataFrame([summary]))

    weekly_df = pd.concat(weekly_frames, ignore_index=True)
    group_df = pd.concat(group_frames, ignore_index=True)
    summary_df = pd.concat(summary_frames, ignore_index=True).sort_values("spec").reset_index(drop=True)
    group_summary = (
        group_df.groupby(["spec", "label", "Promoter_Group", "group_display"], as_index=False)
        .agg(
            avg_contribution=("group_r2_contribution", "mean"),
            avg_share_of_group_r2=("share_of_group_r2", "mean"),
            avg_group_size=("n_stocks", "mean"),
        )
        .sort_values(["spec", "avg_contribution"], ascending=[True, False])
        .reset_index(drop=True)
    )
    return weekly_df, group_df, summary_df, group_summary


def _smooth(series: pd.Series, weeks: int) -> pd.Series:
    return series.rolling(weeks, min_periods=max(6, weeks // 3)).mean()


def plot_md1_core(metrics: pd.DataFrame, output_path: Path, smooth_weeks: int) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.8), sharey=True)
    fig.patch.set_facecolor("white")
    for ax, spec_name, title in zip(axes, ["coarse_all", "fine_all"], ["Coarse Sectors", "Fine Sectors"]):
        _style_axis(ax)
        subset = metrics.loc[metrics["spec"] == spec_name].sort_values("Date")
        ax.plot(subset["Date"], _smooth(subset["same_sector_excess"], smooth_weeks), color=SECTOR_COLOR, linewidth=2.4, label="Same-sector excess")
        ax.plot(subset["Date"], _smooth(subset["same_group_excess"], smooth_weeks), color=GROUP_COLOR, linewidth=2.4, label="Same-group excess")
        ax.plot(subset["Date"], subset["same_sector_excess"], color=SECTOR_COLOR, linewidth=0.7, alpha=0.12)
        ax.plot(subset["Date"], subset["same_group_excess"], color=GROUP_COLOR, linewidth=0.7, alpha=0.12)
        ax.set_title(title, color=TEXT_COLOR, fontsize=13, pad=10, fontweight="bold")
        ax.set_xlabel("Date", color=TEXT_COLOR)
    axes[0].set_ylabel("Excess Correlation Over Baseline", color=TEXT_COLOR)
    axes[0].legend(frameon=False, loc="upper left")
    fig.suptitle("MD1: Ownership Versus Sector in Rolling 52-Week Correlations", color=TEXT_COLOR, fontsize=16, fontweight="bold")
    plt.tight_layout()
    fig.savefig(output_path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def plot_md1_psu(metrics: pd.DataFrame, output_path: Path, smooth_weeks: int) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.8), sharey=True)
    fig.patch.set_facecolor("white")
    for ax, spec_names, title in zip(
        axes,
        [("coarse_all", "coarse_ex_psu"), ("fine_all", "fine_ex_psu")],
        ["Coarse Sectors", "Fine Sectors"],
    ):
        _style_axis(ax)
        for spec_name, color in zip(spec_names, [WITH_PSU_COLOR, EX_PSU_COLOR]):
            subset = metrics.loc[metrics["spec"] == spec_name].sort_values("Date")
            ax.plot(subset["Date"], _smooth(subset["same_group_excess"], smooth_weeks), color=color, linewidth=2.4, label=subset["label"].iloc[0])
        ax.set_title(title, color=TEXT_COLOR, fontsize=13, pad=10, fontweight="bold")
        ax.set_xlabel("Date", color=TEXT_COLOR)
    axes[0].set_ylabel("Same-Group Excess Correlation", color=TEXT_COLOR)
    axes[0].legend(frameon=False, loc="upper left")
    fig.suptitle("MD1: PSU Sensitivity of the Ownership Signal", color=TEXT_COLOR, fontsize=16, fontweight="bold")
    plt.tight_layout()
    fig.savefig(output_path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def plot_md1_groups(cohesion: pd.DataFrame, output_path: Path, smooth_weeks: int) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(15, 9), sharex=True)
    fig.patch.set_facecolor("white")
    for ax in axes:
        _style_axis(ax)
    private_groups = ["Tata", "Adani", "Bajaj", "Birla", "Mahindra", "Reliance_RIL", "Reliance_ADAG"]
    colors = ["#1d4ed8", "#b45309", "#0f766e", "#9333ea", "#dc2626", "#0891b2", "#475569"]
    subset = cohesion.loc[cohesion["spec"] == "fine_all"]
    for group, color in zip(private_groups, colors):
        frame = subset.loc[subset["group"] == group].sort_values("Date")
        if frame.empty:
            continue
        axes[0].plot(frame["Date"], _smooth(frame["group_cohesion_excess"], smooth_weeks), color=color, linewidth=2.0, label=_display_group(group))
    axes[0].set_title("Private Group Cohesion (Fine-Sector Window)", color=TEXT_COLOR, fontsize=13, pad=10, fontweight="bold")
    axes[0].set_ylabel("Cohesion Excess", color=TEXT_COLOR)
    axes[0].legend(frameon=False, ncol=4, loc="upper left")

    psu = subset.loc[subset["group"] == "GOI_PSU"].sort_values("Date")
    if not psu.empty:
        axes[1].plot(psu["Date"], _smooth(psu["group_cohesion_excess"], smooth_weeks), color=GROUP_COLOR, linewidth=2.4, label="PSU")
        axes[1].plot(psu["Date"], psu["group_cohesion_excess"], color=GROUP_COLOR, linewidth=0.7, alpha=0.12)
    axes[1].set_title("PSU Cohesion (Fine-Sector Window)", color=TEXT_COLOR, fontsize=13, pad=10, fontweight="bold")
    axes[1].set_ylabel("Cohesion Excess", color=TEXT_COLOR)
    axes[1].set_xlabel("Date", color=TEXT_COLOR)
    axes[1].legend(frameon=False, loc="upper left")
    fig.suptitle("MD1: Group-by-Group Cohesion Over Time", color=TEXT_COLOR, fontsize=16, fontweight="bold")
    plt.tight_layout()
    fig.savefig(output_path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def plot_md1_effective(effective: pd.DataFrame, output_path: Path, smooth_weeks: int) -> None:
    fig, ax = plt.subplots(figsize=(15, 5.5))
    fig.patch.set_facecolor("white")
    _style_axis(ax)
    for spec_name, color in [("fine_all", WITH_PSU_COLOR), ("fine_ex_psu", EX_PSU_COLOR)]:
        subset = effective.loc[effective["spec"] == spec_name].sort_values("Date")
        ax.plot(subset["Date"], _smooth(subset["effective_entity_bets"], smooth_weeks), color=color, linewidth=2.4, label=subset["label"].iloc[0])
    base = effective.loc[effective["spec"] == "fine_all"].sort_values("Date")
    ax.plot(base["Date"], _smooth(base["n_active_entities"], smooth_weeks), color=MUTED_COLOR, linewidth=2.0, linestyle="--", label="Active entities")
    ax.set_title("MD1: Heuristic Effective Number of Entity-Level Bets", color=TEXT_COLOR, fontsize=16, pad=12, fontweight="bold")
    ax.set_ylabel("Count", color=TEXT_COLOR)
    ax.set_xlabel("Date", color=TEXT_COLOR)
    ax.legend(frameon=False, loc="upper left")
    plt.tight_layout()
    fig.savefig(output_path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def plot_md2_core(weekly: pd.DataFrame, output_path: Path, smooth_weeks: int) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(15, 9), sharex=True)
    fig.patch.set_facecolor("white")
    for ax in axes:
        _style_axis(ax)
    for spec_name, color in [("coarse_all", SECTOR_COLOR), ("fine_all", WITH_PSU_COLOR)]:
        subset = weekly.loc[weekly["spec"] == spec_name].sort_values("Date")
        axes[0].plot(subset["Date"], _smooth(subset["sector_r2"], smooth_weeks), color=color, linewidth=2.4, label=subset["label"].iloc[0])
        axes[0].plot(subset["Date"], subset["sector_r2"], color=color, linewidth=0.7, alpha=0.1)
    axes[0].set_title("Sector Share of Weekly Cross-Sectional Variance", color=TEXT_COLOR, fontsize=13, pad=10, fontweight="bold")
    axes[0].set_ylabel("Sector R-squared", color=TEXT_COLOR)
    axes[0].legend(frameon=False, loc="upper left")

    for spec_name, color in [("coarse_all", WITH_PSU_COLOR), ("coarse_ex_psu", EX_PSU_COLOR), ("fine_all", "#0f766e"), ("fine_ex_psu", "#7c3aed")]:
        subset = weekly.loc[weekly["spec"] == spec_name].sort_values("Date")
        axes[1].plot(subset["Date"], _smooth(subset["group_r2"], smooth_weeks), color=color, linewidth=2.2, label=subset["label"].iloc[0])
        axes[1].plot(subset["Date"], subset["group_r2"], color=color, linewidth=0.7, alpha=0.08)
    axes[1].set_title("Incremental Promoter-Group Share After Sector Removal", color=TEXT_COLOR, fontsize=13, pad=10, fontweight="bold")
    axes[1].set_ylabel("Group R-squared", color=TEXT_COLOR)
    axes[1].set_xlabel("Date", color=TEXT_COLOR)
    axes[1].legend(frameon=False, ncol=2, loc="upper left")
    fig.suptitle("MD2: Weekly Sector and Ownership Variance Decomposition", color=TEXT_COLOR, fontsize=16, fontweight="bold")
    plt.tight_layout()
    fig.savefig(output_path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def plot_md2_groups(group_contrib: pd.DataFrame, output_path: Path, smooth_weeks: int) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.8), sharey=True)
    fig.patch.set_facecolor("white")
    for ax in axes:
        _style_axis(ax)
    for ax, spec_name, title in zip(axes, ["coarse_all", "fine_all"], ["Coarse Sectors", "Fine Sectors"]):
        subset = group_contrib.loc[group_contrib["spec"] == spec_name].copy()
        top_groups = (
            subset.groupby("group_display")["group_r2_contribution"]
            .mean()
            .sort_values(ascending=False)
            .head(5)
            .index.tolist()
        )
        colors = ["#1d4ed8", "#b45309", "#0f766e", "#7c3aed", "#dc2626"]
        for group, color in zip(top_groups, colors):
            frame = subset.loc[subset["group_display"] == group].sort_values("Date")
            ax.plot(frame["Date"], _smooth(frame["group_r2_contribution"], smooth_weeks), color=color, linewidth=2.0, label=group)
        ax.set_title(title, color=TEXT_COLOR, fontsize=13, pad=10, fontweight="bold")
        ax.set_xlabel("Date", color=TEXT_COLOR)
    axes[0].set_ylabel("Group Contribution to Incremental R-squared", color=TEXT_COLOR)
    axes[0].legend(frameon=False, loc="upper left")
    fig.suptitle("MD2: Group-Level Contribution to the Ownership Factor", color=TEXT_COLOR, fontsize=16, fontweight="bold")
    plt.tight_layout()
    fig.savefig(output_path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def write_md1_report(output_path: Path, rolling_summary: pd.DataFrame, cohesion: pd.DataFrame) -> None:
    coarse_all = rolling_summary.loc[rolling_summary["spec"] == "coarse_all"].iloc[0]
    coarse_ex = rolling_summary.loc[rolling_summary["spec"] == "coarse_ex_psu"].iloc[0]
    fine_all = rolling_summary.loc[rolling_summary["spec"] == "fine_all"].iloc[0]
    fine_ex = rolling_summary.loc[rolling_summary["spec"] == "fine_ex_psu"].iloc[0]
    cohesion_summary = (
        cohesion.loc[cohesion["spec"] == "fine_all"]
        .groupby(["group_display", "group_type"], as_index=False)
        .agg(avg_cohesion_excess=("group_cohesion_excess", "mean"), avg_members=("n_members", "mean"))
        .sort_values("avg_cohesion_excess", ascending=False)
    )

    lines = []
    lines.append("# MD1 Report: Rolling Correlation Study")
    lines.append("")
    lines.append("This notebook section reproduces the original 52-week rolling-correlation study from the first project note, on the repaired historical panel.")
    lines.append("")
    lines.append("## Q1. Is same-group co-movement larger than same-sector co-movement?")
    lines.append("")
    lines.append(f"- Coarse sectors with PSU: same-group excess `{coarse_all['avg_same_group_excess']:.3f}` vs same-sector excess `{coarse_all['avg_same_sector_excess']:.3f}`.")
    lines.append(f"- Fine sectors with PSU: same-group excess `{fine_all['avg_same_group_excess']:.3f}` vs same-sector excess `{fine_all['avg_same_sector_excess']:.3f}`.")
    lines.append(f"- Same-group excess is above same-sector excess in `{coarse_all['share_weeks_group_gt_sector']:.1%}` of coarse-sector windows and `{fine_all['share_weeks_group_gt_sector']:.1%}` of fine-sector windows.")
    lines.append("")
    lines.append("Inference: ownership produces a persistent second layer of co-movement, but the strong claim that it cleanly dominates sector is not supported once sector controls become fine.")
    lines.append("")
    lines.append("## Q2. What changes when PSUs are excluded?")
    lines.append("")
    lines.append(f"- Coarse same-group excess falls from `{coarse_all['avg_same_group_excess']:.3f}` to `{coarse_ex['avg_same_group_excess']:.3f}`.")
    lines.append(f"- Fine same-group excess falls from `{fine_all['avg_same_group_excess']:.3f}` to `{fine_ex['avg_same_group_excess']:.3f}`.")
    lines.append("")
    lines.append("Inference: PSU co-movement is a real part of the ownership-style concentration story, but the private-group signal remains even after removing PSUs.")
    lines.append("")
    lines.append("## Q3. Which blocks are most cohesive?")
    lines.append("")
    for row in cohesion_summary.itertuples():
        lines.append(f"- `{row.group_display}` ({row.group_type}) average cohesion excess `{row.avg_cohesion_excess:.3f}` with average concurrent membership `{row.avg_members:.1f}`.")
    lines.append("")
    lines.append("## Q4. Effective number of bets")
    lines.append("")
    lines.append(f"- Fine-sector, with-PSU average effective entity bets: `{fine_all['avg_effective_entity_bets']:.1f}` out of `{fine_all['avg_active_entities']:.1f}` active entities.")
    lines.append("- This remains a heuristic because historical market-cap weights are not available in the local panel.")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_md2_report(output_path: Path, variance_summary: pd.DataFrame, group_summary: pd.DataFrame) -> None:
    coarse_all = variance_summary.loc[variance_summary["spec"] == "coarse_all"].iloc[0]
    coarse_ex = variance_summary.loc[variance_summary["spec"] == "coarse_ex_psu"].iloc[0]
    fine_all = variance_summary.loc[variance_summary["spec"] == "fine_all"].iloc[0]
    fine_ex = variance_summary.loc[variance_summary["spec"] == "fine_ex_psu"].iloc[0]
    top_groups = group_summary.loc[group_summary["spec"] == "fine_all"].head(6)

    lines = []
    lines.append("# MD2 Report: Weekly Variance Decomposition")
    lines.append("")
    lines.append("This notebook section reproduces the original weekly cross-sectional variance-decomposition study from the second project note, on the repaired historical panel.")
    lines.append("")
    lines.append("## Q1. How much weekly cross-sectional variance does sector explain?")
    lines.append("")
    lines.append(f"- Coarse sectors average `R²`: `{coarse_all['avg_sector_r2']:.3f}`.")
    lines.append(f"- Fine sectors average `R²`: `{fine_all['avg_sector_r2']:.3f}`.")
    lines.append("")
    lines.append("## Q2. How much incremental variance does promoter-group identity explain after sector?")
    lines.append("")
    lines.append(f"- Coarse sectors with PSU: group `R²` `{coarse_all['avg_group_r2']:.3f}`.")
    lines.append(f"- Coarse sectors ex PSU: group `R²` `{coarse_ex['avg_group_r2']:.3f}`.")
    lines.append(f"- Fine sectors with PSU: group `R²` `{fine_all['avg_group_r2']:.3f}`.")
    lines.append(f"- Fine sectors ex PSU: group `R²` `{fine_ex['avg_group_r2']:.3f}`.")
    lines.append("")
    lines.append("Inference: the group factor is real but smaller than sector. It should be interpreted as an incremental structural layer, not the main market partition.")
    lines.append("")
    lines.append("## Q3. Is the group factor growing over time?")
    lines.append("")
    lines.append(f"- Coarse with PSU: `2015-2019` mean `{coarse_all['mean_2015_2019']:.3f}` vs `2020-2025` mean `{coarse_all['mean_2020_2025']:.3f}`; change `{coarse_all['diff_2020_2025_minus_2015_2019']:.3f}`.")
    lines.append(f"- Fine with PSU: `2015-2019` mean `{fine_all['mean_2015_2019']:.3f}` vs `2020-2025` mean `{fine_all['mean_2020_2025']:.3f}`; change `{fine_all['diff_2020_2025_minus_2015_2019']:.3f}`.")
    lines.append(f"- Fine ex PSU trend slope per year `{fine_ex['trend_slope_per_year']:.4f}` with p-value `{fine_ex['trend_pvalue']:.3f}`.")
    lines.append("")
    lines.append("Inference: the strong upward-growth story is not robust. It weakens and turns negative under the stricter fine-sector specification.")
    lines.append("")
    lines.append("## Q4. Which groups drive the factor?")
    lines.append("")
    for row in top_groups.itertuples():
        lines.append(f"- `{row.group_display}` average contribution `{row.avg_contribution:.3f}`, average share of factor `{row.avg_share_of_group_r2:.1%}`, average group size `{row.avg_group_size:.1f}`.")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_master_summary(output_path: Path, input_path: Path, output_dir: Path) -> None:
    lines = []
    lines.append("# Phase 4 Summary")
    lines.append("")
    lines.append(f"- Input panel: `{input_path}`")
    lines.append(f"- Notebook: `phase4/phase4_analysis_notebook.ipynb`")
    lines.append(f"- Output assets: `{output_dir}`")
    lines.append("")
    lines.append("This package contains only the two original Phase 4 studies:")
    lines.append("- MD1: the rolling correlation study")
    lines.append("- MD2: the weekly cross-sectional variance decomposition")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def run_phase4_package(spec: Phase4Spec | None = None) -> dict[str, pd.DataFrame]:
    spec = spec or Phase4Spec()
    panel = load_panel(spec.input_path)

    md1_dir = spec.output_dir / "md1_rolling_correlation"
    md2_dir = spec.output_dir / "md2_variance_decomposition"
    md1_dir.mkdir(parents=True, exist_ok=True)
    md2_dir.mkdir(parents=True, exist_ok=True)

    md1_metrics, md1_cohesion, md1_effective, md1_summary = compute_md1_rolling(
        panel=panel,
        specs=DEFAULT_SPECS,
        rolling_window=spec.rolling_window,
        min_obs=spec.rolling_min_obs,
    )
    md1_metrics.to_csv(md1_dir / "rolling_metrics.csv", index=False)
    md1_cohesion.to_csv(md1_dir / "group_cohesion.csv", index=False)
    md1_effective.to_csv(md1_dir / "effective_bets.csv", index=False)
    md1_summary.to_csv(md1_dir / "summary.csv", index=False)
    plot_md1_core(md1_metrics, md1_dir / "01_core_comparison.png", spec.smooth_weeks)
    plot_md1_psu(md1_metrics, md1_dir / "02_psu_sensitivity.png", spec.smooth_weeks)
    plot_md1_groups(md1_cohesion, md1_dir / "03_group_cohesion.png", spec.smooth_weeks)
    plot_md1_effective(md1_effective, md1_dir / "04_effective_bets.png", spec.smooth_weeks)
    write_md1_report(md1_dir / "REPORT.md", md1_summary, md1_cohesion)

    md2_weekly, md2_groups, md2_summary, md2_group_summary = compute_md2_variance(
        panel=panel,
        specs=DEFAULT_SPECS,
        min_stocks=spec.min_stocks,
        permutations=spec.permutations,
        seed=spec.seed,
        newey_west_lags=spec.newey_west_lags,
    )
    md2_weekly.to_csv(md2_dir / "weekly_decomposition.csv", index=False)
    md2_groups.to_csv(md2_dir / "group_contributions.csv", index=False)
    md2_summary.to_csv(md2_dir / "summary.csv", index=False)
    md2_group_summary.to_csv(md2_dir / "group_summary.csv", index=False)
    plot_md2_core(md2_weekly, md2_dir / "01_variance_decomposition.png", spec.smooth_weeks)
    plot_md2_groups(md2_groups, md2_dir / "02_group_contributions.png", spec.smooth_weeks)
    write_md2_report(md2_dir / "REPORT.md", md2_summary, md2_group_summary)

    write_master_summary(spec.output_dir / "PHASE4_SUMMARY.md", spec.input_path, spec.output_dir)

    return {
        "md1_metrics": md1_metrics,
        "md1_cohesion": md1_cohesion,
        "md1_effective": md1_effective,
        "md1_summary": md1_summary,
        "md2_weekly": md2_weekly,
        "md2_groups": md2_groups,
        "md2_summary": md2_summary,
        "md2_group_summary": md2_group_summary,
    }
