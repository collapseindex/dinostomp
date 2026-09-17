"""The second picture: four models, the same 1,000 items, with and without the page.

    python audits/jevlike/models_chart.py     # writes four_models.png next to this file

Numbers are typed here from the audit (FINDINGS.md, "Three hosted models on
the same items") rather than recomputed, so the picture cannot drift from the
text without somebody noticing. Accuracy is on checkable output; the bare
menu letters each model returned are excluded and counted in the text.
"""

from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# (label, informed %, blind %, note)   same 1,000 seeded items of the test split
ROWS = [
    ("Jev-like scorer, from scratch (one pass)", 29.8, 5.0, "4 s, $0.00"),
    ("Qwen3 30B-A3B instruct", 29.8, 6.4, "23 min, $0.04, 87 bare letters excluded"),
    ("GPT-5.6 Luna, reasoning off", 22.8, 1.4, "18 min, $0.08"),
    ("Llama 3.1 8B instruct", 17.4, 3.4, "12 min, $0.04, 79 bare letters excluded"),
]
FLOOR = 3.6
BLUE = "#2a78d6"
GREY = "#b9b7b2"
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e6e5e2"

fig, ax = plt.subplots(figsize=(16, 9), dpi=100)
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)
rows = ROWS[::-1]
ys = list(range(len(rows)))
h = 0.34
inf = ax.barh([y + h / 2 for y in ys], [r[1] for r in rows], color=BLUE, height=h, label="With the page")
bli = ax.barh([y - h / 2 for y in ys], [r[2] for r in rows], color=GREY, height=h, label="Menu only (page withheld)")
for y, r in zip(ys, rows):
    ax.text(r[1] + 0.5, y + h / 2, f"{r[1]:.1f}%", va="center", ha="left", fontsize=19, color=INK, fontweight="bold")
    ax.text(r[2] + 0.5, y - h / 2, f"{r[2]:.1f}%", va="center", ha="left", fontsize=14, color=INK2)
    # the note sits on the grey row, whose value label never reaches x=12
    ax.text(43.5, y - h / 2, r[3], va="center", ha="right", fontsize=13, color=INK2)
ax.axvline(FLOOR, color=INK2, linewidth=1, linestyle=(0, (3, 3)))
ax.text(FLOOR + 0.3, len(rows) - 0.45, f"uniform guess {FLOOR}%", fontsize=11.5, color=INK2, ha="left", va="top")
ax.set_yticks(ys)
ax.set_yticklabels([r[0] for r in rows], fontsize=16, color=INK)
ax.set_xlim(0, 44)
ax.set_xticks([0, 10, 20, 30, 40])
ax.set_xticklabels([f"{t}%" for t in [0, 10, 20, 30, 40]], fontsize=13, color=INK2)
ax.tick_params(axis="y", length=0)
ax.tick_params(axis="x", colors=INK2, length=0)
ax.grid(axis="x", color=GRID, linewidth=1)
ax.set_axisbelow(True)
for side in ("top", "right", "left", "bottom"):
    ax.spines[side].set_visible(False)
fig.text(0.04, 0.95, "Faster, sure. But is it reading?",
         fontsize=24, color=INK, fontweight="bold", ha="left")
fig.text(0.04, 0.905, "Which link did the human click next? One from-scratch one-pass scorer against three hosted LLMs, the same 1,000 Wikispeedia items.",
         fontsize=14.5, color=INK2, ha="left")
fig.text(0.04, 0.872, "Blue: with the page. Grey: the same model with the page withheld, so how much of the score is the menu. Every arm clears its own blind run.",
         fontsize=14.5, color=INK2, ha="left")
fig.text(0.04, 0.055, "dinostomp run, 2026-09-17; exact match on the option text; temperature 0; prices per OpenRouter's listing that day. Accuracy on checkable output.",
         fontsize=11.5, color=INK2, ha="left")
fig.text(0.04, 0.025, "Records, checkpoint and scripts: github.com/collapseindex/dinostomp/tree/main/audits/jevlike",
         fontsize=11.5, color=INK2, ha="left")
plt.subplots_adjust(left=0.30, right=0.97, top=0.82, bottom=0.14)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "four_models.png")
fig.savefig(out, facecolor=SURFACE)
print("wrote", out)
