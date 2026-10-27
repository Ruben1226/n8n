# Claude Code Office

Oficina isométrica 2D que muestra, en tiempo real y **solo lectura**, qué hacen
tus sesiones de Claude Code, sus subagentes y los procesos externos de tu
trabajo (Python, ROOT, Geant4, TOPAS…). Se ejecuta en tu ordenador; la abres
desde el propio equipo, o desde el portátil y el móvil a través de Tailscale.

- Los estados salen de **eventos reales** (hooks de Claude Code y `/proc`). Cada
  estado indica su **fuente** y su **confianza**, y separa lo detectado de lo inferido.
- No guarda prompts, respuestas, entradas ni salidas de herramientas, ni
  argumentos de comandos. Solo metadatos: tipo de evento, herramienta, ids y hora.
- No envía nada a Internet, no controla Claude Code y no ejecuta comandos desde la web.

---

## Instalación rápida

Requisitos: Linux, Python ≥ 3.11 y Claude Code. No necesitas Node, Docker ni root.

```bash
cd claude-code-office
scripts/install.sh                         # .venv + dependencias + config.toml
python3 collector/install_hooks.py         # 1) muestra el bloque de hooks (no modifica nada; ver también hooks-settings.example.json)
python3 collector/install_hooks.py --install   # 2) lo fusiona en ~/.claude/settings.json (pide confirmación y hace copia)
scripts/run.sh                             # arranca en segundo plano
```

Abre <http://127.0.0.1:8765>. Para probar la interfaz sin Claude Code:
`scripts/run.sh --demo` (verás la etiqueta **DEMO — datos ficticios**; usa
otra base de datos, `demo.db`, así que no se mezcla con tu historial real).

Para parar: `scripts/stop.sh`. Para diagnosticar: `scripts/diagnose.sh`.

---

## Todas tus sesiones, incluido Remote Control

`install_hooks.py --install` escribe los hooks en **`~/.claude/settings.json`
(ámbito de usuario)**. Claude Code carga ese archivo en **todas** las sesiones de
tu usuario en este ordenador, sea cual sea el proyecto o cómo se hayan lanzado:

| Cómo se lanzó la sesión | ¿Se ve? | Etiqueta |
|---|---|---|
| `claude` en una terminal o en tmux | Sí, con hooks | `tmux` si corre dentro de tmux |
| `claude remote-control` (servidor que lanza sesiones desde claude.ai/code o la app móvil) | Sí, con hooks | **RC** |
| `claude --remote-control` | Sí, con hooks | **RC** |
| Remote Control activado a mitad de sesión con `/remote-control` | Sí, con hooks | sin `RC` (ver limitaciones) |
| Extensiones de IDE, `claude -p`, Agent SDK en este equipo | Sí, con hooks | el `entrypoint` que informe Claude Code |
| Sesiones abiertas **antes** de instalar los hooks | Sí, **sin hooks**: se descubren por la fecha de su transcript | `sin hooks` (confianza baja) |
| Sesiones de Claude Code **en la nube** (claude.ai/code sin Remote Control) | **No**: corren en contenedores de Anthropic y sus hooks no se ejecutan en tu equipo | — |
| Sesiones en **otro** ordenador | No, salvo que instales allí otra copia | — |

Con Remote Control la sesión sigue corriendo en **tu** ordenador (desde el móvil
solo la manejas), así que sus hooks se ejecutan localmente y aparece en la oficina
como cualquier otra. El hook marca la sesión como `RC` si encuentra un proceso
`claude` lanzado con `remote-control` o `--remote-control` entre sus procesos
padre. Así tienes en el móvil, a la vez, el chat de Remote Control y el panel de
la oficina, con un aviso naranja **«⚠ N esperan tu respuesta»** cuando alguna
sesión pide permiso o espera respuesta.

**Sesiones ya abiertas:** cargan los hooks al arrancar. Reinícialas (o usa
`/hooks` para revisarlos) para que pasen de «sin hooks» a datos completos. La
pantalla **Estado** muestra cuántos procesos `claude` siguen sin enviar eventos.

**Si alguna sesión no aparece:** comprueba que no tenga `"disableAllHooks": true`
en un `.claude/settings.json` de proyecto, ni una política gestionada que permita
solo hooks gestionados.

---

## La oficina

| Zona | Quién está |
|---|---|
| Coordinación | sesiones de Claude Code (insignia dorada) |
| Zona de agentes | subagentes y eventos no atribuidos |
| Sala de revisión | subagentes cuyo tipo contiene *review / verify / audit / test / check / critic* |
| Laboratorio de simulación | procesos externos (máquinas con gráfica y LEDs) |
| Zona de descanso | entidades sin actividad observada (`idle`, inferido) |

