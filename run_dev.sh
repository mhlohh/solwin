#!/usr/bin/env bash
# run_dev.sh — run the entire Solwin stack with one command.
#
#   ./run_dev.sh            start whatever isn't already running, wait for health
#   ./run_dev.sh --restart  kill whatever is listening first, then start everything
#   ./run_dev.sh --reset    --restart + re-seed the inbox DB and demo data (needs GEMINI_API_KEY)
#   ./run_dev.sh --stop     stop everything (services + leftover launchd jobs)
#   ./run_dev.sh --status   just print the current state
#
# Services (start order matters: Backend calls ML, Frontend calls Backend+Data):
#   ml       :8000   FastAPI hybrid-AI pipeline      app/ml_services/.venv
#   backend  :8001   Backend API (ops DB, reviews)   app/Backend/.venv
#   data     :8002   Inbox Data API (20,862 rows)    app/data/inbox_dev.db
#   frontend :5173   Vite dev server                 app/frontend
#
# Logs: .freebuff/logs/<service>.log — tail them when a service shows DOWN.
set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$REPO_ROOT/.freebuff/logs"
DATA_DB="$REPO_ROOT/app/data/inbox_dev.db"
BACKEND_DB="$REPO_ROOT/app/Backend/solwin_dev.db"
UV_BIN="$(command -v uv || echo "$HOME/.local/bin/uv")"
mkdir -p "$LOG_DIR"

# name|port|health_path
SERVICES=(
  "ml|8000|/health"
  "backend|8001|/health"
  "data|8002|/health"
  "frontend|5173|/"
)

label_for()  { echo "solwin-dev-$1"; }
log_for()    { echo "$LOG_DIR/$1.log"; }
pidfile_for(){ echo "$LOG_DIR/$1.pid"; }

cmd_for() { # full command incl. workdir + env, used for both nohup and launchd
  case "$1" in
    ml)
      echo "cd $REPO_ROOT/app/ml_services && exec .venv/bin/uvicorn ml_service.main:app --host 127.0.0.1 --port 8000" ;;
    backend)
      echo "cd $REPO_ROOT/app/Backend && exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001" ;;
    data)
      echo "cd $REPO_ROOT/app/data && DATABASE_URL=sqlite:///$DATA_DB exec ../Backend/.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8002" ;;
    frontend)
      echo "cd $REPO_ROOT/app/frontend && exec npm run dev -- --host 127.0.0.1 --port 5173 --strictPort" ;;
  esac
}

port_of()   { echo "$1" | cut -d'|' -f2; }
name_of()   { echo "$1" | cut -d'|' -f1; }
health_of() { echo "$1" | cut -d'|' -f3; }

listening_pids() { lsof -t -nP -iTCP:"$1" -sTCP:LISTEN 2>/dev/null || true; }
probe() { curl -s -o /dev/null -w "%{http_code}" --max-time 2 "http://127.0.0.1:$1$2" 2>/dev/null; }

say()  { printf '%s\n' "$*"; }
warn() { printf '⚠️  %s\n' "$*"; }
ok()   { printf '✅ %s\n' "$*"; }

# ---------------------------------------------------------------- artifacts
ensure_artifacts() {
  [ -x "$REPO_ROOT/app/ml_services/.venv/bin/uvicorn" ] || {
    warn "ML venv missing — installing (pip install -e .)"; (
      cd "$REPO_ROOT/app/ml_services" && python3 -m venv .venv &&
      .venv/bin/pip install -q -e .
    ) || { say "❌ ML dependency install failed"; exit 1; }
  }
  [ -x "$REPO_ROOT/app/Backend/.venv/bin/uvicorn" ] || {
    warn "Backend venv missing — running uv sync"; (
      cd "$REPO_ROOT/app/Backend" && "$UV_BIN" sync
    ) || { say "❌ Backend dependency install failed"; exit 1; }
  }
  [ -d "$REPO_ROOT/app/frontend/node_modules" ] || {
    warn "Frontend node_modules missing — running npm install"; (
      cd "$REPO_ROOT/app/frontend" && npm install --no-audit --no-fund
    ) || { say "❌ npm install failed"; exit 1; }
  }
  if [ ! -f "$DATA_DB" ]; then
    warn "Inbox DB missing — seeding 20,862 records from the CSV (takes ~1 min)"
    ( cd "$REPO_ROOT/app/data" && DATABASE_URL="sqlite:///$DATA_DB" \
      "$UV_BIN" run --project ../Backend python -m backend.seed ) \
      || { say "❌ Inbox seed failed"; exit 1; }
    ok "Inbox DB seeded → $DATA_DB"
  fi
  if [ ! -f "$BACKEND_DB" ]; then
    warn "Backend DB missing — bootstrapping tables + demo data (needs GEMINI_API_KEY)"
    ( cd "$REPO_ROOT/app/Backend" && "$UV_BIN" run python scripts/bootstrap_local.py ) \
      || { say "❌ Backend bootstrap failed (check app/Backend/.env)"; exit 1; }
    ok "Backend DB bootstrapped → $BACKEND_DB"
  fi
}

