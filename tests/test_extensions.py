"""The extension rail, and the one rule that makes it safe.

THE HARD RULE: an extension may add findings, never remove or soften one.

These tests exist because that rule cannot live in a style guide. The moment an
extension can make a verdict greener, every SOUND in the wild means "sound
according to whatever plugins that person had installed", and the engine
fingerprint stops covering the thing that decided.
"""

import types

import pytest

from dinostomp.extensions import (Collector, ExtensionCheck, ExtensionError, LoadedExtension,
                                  discover, run_extensions, thresholds_fingerprint)
from dinostomp.lint import CHECKS, THRESHOLDS


class FakeEP:
    def __init__(self, name, module):
        self.name = name
        self._module = module

    def load(self):
        if isinstance(self._module, Exception):
            raise self._module
        return self._module


def provider(name="demo", version="1.0", checks=None, trials=True, clean=True):
    mod = types.ModuleType(f"demo_{name}")
    mod.NAME = name
    mod.VERSION = version
    mod.CHECKS = checks if checks is not None else [
        ExtensionCheck(id="X1", name="a demo check", gating=False,
                       applies_when="always", run=lambda ctx, out: out.finding(
                           "X1", "warn", "demo finding", n=1))]
    if trials:
        mod.TRIALS = [("a planted defect", lambda root: root)]
    if clean:
        mod.CLEAN_PODS = [("a clean pod", lambda root: root)]
    return mod


CORE_IDS = {cid for cid, *_ in CHECKS}


# --- the collector is write-only ---------------------------------------------


def test_the_collector_offers_no_way_to_read_or_edit():
    """A plugin that can read the verdict is one step from one that shapes it."""
    c = Collector()
    public = {m for m in dir(c) if not m.startswith("_")}
    assert public == {"finding", "drain"}, f"the collector grew an API: {public}"


def test_an_unknown_level_is_refused():
    with pytest.raises(ExtensionError):
        Collector().finding("X1", "definitely-fine", "trust me")


# --- the hard rule ------------------------------------------------------------


def test_mutating_a_threshold_aborts_the_audit():
    """Not "drop the findings and carry on". A report whose settings cannot be
    reconstructed is worse than no report."""
    def sneaky(ctx, out):
        THRESHOLDS["guess_margin"] = 0.99
        out.finding("X1", "pass", "nothing to see here")

    ext = LoadedExtension("sneaky", "1.0", "abc", [
        ExtensionCheck("X1", "n", False, "always", sneaky)], validated=True)
    original = THRESHOLDS["guess_margin"]
    try:
        with pytest.raises(ExtensionError, match="mutated THRESHOLDS"):
            run_extensions([ext], {}, THRESHOLDS)
    finally:
        THRESHOLDS["guess_margin"] = original


def test_the_threshold_fingerprint_actually_notices():
    """Negative half: if the fingerprint could not see a change, the guard above
    would pass for the wrong reason."""
    a = thresholds_fingerprint({"x": 1, "y": 2})
    assert a == thresholds_fingerprint({"y": 2, "x": 1}), "order must not matter"
    assert a != thresholds_fingerprint({"x": 1.0001, "y": 2}), "a moved dial must change it"


def test_a_core_finding_that_changes_refuses_the_report(tmp_path):
    """The bluntest guard, and the one that has to wrap the RIGHT window.

    An earlier version compared core findings before and after the merge loop,
    where no extension code runs, so it could not fire. This test is what
    proved that; it now sabotages from inside a check's `run`, which is where
    extension code actually executes.
    """
    from dinostomp.lint import lint_eval
    from dinostomp.runner import OK, run_spec
    from tests.test_lint import arith_items, write_eval

    pod = write_eval(tmp_path, arith_items())
    assert run_spec(pod).exit_code == OK

    def sabotage(ctx, out):
        # reach for the reporter the way a hostile extension would have to
        import gc

        from dinostomp.lint import Reporter
        for obj in gc.get_objects():
            if isinstance(obj, Reporter) and "S1" in getattr(obj, "findings", {}):
                obj.findings.pop("S1")
                break
        out.finding("X1", "pass", "nothing to see here")

    ext = LoadedExtension("saboteur", "1.0", "h", [
        ExtensionCheck("X1", "n", False, "always", sabotage)], validated=True)
    import dinostomp.lint as lint_mod

    real_discover = lint_mod.discover
    lint_mod.discover = lambda core_ids, **kw: ([ext], [])
    try:
        report, issues = lint_eval(pod)
    finally:
        lint_mod.discover = real_discover
    assert report is None, "a tampered core finding must refuse the report"
    assert any("core finding changed" in i.message for i in issues)


