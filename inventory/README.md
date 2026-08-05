# The tracking loop

This folder is how the whole repo learns what you've already bought, so the
prompts, checklists and `STATUS.md` stop asking for parts you already own.

You do **not** need to know git, or run anything, to use this. The loop
works entirely by saving text files.

## How it works

1. Shop using one of the files in `prompts/` (see the root `README.md` for
   the full walkthrough). When the shopping agent finishes, it ends its
   reply with a fenced block that starts with:

   ````
   ```lego-workshop-order
   ````

2. Copy that whole fenced block (including the opening and closing lines)
   and save it into a **new file in this folder**, `inventory/orders/`. Any
   filename works, as long as it ends in `.md` — for example
   `inventory/orders/2026-08-04.md` or `inventory/orders/bricklink-order-1.md`.
   You can paste just the block, or the agent's whole reply — only the
   fenced block matters, everything else is ignored.

3. Run `make` (optional — see below).

4. Open `STATUS.md`. It will have shrunk to reflect what you now own. The
   files in `prompts/`, `exports/`, and `checklists/` all update the same
   way.

Repeat after every order. Each new file adds to what you own — it doesn't
replace the old ones, so keep every order as its own file and never edit one
after saving it.

**Don't paste the same order into two different files** — each `part:` line
is counted every time it appears, so the same order pasted twice would count
double.

## About `make`

`make` regenerates everything in this repo from the data plus whatever is in
this folder. Running it is **optional**:

- If you know how to run a command in a terminal, run `make` after saving an
  order file, and everything (prompts, checklists, exports, `STATUS.md`)
  updates immediately.
- If you don't, that's fine — save the file anyway. The next time anyone
  runs `make` (including a future Claude session working in this repo), it
  will pick up every order file you've saved and catch up all at once.

Nothing here requires committing to git either. If you do use git, commit
`inventory/orders/<your new file>` along with the regenerated `STATUS.md`,
`prompts/`, `exports/`, and `checklists/` so the history stays in sync.

## What's in this folder

| File | What it is |
|---|---|
| `orders/example.md.txt` | A **fictional** worked example (see the file itself). Ends in `.md.txt`, not `.md`, so the generator ignores it — it never counts toward what you own. |
| `orders/.gitkeep` | Keeps this folder tracked in git even before you've saved a real order. Harmless — ignore it. |
| `orders/<your files>` | Your real saved order reports, once you start shopping. |

## The report format, if you're curious

Every order report is a handful of plain-text lines inside a fenced block.
The prompts always produce it in exactly this shape:

```
site: bricklink            (or: lego-pab)
store: <store name>        (bricklink only)
date: <YYYY-MM-DD>
part: <id> qty <n> color <color> cond <N|U> unit <usd>
skipped: <id> reason <free text>
substituted: <requested-id> -> <bought-id> qty <n> color <color> cond <N|U> unit <usd>
shipping: <usd>
total: <usd>
```

- One `part:` line per lot actually bought.
- `skipped:` lines are recorded (so you know what's still missing) but don't
  count as owned.
- `substituted:` lines credit the part the book actually asks for
  (`<requested-id>`) when `<bought-id>` is its listed alternate; otherwise
  they credit whatever was actually bought, if it's a recognized part.
- If a saved file doesn't match this shape, `make` stops with an error
  naming the exact file and line — it never silently miscounts. If that
  happens, check the file against the example above, fix the line, and run
  `make` again.
