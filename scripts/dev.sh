#!/usr/bin/env bash
# The local demo stack as one command -- and what the LaunchAgent runs at login.
#
#   Docker Desktop -> lokara-db :54322 -> FastAPI :3001 -> Next.js :3000
#
# Why this exists: after a reboot none of the three came back on their own. The
# Postgres container has `restart: unless-stopped` and survives, but Docker Desktop
# itself does not start headless, and the API and web are plain foreground processes
# that die with their terminal. The result looked like a broken demo when it was only
# an unstarted one.
#
# Usage:
#   scripts/dev.sh [start]      bring everything up; wait until each part answers
#   scripts/dev.sh stop         stop api and web (the db keeps its restart policy)
#   scripts/dev.sh restart      stop, then start
#   scripts/dev.sh status       what is up, what is not
#   scripts/dev.sh logs [api|web]   tail a log (default: both, interleaved)
#
# Idempotent on purpose: running `start` against a live stack re-checks health and
# changes nothing. The LaunchAgent may fire it when things are already up.
#
# This never touches Supabase and never runs migrations or the seed. It starts what
# is already there. For a clean database use scripts/verify_demo_path.sh --fresh.

set -uo pipefail

cd "$(dirname "$0")/.."
ROOT="$PWD"

# A LaunchAgent inherits almost no PATH, and uv/bun/docker all live under $HOME here.
# Absolute-safe order: user tools first, then Homebrew (both arches), then the base.
export PATH="$HOME/.local/bin:$HOME/.bun/bin:$HOME/.docker/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# docs/01 D9: ApiSettings deliberately has no default for ENVIRONMENT, so the API
# refuses to start without it. Same value scripts/gate.sh exports.
export ENVIRONMENT="${ENVIRONMENT:-local}"

RUN_DIR="$ROOT/.dev"
LOG_DIR="$RUN_DIR/logs"
mkdir -p "$LOG_DIR"

API_PORT=3001   # lokara_api.main:run -> ApiSettings().api_port
WEB_PORT=3000   # apps/web package.json -> next dev --port 3000

# --- small helpers -------------------------------------------------------------------

BOLD=$'\033[1m'; GREEN=$'\033[32m'; RED=$'\033[31m'; DIM=$'\033[2m'; OFF=$'\033[0m'

say()  { printf '%s\n' "$*"; }
step() { printf '  %-34s' "$*"; }
ok()   { printf '%s%s%s\n' "$GREEN" "${1:-ok}" "$OFF"; }
bad()  { printf '%s%s%s\n' "$RED" "${1:-FAILED}" "$OFF"; }

port_pid() { lsof -nP -iTCP:"$1" -sTCP:LISTEN -t 2>/dev/null | head -1; }
listening() { [[ -n "$(port_pid "$1")" ]]; }

# Wait for a command to succeed, or give up. wait_for <seconds> <command...>
wait_for() {
  local deadline=$(( SECONDS + $1 )); shift
  until "$@" >/dev/null 2>&1; do
    (( SECONDS >= deadline )) && return 1
    sleep 1
  done
  return 0
}

# --- the parts -----------------------------------------------------------------------

start_docker() {
  step "Docker daemon"
  if docker info >/dev/null 2>&1; then ok "already running"; return 0; fi
  open -a Docker >/dev/null 2>&1 || { bad "cannot launch Docker Desktop"; return 1; }
  if wait_for 120 docker info; then ok "started"; else bad "timeout after 120s"; return 1; fi
}

db_healthy() {
  [[ "$(docker inspect -f '{{.State.Health.Status}}' lokara-db 2>/dev/null)" == "healthy" ]]
}

start_db() {
  step "lokara-db :54322"
  # `compose up` errors out when the container already exists but is merely stopped --
  # exactly the post-reboot case. Start it by name first, fall back to compose when the
  # container is genuinely absent.
  if ! docker start lokara-db >/dev/null 2>&1; then
    docker compose up -d db >/dev/null 2>&1 || { bad "compose up failed"; return 1; }
  fi
  if wait_for 60 db_healthy; then ok "healthy"; else bad "not healthy after 60s"; return 1; fi
}

