"""The single generator for order prompts, order-export files, printable
checklists, and STATUS.md.

    python3 src/generate.py

Reads (via books.py):
    data/parts.json, data/books/*.json, data/book-pairs.json
And every order report a parent has saved:
    inventory/orders/*.md

Writes:
    prompts/order-prompt-{bricklink,lego}-{simple-machines,clever-contraptions,both}.md
    exports/bricklink-wanted-{simple-machines,clever-contraptions,both}.xml
    exports/pick-a-brick-{simple-machines,clever-contraptions,both}.csv
    checklists/checklist-{simple-machines,clever-contraptions,both}.md
    STATUS.md

Nothing here is hand-maintained except the prose templates below. Change an
order report or the data catalog and every output follows -- run `make`.

REMAINING need, everywhere in this file, means: what a book's per-model
maximum asks for, minus what inventory/orders/*.md report you already own.
At cold start (no order reports yet) that is simply the full list.
"""
import csv
import math
import re
import sys
from datetime import date as _date
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
import books  # noqa: E402 -- needs SRC on sys.path first

PROMPTS = ROOT / "prompts"
EXPORTS = ROOT / "exports"
CHECKLISTS = ROOT / "checklists"
ORDERS_DIR = ROOT / "inventory" / "orders"

# A fixed date, never wall-clock time: two consecutive `make` runs with no
# other change must produce byte-identical files.
EXAMPLE_DATE = "2026-08-10"

BOOK_ORDER = ["simple-machines", "clever-contraptions"]   # reading order
SCOPES = BOOK_ORDER + ["both"]


# ---------------------------------------------------------------------------
# Need / remaining, per scope
# ---------------------------------------------------------------------------

def need_for_scope(scope):
    """part -> quantity needed, for one book or 'both' (the shared per-model
    peak across whichever pair of books declares one -- every part in this
    two-book catalog is covered by the sm/cc pair, so this is always
    max(sm_need, cc_need); the fallback exists only so a future third,
    unpaired book can't silently break 'both')."""
    if scope != "both":
        return books.need(scope)
    out = {}
    for part in books.PARTS:
        peak = books.peak_for(part)
        if peak is None:
            peak = max(books.need(s).get(part, 0) for s in BOOK_ORDER)
        out[part] = peak
    return out


def rows_for_scope(scope, owned):
    """Every part this scope still needs, remaining qty > 0, with the buy
    columns (want/have/qty/line) attached."""
    need = need_for_scope(scope)
    out = []
    for r in books.rows():
        want = need.get(r["part"], 0)
        if want <= 0:
            continue
        have = owned.get(r["part"], 0)
        remaining = max(0, want - have)
        if remaining <= 0:
            continue
        row = dict(r, want=want, have=have, qty=remaining,
                    line=round(remaining * r["price_est"], 2))
        out.append(row)
    return out


def scope_title(scope):
    if scope == "both":
        return "Both books"
    return books.BOOKS[scope]["meta"]["title"]


def _book_phrase(scope):
    if scope == "both":
        sm = books.BOOKS["simple-machines"]["meta"]["title"]
        cc = books.BOOKS["clever-contraptions"]["meta"]["title"]
        return (f"both of Yoshihito Isogawa's *LEGO Technic Non-Electric Models* "
                f"books — **{sm}** and **{cc}**")
    meta = books.BOOKS[scope]["meta"]
    return f"Yoshihito Isogawa's *LEGO Technic Non-Electric Models: {meta['title']}*"


# ---------------------------------------------------------------------------
# Order-report parsing (inventory/orders/*.md -> owned dict)
# ---------------------------------------------------------------------------

ORDER_FENCE = re.compile(r"^```lego-workshop-order[ \t]*\n(.*?)\n```[ \t]*$",
                          re.M | re.S)

SITE_VALUES = {"bricklink", "lego-pab"}

_NUM = r"\d+(?:\.\d+)?"
SITE_LINE = re.compile(r"^site:\s*(?P<v>\S+)\s*$")
STORE_LINE = re.compile(r"^store:\s*(?P<v>.+?)\s*$")
DATE_LINE = re.compile(r"^date:\s*(?P<v>\d{4}-\d{2}-\d{2})\s*$")
PART_LINE = re.compile(
    rf"^part:\s*(?P<id>\S+)\s+qty\s+(?P<qty>\d+)\s+color\s+(?P<color>.+?)\s+"
    rf"cond\s+(?P<cond>[NU])\s+unit\s+(?P<unit>{_NUM})\s*$")
