// HTTP de solo lectura + WebSocket con reconexión exponencial.

export async function getJSON(path) {
  const res = await fetch(path, { headers: { Accept: 'application/json' }, cache: 'no-store' });
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return res.json();
}

export function connect(store) {
  let delay = 1000;
  let ws = null;
  let watchdog = null;

  const armWatchdog = () => {
    clearTimeout(watchdog);
    // El servidor envía heartbeat cada 10 s; sin nada en 30 s se reconecta.
    watchdog = setTimeout(() => ws && ws.close(), 30000);
  };

  const open = () => {
    store.setConnection(store.connection === 'open' ? 'reconnecting' : store.connection);
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${proto}//${location.host}/ws`);
    ws.onopen = () => {
      delay = 1000;
      store.setConnection('open');
      armWatchdog();
    };
    ws.onmessage = (m) => {
      armWatchdog();
      let msg;
      try {
        msg = JSON.parse(m.data);
      } catch {
        return;
      }
      if (msg.type === 'snapshot') store.snapshot(msg);
      else if (msg.type === 'entities') store.upsert(msg.entities);
      else if (msg.type === 'events') store.addEvents(msg.events);
      else if (msg.type === 'heartbeat') {
        store.setServerTime(msg.server_time);
        store.health = { ...store.health, ...msg.health };
        store.emit('heartbeat');
      }
    };
    ws.onclose = () => {
      clearTimeout(watchdog);
      store.setConnection('reconnecting');
      setTimeout(open, delay + Math.random() * 500);
      delay = Math.min(delay * 2, 30000);
    };
    ws.onerror = () => ws.close();
  };

  open();
}
