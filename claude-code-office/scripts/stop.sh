#!/usr/bin/env bash
# Para el servidor lanzado con scripts/run.sh (no afecta a Claude Code).
set -euo pipefail
DATA="${CLAUDE_OFFICE_DATA_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/claude-office}"
PIDFILE="$DATA/server.pid"
if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  kill "$(cat "$PIDFILE")"
  rm -f "$PIDFILE"
  echo "Parado."
else
  rm -f "$PIDFILE"
  echo "No estaba en marcha (si usas systemd: systemctl --user stop claude-office)."
fi