SUB_LINE = re.compile(
    rf"^substituted:\s*(?P<req>\S+)\s*->\s*(?P<bought>\S+)\s+qty\s+(?P<qty>\d+)\s+"
    rf"color\s+(?P<color>.+?)\s+cond\s+(?P<cond>[NU])\s+unit\s+(?P<unit>{_NUM})\s*$")
SKIP_LINE = re.compile(r"^skipped:\s*(?P<id>\S+)\s+reason\s+(?P<reason>.+)$")
SHIP_LINE = re.compile(rf"^shipping:\s*(?P<v>{_NUM})\s*$")
TOTAL_LINE = re.compile(rf"^total:\s*(?P<v>{_NUM})\s*$")


def _fail(file, lineno, msg):
    # Hard SystemExit, naming file + line -- a torn report should never ship
    # as a silent miscount.
    raise SystemExit(f"{file}:{lineno}: {msg}")


def _warn(file, lineno, msg):
    print(f"warning: {file}:{lineno}: {msg}", file=sys.stderr)


def _parse_block(file, start_line, block_text, owned):
    site = store = order_date = shipping = total = None
    part_lines, subs, skips = [], [], []

    for offset, raw in enumerate(block_text.splitlines()):
        lineno = start_line + offset
        line = raw.strip()
        if not line:
            continue
        prefix = line.split(":", 1)[0] + ":"
        if prefix == "site:":
            m = SITE_LINE.match(line)
            if not m:
                _fail(file, lineno, f"malformed site line: {raw!r}")
            site = m.group("v")
            if site not in SITE_VALUES:
                _fail(file, lineno,
                      f"unknown site {site!r} (expected 'bricklink' or 'lego-pab')")
        elif prefix == "store:":
            m = STORE_LINE.match(line)
            if not m:
                _fail(file, lineno, f"malformed store line: {raw!r}")
            store = m.group("v")
        elif prefix == "date:":
            m = DATE_LINE.match(line)
            if not m:
                _fail(file, lineno, f"malformed date line, want YYYY-MM-DD: {raw!r}")
            order_date = m.group("v")
            try:
                _date.fromisoformat(order_date)
            except ValueError:
                _fail(file, lineno, f"not a real calendar date: {order_date!r}")
        elif prefix == "part:":
            m = PART_LINE.match(line)
            if not m:
                _fail(file, lineno, f"malformed part line: {raw!r}")
            part_lines.append((lineno, m))
        elif prefix == "substituted:":
            m = SUB_LINE.match(line)
            if not m:
                _fail(file, lineno, f"malformed substituted line: {raw!r}")
            subs.append((lineno, m))
        elif prefix == "skipped:":
            m = SKIP_LINE.match(line)
            if not m:
                _fail(file, lineno, f"malformed skipped line: {raw!r}")
            skips.append((lineno, m))
        elif prefix == "shipping:":
            m = SHIP_LINE.match(line)
            if not m:
                _fail(file, lineno, f"malformed shipping line: {raw!r}")
            shipping = float(m.group("v"))
        elif prefix == "total:":
            m = TOTAL_LINE.match(line)
            if not m:
                _fail(file, lineno, f"malformed total line: {raw!r}")
            total = float(m.group("v"))
        else:
            _fail(file, lineno,
                  "unrecognized line -- expected one of site/store/date/part/"
                  f"skipped/substituted/shipping/total: {raw!r}")

    if site is None:
        _fail(file, start_line, "order block missing required 'site:' line")
    if order_date is None:
        _fail(file, start_line, "order block missing required 'date:' line")
    if shipping is None:
        _fail(file, start_line, "order block missing required 'shipping:' line")
    if total is None:
        _fail(file, start_line, "order block missing required 'total:' line")

    computed = 0.0
    for lineno, m in part_lines:
        pid, qty, unit = m.group("id"), int(m.group("qty")), float(m.group("unit"))
        computed += qty * unit
        if pid in books.PARTS:
            owned[pid] = owned.get(pid, 0) + qty
        else:
            _warn(file, lineno, f"unknown part id {pid!r} on a part: line -- skipping")

    for lineno, m in subs:
        req, bought = m.group("req"), m.group("bought")
        qty, unit = int(m.group("qty")), float(m.group("unit"))
        computed += qty * unit
        req_alt = books.PARTS.get(req, {}).get("alt")
        if req_alt == bought:
            owned[req] = owned.get(req, 0) + qty
        elif bought in books.PARTS:
            owned[bought] = owned.get(bought, 0) + qty
        else:
            _warn(file, lineno,
                  f"substituted part {bought!r} is not a known part id and is not "
                  f"{req!r}'s listed alternate -- skipping")

    computed = round(computed + shipping, 2)
    if abs(computed - total) > 0.02:
        _warn(file, start_line,
              f"reported total ${total:.2f} does not match parts + shipping "
              f"(${computed:.2f}) -- tax/fees aren't itemized in this grammar, so "
              "this is a warning, not an error")

    return dict(site=site, store=store, date=order_date, n_parts=len(part_lines),
                n_subs=len(subs), n_skips=len(skips))


