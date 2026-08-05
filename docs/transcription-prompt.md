# Transcription prompt — adding another Isogawa book

Copy everything below the line into a **fresh Claude chat**, attach clear
photos of the book's cover and every page of its back-of-book parts list,
and send it. Save Claude's reply into a file (anywhere, e.g.
`add-book-reply.md`) and hand it to whoever is maintaining this repo (or a
future Claude Code session working in it) — see "What happens next" below
for how the reply becomes real files.

---

## Full text to copy

```
You are transcribing the back-of-book parts list from a Yoshihito Isogawa
LEGO Technic book (No Starch Press) into this repo's data format. I've
attached photographs of the cover and every page of the parts list. Read the
numbers directly from the photos — do not guess from memory of similar
Isogawa books, and do not reuse figures from a different edition or printing.

=====================================================================
WHAT TO PRODUCE
=====================================================================

Three things, each its own fenced block.

--- Block 1: the new book file -------------------------------------

```lego-workshop-book
{
  "slug": "idea-book-1",
  "meta": {
    "key": "ib1",
    "title": "The Lego Technic Idea Book: Simple Machines",
    "short": "IB1",
    "models": 100,
    "isbn": "978-0-000-00000-0",
    "publisher": "No Starch Press",
    "author": "Yoshihito Isogawa",
    "buy_links": ["https://nostarch.com/...", "https://www.amazon.com/..."],
    "blurb": "One sentence describing the book."
  },
  "parts": [
    {"part": "32015", "qty": 4, "page": 60},
    {"part": "3711", "qty": 45, "page": 61}
  ]
}
```

This becomes `data/books/<slug>.json`. Note that "parts" here holds ONLY
part id, quantity, and page — no name, group, or price. Those live in the
shared catalog, block 2.

--- Block 2: new or changed catalog entries -------------------------

One entry per part that ISN'T ALREADY in this repo's `data/parts.json` (I
will tell you the current part list if you ask, or you can assume any part
you don't recognize from a standard Technic catalog is new):

```lego-workshop-parts
{
  "32015": {
    "name": "Angle element #5 (112.5 deg)",
    "group": "Connectors",
    "page": 60,
    "alt": null,
    "source": "pick-a-brick",
    "price_est": 0.20,
    "bricklink_url": "https://www.bricklink.com/v2/catalog/catalogitem.page?P=32015",
    "pab_url": "https://www.lego.com/en-us/pick-and-build/pick-a-brick?query=32015"
  }
}
```

--- Block 3: paired-volume peak (ONLY if this book pairs with an existing
    tracked book — see "paired_with" below; omit this block entirely if not) --

```lego-workshop-peak
{"books": ["idea-book-1", "some-other-tracked-book"],
 "peak": {"32015": 6, "3711": 50}}
