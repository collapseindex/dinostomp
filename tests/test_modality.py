"""Asset-backed items: the input lives in a file.

Written against `modality` and `perceptual` directly, because the trials prove
the CHECKS fire and these prove the primitives underneath them behave. Both
matter: a check can pass its trial for the wrong reason.
"""

import hashlib
import struct
import zlib
from pathlib import Path

import pytest

from dinostomp import modality, perceptual

BS = chr(92)


def png(rows) -> bytes:
    raw = b"".join(b"\x00" + bytes(r) for r in rows)

    def chunk(tag, body):
        return (struct.pack(">I", len(body)) + tag + body
                + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", len(rows[0]), len(rows), 8, 0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def block(x0=2, y0=2, w=5, h=5, side=16):
    return [[20 if x0 <= x < x0 + w and y0 <= y < y0 + h else 235
             for x in range(side)] for y in range(side)]


# --- path confinement: a dataset is untrusted input --------------------------


@pytest.mark.parametrize("uri", [
    "../escape.png",
    "../../escape.png",
    "sub/../../escape.png",
    "C:/Windows/System32/drivers/etc/hosts",
    "C:" + BS + "Windows" + BS + "notepad.exe",
    "/etc/passwd",
    "//server/share/x.png",
    BS * 2 + "server" + BS + "share" + BS + "x.png",
])
def test_an_asset_path_may_not_leave_the_pod(uri, tmp_path):
    """A uri comes from a dataset, and a dataset can be written by anyone.

    Absolute paths are refused even when harmless: a pod is only portable if
    everything it needs travels with it.

    The Windows and UNC forms run on EVERY platform on purpose. `is_absolute()`
    answers for the local platform, so a drive-letter path is absolute on
    Windows and an ordinary relative path on Linux; this suite passed on the
    Windows machine it was written on and failed in CI (D-044).
    """
    assert modality.resolve(uri, tmp_path) is None, f"{uri!r} was allowed to resolve"


@pytest.mark.parametrize("uri", ["images/a.png", "sub/dir/b.png", "./c.png",
                                 "images" + BS + "windows-style.png"])
def test_ordinary_relative_paths_are_not_caught_by_the_guard(uri, tmp_path):
    """The other direction. A guard that refuses everything is not a guard, and
    a Windows-authored pod writing `images\a.png` must still work."""
    assert modality.resolve(uri, tmp_path) is not None, f"{uri!r} was wrongly refused"


def test_an_ordinary_relative_path_resolves(tmp_path):
    (tmp_path / "images").mkdir()
    (tmp_path / "images" / "a.png").write_bytes(png(block()))
    got = modality.resolve("images/a.png", tmp_path)
    assert got is not None and got.is_file()


# --- hashing and verification ------------------------------------------------


def test_a_changed_file_is_caught_and_a_matching_one_is_not(tmp_path):
    data = png(block())
    (tmp_path / "a.png").write_bytes(data)
    item = {"id": "x", "target": "t",
            "input_ref": {"kind": "image", "uri": "a.png",
                          "sha256": hashlib.sha256(data).hexdigest()}}
    problems, digests = modality.verify_refs([item], tmp_path)
    assert not problems and digests["x"] == hashlib.sha256(data).hexdigest()

    (tmp_path / "a.png").write_bytes(png(block(x0=6)))
    problems, digests = modality.verify_refs([item], tmp_path)
    assert [p.kind for p in problems] == ["hash-mismatch"]
    assert "x" not in digests, (
        "an item whose asset failed verification must not appear in the digest map: "
        "a placeholder there makes every broken item a duplicate of every other")


def test_asset_bytes_are_not_newline_normalised(tmp_path):
    """The engine fingerprint normalises line endings on purpose. An asset must
    NOT: a PNG whose CRLFs were 'fixed' is a corrupt PNG."""
    (tmp_path / "a.bin").write_bytes(b"\r\n\r\n")
    (tmp_path / "b.bin").write_bytes(b"\n\n")
    assert modality.sha256_file(tmp_path / "a.bin") != modality.sha256_file(tmp_path / "b.bin")


# --- the label in the path ---------------------------------------------------


def test_a_class_directory_leaks_and_a_substring_does_not():
    assert modality.path_leaks_label("images/test/cat/0001.png", ["cat"]) == "cat"
    assert modality.path_leaks_label("images/cat_0001.png", ["cat"]) == "cat"
    # 'cat' inside 'concatenated' is not a leak, and a check that says it is
    # will be switched off by the first person it annoys.
    assert modality.path_leaks_label("images/concatenated/0001.png", ["cat"]) is None
    assert modality.path_leaks_label("images/scatter/0001.png", ["cat"]) is None
    # Short labels are ignored: a 2-character class name matches everywhere.
    assert modality.path_leaks_label("images/ab/0001.png", ["ab"]) is None


# --- perceptual --------------------------------------------------------------


@pytest.mark.skipif(not perceptual.available(), reason="needs the vision extra")
def test_a_brightened_copy_hashes_close_and_a_different_picture_does_not(tmp_path):
    base = block()
    (tmp_path / "a.png").write_bytes(png(base))
    (tmp_path / "b.png").write_bytes(png([[min(255, v + 4) for v in r] for r in base]))
    (tmp_path / "c.png").write_bytes(png(block(x0=9, y0=9, w=4, h=6)))

    a, b, c = (perceptual.dhash(tmp_path / n) for n in ("a.png", "b.png", "c.png"))
    assert None not in (a, b, c)
    assert perceptual.distance(a, b) <= perceptual.NEAR_DUP_BITS, (
        "a brightened copy of the same picture must read as a near-duplicate")
    assert perceptual.distance(a, c) > perceptual.NEAR_DUP_BITS, (
        "two different pictures must not")


@pytest.mark.skipif(not perceptual.available(), reason="needs the vision extra")
def test_the_bucketed_search_finds_what_the_exhaustive_one_does(tmp_path):
    """The bucketing is a pigeonhole argument, not a heuristic, so it must lose
    no pair the O(n^2) comparison would find. If it ever does, the check is
    silently under-reporting, which is the flattering direction."""
    hashes = {f"i{n}": (n * 2654435761) % (1 << 64) for n in range(220)}
    hashes["near-a"] = 0xF0F0F0F0F0F0F0F0
    hashes["near-b"] = 0xF0F0F0F0F0F0F0F1
    bits = perceptual.NEAR_DUP_BITS

    exhaustive = set()
    ids = sorted(hashes)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if perceptual.distance(hashes[a], hashes[b]) <= bits:
                exhaustive.add((a, b))
    bucketed = {(a, b) for a, b, _ in perceptual.near_duplicate_pairs(hashes, bits)}
    assert bucketed == exhaustive
    assert ("near-a", "near-b") in bucketed


def test_a_corrupt_image_returns_none_rather_than_raising(tmp_path):
    (tmp_path / "bad.png").write_bytes(b"not a png at all")
    assert perceptual.dhash(tmp_path / "bad.png") is None


def test_the_check_skips_rather_than_passes_without_the_extra():
    """The wording matters more than the mechanism: a reader must not come away
    thinking the dataset was searched."""
    reason = perceptual.missing_reason()
    assert "pip install" in reason and "dinostomp[vision]" in reason
    assert "S1 and S7" in reason, "the skip should say what IS still covered"


# --- instruction framings ----------------------------------------------------
#
# templates.py had no test naming it. It is reached only through the runner's
# framing probe, so a change to a framing would have been caught by nothing
# until a probe run disagreed with a published number.


def test_every_framing_leaves_the_item_text_untouched():
    """A framing varies what the model is told about the TASK. If it altered the
    item, a swing between framings would measure the edit rather than the
    phrasing, and P11/P12 would attribute it to the wrong thing."""
    from dinostomp.templates import DEFAULT_FRAMINGS, framed_input

    item = {"input": "What is 17 + 25?"}
    for name in DEFAULT_FRAMINGS:
        rendered = framed_input(item, name)
        assert item["input"] in rendered, f"framing {name!r} does not contain the item verbatim"


def test_framings_are_uniquely_named_and_every_name_resolves():
    from dinostomp.templates import DEFAULT_FRAMINGS, FRAMINGS, FRAMINGS_BY_NAME

    names = [f.name for f in FRAMINGS]
    assert len(set(names)) == len(names), "two framings share a name"
    assert set(DEFAULT_FRAMINGS) == set(names)
    for name in DEFAULT_FRAMINGS:
        assert FRAMINGS_BY_NAME[name].name == name
    assert "bare" in DEFAULT_FRAMINGS, (
        "the unframed control has to be in the default set or every swing is "
        "measured against another framing rather than against no framing")


def test_no_framing_names_a_specific_output_format():
    """Changing the requested FORMAT moves the scorer too, so a swing would stop
    being about the phrasing. The module docstring states this as a rule; this
    asserts it."""
    from dinostomp.templates import FRAMINGS

    banned = ("json", "yaml", "one word", "single letter", "```", "only the number")
    for framing in FRAMINGS:
        body = framing.template.lower()
        for word in banned:
            assert word not in body, (
                f"framing {framing.name!r} constrains the output format ({word!r}), "
                f"so a swing under it would measure the scorer")


def test_a_chat_input_is_refused_rather_than_reframed():
    """Framing a chat-message input would mean rewriting somebody's system
    prompt, which is not what this probe varies."""
    import pytest as _pytest

    from dinostomp.templates import framed_input

    with _pytest.raises(ValueError):
        framed_input({"input": [{"role": "user", "content": "hi"}]}, "instructed")
