# BT MFG Capacity-New — Project Wiki

## What This Is

Two separate tools living in the same folder (`btmfg-capacity-new`):

| Tool | How it runs | Where you see it |
|------|-------------|------------------|
| **Capacity Dashboard** | Flask app, local only | `http://localhost:8765/` |
| **Value Dashboard** | Static site, auto-pushed to GitHub Pages | `https://<your-github-username>.github.io/btmfg-capacity/` |

---

## Tool 1 — Capacity Dashboard (Flask)

**What it does:** Reads the "Job Trackers BT MFG" Trello board live, groups cards by column (= machine), and shows queued hours + days-at-capacity with traffic-light status (green/yellow/red). Auto-refreshes every minute.

**How to run:** Double-click `start.command` (or run it in Terminal). First run creates a Python venv and installs dependencies automatically.

**Key files:**
- `app.py` — Flask web server, exposes `/api/capacity`
- `capacity.py` — math: computes load per Trello column
- `trello_client.py` — thin Trello REST API wrapper
- `templates/capacity.html` — the dashboard UI

**How it calculates hours per card:**
Looks for Trello Custom Fields on each card:
- **Setup** → field named something like "setup min", "setup time"
- **Cycle** → "cycle min", "minutes per part", "cycle"
- **Qty** → "qty", "quantity", "count"

Formula: `minutes = setup + (cycle × qty)`

If no cycle field is set, falls back to `DEFAULT_MIN_PER_CARD` (default: 60 min).

---

## Tool 2 — Value Dashboard (GitHub Pages)

**What it does:** Pulls every active Trello card, finds the matching Sun Automation PO PDF (via Gmail or a local folder), parses the line-item dollar value, and aggregates totals by machine column and customer. Writes `docs/dashboard.json`, commits, and pushes to GitHub — GitHub Pages serves the static site.

**How it updates:** A macOS launchd job runs `update_dashboard.py` on a schedule (set in `launchd/com.btmfg.dashboard.plist`). Each run fetches fresh data and pushes a new commit.

**Key files:**
- `update_dashboard.py` — main script: fetches Trello → Gmail → parses PDFs → writes `docs/` → git push
- `gmail_client.py` — Gmail API wrapper (OAuth)
- `po_source.py` — finds PO PDFs (Gmail first, local folder fallback)
- `value.py` — part number normalization helpers
- `docs/` — static site files served by GitHub Pages
  - `dashboard.json` — latest data snapshot
  - `last_updated.json` — freshness file
  - `index.html` — dashboard UI
  - `auth.js` — password hash (if `DASHBOARD_PASSWORD` is set in `.env`)

**Card naming convention:** Cards must be named `SUN PO {number} Line {n}` (e.g., "SUN PO 351934 Line 2") for the value lookup to work.

---

## Related Folders

| Folder | What it is |
|--------|------------|
| `btmfg-capacity-new/` | **This project** — active |
| `btmfg-automation/` | Original toolkit: PO intake, drawing annotation, shop paperwork printing, Trello card processing |
| `btmfg-capacity/` | Older/earlier capacity dashboard iteration |

---

## Setup Checklist

Work through these in order. You can pause between any step.

### ✅ Step 0 — Make scripts executable
```bash
cd ~/Documents/Claude/btmfg-capacity-new
chmod +x setup_dashboard.command setup_github.command start.command
```

### 🔄 Step 1 — GitHub CLI login *(in progress)*
```bash
brew install gh    # if not already installed
gh auth login
# Choose: GitHub.com → HTTPS → Login with a web browser
# Paste the 8-character code shown in Terminal into the browser
```
Verify it worked: `gh auth status`

### ⬜ Step 2 — Push to GitHub + enable Pages
```bash
open setup_github.command
```
Then on github.com:
1. Open the new repo → **Settings → Pages**
2. Source: **Deploy from a branch**, Branch: **main**, Folder: **/docs**
3. Save — site goes live at `https://<your-username>.github.io/btmfg-capacity/` within ~2 min

> Note: GitHub Pages on private repos requires GitHub Pro. If you don't have it, either make the repo public or use Cloudflare Pages instead.

