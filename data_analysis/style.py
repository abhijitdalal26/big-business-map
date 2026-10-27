"""Matplotlib house style.

Reuses the visual language already established in ``scripts/make_charts.py``:
left-aligned bold titles, a subtitle line, a source footnote, muted axes and
no top/right spines.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter

from config import ACCENT, BAR, BG, DPI, FONT, GRID, INK, MUTED, PALETTE

plt.rcParams.update({
    "font.family": FONT,
    "font.size": 10,
    "axes.facecolor": BG,
    "figure.facecolor": BG,
    "savefig.facecolor": BG,
    "axes.edgecolor": "#C9D2DD",
    "axes.labelcolor": INK,
    "axes.titlecolor": INK,
    "text.color": INK,
    "xtick.color": "#4A5563",
    "ytick.color": "#4A5563",
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "legend.frameon": False,
    "figure.dpi": DPI,
    "savefig.dpi": DPI,
    "savefig.bbox": "tight",
})


def money_b(x: float, _pos: int | None = None) -> str:
    """Format a number in USD billions as a compact label."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return ""
    a = abs(x)
    if a >= 1000:
        return f"${x / 1000:,.1f}T"
    if a >= 1:
        return f"${x:,.0f}B"
    if a == 0:
        return "$0"
    return f"${x * 1000:,.0f}M"


def money_m(x: float, _pos: int | None = None) -> str:
    """Format a number in USD millions as a compact label."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return ""
    a = abs(x)
    if a >= 1000:
        return f"${x / 1000:,.1f}B"
    return f"${x:,.0f}M"


def count_fmt(x: float, _pos: int | None = None) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return ""
    if abs(x) >= 1_000_000:
        return f"{x / 1_000_000:,.1f}M"
    if abs(x) >= 1_000:
        return f"{x / 1_000:,.0f}K"
    return f"{x:,.0f}"


def pct_fmt(x: float, _pos: int | None = None) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return ""
    return f"{x:,.0f}%"


#: Where the source footnote sits, in figure coordinates.  Negative means
#: "just below the figure", which keeps it clear of the x tick labels.
_SOURCE_Y = -0.015


def _source_note(fig, source: str) -> None:
    """Draw the source footnote once, below the figure.

    It used to be drawn in *axis* coordinates, which put it straight on top
    of the x tick labels, and it was drawn twice (here and in ``save``).
    """
    if not source:
        return
    if getattr(fig, "_source_drawn", False):
        return
    fig.text(0.0, _SOURCE_Y, source, fontsize=7.8, color=MUTED,
             va="top", ha="left")
    fig._source_drawn = True


def style(ax, title: str, subtitle: str = "", source: str = "",
          title_size: float = 13, sub_size: float = 9.5) -> None:
    """Apply the house chart furniture to a single axis."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color("#C9D2DD")
    ax.spines["bottom"].set_color("#C9D2DD")
    ax.set_axisbelow(True)

    ax.set_title("")
    pad = 22 if subtitle else 12
    ax.text(0, 1.0 + (0.035 if subtitle else 0.0), title, transform=ax.transAxes,
            fontsize=title_size, fontweight="bold", color=INK, va="bottom", ha="left")
    if subtitle:
        ax.text(0, 1.0 + 0.002, subtitle, transform=ax.transAxes,
                fontsize=sub_size, color="#5A6673", va="bottom", ha="left")
    if source:
        _source_note(ax.figure, source)


def _axis_fmt_for(value_fmt):
    """Return the axis formatter that matches a bar-label formatter.

    Bar labels are already formatted for the reader ("$45B", "12%"). The
    x-axis used to print the raw numbers behind them, which is unreadable
    once the values are in the hundreds of millions. This maps the four
    house formatters onto themselves so the axis reads the same way.
    """
    if value_fmt is money_b:
        return money_b
    if value_fmt is money_m:
        return money_m
    if value_fmt is pct_fmt:
        return pct_fmt
    if value_fmt is count_fmt:
        return count_fmt
    return None


def hbar(ax, labels, values, color=BAR, highlight: str | None = None,
         highlight_color=ACCENT, value_fmt=money_b, pad: float = 0.012):
    """Horizontal bar chart with optional highlight of one label.

    ``highlight`` is matched case-insensitively against ``labels``.
    """
    labels = list(labels)
    values = np.asarray(values, dtype=float)
    y = np.arange(len(labels))[::-1]
    colors = [highlight_color if (highlight and str(l).lower() == str(highlight).lower())
              else color for l in labels]
    ax.barh(y, values, color=colors, height=0.68, zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    span = max(values.max(), 1.0)
    for yi, v in zip(y, values):
        ax.text(v + span * pad, yi, value_fmt(v), va="center", ha="left",
                fontsize=8.6, color=INK, zorder=4)
    ax.set_xlim(0, span * 1.20)
    xf = _axis_fmt_for(value_fmt)
    if xf is not None:
        ax.xaxis.set_major_formatter(FuncFormatter(xf))
    return ax


def save(fig, path: Path, source: str = "") -> Path:
    """Save a figure with a consistent source footnote."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if source:
        _source_note(fig, source)
    fig.savefig(path, facecolor=BG)
    plt.close(fig)
    return path


def new_fig(width: float = 9.0, height: float = 5.2):
    fig, ax = plt.subplots(figsize=(width, height))
    return fig, ax


def figure_from_ax(ax, width: float = 9.0, height: float = 5.2):
    """Resize an existing axis to the house figure size."""
    fig = ax.figure
    fig.set_size_inches(width, height)
    return fig, ax


def color_for(i: int) -> str:
    return PALETTE[i % len(PALETTE)]


__all__ = [
    "plt", "np", "FuncFormatter", "INK", "BAR", "ACCENT", "MUTED", "BG", "GRID",
    "PALETTE", "money_b", "money_m", "count_fmt", "pct_fmt", "style", "hbar",
    "save", "new_fig", "figure_from_ax", "color_for",
]
