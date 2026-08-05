"""Loader for the public parts catalog.

Reads three data files instead of carrying the catalog as inline literals,
because this repo is meant to grow past two books over time (see
docs/transcription-prompt.md in the private tracker's plan for the eventual
add-a-book workflow):

    data/parts.json          global catalog, one entry per part
    data/books/*.json        one file per volume: which parts it needs, and
                              how many, per model
    data/book-pairs.json     cross-check figures for volumes that print a
                              shared "needed by either book" quantity

check() runs at import time and hard-fails (SystemExit) if the files
disagree with each other or with themselves -- a torn edit should never ship
silently.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

SOURCES = {"bricklink", "pick-a-brick", "any-lego-bin"}

BLINK = "https://www.bricklink.com/v2/catalog/catalogitem.page?P={}"
PAB = "https://www.lego.com/en-us/pick-and-build/pick-a-brick?query={}"


def _load_json(path):
    return json.loads(path.read_text())


_raw_parts = _load_json(DATA / "parts.json")
META = _raw_parts.pop("_meta")   # generation date + estimate disclaimer
PARTS = _raw_parts               # part id -> {name, group, page, alt, source, ...}

BOOKS = {d["slug"]: d for d in
          (_load_json(p) for p in sorted((DATA / "books").glob("*.json")))}

PAIRS = _load_json(DATA / "book-pairs.json")["pairs"]


def rows():
    """One dict per part in the global catalog, sorted page then part id."""
    return [dict(part=part, **fields) for part, fields in
            sorted(PARTS.items(), key=lambda kv: (kv[1]["page"], kv[0]))]


def need(slug):
    """part -> per-model quantity for one book, 0 for parts that book's own
    printed list doesn't need at all."""
    wanted = {r["part"]: r["qty"] for r in BOOKS[slug]["parts"]}
    return {part: wanted.get(part, 0) for part in PARTS}


def peak_for(part):
    """The shared per-model maximum for a part, from whichever declared pair
    includes it, or None if it isn't part of a pair."""
    for pair in PAIRS:
        if part in pair["peak"]:
            return pair["peak"][part]
    return None


def check() -> None:
    """Cross-validate the three data files against each other."""
    bad = []

    if len(PARTS) != 161:
        bad.append(f"expected 161 parts in the union, found {len(PARTS)}")

    book_parts = set()
    for slug, book in BOOKS.items():
        seen = set()
        for row in book["parts"]:
            part = row["part"]
            if part in seen:
                bad.append(f"{slug}: {part} listed twice")
            seen.add(part)
            book_parts.add(part)
            if part not in PARTS:
                bad.append(f"{slug}: {part} not in data/parts.json")

    for part in PARTS:
        if part not in book_parts:
            bad.append(f"{part}: in data/parts.json but no book lists it")

    for pair in PAIRS:
        a, b = pair["books"]
        need_a, need_b = need(a), need(b)
        for part, peak in pair["peak"].items():
            qa, qb = need_a.get(part, 0), need_b.get(part, 0)
            if max(qa, qb) != peak:
                bad.append(f"{part}: max({a}={qa}, {b}={qb}) = {max(qa, qb)} "
                           f"!= declared peak {peak}")

    for part, fields in PARTS.items():
        if fields["source"] not in SOURCES:
            bad.append(f"{part}: unknown source {fields['source']!r}")
        if not fields["price_est"] > 0:
            bad.append(f"{part}: price_est must be > 0, got {fields['price_est']!r}")

    if bad:
        raise SystemExit("books.py failed self-check:\n  " + "\n  ".join(bad))


check()
