#!/usr/bin/env bash
# Arranca el servidor. Por defecto en segundo plano (PID en el directorio de
# datos); con --foreground se queda en primer plano (lo usa systemd).
# Argumentos extra (--demo, --host, --port, --config) se pasan al backend.
set -euo pipefail
cd "$(dirname "$0")/.."
DATA="${CLAUDE_OFFICE_DATA_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/claude-office}"
mkdir -p "$DATA"
PIDFILE="$DATA/server.pid"

FOREGROUND=0
ARGS=()
for a in "$@"; do
  if [ "$a" = "--foreground" ]; then FOREGROUND=1; else ARGS+=("$a"); fi
done

if [ ! -x .venv/bin/python ]; then
  echo "Falta el entorno virtual: ejecuta scripts/install.sh" >&2
  exit 1
fi

if [ "$FOREGROUND" = 1 ]; then
  exec .venv/bin/python -m backend.app "${ARGS[@]}"
fi

if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "Ya está en marcha (PID $(cat "$PIDFILE")). Usa scripts/stop.sh para pararlo."
  exit 0
fi
nohup .venv/bin/python -m backend.app "${ARGS[@]}" >>"$DATA/server.out" 2>&1 &
echo $! >"$PIDFILE"
sleep 1
if kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "Claude Code Office en marcha (PID $(cat "$PIDFILE")). Log: $DATA/backend.log"
else
  echo "No arrancó; revisa $DATA/server.out" >&2
  exit 1
fi