# ---------------------------------------------------------------- lifecycle
stop_all() {
  for s in ml backend data frontend; do launchctl remove "$(label_for "$s")" 2>/dev/null; done
  # labels used by earlier sessions of this repo
  launchctl remove solwin-data-api 2>/dev/null
  launchctl remove solwin-preview-vite 2>/dev/null
  local entry port pids
  for entry in "${SERVICES[@]}"; do
    port="$(port_of "$entry")"
    pids="$(listening_pids "$port")"
    [ -n "$pids" ] && kill $pids 2>/dev/null
  done
  pkill -f "uvicorn ml_service.main:app" 2>/dev/null
  pkill -f "uvicorn app.main:app" 2>/dev/null
  pkill -f "uvicorn backend.main:app" 2>/dev/null
  pkill -f -- "--port 5173" 2>/dev/null
  sleep 2
  for entry in "${SERVICES[@]}"; do
    pids="$(listening_pids "$(port_of "$entry")")"
    [ -n "$pids" ] && kill -9 $pids 2>/dev/null
  done
  rm -f "$LOG_DIR"/*.pid
  ok "All services stopped"
}

start_plain() { # $1=service name — fallback only; the runner reaps nohup children on macOS
  : > "$(log_for "$1")"
  nohup /bin/bash -c "$(cmd_for "$1")" > "$(log_for "$1")" 2>&1 < /dev/null &
  echo $! > "$(pidfile_for "$1")"
}

start_launchd() { # $1=service name
  : > "$(log_for "$1")"
  # export PATH *inside* the shell — a `PATH=... cmd` prefix would only apply
  # to the first command of the chain, leaving `npm` unfindable for the rest.
  launchctl submit -l "$(label_for "$1")" -- /bin/sh -c \
    "export PATH=/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$HOME/.local/bin; $(cmd_for "$1") >> $(log_for "$1") 2>&1"
}

is_running() { # $1=name $2=port
  [ -n "$(listening_pids "$2")" ]
}

# bash 3.2 on macOS has no associative arrays — track per-service state
# in fixed variables instead.
VIA_ML=; VIA_BACKEND=; VIA_DATA=; VIA_FRONTEND=
RETRIED_ML=; RETRIED_BACKEND=; RETRIED_DATA=; RETRIED_FRONTEND=
set_via()    { case "$1" in ml) VIA_ML=$2 ;; backend) VIA_BACKEND=$2 ;; data) VIA_DATA=$2 ;; frontend) VIA_FRONTEND=$2 ;; esac; }
get_via()    { case "$1" in ml) echo "$VIA_ML" ;; backend) echo "$VIA_BACKEND" ;; data) echo "$VIA_DATA" ;; frontend) echo "$VIA_FRONTEND" ;; esac; }
set_retried(){ case "$1" in ml) RETRIED_ML=1 ;; backend) RETRIED_BACKEND=1 ;; data) RETRIED_DATA=1 ;; frontend) RETRIED_FRONTEND=1 ;; esac; }
get_retried(){ case "$1" in ml) echo "$RETRIED_ML" ;; backend) echo "$RETRIED_BACKEND" ;; data) echo "$RETRIED_DATA" ;; frontend) echo "$RETRIED_FRONTEND" ;; esac; }
port_for_name() { case "$1" in ml) echo 8000 ;; backend) echo 8001 ;; data) echo 8002 ;; frontend) echo 5173 ;; esac; }

launchd_job_active() { # $1=service name — has launchd actually spawned it?
  launchctl print "gui/$(id -u)/$(label_for "$1")" 2>/dev/null | grep -qE 'state = (active|spawn scheduled|waiting)' \
    && launchctl print "gui/$(id -u)/$(label_for "$1")" 2>/dev/null | grep -q 'pid ='
}

start_and_wait() {
  local deadline=$((SECONDS + 90)) entry name port health

  for entry in "${SERVICES[@]}"; do
    name="$(name_of "$entry")"; port="$(port_of "$entry")"
    if is_running "$name" "$port"; then
      ok "$name already listening on :$port (skipping start)"
      set_via "$name" existing
    elif command -v launchctl >/dev/null 2>&1; then
      # macOS: plain background children get reaped when the calling shell's
      # process group dies, so launch directly under launchd (survives exit).
      start_launchd "$name"; set_via "$name" launchd
    else
      start_plain "$name"; set_via "$name" nohup
    fi
  done

  # launchd spawn takes a few seconds — give every launchd job a grace window
  # before considering any fallback, otherwise we race it and double-bind ports.
  if [ "$(get_via ml)" = "launchd" ] || [ "$(get_via backend)" = "launchd" ] || \
     [ "$(get_via data)" = "launchd" ] || [ "$(get_via frontend)" = "launchd" ]; then
    sleep 6
  fi

  local any_pending=1
  while [ $any_pending -eq 1 ] && [ $SECONDS -lt $deadline ]; do
    any_pending=0
    for entry in "${SERVICES[@]}"; do
      name="$(name_of "$entry")"; port="$(port_of "$entry")"; health="$(health_of "$entry")"
      [ "$(probe "$port" "$health")" = "200" ] && continue
      any_pending=1
      # launchd job died (bad command?) — try a plain start as last resort,
      # but only when launchd itself confirms the job is gone, not merely slow.
      if [ "$(get_via "$name")" = "launchd" ] && [ -z "$(get_retried "$name")" ] \
         && ! is_running "$name" "$port" && ! launchd_job_active "$name"; then
        warn "$name launchd job failed — retrying with a plain start"
        start_plain "$name"; set_via "$name" nohup; set_retried "$name"
      fi
    done
    [ $any_pending -eq 1 ] && sleep 2
  done
}

report() {
  local entry name port health code state pid
  say ""
  say "──────────────────────────────────────────────────────────"
  printf ' %-9s %-6s %-10s %s\n' "SERVICE" "PORT" "STATUS" "URL"
  say "──────────────────────────────────────────────────────────"
  for entry in "${SERVICES[@]}"; do
    name="$(name_of "$entry")"; port="$(port_of "$entry")"; health="$(health_of "$entry")"
    code="$(probe "$port" "$health")"
    if [ "$code" = "200" ]; then state="UP"; else state="DOWN"; fi
    pid="$(listening_pids "$port" | head -1)"
    printf ' %-9s %-6s %-10s http://localhost:%s%s\n' "$name" "$port" "$state" "$port" "${health%/}"
    [ "$state" = "DOWN" ] && warn "$name is DOWN — tail $(log_for "$name")"
  done
  say "──────────────────────────────────────────────────────────"
  say "Logs: $LOG_DIR/{ml,backend,data,frontend}.log"
  say "App:  http://localhost:5173   ·   API docs: http://localhost:8001/docs"
}

case "${1:-start}" in
  --stop)
    stop_all ;;
  --status)
    report ;;
  --restart)
    stop_all; ensure_artifacts; start_and_wait; report ;;
  --reset)
    stop_all
    warn "Resetting databases"
    rm -f "$DATA_DB" "$BACKEND_DB"
    ensure_artifacts; start_and_wait; report ;;
  start)
    ensure_artifacts; start_and_wait; report ;;
  *)
    say "usage: $0 [start|--restart|--reset|--stop|--status]"; exit 2 ;;
esac