Cada entidad conserva su puesto mientras esté activa. Toca o haz clic en un
personaje (o en su mesa) para abrir el detalle: tipo, id abreviado, estado,
confianza, fuente, motivo, herramienta actual, último evento, tiempo en el
estado, padre o hijos, procesos asociados y últimos eventos con filtro.
Arrastra para moverte, rueda o pellizco para el zoom, y ⤢ para encajar la vista.
**Lista** ofrece la misma información en una tabla accesible; es también la
alternativa automática si el renderizado gráfico falla.

### Estados

| Estado | Significado | Fuente típica |
|---|---|---|
| ⚙ Trabajando | prompt recibido o herramienta en curso | hook |
| … Esperando | entre herramientas, o **pide permiso / espera respuesta** (anillo naranja) | hook |
| ✓ Completado | `Stop` (fin de turno), `SubagentStop` o `SessionEnd` | hook |
| ! Error | `PostToolUseFailure` (visible al menos 8 s) | hook |
| ◌ Inactivo | sin eventos durante `idle_after_seconds`; **no** implica descanso | inferido |
| ⌛ Datos obsoletos | «trabajando» sin eventos ni herramienta abierta durante `stale_after_seconds` | inferido |
| ▶ En ejecución / ■ Terminado | proceso externo vivo o desaparecido | /proc |
| ? Desconocido | no hay datos suficientes | — |

Una herramienta larga (por ejemplo una simulación lanzada con Bash) mantiene
«Trabajando» mientras siga abierta: no se marca como obsoleta.

---

## Cómo funciona

```
Claude Code ──hook (stdin JSON)──► collector/claude_hook.py ──append──► ~/.local/share/claude-office/events/hooks-AAAA-MM-DD.jsonl
                                                                                  │
/proc (cada 5 s) ─────────────────────────────────────┐                          │ lectura incremental (offset + inodo)
~/.claude/projects/*.jsonl (solo fechas) ─────────────┤                          ▼
                                                      └──► backend (FastAPI) ─► máquina de estados ─► SQLite (office.db)
                                                                      │
                                                     HTTP de lectura + WebSocket (deltas)
                                                                      ▼
                                                    frontend (Phaser 3 + HTML)
```

- **Hook** (`collector/claude_hook.py`): solo biblioteca estándar, sin red,
  siempre termina con código 0 y sin salida, con `timeout` de 5 s. Si el
  servidor está caído los eventos se acumulan en el JSONL y se procesan al
  volver; Claude Code no se entera.
- **Backend** (`backend/`): `domain/` es puro y está testeado (normalizador,
  máquina de estados, asignación de puestos); `services/` hace la E/S
  (lector JSONL, monitor de procesos, transcripts, demo, difusión); `storage/`
  es SQLite (`entities`, `events`, `settings`) con índices por timestamp,
  entidad, sesión y tipo, más retención configurable.
- **Frontend** (`frontend/`): módulos ES sin paso de compilación y Phaser 3.90
  local (sin CDN). La escena solo traduce estado → animación; no decide estados.

### Esquema de evento normalizado

Basado en payloads **reales** capturados con Claude Code 2.1.311
(`tests/fixtures/hook_payloads_cc2.1.311.jsonl`, con el contenido privado redactado):

```json
{"v":1,"event_id":"uuid","timestamp":"2026-10-27T19:44:21.007Z","event_type":"PreToolUse",
 "source":"hook","session_id":"…","agent_id":"a0d5…","agent_type":"general-purpose",
 "tool_name":"Bash","tool_use_id":"toolu_…","prompt_id":"…",
 "meta":{"cwd":"/home/tú/proyecto","permission_mode":"default","effort":"medium","duration_ms":18},
 "origin":{"entrypoint":"cli","cloud":false,"tmux":true,"remote_control":true,"claude_pid":4242,"claude_start":123456}}
```

Se descartan siempre: `prompt`, `tool_input`, `tool_response`, `error`,
`last_assistant_message`, `transcript_path` y las descripciones de tareas.

### Atribución de subagentes

En la versión probada, los eventos de herramientas de un subagente llevan
`agent_id`/`agent_type`, así que se atribuyen a su personaje con confianza alta.
Si una versión no los incluye y hay subagentes activos, los eventos sin
`agent_id` van a una entidad **«no atribuido»**: no se adivina.

### Procesos externos

Se listan solo los procesos **de tu usuario** cuyo `comm` o ejecutable coincide
con `[processes].allowlist` (admite comodines). Se identifican por PID + hora
de inicio, así que un PID reutilizado cuenta como otro proceso. La asociación
con una sesión se busca, por orden:

1. descendiente del proceso `claude` de la sesión → «asociación directa» (alta);
2. mismo directorio de trabajo (o subdirectorio) → «asociación probable» (baja);
3. si no hay ninguna de las dos, el proceso queda sin asociación.

Nunca se guardan argumentos ni variables de entorno. Con
`record_script_name = true` se guarda además el nombre del script de los
intérpretes (`analisis.py`), solo el nombre de archivo.

---

## API (solo lectura)

| Endpoint | Descripción |
|---|---|
| `GET /api/health` | estado, versión, fuentes, último hook, último escaneo, errores recientes |
| `GET /api/entities?include_archived=&limit=` (≤500) | entidades activas (o también archivadas) |
| `GET /api/entities/{id}` | detalle y relacionados |
| `GET /api/entities/{id}/events?limit=` (≤200) | eventos de la entidad |
| `GET /api/events?since=&event_type=&limit=` (≤500) | eventos recientes (`since`: ISO-8601 o epoch) |
| `GET /api/stats` | recuento por estado y tipo |
| `GET /api/config/public` | configuración no sensible |
| `WS /ws` | `snapshot` inicial, luego deltas `entities` / `events` y `heartbeat` cada 10 s |

No hay endpoints de escritura: `POST/PUT/DELETE` responden 405.

---

## Acceso desde el portátil y el móvil (Tailscale)

No abras puertos en el router ni escuches en `0.0.0.0`. Tienes dos opciones:

**A. `tailscale serve` (recomendada):** el servidor sigue en `127.0.0.1` y
Tailscale lo publica solo dentro de tu tailnet, con HTTPS:

```bash
tailscale serve --bg 8765
tailscale serve status        # muestra la URL https://<equipo>.<tailnet>.ts.net
```

**B. Escuchar en la IP de Tailscale:** en `config.toml` pon
`host = "100.x.y.z"` (la de `tailscale ip -4`) y reinicia. Abre
`http://100.x.y.z:8765` desde el otro dispositivo.

Comprobar: `tailscale status` en ambos equipos; `curl http://<ip>:8765/api/health`
desde el portátil. El WebSocket rechaza conexiones cuyo `Origin` no coincida con
el host, para que otras webs abiertas en tu navegador no puedan leer el panel.

---

## Configuración (`config.toml`)

Copia comentada en `config.example.toml`. Opciones: host y puerto, nombre y tema
de la oficina (`warm` | `night`), animación reducida para todos los clientes,
activar o desactivar cada fuente (hooks, transcripts, procesos), intervalos de
escaneo, umbrales `stale` / `idle` / visibilidad de errores y de terminados /
archivado, directorio de datos, días de retención, allowlist de procesos y modo
demo. Ruta alternativa: `CLAUDE_OFFICE_CONFIG=/ruta/config.toml`. Directorio de
datos alternativo: `CLAUDE_OFFICE_DATA_DIR` (respetado también por el hook).

---

## Operación

- **Servicio de usuario (opcional):** `scripts/install.sh --systemd` y luego
  `systemctl --user enable --now claude-office`. Para que arranque sin iniciar
  sesión: `loginctl enable-linger $USER`.
- **Reiniciar:** `systemctl --user restart claude-office` o `scripts/stop.sh && scripts/run.sh`.
- **Logs:** `~/.local/share/claude-office/backend.log` (backend) y `collector.log` (errores del hook).
- **Actualizar:** `git pull && scripts/install.sh` y reinicia el servicio.
- **Copia de seguridad:** para el servidor y copia `~/.local/share/claude-office/`
  (o, en caliente: `sqlite3 office.db ".backup copia.db"`). **Restaurar:** para
  el servidor, devuelve los archivos a su sitio y arráncalo.
- **Comprobar que Claude Code reconoce los hooks:** `/hooks` dentro de una sesión,
  o `python3 collector/install_hooks.py --status`.
- **Prueba manual del hook:**
  `echo '{"hook_event_name":"Notification","session_id":"prueba"}' | python3 collector/claude_hook.py`
  y mira el último `hooks-*.jsonl`.

### Desinstalar

```bash
python3 collector/install_hooks.py --uninstall   # quita SOLO nuestros hooks (con copia de seguridad)
systemctl --user disable --now claude-office 2>/dev/null; rm -f ~/.config/systemd/user/claude-office.service
scripts/stop.sh
rm -rf ~/.local/share/claude-office              # historial (opcional)
```

Las copias `~/.claude/settings.json.bak-claude-office-*` se pueden borrar cuando quieras.