def load_owned():
    """Sum every reported order in inventory/orders/*.md into one owned dict.
    Only *.md is parsed -- inventory/orders/example.md.txt is deliberately
    ignored (see inventory/README.md)."""
    owned = {}
    summaries = []
    if ORDERS_DIR.exists():
        for path in sorted(ORDERS_DIR.glob("*.md")):
            text = path.read_text()
            fences = list(ORDER_FENCE.finditer(text))
            if not fences:
                _fail(path.name, 1,
                      "no ```lego-workshop-order block found -- inventory/orders/ "
                      "should only contain saved order reports")
            for m in fences:
                start_line = text.count("\n", 0, m.start(1)) + 1
                summaries.append(_parse_block(path.name, start_line, m.group(1), owned))
    summaries.sort(key=lambda s: (s["date"], s["site"], s["store"] or ""))
    return owned, summaries


REPORT_SCHEMA = """```lego-workshop-order
site: bricklink            (or: lego-pab)
store: <store name>        (bricklink only)
date: <YYYY-MM-DD>
part: <id> qty <n> color <color> cond <N|U> unit <usd>
skipped: <id> reason <free text>
substituted: <requested-id> -> <bought-id> qty <n> color <color> cond <N|U> unit <usd>
shipping: <usd>
total: <usd>
```"""


# ---------------------------------------------------------------------------
# Colour conventions (optional; see prompt section 3)
# ---------------------------------------------------------------------------

BEAM_LENGTH_COLORS = {"32523": ("red", "3M"), "32316": ("orange", "5M"),
                       "32524": ("yellow", "7M"), "40490": ("green", "9M"),
                       "32525": ("blue", "11M"), "41239": ("white", "13M"),
                       "32278": ("black", "15M")}

ANGLE_COLORS = {"32013": "red", "32034": "orange", "32016": "yellow",
                 "32192": "green", "32015": "blue", "32014": "black"}

FUNCTION_COLORS = {"2780": "black (friction)", "3673": "grey (frictionless)",
                    "43093": "blue (friction)", "3749": "tan (frictionless)",
                    "6558": "blue (friction)", "32556": "tan (frictionless)"}

DEFAULT_COLOR = "any — cheapest available"

COLOR_CONVENTIONS = [
    "## 3. Colour conventions (optional)",
    "",
    "This whole section is optional — a color system some families use so a young",
    "builder can find the right part by sight instead of counting holes. Skip it",
    "completely and buy the cheapest available colour for everything below; no model",
    "needs a particular colour to work.",
    "",
    "If you want it, apply it to every row below whose Colour column names it:",
    "",
    "- **Straight beams** in a length rainbow: 3M red, 5M orange, 7M yellow, 9M green,",
    "  11M blue, 13M white, 15M black.",
    "- **Angle elements** (#1-#6) colour-coded by angle number: #1 red, #2 orange,",
    "  #3 yellow, #4 green, #5 blue, #6 black. (Any consistent assignment works —",
    "  this is just one example.)",
    "- **Pins, bushes and axle pins** keep LEGO's own factory colours, because LEGO",
    "  already encodes function there: black or blue means friction (it grips and",
    "  holds); tan or grey means frictionless (it spins freely). Worth keeping even",
    "  if you skip the rest of this system.",
    "- **Everything else**: cheapest available colour — it isn't functional or",
    "  cosmetic here.",
    "",
]