def test_an_extension_can_only_make_a_verdict_redder():
    from dinostomp.lint import Reporter

    def verdict_with(level, validated):
        rep = Reporter()
        for cid, *_ in CHECKS:
            rep.not_applicable(cid, "out of scope for this test")
        ext = [{"check_id": "x:demo:X1", "level": level, "detail": "d", "n": 1,
                "examples": [], "evidence": {}, "name": "n", "gating": level == "fail",
                "extension": "demo", "validated": validated}]
        return rep.report("t", extensions=ext,
                          loaded_extensions=[LoadedExtension("demo", "1", "h", [], validated)])

    assert verdict_with("pass", True)["summary"]["verdict"] == "sound"
    assert verdict_with("warn", True)["summary"]["verdict"] == "ok"
    assert verdict_with("fail", True)["summary"]["verdict"] == "broken"
    # and an UNVALIDATED extension cannot move the verdict at all, in either
    # direction: it is reported, and it does not vote
    assert verdict_with("fail", False)["summary"]["verdict"] == "sound"


# --- the evidence tax ---------------------------------------------------------


def test_an_extension_without_trials_is_loaded_but_not_counted():
    """Its findings are still REPORTED. Suppressing them would be its own kind
    of dishonesty; the honest move is to label them."""
    loaded, problems = discover(CORE_IDS, entry_points=[FakeEP("demo", provider(trials=False))])
    assert not problems
    assert len(loaded) == 1 and loaded[0].validated is False
    assert "no TRIALS" in loaded[0].reason
    assert "excluded from coverage" in loaded[0].reason


def test_an_extension_without_a_clean_pod_is_not_counted_either():
    loaded, _ = discover(CORE_IDS, entry_points=[FakeEP("demo", provider(clean=False))])
    assert loaded[0].validated is False
    assert "CLEAN_PODS" in loaded[0].reason


def test_a_fully_evidenced_extension_counts():
    loaded, problems = discover(CORE_IDS, entry_points=[FakeEP("demo", provider())])
    assert not problems
    assert loaded[0].validated is True and loaded[0].reason == ""


# --- refusals -----------------------------------------------------------------


def test_a_check_id_colliding_with_core_is_refused():
    bad = provider(checks=[ExtensionCheck("S1", "impostor", True, "always",
                                          lambda ctx, out: None)])
    loaded, problems = discover(CORE_IDS, entry_points=[FakeEP("bad", bad)])
    assert loaded == []
    assert "collide with core checks" in problems[0]


def test_an_extension_that_raises_on_import_is_refused_not_fatal():
    loaded, problems = discover(CORE_IDS, entry_points=[
        FakeEP("boom", ImportError("no")), FakeEP("good", provider())])
    assert [e.name for e in loaded] == ["demo"], "one bad extension must not kill the rest"
    assert "raised on import" in problems[0]


def test_a_provider_with_no_checks_is_refused():
    loaded, problems = discover(CORE_IDS, entry_points=[FakeEP("empty", provider(checks=[]))])
    assert loaded == [] and "declares no CHECKS" in problems[0]


def test_a_non_check_entry_is_refused():
    loaded, problems = discover(CORE_IDS, entry_points=[
        FakeEP("junk", provider(checks=[{"id": "X1"}]))])
    assert loaded == [] and "not ExtensionCheck" in problems[0]


def test_a_crashing_check_is_skipped_and_named():
    def boom(ctx, out):
        raise ValueError("kaboom")

    ext = LoadedExtension("demo", "1", "h", [
        ExtensionCheck("X1", "n", False, "always", boom)], validated=True)
    findings, problems = run_extensions([ext], {}, THRESHOLDS)
    assert findings == []
    assert "demo:X1 raised and was skipped: kaboom" in problems[0]


# --- the report names its inputs ---------------------------------------------


def test_the_report_hashes_and_names_every_loaded_extension():
    from dinostomp.lint import Reporter

    rep = Reporter()
    for cid, *_ in CHECKS:
        rep.not_applicable(cid, "out of scope for this test")
    ext = LoadedExtension("demo", "2.1", "f" * 64, [ExtensionCheck(
        "X1", "n", False, "always", lambda c, o: None)], validated=True)
    report = rep.report("t", extensions=[], loaded_extensions=[ext])
    assert report["extensions"] == [
        {"name": "demo", "version": "2.1", "sha256": "f" * 64,
         "checks": ["X1"], "validated": True}]
    assert report["coverage"]["extensions"] == {"loaded": 1, "validated": 1, "unvalidated": 0}


def test_findings_are_namespaced_so_provenance_is_never_ambiguous():
    ext = LoadedExtension("acme", "1", "h", [ExtensionCheck(
        "X1", "n", False, "always",
        lambda ctx, out: out.finding("X1", "warn", "d"))], validated=True)
    findings, _ = run_extensions([ext], {}, THRESHOLDS)
    assert findings[0]["check_id"] == "x:acme:X1"
    assert findings[0]["extension"] == "acme"
