// Interfaz HTML: cabecera, lista accesible, panel de detalle, registro de
// eventos y diálogos. Todo el texto se inserta con textContent (nunca HTML).

import { getJSON } from './api.js';
import { CONFIDENCE, DETAIL, KIND, SOURCE, STATUS, fmtAge, fmtTime, needsAttention, originTags, statusInfo } from './status.js';

const $ = (id) => document.getElementById(id);

function el(tag, props = {}, ...children) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === 'class') n.className = v;
    else if (k === 'style') Object.assign(n.style, v);
    else if (k.startsWith('on')) n.addEventListener(k.slice(2), v);
    else if (v !== undefined && v !== null && v !== false) n.setAttribute(k, v === true ? '' : v);
  }
  for (const c of children) {
    if (c === null || c === undefined || c === false) continue;
    n.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return n;
}

function chip(status, detail) {
  const s = statusInfo(status);
  const d = detail && DETAIL[detail] ? ` · ${DETAIL[detail]}` : '';
  return el('span', { class: 'status-chip', style: { background: s.color } }, `${s.icon} ${s.label}${d}`);
}

function tagsFor(e) {
  return originTags(e).map((t) => el('span', { class: `tag ${t === 'RC' ? 'tag-rc' : ''}` }, t));
}

function eventLine(ev, store) {
  const ent = store.entities.get(ev.entity_id);
  const who = ent ? ent.display_name : ev.entity_id || '—';
  const what = [ev.event_type, ev.tool_name].filter(Boolean).join(' · ');
  return el(
    'li',
    {},
    el('span', { class: 't' }, fmtTime(ev.timestamp)),
    el('span', {}, el('b', {}, what), ' ', who, ' ', el('span', { class: 'src' }, `(${ev.source})`)),
  );
}

export class UI {
  constructor(store, opts) {
    this.store = store;
    this.opts = opts; // { scene: () => scene|null, onMotion: fn }
    this.detailEvents = [];
    this.bind();
    store.on((kind, payload) => this.onStore(kind, payload));
    setInterval(() => this.tickSecond(), 1000);
  }

  bind() {
    $('btn-view').addEventListener('click', () => this.toggleList());
    $('btn-events').addEventListener('click', () => this.togglePanel('events-panel', 'btn-events'));
    $('e-close').addEventListener('click', () => this.togglePanel('events-panel', 'btn-events', false));
    $('d-close').addEventListener('click', () => this.store.select(null));
    $('btn-legend').addEventListener('click', () => this.openLegend());
    $('btn-status').addEventListener('click', () => this.openStatus());
    $('btn-motion').addEventListener('click', () => this.opts.onMotion());
    $('attention').addEventListener('click', () => {
      const e = [...this.store.entities.values()].find(needsAttention);
      if (e) this.store.select(e.id);
    });
    $('e-source').addEventListener('change', () => this.renderEvents());
    $('e-type').addEventListener('change', () => this.renderEvents());
    $('d-filter').addEventListener('change', () => this.renderDetailEvents());
    $('zoom-in').addEventListener('click', () => this.opts.scene()?.zoomBy(1.2));
    $('zoom-out').addEventListener('click', () => this.opts.scene()?.zoomBy(1 / 1.2));
    $('zoom-fit').addEventListener('click', () => this.opts.scene()?.fitView());
    document.addEventListener('keydown', (ev) => {
      if (ev.key === 'Escape') this.store.select(null);
    });
  }

  setMotionLabel(reduced) {
    const b = $('btn-motion');
    b.textContent = reduced ? 'Animación: mínima' : 'Animación: sí';
    b.setAttribute('aria-pressed', String(reduced));
  }

  applyConfig(cfg) {
    $('office-name').textContent = cfg.office_name || 'Claude Code Office';
    document.title = cfg.demo ? `DEMO · ${cfg.office_name}` : cfg.office_name;
    $('demo-badge').hidden = !cfg.demo;
    if (cfg.theme === 'night') document.documentElement.dataset.theme = 'dark';
  }

  toggleList(force) {
    const list = $('list-view');
    const show = force ?? list.hidden;
    list.hidden = !show;
    // La lista se superpone a la escena (sin ocultar el canvas, que quedaría a 0×0)
    // y se pausa el dibujo mientras tanto.
    this.opts.setScenePaused?.(show);
    $('btn-view').setAttribute('aria-pressed', String(show));
    $('btn-view').textContent = show ? 'Oficina' : 'Lista';
    if (show) this.renderList();
  }

