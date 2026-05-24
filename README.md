# BT MFG Capacity Dashboard

A live finite-capacity view of the **Job Trackers BT MFG** Trello board.
Reads cards from Trello, groups them by column (= machine), and shows queued
hours / days-at-capacity per column with traffic-light status. Auto-refreshes
every minute.

Built as a small Flask app so it runs the same way Ben's other shop tools do
(`start.command`), uses a `.env` for credentials, and can be cloned on any
computer he works from.

---

## Quick start (first machine)

```bash
cd btmfg-capacity
cp .env.example .env
# Edit .env: paste your TRELLO_API_KEY and TRELLO_TOKEN
open start.command       # double-click also works
```

The launcher creates a virtualenv on first run, installs dependencies, starts
the server on `http://localhost:8765/`, and opens it in your browser.

## Quick start (new machine)

After running `setup_github.command` once, clone from GitHub on any new PC:

```bash
gh repo clone <your-github-username>/btmfg-capacity
cd btmfg-capacity
cp .env.example .env       # then paste credentials
open start.command
```

---

## What it shows

For each Trello list (machine column):

- Card count
- Queued hours (sum of setup + cycle × qty across cards)
- Days at capacity given your `HOURS_PER_DAY` setting
- Traffic-light status (green / yellow / red) using `THRESH_YELLOW_HRS` / `THRESH_RED_HRS`

Plus a bar chart of hours-per-column and click-through links to each card on
Trello.

## How it estimates hours per card

Looks for three Trello Custom Fields (case-insensitive substring match):

| Concept | Field name hints                          |
|---------|-------------------------------------------|
| Setup   | `setup min`, `setup minutes`, `setup time`, `setup` |
| Cycle   | `cycle min`, `cycle minutes`, `cycle time`, `minutes per part`, `cycle` |
| Qty     | `qty`, `quantity`, `count`                |

For each card: **minutes = setup + cycle × qty**.

If a card has no cycle field set, the dashboard uses `DEFAULT_MIN_PER_CARD`
from `.env` (60 by default) so it always shows *something* useful.

## Setting up Trello credentials

1. Go to <https://trello.com/power-ups/admin>.
2. Either create a new Power-Up (call it "BTMFG Automation") or use your
   existing one.
3. On its admin page, click **API key** — copy the 32-char hex key.
4. Click the **Token** link in the description, then **Allow** on the next
   page. Copy the long token string.
5. Paste both into `.env`.

The API key is treated as public by Trello; the token grants access scoped to
your user. Both live only in `.env`, which is git-ignored.

## Project layout

```
btmfg-capacity/
├── app.py                # Flask app entrypoint
├── trello_client.py      # Thin Trello REST wrapper
├── capacity.py           # Pure functions: compute load per column
├── templates/
│   └── capacity.html     # Dashboard UI
├── static/               # Reserved for assets (none yet)
├── requirements.txt
├── .env.example          # Copy to .env and fill in
├── .gitignore
├── start.command         # macOS launcher
└── setup_github.command  # One-time GitHub setup helper
```

## Adding the rest of the BT MFG toolkit

This repo is the **capacity dashboard** slice. The broader BT MFG automation
toolkit (PO intake, drawing annotation, shop-paperwork printing, workflow
dashboard) lives in a separate folder. To consolidate:

1. Drop those scripts into this repo as additional modules.
2. Register their entry points as new Flask routes (or keep them as separate
   `.command` files alongside).
3. Update this README's project layout section.

The split is intentional for now — keep capacity scoped and tested, expand
the repo as you fold in the rest.

## Configuration knobs

All in `.env`:

| Variable               | Default | Effect                                    |
|------------------------|---------|-------------------------------------------|
| `TRELLO_API_KEY`       | —       | Required. Your Power-Up's API key.        |
| `TRELLO_TOKEN`         | —       | Required. Your authorization token.       |
| `TRELLO_BOARD_ID`      | `YG0Dh7Kp` | Job Trackers BT MFG.                  |
| `DEFAULT_MIN_PER_CARD` | `60`    | Fallback minutes when cycle is blank.     |
| `HOURS_PER_DAY`        | `8`     | For days-at-capacity math.                |
| `THRESH_YELLOW_HRS`    | `32`    | Queue ≥ this → yellow status.             |
| `THRESH_RED_HRS`       | `80`    | Queue ≥ this → red (overloaded) status.   |
| `PORT`                 | `8765`  | Local Flask port.                         |

## Why a Flask app and not the standalone HTML?

The first cut was a standalone `.html` file that called Trello directly from
the browser. Chrome blocks `fetch` from `file://` origins for security, so the
fetch failed. Serving from Flask gives us a real `http://localhost` origin
that Trello's CORS accepts, lets the dashboard pull credentials from `.env`
(no paste step), and matches the pattern of Ben's other shop tools.

## License

Private. Don't redistribute.
