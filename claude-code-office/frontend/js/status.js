// Etiquetas, iconos y colores por estado. El color nunca es la única pista:
// siempre va acompañado de icono y texto.

export const STATUS = {
  working: { label: 'Trabajando', icon: '⚙', color: '#3fae6a' },
  waiting: { label: 'Esperando', icon: '…', color: '#e0a526' },
  completed: { label: 'Completado', icon: '✓', color: '#4a90d9' },
  error: { label: 'Error', icon: '!', color: '#e0524a' },
  idle: { label: 'Inactivo', icon: '◌', color: '#9a9aa6' },
  running: { label: 'En ejecución', icon: '▶', color: '#2fb5b0' },
  exited: { label: 'Terminado', icon: '■', color: '#7d7d8a' },
  unknown: { label: 'Desconocido', icon: '?', color: '#b28bd6' },
  stale: { label: 'Datos obsoletos', icon: '⌛', color: '#c27c4e' },
};

export const DETAIL = {
  between_tools: 'entre herramientas',
  needs_permission: 'pide permiso',
  needs_input: 'espera tu respuesta',
  session_start: 'sesión iniciada',
  interrupted: 'interrumpido',
  after_error: 'tras un error',
  prompt: 'prompt recibido',
  tool: 'usando herramienta',
  turn_end: 'fin de turno',
  turn_end_bg: 'fin de turno (tareas en 2º plano)',
  subagent_end: 'subagente terminado',
  session_end: 'sesión cerrada',
  parent_end: 'sesión padre cerrada',
  process_gone: 'proceso claude desaparecido',
  compacting: 'compactando contexto',
  started: 'iniciado',
  tool_error: 'fallo de herramienta',
  transcript_activity: 'actividad en transcript',
};

export const KIND = {
  claude_session: 'Sesión de Claude Code',
  subagent: 'Subagente',
  unattributed: 'Eventos no atribuidos',
  external_process: 'Proceso externo',
};

export const SOURCE = {
  hook: 'hook (detectado)',
  process_monitor: 'monitor de procesos (detectado)',
  transcript: 'transcript (inferido, sin hooks)',
  derived: 'inferencia',
  demo: 'DEMO (ficticio)',
};

export const CONFIDENCE = { high: 'alta', medium: 'media', low: 'baja' };

export function statusInfo(s) {
  return STATUS[s] || STATUS.unknown;
}

export function needsAttention(e) {
  return e.status === 'waiting' && (e.detail === 'needs_permission' || e.detail === 'needs_input');
}

export function originTags(e) {
  const o = e.origin || {};
  const tags = [];
  if (o.remote_control) tags.push('RC');
  if (o.tmux) tags.push('tmux');
  if (o.cloud) tags.push('nube');
  if (o.entrypoint && !['cli'].includes(o.entrypoint)) tags.push(o.entrypoint);
  if (e.kind === 'claude_session' && !e.has_hooks) tags.push('sin hooks');
  return tags;
}

export function fmtAge(ms) {
  if (ms == null || Number.isNaN(ms)) return '—';
  const s = Math.max(0, Math.round(ms / 1000));
  if (s < 60) return `${s} s`;
  if (s < 3600) return `${Math.floor(s / 60)} min ${s % 60} s`;
  const h = Math.floor(s / 3600);
  return `${h} h ${Math.floor((s % 3600) / 60)} min`;
}

export function fmtTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

// Color estable por entidad (hash del id).
export function entityHue(id) {
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0;
  return h % 360;
}