  togglePanel(id, btn, force) {
    const p = $(id);
    const show = force ?? p.hidden;
    p.hidden = !show;
    $(btn).setAttribute('aria-pressed', String(show));
    if (show && id === 'events-panel') {
      // En móvil solo cabe una hoja inferior a la vez.
      if (window.matchMedia('(max-width: 760px)').matches) $('detail').hidden = true;
      this.renderEvents();
    }
  }

  onStore(kind, payload) {
    if (kind === 'connection') this.renderHeader();
    if (kind === 'snapshot' || kind === 'entities') {
      this.renderHeader();
      if (!$('list-view').hidden) this.renderList();
      this.renderDetail();
      $('empty').hidden = this.store.entities.size > 0;
    }
    if (kind === 'events' || kind === 'snapshot') {
      if (!$('events-panel').hidden) this.renderEvents();
      if (this.store.selected && payload) {
        const mine = payload.filter((e) => e.entity_id === this.store.selected);
        if (mine.length) {
          this.detailEvents = [...mine.reverse(), ...this.detailEvents].slice(0, 100);
          this.renderDetailEvents();
        }
      }
    }
    if (kind === 'select') this.openDetail(payload);
  }

  tickSecond() {
    this.renderFreshness();
    if (this.store.selected) this.renderDetailFields();
  }

  // ------------------------------------------------------------ cabecera
  renderHeader() {
    const c = this.store.connection;
    const conn = $('conn');
    conn.className = `pill pill-${c}`;
    conn.textContent = c === 'open' ? 'Conectado' : c === 'reconnecting' ? 'Reconectando…' : 'Conectando…';
    const attn = [...this.store.entities.values()].filter(needsAttention).length;
    const a = $('attention');
    a.hidden = attn === 0;
    a.textContent = `⚠ ${attn} esperan tu respuesta`;
    this.renderFreshness();
  }

  renderFreshness() {
    const f = $('freshness');
    const last = this.store.lastDataAt();
    if (this.store.connection !== 'open') {
      f.textContent = 'Sin conexión: datos posiblemente obsoletos';
      f.className = 'pill pill-stale';
      return;
    }
    if (!last) {
      f.textContent = 'Sin datos todavía';
      f.className = 'pill';
      return;
    }
    const age = this.store.now() - last;
    f.textContent = `Último dato hace ${fmtAge(age)}`;
    const staleAfter = (this.store.config?.stale_after_seconds ?? 300) * 1000;
    f.className = age > staleAfter ? 'pill pill-stale' : 'pill';
  }

  // --------------------------------------------------------------- lista
  renderList() {
    const body = $('list-body');
    body.replaceChildren();
    const rows = [...this.store.entities.values()].sort((a, b) => (b.last_seen_at || '').localeCompare(a.last_seen_at || ''));
    for (const e of rows) {
      const tr = el(
        'tr',
        { tabindex: '0', onclick: () => this.store.select(e.id), onkeydown: (ev) => ev.key === 'Enter' && this.store.select(e.id) },
        el('td', {}, e.display_name, ...tagsFor(e)),
        el('td', {}, KIND[e.kind] || e.kind),
        el('td', {}, chip(e.status, e.detail)),
        el('td', {}, SOURCE[e.source] || e.source),
        el('td', {}, `${e.last_event_type || '—'} · ${fmtTime(e.last_seen_at)}`),
      );
      body.append(tr);
    }
    if (!rows.length) body.append(el('tr', {}, el('td', { colspan: '5' }, 'Sin entidades activas.')));
  }

  // ------------------------------------------------------------- detalle
  async openDetail(id) {
    const panel = $('detail');
    if (!id) {
      panel.hidden = true;
      return;
    }
    if (window.matchMedia('(max-width: 760px)').matches) this.togglePanel('events-panel', 'btn-events', false);
    panel.hidden = false;
    this.detailEvents = [];
    this.renderDetail();
    this.opts.scene()?.focus(id);
    try {
      const r = await getJSON(`/api/entities/${encodeURIComponent(id)}/events?limit=100`);
      if (this.store.selected === id) {
        this.detailEvents = r.events;
        this.renderDetailEvents();
      }
    } catch (err) {
      this.detailEvents = [];
      this.renderDetailEvents(String(err.message || err));
    }
  }

