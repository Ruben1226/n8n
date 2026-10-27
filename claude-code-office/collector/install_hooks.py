#!/usr/bin/env python3
"""Instala, muestra o desinstala los hooks de Claude Code Office.

Por defecto solo IMPRIME el bloque JSON que habría que fusionar. Con
--install fusiona las entradas en ~/.claude/settings.json (ámbito de
usuario: aplica a TODAS las sesiones de Claude Code de este usuario en esta
máquina, incluidas las de Remote Control), tras hacer una copia de
seguridad y pedir confirmación. Nunca borra hooks ajenos.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shlex
import shutil
import sys

MARKER = "claude_hook.py"
EVENTS = (
    "SessionStart",
    "SessionEnd",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "PostToolUseFailure",
    "Stop",
    "SubagentStart",
    "SubagentStop",
    "Notification",
    "PermissionRequest",
    "PreCompact",
)
HOOK_TIMEOUT_S = 5


def hook_command(python: str) -> str:
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "claude_hook.py")
    return f"{shlex.quote(python)} {shlex.quote(script)}"


def hooks_block(command: str) -> dict:
    return {
        ev: [{"matcher": "", "hooks": [{"type": "command", "command": command, "timeout": HOOK_TIMEOUT_S}]}]
        for ev in EVENTS
    }


def _is_ours(hook: dict) -> bool:
    return isinstance(hook, dict) and MARKER in str(hook.get("command", ""))


def strip_ours(settings: dict) -> dict:
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return settings
    for ev in list(hooks):
        groups = hooks[ev]
        if not isinstance(groups, list):
            continue
        kept = []
        for g in groups:
            if isinstance(g, dict) and isinstance(g.get("hooks"), list):
                inner = [h for h in g["hooks"] if not _is_ours(h)]
                if inner:
                    kept.append({**g, "hooks": inner})
                elif not g["hooks"]:
                    kept.append(g)
            else:
                kept.append(g)
        if kept:
            hooks[ev] = kept
        else:
            del hooks[ev]
    if not hooks:
        settings.pop("hooks", None)
    return settings


def merge_ours(settings: dict, command: str) -> dict:
    settings = strip_ours(settings)
    hooks = settings.setdefault("hooks", {})
    for ev, groups in hooks_block(command).items():
        hooks.setdefault(ev, []).extend(groups)
    return settings


def load(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        text = f.read()
    data = json.loads(text) if text.strip() else {}
    if not isinstance(data, dict):
        raise SystemExit(f"{path} no contiene un objeto JSON; no se modifica.")
    return data


def backup(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = f"{path}.bak-claude-office-{ts}"
    shutil.copy2(path, dst)
    return dst


def write(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp-claude-office"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def confirm(question: str) -> bool:
    try:
        return input(f"{question} [s/N] ").strip().lower() in ("s", "si", "sí", "y", "yes")
    except EOFError:
        return False


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--install", action="store_true", help="fusionar los hooks en el archivo de settings")
    mode.add_argument("--uninstall", action="store_true", help="quitar solo los hooks de Claude Code Office")
    mode.add_argument("--status", action="store_true", help="indicar si los hooks están instalados")
    p.add_argument("--settings", default=os.path.expanduser("~/.claude/settings.json"))
    p.add_argument("--python", default="python3", help="intérprete para el hook (por defecto python3 del PATH)")
    p.add_argument("--yes", action="store_true", help="no pedir confirmación")
    a = p.parse_args(argv)
    command = hook_command(a.python)

    if a.status:
        s = load(a.settings)
        found = sorted(
            ev
            for ev, groups in (s.get("hooks") or {}).items()
            if isinstance(groups, list)
            and any(_is_ours(h) for g in groups if isinstance(g, dict) for h in (g.get("hooks") or []))
        )
        missing = [ev for ev in EVENTS if ev not in found]
        print(f"Archivo: {a.settings}")
        print(f"Eventos con hook instalado: {', '.join(found) or 'ninguno'}")
        if missing:
            print(f"Eventos sin hook: {', '.join(missing)}")
        return 0 if not missing else 1

    if not (a.install or a.uninstall):
        print("# Fusiona este bloque en ~/.claude/settings.json (o usa --install):")
        print(json.dumps({"hooks": hooks_block(command)}, indent=2, ensure_ascii=False))
        return 0

    settings = load(a.settings)
    new = merge_ours(json.loads(json.dumps(settings)), command) if a.install else strip_ours(json.loads(json.dumps(settings)))
    if new == settings:
        print("Sin cambios: la configuración ya está en el estado pedido.")
        return 0
    action = "instalar" if a.install else "desinstalar"
    if not a.yes and not confirm(f"¿{action.capitalize()} los hooks de Claude Code Office en {a.settings}?"):
        print("Cancelado; no se ha modificado nada.")
        return 1
    bak = backup(a.settings)
    if bak:
        print(f"Copia de seguridad: {bak}")
    write(a.settings, new)
    print(f"Hooks {'instalados' if a.install else 'desinstalados'} en {a.settings}.")
    if a.install:
        print("Las sesiones nuevas los cargan al arrancar; las ya abiertas pueden necesitar /hooks o reiniciarse.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
