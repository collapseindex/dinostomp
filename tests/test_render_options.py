"""The rendered option block must label every option with printable letters.

D-097: `chr(65 + i)` ran past Z into `[`, `\\`, `]` at option 27 and into
control characters at option 59. Wikispeedia menus run to 64 options, so
most of the block's tail had no readable label at all.
"""

from dinostomp.runner import render_options, shuffled_input
from dinostomp.workbook import col_letter


def _item(n):
    return {"id": "x", "input": "Q?", "choices": [f"opt{i}" for i in range(n)],
            "target": "opt0"}


def test_labels_follow_spreadsheet_columns_past_z():
    lines = render_options(_item(64), _item(64)["choices"]).split("\n")
    block = lines[2:2 + 64]
    labels = [ln.split(". ", 1)[0] for ln in block]
    assert labels[:3] == ["A", "B", "C"]
    assert labels[25:28] == ["Z", "AA", "AB"]
    assert labels[51:53] == ["AZ", "BA"]
    assert labels[63] == "BL"
    assert labels == [col_letter(i + 1) for i in range(64)]


def test_every_label_is_printable_and_unique():
    block = render_options(_item(80), _item(80)["choices"]).split("\n")[2:82]
    labels = [ln.split(". ", 1)[0] for ln in block]
    assert len(set(labels)) == 80
    assert all(lb.isalpha() and lb.isupper() for lb in labels)
    assert all(ln.endswith(f"opt{i}") for i, ln in enumerate(block))


def test_shuffle_keeps_labels_and_moves_texts():
    item = _item(40)
    base = render_options(item, item["choices"]).split("\n")[2:42]
    shuf = shuffled_input(item, 7).split("\n")[2:42]
    assert [ln.split(". ", 1)[0] for ln in base] == [ln.split(". ", 1)[0] for ln in shuf]
    assert sorted(ln.split(". ", 1)[1] for ln in base) == sorted(ln.split(". ", 1)[1] for ln in shuf)
    assert base != shuf