  renderDetail() {
    const id = this.store.selected;
    if (!id) return;
    const e = this.store.entities.get(id);
    if (!e) {
      $('d-name').textContent = 'Entidad archivada';
      $('d-fields').replaceChildren(el('dt', {}, 'Nota'), el('dd', {}, 'Ya no está activa; su historial se conserva.'));
      return;
    }
    $('d-name').replaceChildren(document.createTextNode(e.display_name), ...tagsFor(e));
    this.renderDetailFields();
    const rel = $('d-related');
    rel.replaceChildren();
    const related = [...this.store.entities.values()].filter((x) => x.parent_id === e.id || x.id === e.parent_id);
    for (const r of related) {
      const label = r.id === e.parent_id ? 'Padre' : KIND[r.kind] || r.kind;
      const assoc = r.association && r.kind === 'external_process' ? ` (${r.association.confidence === 'high' ? 'asociación directa' : 'asociación probable'})` : '';
      rel.append(el('li', {}, `${label}: `, el('button', { onclick: () => this.store.select(r.id) }, r.display_name), ` — ${statusInfo(r.status).label}${assoc}`));
    }
    if (!related.length) rel.append(el('li', {}, 'Ninguno'));
  }

  renderDetailFields() {
    const e = this.store.entities.get(this.store.selected);
    if (!e) return;
    const now = this.store.now();
    const since = e.status_since ? now - new Date(e.status_since).getTime() : null;
    const lastAge = e.last_seen_at ? now - new Date(e.last_seen_at).getTime() : null;
    const rows = [
      ['Tipo', KIND[e.kind] || e.kind],
      ['Identificador', e.session_id ? `${e.session_id.slice(0, 8)}…` : e.pid ? `PID ${e.pid}` : e.id],
      e.agent_id ? ['Agente', `${e.agent_type || '?'} (${e.agent_id.slice(0, 8)})`] : null,
      ['Estado', chip(e.status, e.detail)],
      ['Confianza', CONFIDENCE[e.confidence] || e.confidence],
      ['Fuente', SOURCE[e.source] || e.source],
      ['Motivo', e.reason || '—'],
      ['Herramienta', e.current_tool || '—'],
      ['Último evento', `${e.last_event_type || '—'} · ${fmtTime(e.last_seen_at)} (hace ${fmtAge(lastAge)})`],
      ['En este estado', fmtAge(since)],
      e.cwd ? ['Directorio', e.cwd] : null,
      e.kind === 'claude_session' ? ['Origen', [e.origin?.entrypoint || '¿?', e.origin?.remote_control ? 'Remote Control' : null, e.origin?.tmux ? 'tmux' : null, e.origin?.cloud ? 'nube' : null].filter(Boolean).join(' · ')] : null,
      e.kind === 'claude_session' && e.process_alive != null ? ['Proceso claude', e.process_alive ? `vivo (PID ${e.claude_pid})` : 'ya no existe'] : null,
      e.kind === 'external_process' ? ['Asociación', e.association ? `${e.association.reason} (${CONFIDENCE[e.association.confidence]})` : 'sin evidencia suficiente'] : null,
      e.counters ? ['Contadores', `${e.counters.events || 0} eventos · ${e.counters.tools || 0} herramientas · ${e.counters.errors || 0} errores`] : null,
    ].filter(Boolean);
    $('d-fields').replaceChildren(...rows.flatMap(([k, v]) => [el('dt', {}, k), el('dd', {}, v)]));
    const warn = $('d-stale');
    const staleMs = (this.store.config?.stale_after_seconds ?? 300) * 1000;
    let msg = null;
    if (this.store.connection !== 'open') msg = 'Sin conexión con el servidor: los datos pueden estar desactualizados.';
    else if (e.status === 'stale') msg = 'No llegan eventos de esta entidad: el estado es una inferencia.';
    else if (e.source === 'transcript') msg = 'Sesión sin hooks: el estado se infiere solo por la fecha del transcript.';
    else if (e.status === 'working' && lastAge > staleMs) msg = `Sin eventos desde hace ${fmtAge(lastAge)}${e.open_tools ? ' (hay una herramienta en curso)' : ''}.`;
    warn.hidden = !msg;
    warn.textContent = msg || '';
  }

