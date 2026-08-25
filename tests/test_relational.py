"""The JN series: two tables and the join between them.

Same house rule: a planted defect per check and a clean control the whole
series must stay silent on. The clean control is a line-item table joined to a
vendor lookup, which is the ordinary shape, and it must produce nothing.

The headline case is not invented. A public Animal Crossing dataset stores a
villager's favourite song as `To The Edge` and the song table stores it as
`To the Edge`; three villagers vanish from every per-song analysis and nothing
raises. `test_the_acnh_case` reproduces it at small scale.
"""

import csv

from dinostomp.lint import JOIN_CHECKS, lint_join

CHILD_HEADER = ["order_id", "vendor_code", "amount"]
CHILD_ROWS = [
    ["ORD-1001", "ACME", "120.00"],
    ["ORD-1002", "GLOBEX", "300.50"],
    ["ORD-1003", "INITECH", "88.25"],
    ["ORD-1004", "ACME", "640.00"],
    ["ORD-1005", "HOOLI", "980.10"],
    ["ORD-1006", "GLOBEX", "150.75"],
]
PARENT_HEADER = ["vendor_code", "vendor_name", "region"]
PARENT_ROWS = [
    ["ACME", "Acme Corp", "West"],
    ["GLOBEX", "Globex", "East"],
    ["INITECH", "Initech", "North"],
    ["HOOLI", "Hooli", "South"],
    ["SOYLENT", "Soylent", "West"],
]


def write(tmp_path, header, rows, name):
    path = tmp_path / name
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def audit(tmp_path, child_rows=None, parent_rows=None, **kw):
    left = write(tmp_path, CHILD_HEADER, child_rows or CHILD_ROWS, "orders.csv")
    right = write(tmp_path, PARENT_HEADER, parent_rows or PARENT_ROWS, "vendors.csv")
    report, issues, ctx = lint_join(left, right, **kw)
    assert report is not None, [i.message for i in issues]
    return {f["id"]: f["level"] for f in report["findings"]}, report, ctx


def detail_for(report, cid):
    return next(f["detail"] for f in report["findings"] if f["id"] == cid)


def examples_for(report, cid):
    return next(f.get("examples", []) for f in report["findings"] if f["id"] == cid)


