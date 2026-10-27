#!/usr/bin/env bash
# Diagnóstico de solo lectura: no modifica nada.
cd "$(dirname "$0")/.."
DATA="${CLAUDE_OFFICE_DATA_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/claude-office}"
PY=python3; [ -x .venv/bin/python ] && PY=.venv/bin/python
read -r HOST PORT < <("$PY" -c 'from backend.config import load_config; c=load_config(); print(c["server"]["host"], c["server"]["port"])' 2>/dev/null || echo "127.0.0.1 8765")
ok() { printf '  \033[32m✔\033[0m %s\n' "$*"; }
ko() { printf '  \033[31m✘\033[0m %s\n' "$*"; }
info() { printf '  · %s\n' "$*"; }

echo "== Servidor ($HOST:$PORT)"
if command -v ss >/dev/null; then
  if ss -ltnH 2>/dev/null | awk '{print $4}' | grep -q ":$PORT\$"; then ok "puerto $PORT escuchando"; else ko "nada escucha en $PORT (scripts/run.sh)"; fi
fi
H=$(curl -fsS --max-time 3 "http://$HOST:$PORT/api/health" 2>/dev/null)
if [ -n "$H" ]; then ok "/api/health responde"; echo "$H" | "$PY" -m json.tool | sed 's/^/      /' | head -40; else ko "/api/health no responde"; fi

echo "== Hooks de Claude Code"
"$PY" collector/install_hooks.py --status | sed 's/^/  /'
LAST=$(ls -1 "$DATA"/events/hooks-*.jsonl 2>/dev/null | tail -1)
if [ -n "$LAST" ]; then
  ok "último archivo de eventos: $LAST ($(wc -l <"$LAST") líneas)"
  info "último evento: $(tail -1 "$LAST" | "$PY" -c 'import json,sys; d=json.loads(sys.stdin.read()); print(d["timestamp"], d["event_type"], d.get("session_id","")[:8])' 2>/dev/null)"
else
  ko "aún no se ha escrito ningún evento en $DATA/events (¿hooks instalados? ¿sesión nueva abierta?)"
fi
[ -s "$DATA/collector.log" ] && { info "errores del recolector (últimos 3):"; tail -3 "$DATA/collector.log" | sed 's/^/      /'; }
info "prueba manual del hook: echo '{\"hook_event_name\":\"Notification\",\"session_id\":\"diag\"}' | python3 collector/claude_hook.py"

echo "== Tailscale"
if command -v tailscale >/dev/null; then
  if tailscale status >/dev/null 2>&1; then ok "conectado; IP: $(tailscale ip -4 2>/dev/null | head -1)"; else ko "tailscale instalado pero no conectado"; fi
else
  info "tailscale no está instalado en este equipo"
fi

echo "== Servicio"
if command -v systemctl >/dev/null && systemctl --user list-unit-files claude-office.service >/dev/null 2>&1; then
  info "systemd: $(systemctl --user is-active claude-office 2>/dev/null) (reiniciar: systemctl --user restart claude-office)"
elif [ -f "$DATA/server.pid" ]; then
  info "lanzado con run.sh, PID $(cat "$DATA/server.pid") (reiniciar: scripts/stop.sh && scripts/run.sh)"
fi
