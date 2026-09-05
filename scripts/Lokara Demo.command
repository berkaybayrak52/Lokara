#!/usr/bin/env bash
# The one-click entry point for the local demo. Double-click this (or its Desktop
# alias) and Terminal opens, brings the stack up and lands on the demo in Chrome.
#
# It is a thin wrapper: all the real work -- Docker, lokara-db, the API, the web
# server and their health checks -- lives in scripts/dev.sh, which is idempotent.
# Clicking twice re-checks and changes nothing.
#
# The browser is opened only after dev.sh reports success, and always on "/", because
# PortalEntry sets the session cookie there. Jumping straight into /a/<account>
# without it gives 401s and an empty page (DEMO-RUNBOOK.md).

cd "$(dirname "$0")/.."

printf '\033]0;Lokara Demo\007'   # window title, so the Terminal tab is identifiable
clear

if ./scripts/dev.sh start; then
  open "http://localhost:3000/"
  printf '\n\033[2mBrowser geöffnet. Fenster kann geschlossen werden — der Stack läuft weiter.\n'
  printf 'Stoppen:  scripts/dev.sh stop\033[0m\n'
else
  printf '\n\033[31mStart fehlgeschlagen.\033[0m Logs:  scripts/dev.sh logs\n'
  printf '\033[2mFenster offen lassen und die Meldung oben lesen.\033[0m\n'
  read -r -p "Enter zum Schließen "
fi
