#!/usr/bin/env bash
# Amorçage d'un conteneur neuf pour la chaîne de prospection (sessions planifiées).
# Idempotent : ne refait que ce qui manque. Durée : 1 à 4 min la première fois.
set -euo pipefail
VENV="${VENV:-/home/user/.venv-webtest}"
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$VENV/ms-playwright}"
if [ ! -x "$VENV/bin/python" ]; then python3 -m venv "$VENV"; fi
"$VENV/bin/python" -m pip install -q --upgrade pip >/dev/null
"$VENV/bin/python" -m pip install -q "playwright==1.64.1" requests beautifulsoup4 lxml
if ! ls "$PLAYWRIGHT_BROWSERS_PATH" 2>/dev/null | grep -q '^chromium-'; then
  "$VENV/bin/python" -m playwright install chromium
fi
# Lighthouse (npx le télécharge au premier appel) et Chromium pour Lighthouse
export CHROME_PATH="${CHROME_PATH:-/opt/pw-browsers/chromium-1243/chrome-linux64/chrome}"
if [ ! -x "$CHROME_PATH" ]; then
  CHROME_PATH="$(ls -d "$PLAYWRIGHT_BROWSERS_PATH"/chromium-*/chrome-linux*/chrome 2>/dev/null | head -1 || true)"
  echo "CHROME_PATH=$CHROME_PATH"
fi
command -v jq >/dev/null 2>&1 || { apt-get install -y -q jq >/dev/null 2>&1 || true; }
"$VENV/bin/python" - <<'PY'
import playwright, requests, bs4, lxml, importlib.metadata as m
print("python deps ok, playwright", m.version("playwright"))
PY
PLAYWRIGHT_BROWSERS_PATH="$PLAYWRIGHT_BROWSERS_PATH" "$VENV/bin/python" - <<'PY'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True); print("chromium ok", b.version); b.close()
PY
echo "bootstrap ok"
