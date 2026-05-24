#!/bin/bash
# One-time helper to push this repo to a new private GitHub repo.
# Requires the `gh` CLI to be installed and authenticated:
#   brew install gh
#   gh auth login

set -e
cd "$(dirname "$0")"

REPO_NAME="${1:-btmfg-capacity}"
VISIBILITY="${2:-private}"

if ! command -v gh >/dev/null 2>&1; then
  echo ""
  echo "  The GitHub CLI ('gh') isn't installed."
  echo "  Install it with: brew install gh"
  echo "  Then run: gh auth login"
  echo "  Then re-run this script."
  echo ""
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo ""
  echo "  You're not signed in to GitHub. Running 'gh auth login'..."
  echo ""
  gh auth login
fi

if [ ! -d ".git" ]; then
  echo "  Initializing git repo..."
  git init -b main
fi

git add .
if git diff --cached --quiet; then
  echo "  Nothing new to commit."
else
  git commit -m "Initial BT MFG capacity dashboard"
fi

if git remote get-url origin >/dev/null 2>&1; then
  echo "  Origin already configured — pushing..."
  git push -u origin main
else
  echo "  Creating GitHub repo '$REPO_NAME' ($VISIBILITY) and pushing..."
  gh repo create "$REPO_NAME" "--$VISIBILITY" --source=. --remote=origin --push
fi

echo ""
echo "  Done. Repo URL:"
gh repo view --json url -q .url
echo ""
echo "  On a new machine:"
echo "    gh repo clone <your-github-username>/$REPO_NAME"
echo "    cd $REPO_NAME"
echo "    cp .env.example .env   # then fill in TRELLO_API_KEY and TRELLO_TOKEN"
echo "    open start.command"
echo ""