start_api() {
  step "API :$API_PORT"
  if listening "$API_PORT"; then ok "already up"; return 0; fi
  ( cd "$ROOT" && nohup uv run lokara-api >>"$LOG_DIR/api.log" 2>&1 & echo $! >"$RUN_DIR/api.pid" )
  if wait_for 90 curl -sf "http://127.0.0.1:$API_PORT/health"; then
    ok "/health 200"
  else
    bad "no /health after 90s"; say "    ${DIM}see $LOG_DIR/api.log${OFF}"; return 1
  fi
}

start_web() {
  step "Web :$WEB_PORT"
  if listening "$WEB_PORT"; then ok "already up"; return 0; fi
  ( cd "$ROOT/apps/web" && nohup bun run dev >>"$LOG_DIR/web.log" 2>&1 & echo $! >"$RUN_DIR/web.pid" )
  if wait_for 120 curl -sf -o /dev/null "http://localhost:$WEB_PORT/"; then
    ok "ready"
  else
    bad "no response after 120s"; say "    ${DIM}see $LOG_DIR/web.log${OFF}"; return 1
  fi
}

stop_one() {
  local name="$1" port="$2" pidfile="$RUN_DIR/$1.pid"
  step "$name"
  local pid; pid="$(port_pid "$port")"
  if [[ -z "$pid" ]]; then ok "not running"; rm -f "$pidfile"; return 0; fi
  # The listener is the child (next-server / uvicorn); kill its group so bun's and
  # uv's wrappers go with it instead of respawning.
  kill "$pid" 2>/dev/null
  [[ -f "$pidfile" ]] && kill "$(cat "$pidfile")" 2>/dev/null
  local deadline=$(( SECONDS + 10 ))
  while listening "$port"; do
    (( SECONDS >= deadline )) && { kill -9 "$pid" 2>/dev/null; break; }
    sleep 1
  done
  rm -f "$pidfile"
  ok "stopped"
}

# --- commands ------------------------------------------------------------------------

cmd_start() {
  say "${BOLD}Lokara — local demo stack${OFF}"
  start_docker || exit 1
  start_db     || exit 1
  start_api    || exit 1
  start_web    || exit 1
  say ""
  say "  Demo:  ${BOLD}http://localhost:$WEB_PORT/${OFF}"
  say "  ${DIM}Start on / so PortalEntry sets the session cookie; it lasts one hour."
  say "  Jumping straight to /a/<account> without it gives 401s and an empty page.${OFF}"
}

cmd_stop() {
  say "${BOLD}Stopping${OFF} ${DIM}(the database keeps running -- it is shared and cheap)${OFF}"
  stop_one web "$WEB_PORT"
  stop_one api "$API_PORT"
}

cmd_status() {
  say "${BOLD}Status${OFF}"
  step "Docker daemon"; docker info >/dev/null 2>&1 && ok "running" || bad "down"
  step "lokara-db :54322"
  local h; h="$(docker inspect -f '{{.State.Health.Status}}' lokara-db 2>/dev/null)"
  [[ "$h" == "healthy" ]] && ok "healthy" || bad "${h:-absent}"
  step "API :$API_PORT"
  curl -sf -o /dev/null "http://127.0.0.1:$API_PORT/health" && ok "/health 200" || bad "down"
  step "Web :$WEB_PORT"
  curl -sf -o /dev/null "http://localhost:$WEB_PORT/" && ok "ready" || bad "down"
}

cmd_logs() {
  case "${1:-both}" in
    api) tail -f "$LOG_DIR/api.log" ;;
    web) tail -f "$LOG_DIR/web.log" ;;
    *)   tail -f "$LOG_DIR/api.log" "$LOG_DIR/web.log" ;;
  esac
}

case "${1:-start}" in
  start)   cmd_start ;;
  stop)    cmd_stop ;;
  restart) cmd_stop; say ""; cmd_start ;;
  status)  cmd_status ;;
  logs)    shift; cmd_logs "$@" ;;
  *) echo "usage: scripts/dev.sh [start|stop|restart|status|logs [api|web]]" >&2; exit 2 ;;
esac
