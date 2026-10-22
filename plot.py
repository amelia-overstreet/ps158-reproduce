"""Plot mean net worth of families headed by a college graduate vs. families headed
by someone with a high-school education or less, 1989-2025 (SCF, 2025 dollars).

Black-and-white journal style: groups are told apart by line style and marker,
and the numbered caption, notes and source sit below the panels.

Reads data/net_worth_by_education.csv (run get_data.py first).
Writes figures/net_worth_by_education.png
"""

import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

DATA = Path("data/net_worth_by_education.csv")
OUT = Path("figures/net_worth_by_education.png")

COLLEGE, HS = "Bachelor's degree or more", "High school or less"
SERIES = {
    COLLEGE: dict(linestyle="-", marker="o", markerfacecolor="black"),
    HS: dict(linestyle="--", marker="s", markerfacecolor="white"),
}
RATIO = dict(linestyle="-", marker="^", markerfacecolor="black")

CAPTION = [
    ("Figure 1.",
     "Mean net worth of U.S. families by education of the reference person, 1989–2025. "
     "Panel (a) shows mean net worth for families whose reference person has a "
     "bachelor's degree or more and for families whose reference person has a "
     "high-school education or less. Panel (b) shows the ratio of the first group's "
     "mean to the second's."),
    ("Notes:",
     "All families. The reference person is the single adult, the man in a mixed-sex "
     "couple, or the older partner in a same-sex couple. \"High school or less\" combines "
     "no high-school diploma and a diploma or GED; families with some college are "
     "omitted. Dollar values are in 2025 dollars, adjusted by the Federal Reserve with "
     "the CPI-U-RS. Estimates use survey weights and pool the five implicates."),
    ("Source:",
     "Board of Governors of the Federal Reserve System, Survey of Consumer Finances, "
     "summary extract public data, 1989–2025."),
]

WIDTH_IN = 7.0          # full text width of a journal page
PLOT_HEIGHT_IN = 2.9
CAPTION_PT = 8.5
WRAP_CHARS = 132        # characters per caption line at CAPTION_PT on WIDTH_IN

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
    "font.size": 9,
    "axes.edgecolor": "black",
    "axes.linewidth": 0.6,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "lines.color": "black",
    "lines.linewidth": 1.0,
    "lines.markersize": 4,
    "lines.markeredgewidth": 0.8,
})


def style(ax, letter):
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)
    ax.set_xticks([1989, 1995, 2001, 2007, 2013, 2019, 2025])
    ax.set_xlim(1987, 2027)
    ax.set_ylim(0, None)
    ax.text(0.02, 0.98, f"({letter})", transform=ax.transAxes, va="top", fontsize=10)


def caption_lines():
    """Wrap each caption paragraph; return (lead-in or None, text) per line."""
    lines = []
    for lead, body in CAPTION:
        wrapped = textwrap.wrap(f"{lead} {body}", WRAP_CHARS)
        lines.append((lead, wrapped[0][len(lead):]))
        lines += [(None, line) for line in wrapped[1:]]
    return lines


def main():
    df = pd.read_csv(DATA)
    df = df[df["group"].isin([COLLEGE, HS])]
    wide = df.pivot(index="year", columns="group")

    lines = caption_lines()
    line_in = CAPTION_PT * 1.45 / 72
    caption_in = len(lines) * line_in + 0.25
    total_in = PLOT_HEIGHT_IN + caption_in
    fig = plt.figure(figsize=(WIDTH_IN, total_in))
    levels, ratio_ax = fig.subplots(1, 2, gridspec_kw=dict(
        left=0.1, right=0.98, top=1 - 0.1 / total_in, bottom=(caption_in + 0.5) / total_in,
        wspace=0.32))

    values = wide["mean_net_worth"] / 1000
    for group in [COLLEGE, HS]:
        levels.plot(values.index, values[group], color="black", label=group,
                    **SERIES[group])
    levels.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    levels.set_ylabel("Mean net worth\n(thousands of 2025 dollars)")
    levels.set_xlabel("Survey year")
    style(levels, "a")
    # The band between the two series is empty in every year.
    levels.legend(loc="center", bbox_to_anchor=(0.55, 0.27), frameon=False,
                  handlelength=3)

    r = values[COLLEGE] / values[HS]
    ratio_ax.plot(r.index, r.values, color="black", **RATIO)
    ratio_ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}"))
    ratio_ax.set_ylabel("Ratio of means\n(bachelor's+ / HS or less)")
    ratio_ax.set_xlabel("Survey year")
    style(ratio_ax, "b")
    ratio_ax.set_ylim(0, r.max() * 1.1)

    renderer = fig.canvas.get_renderer()
    for i, (lead, text) in enumerate(lines):
        y = (caption_in - 0.1 - (i + 0.8) * line_in) / total_in
        x = 0.02
        if lead:
            bold = fig.text(x, y, lead, fontsize=CAPTION_PT, fontweight="bold")
            x += bold.get_window_extent(renderer).width / fig.bbox.width
        fig.text(x, y, text, fontsize=CAPTION_PT)

    OUT.parent.mkdir(exist_ok=True)
    fig.savefig(OUT, dpi=300, facecolor="white")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
