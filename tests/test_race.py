"""`dinostomp race`: a replay of committed runs that cannot say more than they do.

Built on a real dry-provider pod, then mutated: one arm's summary is forged
to claim a higher accuracy than its records support, and the replay must
print MISMATCH for it. Lockstep, the floor mark, the scorer line, and the
refusal to replay an incomplete run are each pinned.
"""
import io
import json

import pytest

from dinostomp.race import (RaceError, bar, floor, load_race, replay, scorer_line)
from dinostomp.runner import OK, run_spec
from tests.test_lint import FLEET, choice_items, rewrite_run_consistently, write_eval


def _pod(tmp_path, models=FLEET[:2]):
    spec = write_eval(tmp_path, choice_items(24), models=models)
    outcome = run_spec(spec)
    assert outcome.exit_code == OK
    assert run_spec(spec, probe="blind").exit_code == OK
    return spec, outcome.run_files


def test_lanes_follow_the_spec_and_replay_in_lockstep(tmp_path):
    spec, _ = _pod(tmp_path)
    loaded, items, lanes = load_race(spec)
    assert [l.model for l in lanes] == ["dry-alpha", "dry-bravo"]
    assert len(items) == 24 and all(l.blind_records for l in lanes)
    out = io.StringIO()
    done = replay(spec, animate=False, out=out)
    text = out.getvalue()
    assert "REPLAY of committed run records; no model is called" in text
    for lane in done:
        assert lane.checkable == 24
        assert f"{lane.accuracy:.1%}" in text
    assert "matches" in text and "MISMATCH" not in text


def test_a_forged_summary_prints_mismatch_and_fails_the_exit_code(tmp_path):
    spec, run_files = _pod(tmp_path)
    run_file = run_files[0]
    summary = run_file.parents[1] / "results" / (run_file.stem + "_summary.json")
    doc = json.loads(summary.read_text(encoding="utf-8"))
    doc["accuracy_on_checkable"] = 0.999
    summary.write_text(json.dumps(doc), encoding="utf-8")
    out = io.StringIO()
    replay(spec, animate=False, out=out)
    assert "MISMATCH (summary 0.999)" in out.getvalue()

    from argparse import Namespace
    from dinostomp.race import cmd_race
    assert cmd_race(Namespace(pod=str(spec), rate=0, limit=None, models=None, no_animate=True)) == 1


def test_an_incomplete_run_is_not_a_lane(tmp_path):
    spec, run_files = _pod(tmp_path)
    manifest = run_files[1].with_name(run_files[1].stem + "_manifest.json")
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    doc["status"] = "stopped"
    manifest.write_text(json.dumps(doc), encoding="utf-8")
    _, _, lanes = load_race(spec)
    assert [l.model for l in lanes] == ["dry-alpha"]


def test_no_runs_is_a_refusal_not_a_crash(tmp_path):
    spec = write_eval(tmp_path, choice_items(24))
    with pytest.raises(RaceError, match="no complete informed run"):
        load_race(spec)


def test_the_floor_and_the_bar_mark_it():
    items = [{"target": "a"}] * 6 + [{"target": "b"}] * 4
    top, share = floor(items)
    assert top == "a" and share == 0.6
    drawn = bar(0.9, share, width=10)
    assert drawn == "######|##." and drawn.count("#") == 8     # 9 cells lit, one carries the floor mark
    assert bar(None, share, width=10) == "......|..."


def test_the_scorer_line_quotes_the_witnesses_that_must_fail():
    spec = {"scorer": {"kind": "exact", "witnesses": [
        {"output": "57", "target": "57", "expect": "pass"},
        {"output": "not 57", "target": "57", "expect": "fail"},
        {"output": "5", "target": "57", "expect": "fail"}]}}
    line = scorer_line(spec)
    assert line == "Scorer: exact (exact). Its own witnesses require these to FAIL: 'not 57' vs key '57'; '5' vs key '57'"
    assert scorer_line({"scorer": {"kind": "exact"}}) == "Scorer: exact (exact)."


def test_models_filter_keeps_spec_order_and_rejects_strangers(tmp_path):
    spec, _ = _pod(tmp_path)
    _, _, lanes = load_race(spec, models=["dry-bravo"])
    assert [l.model for l in lanes] == ["dry-bravo"]
    with pytest.raises(RaceError, match="not in the spec"):
        load_race(spec, models=["dry-zulu"])


def test_a_limited_replay_compares_nothing_to_the_full_run(tmp_path):
    """Found live: --limit 200 printed MISMATCH on every lane, because a
    200-item accuracy was checked against the full run's summary. A partial
    replay says it is partial and computes blind over the same items."""
    spec, _ = _pod(tmp_path)
    out = io.StringIO()
    replay(spec, limit=10, animate=False, out=out)
    text = out.getvalue()
    assert "MISMATCH" not in text and "matches" not in text
    assert "10 of 24 items, evenly spaced" in text and "nothing here is compared with the full-run summaries" in text


def test_a_limited_replay_samples_the_whole_run_not_its_head(tmp_path):
    spec, _ = _pod(tmp_path)
    _, items, _ = load_race(spec)
    out = io.StringIO()
    replay(spec, limit=6, animate=True, rate=0, out=out)
    shown = [i["id"] for i in items if f"[{i['id']}]" in out.getvalue()]
    assert shown == [items[k * 4]["id"] for k in range(6)]     # every 4th of 24

    from argparse import Namespace
    from dinostomp.race import cmd_race
    assert cmd_race(Namespace(pod=str(spec), rate=0, limit=10, models=None, no_animate=True)) == 0


def test_colour_means_free_earned_or_under_and_plain_output_has_none():
    from dinostomp.race import EARNED, FREE, Ink, UNDER, art, color_bar
    plain = Ink(False)
    assert color_bar(0.9, 0.6, plain, width=10) == bar(0.9, 0.6, width=10)
    assert art(plain) == []                                  # piped output stays text
    ink = Ink(True)
    above = color_bar(0.9, 0.6, ink, width=10)
    assert FREE in above and EARNED in above and UNDER not in above
    below = color_bar(0.4, 0.6, ink, width=10)
    assert UNDER in below and EARNED not in below            # under the floor is red end to end
