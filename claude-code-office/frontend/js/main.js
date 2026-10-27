import { connect, getJSON } from './api.js';
import { Store } from './store.js';
import { UI } from './ui.js';

const store = new Store();
let scene = null;
let game = null;

function storageGet(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function storageSet(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* almacenamiento no disponible: preferencia solo en memoria */
  }
}

const systemReduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
let reduceMotion = storageGet('office.reduceMotion') === null ? systemReduce : storageGet('office.reduceMotion') === '1';

const ui = new UI(store, {
  scene: () => scene,
  setScenePaused: (paused) => {
    if (!game) return;
    if (paused) game.loop.sleep();
    else if (!document.hidden) game.loop.wake();
  },
  onMotion: () => {
    reduceMotion = !reduceMotion;
    storageSet('office.reduceMotion', reduceMotion ? '1' : '0');
    ui.setMotionLabel(reduceMotion);
    scene?.syncAll();
  },
});
ui.setMotionLabel(reduceMotion);

async function boot() {
  try {
    store.config = await getJSON('/api/config/public');
    ui.applyConfig(store.config);
    if (store.config.reduce_motion) reduceMotion = true;
    ui.setMotionLabel(reduceMotion);
  } catch (err) {
    console.warn('config', err);
  }
  connect(store);
  try {
    if (!window.Phaser) throw new Error('Phaser no disponible');
    const mod = await import('./scene/office-scene.js');
    const { scene: s, game: g } = mod.startGame(document.getElementById('game'), store, {
      reduceMotion: () => reduceMotion,
      theme: store.config?.theme,
    });
    scene = s;
    game = g;
  } catch (err) {
    // Alternativa accesible si el renderizado gráfico falla.
    console.error('Escena no disponible', err);
    ui.toggleList(true);
    document.getElementById('btn-view').disabled = true;
  }
}

boot();