```

=====================================================================
FIELD RULES
=====================================================================

Block 1 — the book file:

slug — lowercase, hyphens only, from the title. Must not already be one of
  this repo's existing book slugs (ask if unsure).

key — 2-4 letters, must not collide with an existing book's key.

models — the total model count, ONLY if the book states it. Omit the field
  entirely if not found stated anywhere.

isbn — from the back cover / copyright page. Omit if not visible.

buy_links — the No Starch Press product page and the Amazon listing, if you
  can find them; otherwise omit and note it as missing.

parts[].part — the part/design ID EXACTLY AS PRINTED (keep leading zeros,
  "c01" suffixes, "x"-prefixes exactly as shown).

  IMPORTANT — do not "correct" IDs. Always record the number exactly as the
  book prints it, never a number you believe is more "correct" or more
  current, even if you recognize it as an old/retired code. If you suspect a
  printed ID might not match what that number means on BrickLink, do NOT
  silently substitute anything — leave "part" as printed and add a note in
  your reply instead, e.g. "62520c01: printed ID may not match BrickLink's
  catalog for this part — please verify." A human resolves real collisions
  separately; your job is faithful transcription, not correction.

parts[].qty — the quantity printed for THIS book. If the row shows a SECOND,
  parenthesised number like "x2 (x12)", that second number is NOT this field
  — see paired_with below.

parts[].page — the printed page number this row came from.

Block 2 — catalog entries (only for parts not already in data/parts.json):

  name  — the part's printed name/description.
  group — the CLOSEST match from this fixed list. Do not invent a new one:
            Gears, Racks & drives, Axles, Pins & bushes, Connectors, Beams,
            Wheels, System bricks
          If truly nothing fits, ask before inventing anything else. Plain
          System-brand bricks/plates always go in "System bricks".
  page  — same page number as its first appearance in parts[].
  alt   — a second part ID the book explicitly says is an equally acceptable
          substitute (e.g. "#32905"), or null if none is stated. Never guess
          one.
  source — your best guess at where a parent would buy this:
            "any-lego-bin"  — an ordinary System brick/plate almost every
                               household LEGO collection already has (this
                               is nearly always true for "System bricks"
                               group parts, and rarely true for anything
                               else).
            "pick-a-brick"  — a common current-catalog Technic element LEGO's
                               own Pick a Brick service is likely to carry.
            "bricklink"     — anything else, including older/retired molds,
                               specialty parts, and anything you're unsure
                               about. This is the safe default — BrickLink
                               carries virtually everything.
  price_est — a rough planning estimate in USD (BrickLink lot price or Pick
          a Brick unit price, whichever matches "source"). These are
          estimates only, clearly labeled as such everywhere they're shown
          — don't worry about being exact.
  bricklink_url — always exactly
          "https://www.bricklink.com/v2/catalog/catalogitem.page?P=<part>"
  pab_url — always exactly
          "https://www.lego.com/en-us/pick-and-build/pick-a-brick?query=<part>"
  note (optional) — a short string for catalog quirks (mold variants,
          filing oddities) worth a shopper knowing. Omit the field entirely
          if there's nothing to say — most parts won't have one.

Block 3 — paired volume peak:

  Isogawa's paired volumes (like Simple Machines / Clever Contraptions) each
  print a SHARED number in parentheses next to every part's quantity,
  because the two books cross-reference each other. If you see that exact
  pattern in the book you're transcribing too — a second, parenthesised
  number next to every quantity — name the other tracked book you believe
  it's paired with (ask if unsure) and include block 3, with "peak" holding
  one entry per part: the parenthesised number. If you do NOT see a second
  parenthesised number (true for most standalone books), omit block 3
  entirely. Do not assume pairing — only produce this block if you actually
  see the second number.

=====================================================================
BEFORE YOU ANSWER — SELF-CHECK
=====================================================================

1. Re-read each row a second time from the photo. If a digit could be a 5
   vs 6, 1 vs 7, etc., say so in a note in your reply — don't silently pick
   one.
2. Count your "parts" array in block 1 and compare it to how many rows are
   visibly printed across the given pages. If they don't match, find the
   missed row before answering.
3. Check every "group" value in block 2 against the fixed list above.
4. If you produced block 3, confirm max(this book's qty, the other book's
   qty) equals your "peak" value for every part in it — the whole point of
   that block is a number that must reconcile exactly.
5. Confirm all three blocks are valid JSON — no trailing commas, no
   comments, every string quoted.

=====================================================================
WHAT HAPPENS NEXT
=====================================================================

Whoever maintains this repo (very possibly a future Claude Code session)
will:

1. Save block 1 as `data/books/<slug>.json`.
2. Merge block 2's entries into `data/parts.json`.
3. If you produced block 3, append it to `data/book-pairs.json`'s "pairs"
   array.
4. Add "<slug>" to `BOOK_ORDER` near the top of `src/generate.py` (a
   one-line edit — this repo tracks exactly two books today, so the
   generator's per-book loop is a short explicit list rather than an
   auto-discovered one).
5. Run `make check` (`python3 src/books.py`) — it hard-fails with a specific
   message if anything disagrees with itself, most commonly a peak that
   doesn't reconcile or a part used by a book but missing from the catalog.
6. Run `make` — new prompts, exports, and checklists appear for the new
   book automatically, and `STATUS.md` gains a section for it.

If anything's flagged, the fix is almost always asking Claude to re-check
one specific row against the photo and re-send just that correction.
```
