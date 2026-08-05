# Yoshihito Isogawa Inventory

Everything a parent needs to gather the LEGO Technic parts for Yoshihito
Isogawa's *LEGO Technic Non-Electric Models* books — starting from zero,
with no LEGO Technic collection, no spreadsheet, and no need to know how to
code. The whole workflow is built around **Claude in the browser**: you copy
a file from this repo into a chat, it shops for you and stops before paying,
you paste its report back, and this repo keeps score. Everything you need is
a file you can copy, upload, or print — nothing here requires running a
command.

## Step 0: get the books

This repo tracks parts for two books, both by Yoshihito Isogawa, published
by No Starch Press:

| | Simple Machines | Clever Contraptions |
|---|---|---|
| Full title | *LEGO Technic Non-Electric Models: Simple Machines* | *LEGO Technic Non-Electric Models: Clever Contraptions* |
| Models | 141 | 106 |
| ISBN | 978-1-7185-0120-1 | 978-1-7185-0170-6 |
| No Starch Press | [nostarch.com/nonelectric_simplemachines](https://nostarch.com/nonelectric_simplemachines) | [nostarch.com/nonelectric_clevercontraptions](https://nostarch.com/nonelectric_clevercontraptions) |
| Amazon | [LEGO Technic Idea Book, Non-Electric](https://www.amazon.com/LEGO-Technic-Idea-Book-Non-Electric/dp/171850120X) | [LEGO Technic Non-Electric Models: Clever Contraptions](https://www.amazon.com/LEGO-Technic-Non-Electric-Models-Contraptions/dp/1718501706) |

**Buy the books.** This repo only helps you gather the parts to build what's
inside them — the books themselves are the whole point, and neither this
project nor anything in it substitutes for owning them.

## Fastest path

1. **Pick your book** — Simple Machines, Clever Contraptions, or both.
2. **Open the matching file in `prompts/`** and copy its entire contents.
   There are six, one per book per store:

   | | BrickLink | LEGO Pick a Brick |
   |---|---|---|
   | Simple Machines | `prompts/order-prompt-bricklink-simple-machines.md` | `prompts/order-prompt-lego-simple-machines.md` |
   | Clever Contraptions | `prompts/order-prompt-bricklink-clever-contraptions.md` | `prompts/order-prompt-lego-clever-contraptions.md` |
   | Both books | `prompts/order-prompt-bricklink-both.md` | `prompts/order-prompt-lego-both.md` |

   Not sure which? Start with the two `-both.md` prompts — they cover
   everything either book needs in one pass.
3. **Paste it into a fresh Claude-in-the-browser session.** Each prompt is
   completely self-contained — it explains the mission, the ground rules,
   and exactly what to buy. Claude will shop that store, build a cart or
   wanted list, and **stop before paying** — it never checks out. You review
   and pay by hand.
4. **Ask it to finish with its report** if it doesn't already (the prompt
   asks for this automatically) — a small fenced block summarizing what it
   bought, skipped, or substituted.
5. **Save that block** into a new file in `inventory/orders/` — any
   filename ending in `.md` works, e.g. `inventory/orders/2026-08-04.md`.
6. **Run `make`** — optional. If you know how to run a command in a
   terminal, this updates every prompt, checklist, and `STATUS.md`
   immediately. If you don't, save the file anyway; it'll be picked up the
   next time anyone (including a future Claude session) runs `make` in this
   repo.
7. **Watch `STATUS.md` fill up.** It shows exactly how much of each book you
   now have, and points you at the next prompt to run.

Repeat for your next order. Full details on saving reports, including what
happens if a save doesn't parse, are in
[`inventory/README.md`](inventory/README.md).

## Alternative paths

You don't need a browser agent at all — everything is a plain file.

**Upload to BrickLink directly.** `exports/bricklink-wanted-*.xml` are
ready-made BrickLink Wanted Lists (one per book, plus `-both.xml`). Go to
BrickLink → **Want** → **Upload** → **XML**, and upload the file for your
book. Colour and condition are left open on purpose — for these parts,
whatever's cheapest is fine, and used is fine too. These files also include
a handful of ordinary "any household LEGO tub" parts (see below) — that's
harmless; skip buying anything you already have at home.

**Search LEGO Pick a Brick by hand.** `exports/pick-a-brick-*.csv` list the
design ID, name, quantity, estimated price, and a ready search link for
every part LEGO's own Pick a Brick service is likely to carry.

**Print a checklist.** `checklists/checklist-*.md` are plain checkbox lists,
grouped by part family with subtotals, for anyone who'd rather shop from a
piece of paper (or check off parts as they arrive in the mail) than a
screen.

## What it costs

These are **rough planning estimates only** — BrickLink lot prices and LEGO
Pick a Brick pricing both move, and a small order is mostly shipping
anyway. Always verify at checkout. Figures below are the **cold-start**
total: everything needed, assuming you own nothing yet. Once you start
saving order reports, `STATUS.md` shows your actual remaining cost.

| Book | Estimated cost, from zero |
|---|---|
| Simple Machines, on its own | ~$108 |
| Clever Contraptions, on its own | ~$128 |
| Both books, shopped together (the `-both` prompts) | ~$165 |

Shopping the `-both` prompts costs less than the two books added together
(~$237): most parts are shared, so buying to the higher of the two books'
per-model needs, once, covers both — instead of buying each book's own
requirement separately.

## The optional colour system

Every order prompt includes an optional section: a colour convention some
families use so a young builder can find the right part by sight instead of
counting holes (straight beams in a length rainbow, angle elements
colour-coded by angle, LEGO's own friction-vs-frictionless colours kept on
pins). **It's entirely optional and costs nothing to skip** — buying the
cheapest available colour for everything works exactly as well; no model in
either book needs a particular colour to function.

## Adding another Isogawa book

This repo is built to grow past two books. See
[`docs/transcription-prompt.md`](docs/transcription-prompt.md) for the
complete prompt to hand to Claude, photos of the new book's parts list in
hand — it walks through transcribing the list, adding it to this repo's
data files, and regenerating everything.

## Disclaimer

This is an unofficial, fan-made project, not affiliated with or endorsed by
Yoshihito Isogawa, No Starch Press, or the LEGO Group. See
[`NOTICE.md`](NOTICE.md) for the full disclaimer, including what this repo
does and does not reproduce from the books.

## License

The code and data files in this repository are licensed under the MIT
License — see [`LICENSE`](LICENSE).