---

## Pruebas

```bash
scripts/install.sh --dev
.venv/bin/python -m pytest
```

Cubren: normalización con payloads reales y entradas malformadas, redacción de
datos privados en el hook, que el hook nunca falla, el instalador (idempotente,
conserva hooks ajenos, copia de seguridad, desinstalación exacta), la máquina de
estados (determinismo, error mínimo visible, stale/idle inferidos, herramientas
largas, atribución de subagentes, «no atribuido», cierre en cascada, puestos
estables), los procesos (detección y fin de un proceso real, asociación por
árbol y por cwd, PID reutilizado, sin argumentos), los transcripts (sin pisar a
los hooks), la API (vacía, flujo hook → entidad, deduplicación, persistencia
tras reinicio, límites y validación, sin acceso a archivos ni comandos, CSP),
el WebSocket (snapshot y rechazo de `Origin` ajeno) y la separación de la base
de datos demo.

Se verificó además, a mano: una sesión real de `claude -p` con un subagente
aparece con sus herramientas y su PID; la interfaz en escritorio (1400×860) y en
móvil (390×800) con Playwright; y la reconexión del WebSocket tras parar y volver
a arrancar el servidor.

---

## Limitaciones (honestas)

- Los hooks informan de **eventos**, no del estado mental del modelo. Entre
  `PostToolUse` y el siguiente evento el modelo puede estar generando texto, y eso
  se muestra como «Esperando · entre herramientas».
- La ausencia de eventos no distingue entre espera, bloqueo o desconexión: por
  eso `idle` y `stale` se marcan como inferidos.
- Si se activa Remote Control a mitad de sesión con `/remote-control`, el hook no
  puede saberlo: la sesión aparece, pero sin la etiqueta `RC`.
- Las sesiones de Claude Code en la nube no se pueden observar desde tu equipo.
- Las sesiones sin hooks (descubiertas por transcript) solo tienen la fecha de
  modificación del archivo: estado con confianza baja y sin herramientas.
- Si un proceso `claude` muere sin `SessionEnd`, la sesión se cierra cuando el
  monitor de procesos ve que el PID ya no existe (confianza media).
- La asociación por directorio es solo «probable». Los procesos de un subagente
  se asocian a su sesión, porque comparten el proceso `claude`.
- El nombre visible de una sesión sin hooks se deduce del nombre de la carpeta de
  `~/.claude/projects`, que es ambiguo si la ruta tenía guiones.
- En pantallas de alta densidad el lienzo se dibuja a resolución CSS, así que los
  textos de la escena pueden verse algo suaves. Los paneles HTML son nítidos.

## Decisiones de diseño

- **JavaScript (módulos ES) en lugar de TypeScript:** evita exigir Node y un paso
  de compilación en el servidor, y el código sigue separado en módulos (`api`,
  `store`, `ui`, `scene/*`). Migrarlo a TS es directo si hace falta.
- **Sin tabla `state_snapshots`:** `entities` guarda el estado actual y `events`
  el historial completo (incluidos `ProcessStart` y `ProcessExit`), así que el
  estado se puede reconstruir reproduciendo los eventos.
- **JSONL como buzón entre hook y backend:** el hook no depende del servidor y
  `event_id` deduplica si una línea se lee dos veces.
- **Sin `psutil`:** `/proc` basta en Linux y evita una dependencia compilada.

## Sustituir sprites

Los sprites actuales son originales y se generan por código en
`frontend/js/scene/textures.js`. Para usar arte final, carga imágenes con las
mismas claves (`desk`, `chair`, `body`, `head`, `hair`, `rack`, `plant`,
`coffee`, `sofa`, `board`, `cabinet`, `tile-<zona>`) en un `preload()` de
`OfficeScene`: `buildTextures` no sobrescribe las claves que ya existen. Ajusta
`ANCHOR[clave]` para que la base del sprite caiga en su casilla. La distribución
de zonas y puestos está en `frontend/js/scene/iso.js`. Usa solo assets propios,
CC0 o con licencia compatible, y anótalos aquí.

## Dependencias y licencias

| Componente | Licencia | Uso |
|---|---|---|
| FastAPI | MIT | API HTTP y WebSocket |
| Uvicorn | BSD-3-Clause | servidor ASGI |
| websockets | BSD-3-Clause | transporte WebSocket |
| Phaser 3.90.0 | MIT (`frontend/vendor/PHASER-LICENSE.md`) | escena 2D, incluido en el repositorio |
| pytest, httpx (solo desarrollo) | MIT, BSD-3-Clause | pruebas |
| Sprites y decoración | originales, generados por código | — |
