// Estado del cliente: espejo de lo que envía el backend. No decide estados.

const MAX_EVENTS = 300;

export class Store {
  constructor() {
    this.entities = new Map();
    this.events = [];
    this.health = null;
    this.config = null;
    this.connection = 'connecting';
    this.serverOffset = 0; // ms: server_time - Date.now()
    this.selected = null;
    this.listeners = new Set();
  }

  on(fn) {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  emit(kind, payload) {
    for (const fn of this.listeners) {
      try {
        fn(kind, payload);
      } catch (err) {
        console.error(err);
      }
    }
  }

  now() {
    return Date.now() + this.serverOffset;
  }

  setServerTime(iso) {
    if (iso) this.serverOffset = new Date(iso).getTime() - Date.now();
  }

  snapshot(msg) {
    this.entities = new Map(msg.entities.map((e) => [e.id, e]));
    this.events = (msg.events || []).slice(0, MAX_EVENTS);
    if (msg.health) this.health = { ...this.health, ...msg.health };
    this.setServerTime(msg.server_time);
    this.emit('snapshot');
  }

  upsert(list) {
    const changed = [];
    for (const e of list) {
      if (e.archived) this.entities.delete(e.id);
      else this.entities.set(e.id, e);
      changed.push(e);
    }
    this.emit('entities', changed);
  }

  addEvents(list) {
    const seen = new Set(this.events.map((e) => e.event_id));
    const fresh = list.filter((e) => !seen.has(e.event_id));
    if (!fresh.length) return;
    this.events = [...fresh.reverse(), ...this.events].slice(0, MAX_EVENTS);
    this.emit('events', fresh);
  }

  setConnection(state) {
    this.connection = state;
    this.emit('connection', state);
  }

  select(id) {
    this.selected = id;
    this.emit('select', id);
  }

  lastDataAt() {
    let t = 0;
    for (const e of this.entities.values()) {
      const v = e.last_seen_at ? new Date(e.last_seen_at).getTime() : 0;
      if (v > t) t = v;
    }
    return t || null;
  }
}
