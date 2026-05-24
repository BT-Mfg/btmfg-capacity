# Value dashboard — one-time setup

Follow these once, in order. The numbers are the order you should do them
in; many are independent so you can pause between any step.

---

## 0. Make this folder executable

In Terminal:

```
cd ~/Documents/btmfg-capacity
chmod +x setup_dashboard.command setup_github.command start.command
```

---

## 1. GitHub CLI (`gh`)

Install once via Homebrew, then authenticate.

```
brew install gh           # if you don't already have it
gh auth login
```

Pick **GitHub.com** → **HTTPS** → **Login with a web browser**. It will
open Safari and have you paste an 8-character code. After that, `gh auth
status` should report you're signed in.

---

## 2. Create the private GitHub repo (with Pages)

From inside this folder:

```
open setup_github.command
```

That script creates a private GitHub repo called `btmfg-capacity` and
pushes everything. Then turn Pages on:

1. Open the repo on github.com (`gh browse` is shortest).
2. Settings → Pages.
3. Source: **Deploy from a branch**. Branch: **main**, folder: **/docs**.
4. Save. After a minute, your dashboard will be live at:
   `https://<your-github-username>.github.io/btmfg-capacity/`

(Private repos can host GitHub Pages on free **GitHub Pro** plans. If you
don't have Pro, switch the repo to public OR drop the page on Cloudflare
Pages instead — happy to walk you through that swap.)

---

## 3. Trello API credentials

1. Go to <https://trello.com/power-ups/admin>.
2. **New** → name it "BTMFG Automation" → Workspace: your personal one
   → Create.
3. The new Power-Up's page has an **API key** tab — copy the 32-char hex
   string into `.env` as `TRELLO_API_KEY=`.
4. On that same page, click the **Token** link in the description below
   the key. Authorize the app. Copy the long token string into `.env` as
   `TRELLO_TOKEN=`.

To smoke-test, in the repo folder:

```
.venv/bin/python -c "
from dotenv import load_dotenv; import os
from trello_client import TrelloClient
load_dotenv()
t = TrelloClient(os.environ['TRELLO_API_KEY'], os.environ['TRELLO_TOKEN'])
lists = t.lists(os.environ.get('TRELLO_BOARD_ID','YG0Dh7Kp'))
for l in lists: print(l['name'])
"
```

You should see your board's list names print.

---

## 4. Google Gmail API + OAuth

This is the longest step (~20 min the first time).

### 4a. Create a Google Cloud project

1. Sign in to <https://console.cloud.google.com/> with `ben@btmfg.net`.
2. Top bar → project picker → **New Project**. Name: `btmfg-dashboard`.
   Click **Create** and wait, then select it from the picker.

### 4b. Enable the Gmail API

1. In the search bar, type "Gmail API" → click the result.
2. Click **Enable**.

### 4c. OAuth consent screen

1. Left nav: **APIs & Services** → **OAuth consent screen**.
2. User type: **External** → **Create**.
3. App name: `BTMFG Dashboard`. User support email: your email.
   Developer contact email: your email. **Save and continue**.
4. Scopes: skip (leave default). **Save and continue**.
5. Test users: **Add users** → add `ben@btmfg.net`. **Save and continue**.
6. **Back to dashboard**. You can leave the app in "Testing" mode forever.

### 4d. OAuth client

1. Left nav: **APIs & Services** → **Credentials**.
2. **+ Create credentials** → **OAuth client ID**.
3. Application type: **Desktop app**. Name: `btmfg-dashboard-desktop`.
   Click **Create**.
4. A dialog shows the client ID. Click **Download JSON**.
5. Move that downloaded file into this repo folder and rename it to
   exactly `gmail_credentials.json`:

   ```
   mv ~/Downloads/client_secret_*.json ~/Documents/btmfg-capacity/gmail_credentials.json
   ```

### 4e. First-run OAuth dance

```
cd ~/Documents/btmfg-capacity
.venv/bin/python -c "from gmail_client import GmailClient; GmailClient()._service(); print('ok')"
```

A browser tab will open asking you to sign in to your Google account and
authorize the BTMFG Dashboard app. You may see a "This app isn't
verified" screen — click **Advanced** → **Go to BTMFG Dashboard
(unsafe)**. Authorize it. The terminal prints `ok` and writes
`token.json` (git-ignored).

---

## 5. Wire up the cron + first dashboard build

```
open setup_dashboard.command
```

This will:
- Make sure the venv has all dependencies.
- Render the launchd job from its template and load it.
- Run `update_dashboard.py` once now so `docs/dashboard.json` exists.
- Push to GitHub (which triggers Pages to redeploy).

Your dashboard should be live within 2–3 min at:

```
https://<your-github-username>.github.io/btmfg-capacity/
```

If you set `DASHBOARD_PASSWORD=…` in `.env`, the page prompts for it on
first visit and remembers your answer.

---

## Cron status / logs

```
launchctl print gui/$(id -u)/com.btmfg.dashboard | head -40   # status
tail -f launchd/out.log launchd/err.log                       # live logs
```

To change the schedule, edit `StartInterval` in
`launchd/com.btmfg.dashboard.plist.template`, then re-run
`setup_dashboard.command`.

To stop the cron entirely:

```
launchctl bootout gui/$(id -u)/com.btmfg.dashboard
rm ~/Library/LaunchAgents/com.btmfg.dashboard.plist
```