### ⬜ Step 3 — Trello credentials
1. Go to https://trello.com/power-ups/admin
2. Create (or use existing) Power-Up — name it "BTMFG Automation"
3. Copy the **API key** (32-char hex)
4. Click the **Token** link → Authorize → copy the token
5. Paste both into `.env`:
```
TRELLO_API_KEY=your_key_here
TRELLO_TOKEN=your_token_here
```

Smoke test:
```bash
cd ~/Documents/Claude/btmfg-capacity-new
.venv/bin/python -c "
from dotenv import load_dotenv; import os
from trello_client import TrelloClient
load_dotenv()
t = TrelloClient(os.environ['TRELLO_API_KEY'], os.environ['TRELLO_TOKEN'])
for l in t.lists(os.environ.get('TRELLO_BOARD_ID','YG0Dh7Kp')): print(l['name'])
"
```
Should print your Trello board's column names.

### ⬜ Step 4 — Gmail OAuth (~20 min, one-time)
1. Sign in to https://console.cloud.google.com/ with `ben@btmfg.net`
2. Create project: `btmfg-dashboard`
3. Enable **Gmail API**
4. OAuth consent screen: External, app name "BTMFG Dashboard", add `ben@btmfg.net` as test user
5. Create **OAuth client ID** → Desktop app → download JSON
6. Rename and move it:
   ```bash
   mv ~/Downloads/client_secret_*.json ~/Documents/Claude/btmfg-capacity-new/gmail_credentials.json
   ```
7. Run the OAuth dance (opens a browser to authorize):
   ```bash
   cd ~/Documents/Claude/btmfg-capacity-new
   .venv/bin/python -c "from gmail_client import GmailClient; GmailClient()._service(); print('ok')"
   ```
   If you see "This app isn't verified" → click **Advanced → Go to BTMFG Dashboard (unsafe)** → authorize.

### ⬜ Step 5 — Wire up the cron + first build
```bash
open setup_dashboard.command
```
This installs deps, loads the launchd job, runs `update_dashboard.py` once, and pushes to GitHub.

---

## Configuration (`.env` file)

| Variable | Default | Purpose |
|----------|---------|---------|
| `TRELLO_API_KEY` | — | Required |
| `TRELLO_TOKEN` | — | Required |
| `TRELLO_BOARD_ID` | `YG0Dh7Kp` | Job Trackers BT MFG board |
| `DEFAULT_MIN_PER_CARD` | `60` | Fallback minutes when cycle field is blank |
| `HOURS_PER_DAY` | `8` | For days-at-capacity math |
| `THRESH_YELLOW_HRS` | `32` | Queue hours → yellow warning |
| `THRESH_RED_HRS` | `80` | Queue hours → red/overloaded |
| `PORT` | `8765` | Local Flask port |
| `LOCAL_PO_DIR` | — | Optional local folder of PO PDFs (fallback if Gmail is down) |
| `EXCLUDE_LISTS` | `Shipped,Done,Complete,Archived,Archive` | Columns excluded from value totals |
| `DASHBOARD_PASSWORD` | — | Optional password gate on GitHub Pages site |

---

## Useful Commands

```bash
# Start the local capacity dashboard
open ~/Documents/Claude/btmfg-capacity-new/start.command

# Run a manual value dashboard update
cd ~/Documents/Claude/btmfg-capacity-new
.venv/bin/python update_dashboard.py

# Check launchd cron status
launchctl print gui/$(id -u)/com.btmfg.dashboard | head -40

# Watch cron logs live
tail -f ~/Documents/Claude/btmfg-capacity-new/launchd/out.log \
        ~/Documents/Claude/btmfg-capacity-new/launchd/err.log

# Stop the cron job
launchctl bootout gui/$(id -u)/com.btmfg.dashboard
rm ~/Library/LaunchAgents/com.btmfg.dashboard.plist
```

---

## Architecture Diagram

```
Trello Board (Job Trackers BT MFG)
    │
    ├─► Capacity Dashboard (Flask, localhost:8765)
    │       Reads live on each page load
    │       Grouped by column → hours queued → traffic light
    │
    └─► update_dashboard.py  (launchd cron)
            │
            ├─ Gmail API → finds Sun PO PDFs
            ├─ Local folder (fallback)
            └─ Parses PDF line items → dollar values
                    │
                    └─► docs/dashboard.json → git push → GitHub Pages
                            https://<you>.github.io/btmfg-capacity/
```