def test_the_clean_join_produces_no_finding_at_all():
    """Specificity. Every claim below is worthless without this one."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        levels, report, _ = audit(Path(tmp))
    noisy = {cid: levels[cid] for cid in JOIN_CHECKS if levels.get(cid) in ("fail", "warn")}
    assert not noisy, (noisy, [detail_for(report, cid) for cid in noisy])


def test_the_key_is_inferred_and_stated(tmp_path):
    """A join performed on the wrong column does not error, it answers, so the
    choice has to be visible enough to disagree with."""
    _, _, ctx = audit(tmp_path)
    assert ctx["key"] == {"left": "vendor_code", "right": "vendor_code", "inferred": True}
    assert any("join key" in note for note in ctx["notes"])


def test_inference_prefers_the_column_that_identifies_a_row(tmp_path):
    """D-087, found the first time this was pointed at real tables.

    `region` overlaps a shared category column perfectly and is not a key.
    Coverage alone ranks it first; coverage times identification does not.
    """
    child = [row + [PARENT_ROWS[i % 4][2]] for i, row in enumerate(CHILD_ROWS)]
    left = write(tmp_path, CHILD_HEADER + ["region"], child, "orders.csv")
    right = write(tmp_path, PARENT_HEADER, PARENT_ROWS, "vendors.csv")
    report, issues, ctx = lint_join(left, right)
    assert report is not None, [i.message for i in issues]
    assert ctx["key"]["left"] == "vendor_code", ctx["notes"]


def test_jn1_gates_when_nothing_matches_at_all(tmp_path):
    """An inner join that returns the empty set is arithmetic, not a judgement."""
    parent = [["X-" + row[0], row[1], row[2]] for row in PARENT_ROWS]
    levels, report, _ = audit(tmp_path, parent_rows=parent,
                              left_key="vendor_code", right_key="vendor_code")
    assert levels["JN1"] == "fail"
    assert "NOT ONE" in detail_for(report, "JN1")


def test_jn2_counts_orphans_without_gating(tmp_path):
    """Some orphans are ordinary, so this warns and JN1 carries the gate."""
    child = CHILD_ROWS + [["ORD-1007", "UMBRELLA", "12.00"]]
    levels, report, _ = audit(tmp_path, child_rows=child)
    assert levels["JN2"] == "warn"
    assert levels["JN1"] == "pass"
    assert "UMBRELLA" in str(examples_for(report, "JN2"))


def test_jn3_gates_on_a_key_that_only_needs_tidying(tmp_path):
    """The check the module exists for."""
    child = [row[:] for row in CHILD_ROWS]
    child[2][1] = "initech"          # right table says INITECH
    levels, report, _ = audit(tmp_path, child_rows=child)
    assert levels["JN3"] == "fail"
    assert any("'initech' would match 'INITECH'" in e for e in examples_for(report, "JN3"))


def test_the_acnh_case(tmp_path):
    """One capital letter, three rows, no error anywhere.

    The real defect from this repository's own case-study work, reproduced:
    the analysis that comes out is not imprecise, it is manufactured, because
    those villagers appear to favour nothing.
    """
    villagers = [["Bob", "To The Edge"], ["Rosie", "K.K. Rock"], ["Raymond", "To The Edge"],
                 ["Nan", "Go K.K. Rider"], ["Marshal", "To The Edge"],
                 ["Audie", "K.K. Rock"]]
    songs = [["To the Edge", "800"], ["K.K. Rock", "800"], ["Go K.K. Rider", "800"],
             ["Agent K.K.", "800"], ["Aloha K.K.", "800"]]
    left = write(tmp_path, ["Name", "Favorite Song"], villagers, "villagers.csv")
    right = write(tmp_path, ["Name", "Buy"], songs, "music.csv")
    report, issues, ctx = lint_join(left, right,
                                    left_key="Favorite Song", right_key="Name")
    assert report is not None, [i.message for i in issues]
    levels = {f["id"]: f["level"] for f in report["findings"]}
    assert levels["JN3"] == "fail"
    assert "3 row(s)" in detail_for(report, "JN3")
    assert any("'To The Edge' would match 'To the Edge'" in e
               for e in examples_for(report, "JN3"))
    assert report["summary"]["verdict"] == "broken"


def test_jn4_and_jn5_catch_a_join_that_multiplies_rows(tmp_path):
    """A lookup that is not one-to-one, and the row count that proves it."""
    parent = PARENT_ROWS + [["ACME", "Acme Corp (old)", "West"]]
    levels, report, _ = audit(tmp_path, parent_rows=parent)
    assert levels["JN4"] == "warn"
    assert levels["JN5"] == "warn"
    assert "6 left row(s) become 8" in detail_for(report, "JN5")


def test_jn6_catches_a_key_stored_two_ways(tmp_path):
    """`00123` against `123`: both correct in isolation, never equal."""
    child = [[f"ORD-{i}", f"0{i}0", "10.00"] for i in range(1, 7)]
    parent = [[str(int(f"0{i}0")), f"Vendor {i}", "West"] for i in range(1, 7)]
    left = write(tmp_path, CHILD_HEADER, child, "orders.csv")
    right = write(tmp_path, PARENT_HEADER, parent, "vendors.csv")
    report, issues, _ = lint_join(left, right, left_key="vendor_code",
                                  right_key="vendor_code")
    assert report is not None, [i.message for i in issues]
    levels = {f["id"]: f["level"] for f in report["findings"]}
    assert levels["JN6"] == "warn"
    assert "leading zeros" in detail_for(report, "JN6")


def test_jn7_gates_when_a_parent_total_disagrees_with_its_children(tmp_path):
    """Arithmetic, not judgement: both numbers are plausible and only their
    relationship is false."""
    parent = [["ACME", "Acme Corp", "760.00"], ["GLOBEX", "Globex", "451.25"],
              ["INITECH", "Initech", "88.25"], ["HOOLI", "Hooli", "980.10"],
              ["SOYLENT", "Soylent", "0.00"]]
    left = write(tmp_path, CHILD_HEADER, CHILD_ROWS, "orders.csv")
    right = write(tmp_path, ["vendor_code", "vendor_name", "amount"], parent, "vendors.csv")
    report, issues, _ = lint_join(left, right, reconcile=["amount=amount"])
    assert report is not None, [i.message for i in issues]
    levels = {f["id"]: f["level"] for f in report["findings"]}
    assert levels["JN7"] == "pass", detail_for(report, "JN7")

    parent[1][2] = "999.99"          # Globex now claims more than its lines
    right = write(tmp_path, ["vendor_code", "vendor_name", "amount"], parent, "vendors.csv")
    report, _, _ = lint_join(left, right, reconcile=["amount=amount"])
    levels = {f["id"]: f["level"] for f in report["findings"]}
    assert levels["JN7"] == "fail"
    assert "GLOBEX" in str(examples_for(report, "JN7"))


def test_an_ambiguous_key_is_refused_with_the_candidates_named(tmp_path):
    """The refusal that keeps a confident wrong answer from being produced."""
    child = [["a", "x1", "1"], ["b", "x2", "2"], ["c", "x3", "3"],
             ["d", "x4", "4"], ["e", "x5", "5"]]
    parent = [["x1", "a", "1"], ["x2", "b", "2"], ["x3", "c", "3"],
              ["x4", "d", "4"], ["x5", "e", "5"]]
    left = write(tmp_path, ["k1", "k2", "v"], child, "left.csv")
    right = write(tmp_path, ["k2", "k1", "v"], parent, "right.csv")
    report, issues, ctx = lint_join(left, right)
    assert report is None
    assert any("cannot tell which columns join" in i.message for i in issues), \
        [i.message for i in issues]


def test_a_bad_key_name_is_refused_rather_than_inferred_around(tmp_path):
    left = write(tmp_path, CHILD_HEADER, CHILD_ROWS, "orders.csv")
    right = write(tmp_path, PARENT_HEADER, PARENT_ROWS, "vendors.csv")
    report, issues, _ = lint_join(left, right, left_key="nope", right_key="vendor_code")
    assert report is None
    assert any("not in the left table" in i.message for i in issues)


def test_a_weak_best_candidate_is_refused_rather_than_used(tmp_path):
    """D-088, found by the trials arm.

    When the key a user MEANT to join on matches nothing, inference used to
    fall back to whatever else happened to overlap: a planted "nothing matches"
    case silently joined `amount <-> amount` at 33% and reported a healthy join
    on columns nobody meant. A weak best candidate is exactly when the tool has
    to ask instead of answer.
    """
    # The parent carries an `amount` column, so a coincidental numeric overlap
    # IS available once the real key stops matching. That is the trap.
    # Only two of six amounts coincide, which is a 33% overlap: an accident.
    # At 100% identification it still out-scores every other pair, which is
    # precisely why a floor is needed rather than a ranking.
    parent = [["X-ACME", "Acme Corp", "760.00"], ["X-GLOBEX", "Globex", "451.25"],
              ["X-INITECH", "Initech", "88.25"], ["X-HOOLI", "Hooli", "980.10"],
              ["X-SOYLENT", "Soylent", "0.00"]]
    left = write(tmp_path, CHILD_HEADER, CHILD_ROWS, "orders.csv")
    right = write(tmp_path, ["vendor_code", "vendor_name", "amount"], parent, "vendors.csv")
    report, issues, _ = lint_join(left, right)
    assert report is None
    assert any("not a relationship" in i.message for i in issues), [i.message for i in issues]


def test_the_confident_case_is_still_accepted(tmp_path):
    """The other side of D-088: a real key must not be refused by the floor."""
    _, _, ctx = audit(tmp_path)
    assert ctx["key"]["left"] == "vendor_code"