def _color_for(part):
    if part in BEAM_LENGTH_COLORS:
        color, length = BEAM_LENGTH_COLORS[part]
        return f"{color} ({length} straight beam)"
    if part in ANGLE_COLORS:
        return f"{ANGLE_COLORS[part]} (optional colour system, see section 3)"
    if part in FUNCTION_COLORS:
        return f"LEGO default — {FUNCTION_COLORS[part]}"
    return DEFAULT_COLOR


# ---------------------------------------------------------------------------
# Order-prompt generation
# ---------------------------------------------------------------------------

STORE_META = {
    "bricklink": dict(label="BrickLink", source="bricklink", site_tag="bricklink"),
    "lego": dict(label="LEGO Pick a Brick", source="pick-a-brick", site_tag="lego-pab"),
}


def _next_ten(x):
    return math.ceil(x / 10) * 10


def _budget_guard(rows, label):
    if not rows:
        return None
    est = round(sum(r["line"] for r in rows), 2)
    cap = _next_ten(est * 1.5)
    return (f"Estimated subtotal for **{label}**: ${est:.2f}. Pause and ask before "
            f"continuing if the running subtotal for this section passes ${cap:.2f} "
            "(1.5x the estimate here, rounded up to the next $10).")


def _alternates_note(rows):
    alts = sorted({(r["part"], r["alt"]) for r in rows if r.get("alt")})
    if not alts:
        return ("None of the parts below have a listed alternate. If the exact ID "
                "is unavailable, search by name instead — never guess a "
                "substitute. If it still can't be found, skip it and report why.")
    joined = "; ".join(f"`{a}` and `{b}`" for a, b in alts)
    return (f"The book lists these as interchangeable — either is correct: "
            f"{joined}. No other substitutions: if an exact ID is unavailable, "
            "search by name, and if it still can't be found, skip it and report "
            "— never guess a substitute.")


def _extra_note(row):
    """A per-part note worth surfacing as its own bullet, or None if the note
    is fully covered elsewhere (the alternates sentence above, or the
    'check your household bin' framing of the optional section)."""
    note = row.get("note")
    if not note or row["source"] == "any-lego-bin":
        return None
    alt = row.get("alt")
    if alt and note.strip() == f"The book lists #{alt} as an equally acceptable alternate.":
        return None
    return note


def _part_notes(rows):
    notes = [f"- `{r['part']}`: {n}" for r in rows for n in [_extra_note(r)] if n]
    return notes + [""] if notes else []


def _rows_table(rows, with_pab_url):
    header = ["Part", "Name", "Buy qty", "Colour", "Already own", "Est. price"]
    if with_pab_url:
        header.append("Pick a Brick search")
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for r in rows:
        cells = [f"`{r['part']}`", r["name"], str(r["qty"]), _color_for(r["part"]),
                  str(r["have"]), f"${r['line']:.2f}"]
        if with_pab_url:
            cells.append(f"[search]({r['pab_url']})")
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def _worked_example(site_tag, rows):
    """A worked lego-workshop-order block, derived from this prompt's own real
    rows so the arithmetic is exact. Fully synthetic store/date -- no real
    seller name or order number."""
    pool = rows if len(rows) >= 2 else (rows * 2 if rows else
           [dict(part="12345", qty=1, price_est=0.50),
            dict(part="67890", qty=2, price_est=0.25)])
    a, b = pool[0], pool[1]
    conds = ("U", "N") if site_tag == "bricklink" else ("N", "N")
    parts_cost = round(a["qty"] * a["price_est"] + b["qty"] * b["price_est"], 2)
    shipping = 4.25 if site_tag == "bricklink" else 0.00
    total = round(parts_cost + shipping, 2)
    lines = ["```lego-workshop-order", f"site: {site_tag}"]
    if site_tag == "bricklink":
        lines.append("store: ExampleBrickStore")   # fictional -- never a real seller
    lines += [f"date: {EXAMPLE_DATE}",
              f"part: {a['part']} qty {a['qty']} color black cond {conds[0]} "
              f"unit {a['price_est']:.2f}",
              f"part: {b['part']} qty {b['qty']} color black cond {conds[1]} "
              f"unit {b['price_est']:.2f}",
              f"shipping: {shipping:.2f}", f"total: {total:.2f}", "```"]
    return lines