  renderDetailEvents(error) {
    const list = $('d-events');
    const sel = $('d-filter');
    const types = [...new Set(this.detailEvents.map((e) => e.event_type))].sort();
    const cur = sel.value;
    sel.replaceChildren(el('option', { value: '' }, 'todos'), ...types.map((t) => el('option', { value: t }, t)));
    sel.value = types.includes(cur) ? cur : '';
    list.replaceChildren();
    if (error) {
      list.append(el('li', {}, `Error al cargar: ${error}`));
      return;
    }
    const evs = this.detailEvents.filter((e) => !sel.value || e.event_type === sel.value).slice(0, 60);
    for (const ev of evs) list.append(eventLine(ev, this.store));
    if (!evs.length) list.append(el('li', {}, 'Sin eventos.'));
  }

  // ------------------------------------------------------------- eventos
  renderEvents() {
    const src = $('e-source').value;
    const tsel = $('e-type');
    const types = [...new Set(this.store.events.map((e) => e.event_type))].sort();
    const cur = tsel.value;
    tsel.replaceChildren(el('option', { value: '' }, 'todos'), ...types.map((t) => el('option', { value: t }, t)));
    tsel.value = types.includes(cur) ? cur : '';
    const list = $('e-list');
    list.replaceChildren();
    const evs = this.store.events.filter((e) => (!src || e.source === src) && (!tsel.value || e.event_type === tsel.value)).slice(0, 150);
    for (const ev of evs) {
      const li = eventLine(ev, this.store);
      if (ev.entity_id) {
        li.style.cursor = 'pointer';
        li.addEventListener('click', () => this.store.select(ev.entity_id));
      }
      list.append(li);
    }
    if (!evs.length) list.append(el('li', {}, 'Sin eventos.'));
  }

  // ------------------------------------------------------------ diálogos
  openLegend() {
    const ul = $('legend-list');
    ul.replaceChildren(...Object.keys(STATUS).map((k) => el('li', {}, chip(k), ' ', legendText(k))));
    $('legend-dialog').showModal();
  }

  async openStatus() {
    const dl = $('status-fields');
    dl.replaceChildren(el('dt', {}, 'Cargando'), el('dd', {}, '…'));
    $('status-dialog').showModal();
    try {
      const h = await getJSON('/api/health');
      const s = h.sources;
      const rows = [
        ['Backend', `${h.status} · v${h.version} · ${fmtAge(h.uptime_seconds * 1000)} en marcha`],
        ['WebSocket', this.store.connection === 'open' ? 'conectado' : 'desconectado'],
        ['Modo', h.demo ? 'DEMO (base de datos separada)' : 'real'],
        ['Base de datos', `${h.database.ok ? 'OK' : 'ERROR'} · ${h.database.file} · ${h.database.events} eventos`],
        ['Hooks', s.hooks.enabled ? `último evento: ${s.hooks.last_event_at ? fmtTime(s.hooks.last_event_at) : 'nunca'} · líneas malformadas: ${s.hooks.malformed_lines}` : 'desactivado'],
        ['Hooks instalados', s.hooks.installed_for_events.length ? `${s.hooks.installed_for_events.length} eventos` : 'no detectados en ~/.claude/settings.json'],
        ['Procesos', s.process_monitor.enabled ? `último escaneo: ${fmtTime(s.process_monitor.last_scan_at)}` : 'desactivado'],
        ['claude sin hooks', String(s.process_monitor.claude_processes_without_hooks ?? 0)],
        ['Transcripts', s.transcripts.enabled ? `último escaneo: ${fmtTime(s.transcripts.last_scan_at)}` : 'desactivado'],
        ['Entidades activas', String(h.active_entities)],
      ];
      dl.replaceChildren(...rows.flatMap(([k, v]) => [el('dt', {}, k), el('dd', {}, v)]));
      const ul = $('status-errors');
      ul.replaceChildren(...(h.recent_errors.length ? h.recent_errors.map((e) => el('li', {}, `${e.component}: ${e.message}`)) : [el('li', {}, 'Ninguno')]));
    } catch (err) {
      dl.replaceChildren(el('dt', {}, 'Error'), el('dd', {}, String(err.message || err)));
    }
  }
}

function legendText(k) {
  return {
    working: 'hay actividad de herramienta o turno en curso (hook).',
    waiting: 'entre herramientas, o espera permiso/respuesta (naranja = requiere atención).',
    completed: 'fin de turno o agente terminado.',
    error: 'fallo explícito de herramienta (se muestra unos segundos).',
    idle: 'sin actividad observada; no implica descanso real (inferido).',
    running: 'proceso externo vivo.',
    exited: 'proceso externo terminado.',
    unknown: 'no hay datos suficientes.',
    stale: 'no llegan eventos durante el umbral configurado (inferido).',
  }[k];
}
