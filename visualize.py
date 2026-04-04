"""
visualize.py — Visualization of rolling correlation results + stock listing.

Generates:
    1. Time-series plot of baseline, sector excess, and group excess
    2. CSV/printed listing of all stocks with their promoter groups
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path

from config import ROLLING_CORR_PATH, DATA_DIR, ALIGNED_PANEL_PATH


def plot_rolling_correlations(result_df: pd.DataFrame, save_path: Path):
    """
    Plot the three key time series: baseline, sector excess, group excess.
    """
    fig, axes = plt.subplots(2, 1, figsize=(16, 10), gridspec_kw={"height_ratios": [1.2, 1]})
    fig.patch.set_facecolor("#0d1117")

    colors = {
        "baseline": "#8b949e",
        "sector": "#58a6ff",
        "group": "#f78166",
    }

    # ── Top panel: Baseline correlation ──
    ax1 = axes[0]
    ax1.set_facecolor("#0d1117")
    ax1.fill_between(result_df.index, result_df["baseline"], alpha=0.15, color=colors["baseline"])
    ax1.plot(result_df.index, result_df["baseline"], color=colors["baseline"],
             linewidth=1.8, label="Baseline (all-pair mean)")
    ax1.set_ylabel("Pearson Correlation", fontsize=12, color="white")
    ax1.set_title("Market-Wide Baseline Correlation (52-Week Rolling)",
                  fontsize=14, fontweight="bold", color="white", pad=12)
    ax1.legend(loc="upper right", fontsize=10, facecolor="#161b22", edgecolor="#30363d",
               labelcolor="white")
    ax1.tick_params(colors="white")
    ax1.spines["bottom"].set_color("#30363d")
    ax1.spines["left"].set_color("#30363d")
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.grid(axis="y", color="#21262d", linewidth=0.5)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=4))

    # ── Bottom panel: Excess correlations ──
    ax2 = axes[1]
    ax2.set_facecolor("#0d1117")
    ax2.axhline(y=0, color="#30363d", linewidth=0.8, linestyle="--")

    ax2.fill_between(result_df.index, result_df["sector_excess"], alpha=0.12, color=colors["sector"])
    ax2.plot(result_df.index, result_df["sector_excess"], color=colors["sector"],
             linewidth=1.8, label="Same-Sector Excess")

    ax2.fill_between(result_df.index, result_df["group_excess"], alpha=0.12, color=colors["group"])
    ax2.plot(result_df.index, result_df["group_excess"], color=colors["group"],
             linewidth=1.8, label="Same-Group Excess")

    ax2.set_ylabel("Excess Correlation\n(vs. Baseline)", fontsize=12, color="white")
    ax2.set_xlabel("Date", fontsize=12, color="white")
    ax2.set_title("Excess Correlation: Promoter Group vs. Industry Sector (52-Week Rolling)",
                  fontsize=14, fontweight="bold", color="white", pad=12)
    ax2.legend(loc="upper right", fontsize=10, facecolor="#161b22", edgecolor="#30363d",
               labelcolor="white")
    ax2.tick_params(colors="white")
    ax2.spines["bottom"].set_color("#30363d")
    ax2.spines["left"].set_color("#30363d")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.grid(axis="y", color="#21262d", linewidth=0.5)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=4))

    plt.tight_layout(pad=2.0)
    fig.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(f"Saved plot to {save_path}")
    plt.close()


def plot_excess_comparison_bar(result_df: pd.DataFrame, save_path: Path):
    """
    Bar chart comparing average sector vs group excess correlations.
    """
    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")

    means = [result_df["sector_excess"].mean(), result_df["group_excess"].mean()]
    stds = [result_df["sector_excess"].std(), result_df["group_excess"].std()]
    labels = ["Same-Sector\n(Diff. Promoter)", "Same-Group\n(Diff. Sector)"]
    colors = ["#58a6ff", "#f78166"]

    bars = ax.bar(labels, means, yerr=stds, capsize=8, color=colors, alpha=0.85,
                  edgecolor="white", linewidth=0.5, width=0.5,
                  error_kw={"ecolor": "white", "linewidth": 1.5})

    # Add value labels on bars
    for bar, mean, std in zip(bars, means, stds):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + std + 0.003,
                f"{mean:.4f}\n(±{std:.4f})",
                ha="center", va="bottom", fontsize=11, color="white", fontweight="bold")

    ax.set_ylabel("Mean Excess Correlation", fontsize=12, color="white")
    ax.set_title("Promoter Group Effect vs. Industry Sector Effect\n(2021–2025 Average)",
                 fontsize=14, fontweight="bold", color="white", pad=12)
    ax.tick_params(colors="white", labelsize=11)
    ax.spines["bottom"].set_color("#30363d")
    ax.spines["left"].set_color("#30363d")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color="#21262d", linewidth=0.5)

    plt.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(f"Saved bar chart to {save_path}")
    plt.close()


def generate_stock_listing(aligned_df: pd.DataFrame, save_path: Path):
    """
    Generate a clean CSV of all stocks with their promoter groups and sectors.
    """
    listing = (
        aligned_df
        .drop_duplicates(subset=["ticker"])
        [["ticker", "promoter_group", "nse_sector", "gics_sub_industry"]]
        .sort_values(["promoter_group", "nse_sector", "ticker"])
        .reset_index(drop=True)
    )

    listing.to_csv(save_path, index=False)
    print(f"Saved stock listing to {save_path} ({len(listing)} stocks)")

    # Print grouped summary
    for group in sorted(listing["promoter_group"].unique()):
        subset = listing[listing["promoter_group"] == group]
        tickers = ", ".join(subset["ticker"].tolist())
        print(f"\n{'─' * 60}")
        print(f"  {group} ({len(subset)} stocks)")
        print(f"{'─' * 60}")
        print(f"  {tickers}")

    return listing


def main():
    # Load results
    if not ROLLING_CORR_PATH.exists():
        print("ERROR: No rolling correlation data found. Run main.py first.")
        return

    result_df = pd.read_parquet(ROLLING_CORR_PATH)
    aligned_df = pd.read_parquet(ALIGNED_PANEL_PATH)

    output_dir = DATA_DIR / "plots"
    output_dir.mkdir(exist_ok=True)

    # 1. Time-series plot
    print("\n[1/3] Generating time-series plot...")
    plot_rolling_correlations(result_df, output_dir / "rolling_correlations.png")

    # 2. Bar chart comparison
    print("\n[2/3] Generating bar chart...")
    plot_excess_comparison_bar(result_df, output_dir / "excess_comparison.png")

    # 3. Stock listing
    print("\n[3/3] Generating stock listing...")
    listing = generate_stock_listing(aligned_df, DATA_DIR / "stock_listing.csv")


if __name__ == "__main__":
    main()
