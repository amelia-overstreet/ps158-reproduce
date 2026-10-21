"""Plot net worth of families headed by a college graduate vs. families headed by
someone with a high-school education or less, 1989-2025 (SCF, 2025 dollars).

Reads data/net_worth_by_education.csv (run get_data.py first).
Writes figures/net_worth_by_education.png
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

DATA = Path("data/net_worth_by_education.csv")
OUT = Path("figures/net_worth_by_education.png")

COLLEGE, HS = "Bachelor's degree or more", "High school or less"
COLORS = {COLLEGE: "#2a78d6", HS: "#eb6834"}
INK, INK_2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def style(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(INK_2)
    ax.tick_params(colors=INK_2, length=0, labelsize=9)
    ax.set_xticks([1989, 1995, 2001, 2007, 2013, 2019, 2025])
    ax.set_xlim(1987, 2031)


def main():
    df = pd.read_csv(DATA)
    df = df[df["group"].isin([COLLEGE, HS])]
    wide = df.pivot(index="year", columns="group")

    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5), sharex=True,
                             gridspec_kw={"height_ratios": [3, 2]})
    fig.patch.set_facecolor(SURFACE)

    for col, stat in enumerate(["median", "mean"]):
        levels, ratio_ax = axes[0, col], axes[1, col]
        values = wide[f"{stat}_net_worth"] / 1000

        for group in [COLLEGE, HS]:
            s = values[group]
            levels.plot(s.index, s.values, color=COLORS[group], linewidth=2,
                        marker="o", markersize=4)
            label = "Bachelor's+" if group == COLLEGE else "HS or less"
            levels.annotate(f"{label}\n${s.iloc[-1]:,.0f}k", (s.index[-1], s.iloc[-1]),
                            xytext=(6, 0), textcoords="offset points",
                            va="center", fontsize=9, color=INK)
        levels.set_ylim(0, None)
        levels.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}k"))
        levels.set_title(f"{stat.capitalize()} net worth (thousands of 2025 $)",
                         loc="left", fontsize=11, color=INK)

        r = values[COLLEGE] / values[HS]
        ratio_ax.plot(r.index, r.values, color=INK_2, linewidth=2, marker="o", markersize=4)
        for year in [r.index[0], r.index[-1]]:
            ratio_ax.annotate(f"{r[year]:.1f}×", (year, r[year]), xytext=(0, 8),
                              textcoords="offset points", ha="center",
                              fontsize=9, color=INK)
        ratio_ax.set_ylim(0, None)
        ratio_ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}×"))
        ratio_ax.set_title(f"Ratio: {stat} of Bachelor's+ ÷ HS or less",
                           loc="left", fontsize=11, color=INK)

    for ax in axes.flat:
        style(ax)
    # Same scale on both ratio panels so median and mean gaps compare directly.
    top = max(ax.get_ylim()[1] for ax in axes[1]) * 1.1
    for ax in axes[1]:
        ax.set_ylim(0, top)

    fig.suptitle("Net worth gap by education of the family's reference person, 1989–2025",
                 x=0.01, ha="left", fontsize=13, color=INK, fontweight="bold")
    fig.text(0.01, 0.005,
             "Source: Federal Reserve Survey of Consumer Finances, summary extract public data. "
             "2025 dollars (CPI-U-RS). Five implicates pooled.\n"
             "All families. Education is that of the reference person: the single adult, the man "
             "in a mixed-sex couple, or the older partner in a same-sex couple.\n"
             "HS or less = no high-school diploma + diploma/GED.",
             fontsize=7.5, color=INK_2, va="bottom")
    fig.tight_layout(rect=(0, 0.06, 1, 0.97))
    OUT.parent.mkdir(exist_ok=True)
    fig.savefig(OUT, dpi=200, facecolor=SURFACE)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
