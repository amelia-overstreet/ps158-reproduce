"""Plot net worth of families headed by a college graduate vs. families headed by
someone with a high-school education or less, 1989-2025 (SCF, 2025 dollars).
Figure 1 shows medians with 95% confidence intervals as error bars. Figure 2
shows means, with a second panel for the ratio between the two groups.

Black-and-white journal style: groups are told apart by line style and marker,
and the numbered caption, notes and source sit below the panels.

Reads data/net_worth_by_education.csv and data/net_worth_ratio.csv
(run get_data.py first).
Writes figures/net_worth_by_education_median.png (medians, Figure 1) and
figures/net_worth_by_education_mean.png (means, Figure 2).
"""

import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

DATA = Path("data/net_worth_by_education.csv")
RATIO_DATA = Path("data/net_worth_ratio.csv")
# (statistic, figure number, output file, draw 95% error bars, add ratio panel)
FIGURES = [
    ("median", 1, Path("figures/net_worth_by_education_median.png"), True, False),
    ("mean", 2, Path("figures/net_worth_by_education_mean.png"), False, True),
]
ERRORBAR = dict(fmt="none", ecolor="black", elinewidth=0.6, capsize=1.5, capthick=0.6)

COLLEGE, HS = "Bachelor's degree or more", "High school or less"
SERIES = {
    COLLEGE: dict(linestyle="-", marker="o", markerfacecolor="black"),
    HS: dict(linestyle="--", marker="s", markerfacecolor="white"),
}
RATIO = dict(linestyle="-", marker="^", markerfacecolor="black")

NOTES = (
    "All families. The reference person is the single adult, the man in a mixed-sex "
    "couple, or the older partner in a same-sex couple. \"High school or less\" combines "
    "no high-school diploma and a diploma or GED; families with some college are "
    "omitted. Dollar values are in 2025 dollars, adjusted by the Federal Reserve with "
    "the CPI-U-RS. Estimates use survey weights and pool the five implicates."
)
SOURCE = (
    "Board of Governors of the Federal Reserve System, Survey of Consumer Finances, "
    "summary extract public data, 1989–2025."
)


def caption(stat, number, error_bars, ratio_panel):
    groups = (f"{stat} net worth for families whose reference person has a bachelor's "
              "degree or more and for families whose reference person has a high-school "
              "education or less.")
    if ratio_panel:
        body = (f"Panel (a) shows {groups} Panel (b) shows the ratio of the first "
                f"group's {stat} to the second's.")
    else:
        body = f"Lines show {groups}"
    if error_bars:
        body += (" Vertical bars show 95% confidence intervals, which account for sampling "
                 "error (from the Federal Reserve's 999 replicate weights) and imputation "
                 "error.")
    return [
        (f"Figure {number}.",
         f"{stat.capitalize()} net worth of U.S. families by education of the reference "
         f"person, 1989–2025. {body}"),
        ("Notes:", NOTES),
        ("Source:", SOURCE),
    ]


WIDTH_IN = 7.0          # full text width of a journal page
PLOT_HEIGHT_IN = 2.9    # two panels side by side
SINGLE_PLOT_HEIGHT_IN = 3.4
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


def style(ax, letter=None):
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)
    ax.set_xticks([1989, 1995, 2001, 2007, 2013, 2019, 2025])
    ax.set_xlim(1987, 2027)
    ax.set_ylim(0, None)
    if letter:
        ax.text(0.02, 0.98, f"({letter})", transform=ax.transAxes, va="top", fontsize=10)


def caption_lines(paragraphs):
    """Wrap each caption paragraph; return (lead-in or None, text) per line."""
    lines = []
    for lead, body in paragraphs:
        wrapped = textwrap.wrap(f"{lead} {body}", WRAP_CHARS)
        lines.append((lead, wrapped[0][len(lead):]))
        lines += [(None, line) for line in wrapped[1:]]
    return lines


def draw(wide, ratios, stat, number, out, error_bars, ratio_panel):
    lines = caption_lines(caption(stat, number, error_bars, ratio_panel))
    line_in = CAPTION_PT * 1.45 / 72
    caption_in = len(lines) * line_in + 0.25
    total_in = (PLOT_HEIGHT_IN if ratio_panel else SINGLE_PLOT_HEIGHT_IN) + caption_in
    fig = plt.figure(figsize=(WIDTH_IN, total_in))
    axes = fig.subplots(1, 2 if ratio_panel else 1, squeeze=False, gridspec_kw=dict(
        left=0.16 if ratio_panel else 0.15, right=0.98, top=1 - 0.1 / total_in,
        bottom=(caption_in + 0.5) / total_in, wspace=0.32))[0]
    levels = axes[0]

    values = wide[f"{stat}_net_worth"]
    for group in [COLLEGE, HS]:
        if error_bars:
            levels.errorbar(values.index, values[group],
                            yerr=wide[f"{stat}_moe95"][group], **ERRORBAR)
        levels.plot(values.index, values[group], color="black", label=group,
                    **SERIES[group])
    levels.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}"))
    levels.set_ylabel(f"{stat.capitalize()} net worth\n(2025 dollars)")
    levels.set_xlabel("Survey year")
    style(levels, "a" if ratio_panel else None)
    # The band between the two series is empty in every year.
    levels.legend(loc="center", bbox_to_anchor=(0.55, 0.27), frameon=False,
                  handlelength=3)

    if ratio_panel:
        draw_ratio(axes[1], ratios[ratios["stat"] == stat].set_index("year"), stat,
                   error_bars)

    renderer = fig.canvas.get_renderer()
    for i, (lead, text) in enumerate(lines):
        y = (caption_in - 0.1 - (i + 0.8) * line_in) / total_in
        x = 0.02
        if lead:
            bold = fig.text(x, y, lead, fontsize=CAPTION_PT, fontweight="bold")
            x += bold.get_window_extent(renderer).width / fig.bbox.width
        fig.text(x, y, text, fontsize=CAPTION_PT)

    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=300, facecolor="white")
    plt.close(fig)
    print(f"wrote {out}")


def draw_ratio(ax, r, stat, error_bars):
    top = r["ratio"].max()
    if error_bars:
        ax.errorbar(r.index, r["ratio"], yerr=r["ratio_moe95"], **ERRORBAR)
        top = (r["ratio"] + r["ratio_moe95"]).max()
    ax.plot(r.index, r["ratio"], color="black", **RATIO)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}"))
    ax.set_ylabel(f"Ratio of {stat}s\n(bachelor's+ / HS or less)")
    ax.set_xlabel("Survey year")
    style(ax, "b")
    ax.set_ylim(0, top * 1.1)


def main():
    df = pd.read_csv(DATA)
    df = df[df["group"].isin([COLLEGE, HS])]
    wide = df.pivot(index="year", columns="group")
    ratios = pd.read_csv(RATIO_DATA)
    for stat, number, out, error_bars, ratio_panel in FIGURES:
        draw(wide, ratios, stat, number, out, error_bars, ratio_panel)


if __name__ == "__main__":
    main()