def build_prompt(store_key, scope, owned):
    meta = STORE_META[store_key]
    all_rows = rows_for_scope(scope, owned)
    needed = sorted([r for r in all_rows if r["source"] == meta["source"]],
                     key=lambda r: (r["group"], r["name"]))
    optional = sorted([r for r in all_rows if r["source"] == "any-lego-bin"],
                       key=lambda r: (r["group"], r["name"]))
    with_pab = store_key == "lego"
    title = scope_title(scope)
    label = meta["label"]

    L = [f"# Order prompt — {label} — {title}", "",
         "**Generated by `src/generate.py`. Do not edit by hand — run `make`.**", "",
         "*Parent: copy everything below this line into a fresh Claude-in-the-browser "
         "session (or upload/print this file). The prompt is self-contained.*", "",
         "---", "", "## 1. Mission", "",
         f"You are gathering **all** the parts needed to build every model in "
         f"{_book_phrase(scope)}, published by No Starch Press. The parts below are "
         f"the current gap between what the book(s) need and what this family "
         f"already owns, to fill at {label}.", "",
         "**Build the cart (or wanted list) but never pay and never place the "
         "order.** Stop at the final checkout review screen with everything loaded, "
         "so a parent can look it over and pay by hand. Then report back — "
         "section 5 below is the exact format, and it matters: a parent will paste "
         "it back into this project.", "",
         "## 2. Ground rules", "",
         "- Cheapest colour unless the Colour column below says otherwise.",
         "- " + _alternates_note(needed + optional),
         "- Budget guards, computed from this prompt's own estimates: pause and ask "
         "if any single lot's actual price is more than 2x its estimated price "
         "above, or $8, whichever is larger. Section-level guards are noted under "
         "each table."]

    if store_key == "bricklink":
        L += ["- Used condition is welcome, and usually preferred — typically "
              "about 40% cheaper than new. Prefer a lot in used condition whenever a "
              "seller has enough quantity in one lot; fall back to new otherwise.",
              "- Prefer ONE store in the United States that covers as much of the "
              "list as possible, to minimize the number of shipping fees. If one "
              "store cannot fill everything, a second small order is fine — just "
              "don't pay four shipping fees to save four postage-free parts."]
    else:
        L += ["- Price on Pick a Brick does not change with colour, so always "
              "choose the colour instructed below, never \"whatever's cheapest\" "
              "— unless the Colour column literally says "
              "\"any — cheapest available\".",
              "- Search by the design ID in the Part column, or use the "
              "ready-made search link in the last column.",
              "- Use a US Pick a Brick store/region so pricing and stock match the "
              "estimates above."]
    L.append("")
    L += COLOR_CONVENTIONS
    L += ["## 4. The parts", ""]

    if needed:
        L += [f"### Needed — {title}", ""]
        L += _rows_table(needed, with_pab)
        L += ["", "*Rounding a lot up a piece or two for a price break is fine.*", ""]
        L += _part_notes(needed)
        guard = _budget_guard(needed, f"Needed — {title}")
        if guard:
            L += [guard, ""]
    else:
        L += [f"Nothing needed here right now — every {label} part for "
              f"{title} is already covered. \U0001f389", ""]

    if optional:
        L += ["### Optional — check your household LEGO bin first", "",
              "These are ordinary bricks and plates almost every LEGO collection "
              "already has. **Check at home first and buy only what you can't "
              "find** — don't order anything in this section sight unseen.", ""]
        L += _rows_table(optional, with_pab)
        L += ["", "*Rounding a lot up a piece or two for a price break is fine.*", ""]
        L += _part_notes(optional)
        guard = _budget_guard(optional, "Optional — household bin check")
        if guard:
            L += [guard, ""]

    example = _worked_example(meta["site_tag"], needed + optional)
    L += ["## 5. Report back — required format", "",
          "When you are done (cart built, nothing paid), end your reply with "
          "exactly one fenced block like this per store/site you used. A parent "
          "pastes this block back into this project, so the format must be "
          "followed exactly — one `part:` line per lot bought, "
          "`skipped:`/`substituted:` lines only where they happened, `cond` "
          "always `N` for lego-pab:", "",
          REPORT_SCHEMA, "", "For example:", ""] + example + [
          "", "*Trimmed for readability — a real report lists every lot "
          "actually bought.*", ""]

    (PROMPTS / f"order-prompt-{store_key}-{scope}.md").write_text("\n".join(L) + "\n")
    return len(needed), len(optional)


# ---------------------------------------------------------------------------
# BrickLink wanted-list XML
# ---------------------------------------------------------------------------

