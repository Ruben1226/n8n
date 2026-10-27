#!/usr/bin/env bash
# Instalación reproducible y sin root: entorno virtual + config local.
# No toca ~/.claude/settings.json (los hooks se instalan aparte, con confirmación).
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

PY="${PYTHON:-python3}"
"$PY" -c 'import sys; assert sys.version_info >= (3, 11), "Se necesita Python >= 3.11"'

if [ ! -d .venv ]; then
  "$PY" -m venv .venv
fi
.venv/bin/pip install --upgrade pip >/dev/null
.venv/bin/pip install -r requirements.txt
if [ "${1:-}" = "--dev" ]; then
  .venv/bin/pip install -r requirements-dev.txt
fi

if [ ! -f config.toml ]; then
  cp config.example.toml config.toml
  echo "Creado config.toml a partir de config.example.toml"
fi

if [ "${1:-}" = "--systemd" ] || [ "${2:-}" = "--systemd" ]; then
  UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
  mkdir -p "$UNIT_DIR"
  if [ -f "$UNIT_DIR/claude-office.service" ]; then
    echo "Ya existe $UNIT_DIR/claude-office.service; no se sobrescribe."
  else
    sed "s#@ROOT@#$ROOT#g" systemd/claude-office.service > "$UNIT_DIR/claude-office.service"
    systemctl --user daemon-reload
    echo "Unidad instalada. Actívala con: systemctl --user enable --now claude-office"
  fi
fi

cat <<MSG

Listo. Siguientes pasos:
  1. Hooks (para TODAS tus sesiones, incluidas las de Remote Control):
       python3 collector/install_hooks.py            # muestra el bloque a fusionar
       python3 collector/install_hooks.py --install  # lo fusiona con copia de seguridad
  2. Arrancar:   scripts/run.sh          (o scripts/run.sh --demo)
  3. Abrir:      http://127.0.0.1:8765
  4. Diagnóstico: scripts/diagnose.sh
MSG
