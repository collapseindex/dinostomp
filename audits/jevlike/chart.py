"""The one picture: four accuracies on the same 1,000 Wikispeedia test items.

    python audits/jevlike/chart.py            # writes control_leak.png next to this file

Numbers are typed here from the audit (FINDINGS.md) rather than recomputed,
so the picture cannot drift from the text without somebody noticing.
"""

from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# same 1,000 seeded items of the test split, one from-scratch checkpoint
ROWS = [
    ("Informed: page + menu", 29.8, "dinostomp run"),
    ("Jevlike's shuffled-context control", 11.7, "wrong page, 18% of them naming the right target"),
    ("No page at all (dinostomp --probe blind)", 5.0, "menu only"),
    ("Uniform guess (median 46 options)", 3.6, "floor"),
]
BLUE = "#2a78d6"          # palette slot 1, light surface
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e6e5e2"

fig, ax = plt.subplots(figsize=(16, 9), dpi=100)
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)
labels = [r[0] for r in ROWS][::-1]
values = [r[1] for r in ROWS][::-1]
notes = [r[2] for r in ROWS][::-1]
bars = ax.barh(labels, values, color=BLUE, height=0.52)
for bar, v, note in zip(bars, values, notes):
    ax.text(v + 0.6, bar.get_y() + bar.get_height() / 2, f"{v:.1f}%",
            va="center", ha="left", fontsize=20, color=INK, fontweight="bold")
    ax.text(v + 5.2, bar.get_y() + bar.get_height() / 2, note,
            va="center", ha="left", fontsize=14, color=INK2)
ax.set_xlim(0, 44)
ax.set_xticks([0, 10, 20, 30, 40])
ax.set_xticklabels([f"{t}%" for t in [0, 10, 20, 30, 40]], fontsize=13, color=INK2)
ax.tick_params(axis="y", labelsize=16, colors=INK, length=0)
ax.tick_params(axis="x", colors=INK2, length=0)
ax.grid(axis="x", color=GRID, linewidth=1)
ax.set_axisbelow(True)
for side in ("top", "right", "left", "bottom"):
    ax.spines[side].set_visible(False)
fig.text(0.04, 0.95, "A control that reads 11.7% is not a control for a model that reads 29.8%",
         fontsize=24, color=INK, fontweight="bold", ha="left")
fig.text(0.04, 0.905, "One-pass Jev-like scorer on Wikispeedia next-click, one checkpoint, the same 1,000 items for every bar.",
         fontsize=14.5, color=INK2, ha="left")
fig.text(0.04, 0.872, "The control shuffles pages within a batch; on the full split that hands two menus in five a page naming the right target.",
         fontsize=14.5, color=INK2, ha="left")
fig.text(0.04, 0.055, "dinostomp audit of vinnylarouge/jevlike @ 94f5fd1; checkpoint trained from scratch, 3 epochs, seed 42.",
         fontsize=11.5, color=INK2, ha="left")
fig.text(0.04, 0.025, "Records, checkpoint and scripts: github.com/collapseindex/dinostomp/tree/main/audits/jevlike",
         fontsize=11.5, color=INK2, ha="left")
plt.subplots_adjust(left=0.30, right=0.97, top=0.82, bottom=0.14)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "control_leak.png")
fig.savefig(out, facecolor=SURFACE)
print("wrote", out)