def write_bricklink_xml(scope, owned):
    all_rows = rows_for_scope(scope, owned)
    rows = sorted([r for r in all_rows if r["source"] in ("bricklink", "any-lego-bin")],
                  key=lambda r: (r["group"], r["name"]))
    title = scope_title(scope)
    lines = ["<!--",
             f"BrickLink Wanted List — {title}",
             "Generated by src/generate.py from data/parts.json + data/books/*.json,",
             "minus everything already reported owned in inventory/orders/.",
             "Quantities are per-model maximums: the most any single model needs at once.",
             "Colour and condition are deliberately unspecified — cheapest lot wins.",
             "",
             "Includes a handful of 'any household LEGO tub' parts too (see README):",
             "uploading them is harmless, and you can always buy fewer than the",
             "wanted-list quantity if you already have some at home.",
             "-->", "<INVENTORY>"]
    for r in rows:
        remark = f"{r['name']} - p.{r['page']}, need {r['want']}, have {r['have']}"
        lines += ["  <ITEM>",
                  "    <ITEMTYPE>P</ITEMTYPE>",
                  f"    <ITEMID>{escape(r['part'])}</ITEMID>",
                  f"    <MINQTY>{r['qty']}</MINQTY>",
                  f"    <REMARKS>{escape(remark)}</REMARKS>",
                  "  </ITEM>"]
    lines.append("</INVENTORY>")
    (EXPORTS / f"bricklink-wanted-{scope}.xml").write_text("\n".join(lines) + "\n")
    return len(rows)


# ---------------------------------------------------------------------------
# Pick a Brick search-helper CSV
# ---------------------------------------------------------------------------

def write_pab_csv(scope, owned):
    all_rows = rows_for_scope(scope, owned)
    rows = sorted([r for r in all_rows if r["source"] == "pick-a-brick"],
                  key=lambda r: (r["group"], r["name"]))
    path = EXPORTS / f"pick-a-brick-{scope}.csv"
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["design_id", "name", "qty", "est_price", "search_url"])
        for r in rows:
            w.writerow([r["part"], r["name"], r["qty"], f"{r['line']:.2f}", r["pab_url"]])
    return len(rows)


# ---------------------------------------------------------------------------
# Printable checklist
# ---------------------------------------------------------------------------

def write_checklist(scope, owned):
    rows = rows_for_scope(scope, owned)
    title = scope_title(scope)
    by_group = {}
    for r in sorted(rows, key=lambda r: (r["group"], r["name"])):
        by_group.setdefault(r["group"], []).append(r)

    L = [f"# Checklist — {title}", "",
         "*Generated by `src/generate.py`. Print this out and check off parts as "
         "they arrive — or just re-run `make` after saving an order report and "
         "get a fresh one.*", ""]

    grand_pieces = grand_lots = 0
    grand_cost = 0.0
    for group in sorted(by_group):
        group_rows = by_group[group]
        L.append(f"## {group}")
        L.append("")
        sub_pieces = 0
        sub_cost = 0.0
        for r in group_rows:
            L.append(f"- [ ] {r['part']} — {r['name']} ×{r['qty']} "
                      f"(~${r['line']:.2f})")
            sub_pieces += r["qty"]
            sub_cost += r["line"]
        L += ["", f"*Subtotal: {sub_pieces} pieces, ${sub_cost:.2f}*", ""]
        grand_pieces += sub_pieces
        grand_cost += sub_cost
        grand_lots += len(group_rows)

    if not by_group:
        L += [f"Nothing left to buy for {title} — every part is covered! "
              "\U0001f389", ""]
    else:
        L += [f"**Grand total remaining: {grand_pieces} pieces across "
              f"{grand_lots} lots, ~${grand_cost:.2f}**", ""]

    (CHECKLISTS / f"checklist-{scope}.md").write_text("\n".join(L))
    return grand_lots


# ---------------------------------------------------------------------------
# STATUS.md
# ---------------------------------------------------------------------------

def write_status(owned, order_summaries):
    any_owned = any(v > 0 for v in owned.values())
    L = ["# STATUS", "",
         "*Generated by `src/generate.py` — do not edit by hand. Run `make` to "
         "refresh after saving a new order report.*", ""]

    if not any_owned:
        L += ["You're at the very beginning — nothing has been ordered yet. "
              "That's exactly where every family starts. Pick a book below, open "
              "its order prompt, and get shopping. \U0001f9f1", ""]

    for scope in BOOK_ORDER:
        need = need_for_scope(scope)
        listed = [(p, q) for p, q in need.items() if q > 0]
        total_parts = len(listed)
        covered_parts = sum(1 for p, q in listed if owned.get(p, 0) >= q)
        total_pieces = sum(q for _, q in listed)
        covered_pieces = sum(min(owned.get(p, 0), q) for p, q in listed)
        remaining_cost = sum(max(0, q - owned.get(p, 0)) * books.PARTS[p]["price_est"]
                              for p, q in listed)
        pct_parts = round(100 * covered_parts / total_parts) if total_parts else 100
        pct_pieces = round(100 * covered_pieces / total_pieces) if total_pieces else 100

        rows = rows_for_scope(scope, owned)
        pointers = []
        if any(r["source"] == "bricklink" for r in rows):
            pointers.append(f"`prompts/order-prompt-bricklink-{scope}.md`")
        if any(r["source"] == "pick-a-brick" for r in rows):
            pointers.append(f"`prompts/order-prompt-lego-{scope}.md`")
        pointer_text = (" and ".join(pointers) if pointers else
                         "nothing — every part for this book is covered! \U0001f389")

        title = books.BOOKS[scope]["meta"]["title"]
        L += [f"## {title}", "",
              f"- Parts fully covered: {covered_parts} / {total_parts} ({pct_parts}%)",
              f"- Pieces covered: {covered_pieces} / {total_pieces} ({pct_pieces}%)",
              f"- Remaining estimated cost: ${remaining_cost:.2f}",
              f"- Next order: {pointer_text}", ""]

    # "Both books combined" is NOT the sum of the two sections above -- it's
    # the 'both' scope's own peak-based need (the most either book asks for
    # at once), which is cheaper: buying to the peak once covers both books,
    # instead of buying each book's own requirement separately.
    need_both = need_for_scope("both")
    listed_both = [(p, q) for p, q in need_both.items() if q > 0]
    total_pieces_both = sum(q for _, q in listed_both)
    covered_pieces_both = sum(min(owned.get(p, 0), q) for p, q in listed_both)
    remaining_cost_both = sum(max(0, q - owned.get(p, 0)) * books.PARTS[p]["price_est"]
                               for p, q in listed_both)
    combined_pct = (round(100 * covered_pieces_both / total_pieces_both)
                     if total_pieces_both else 100)
    L += ["## Both books combined", "",
          f"- Pieces covered: {covered_pieces_both} / {total_pieces_both} "
          f"({combined_pct}%)",
          f"- Remaining estimated cost: ${remaining_cost_both:.2f}",
          "- This is cheaper than the two totals above added together: buying to "
          "the higher of the two books' per-model needs, once, covers both books "
          "at the same time.",
          "- Fastest path: `prompts/order-prompt-bricklink-both.md` and "
          "`prompts/order-prompt-lego-both.md` cover the shortfall for either "
          "book in one pass.", ""]

    L += ["## Recent order activity", ""]
    if not order_summaries:
        L += ["No order reports saved yet. See `inventory/README.md` for how the "
              "tracking loop works.", ""]
    else:
        L += [f"{len(order_summaries)} order report(s) applied from "
              "`inventory/orders/`:", ""]
        for s in order_summaries:
            store = f" at {s['store']}" if s["store"] else ""
            L.append(f"- {s['date']} — {s['site']}{store}: {s['n_parts']} lot(s), "
                      f"{s['n_subs']} substitution(s), {s['n_skips']} skipped")
        L.append("")

    (ROOT / "STATUS.md").write_text("\n".join(L))


# ---------------------------------------------------------------------------

def main():
    PROMPTS.mkdir(exist_ok=True)
    EXPORTS.mkdir(exist_ok=True)
    CHECKLISTS.mkdir(exist_ok=True)

    owned, order_summaries = load_owned()

    for scope in SCOPES:
        for store_key in ("bricklink", "lego"):
            build_prompt(store_key, scope, owned)
        write_bricklink_xml(scope, owned)
        write_pab_csv(scope, owned)
        write_checklist(scope, owned)

    write_status(owned, order_summaries)

    total_owned_pieces = sum(owned.values())
    print(f"generated 6 prompts + 6 exports + 3 checklists + STATUS.md for "
          f"{len(SCOPES)} scopes; {len(order_summaries)} order report(s) parsed, "
          f"{total_owned_pieces} pieces owned across {len(owned)} part types")


if __name__ == "__main__":
    main()
