// Escena Phaser: dibuja la oficina y refleja los estados que envía el backend.
// No contiene lógica de monitorización: solo traduce estado -> animación.

import { entityHue, needsAttention, originTags, statusInfo } from '../status.js';
import { ANCHOR, buildTextures } from './textures.js';
import { MAP_H, MAP_W, ZONES, breakSpot, deskTile, iso, mapBounds } from './iso.js';

const Phaser = window.Phaser;

function hexToInt(hex) {
  return parseInt(hex.slice(1), 16);
}

function hslInt(h, s, l) {
  const c = Phaser.Display.Color.HSLToColor(h / 360, s, l);
  return c.color;
}

function inZone(x, y) {
  for (const [name, z] of Object.entries(ZONES)) {
    if (x >= z.x && x < z.x + z.w && y >= z.y && y < z.y + z.h) return name;
  }
  return null;
}

export class OfficeScene extends Phaser.Scene {
  constructor(store, opts) {
    super('office');
    this.store = store;
    this.opts = opts; // { reduceMotion: () => bool }
    this.actors = new Map();
  }

  create() {
    buildTextures(this, ZONES);
    this.drawFloor();
    this.drawWalls();
    this.drawDecor();
    this.setupCamera();
    this.unsub = this.store.on((kind, payload) => {
      if (kind === 'snapshot') this.syncAll();
      else if (kind === 'entities') this.syncAll();
      else if (kind === 'select') this.updateSelection();
    });
    this.syncAll();
    this.time.addEvent({ delay: 450, loop: true, callback: () => this.ambientTick() });
    this.events.once('shutdown', () => this.unsub && this.unsub());
  }

  // --------------------------------------------------------------- mundo
  drawFloor() {
    for (let y = 0; y < MAP_H; y++) {
      for (let x = 0; x < MAP_W; x++) {
        const p = iso(x, y);
        const z = inZone(x, y);
        this.add.image(p.x, p.y, z ? `tile-${z}` : 'tile-corridor').setOrigin(0.5, 0).setDepth(-10000);
      }
    }
    for (const z of Object.values(ZONES)) {
      const p = iso(z.x + z.w, z.y + z.h / 2);
      this.add
        .text(p.x + 6, p.y - 4, z.label.toUpperCase(), {
          fontFamily: 'system-ui, sans-serif',
          fontSize: '11px',
          fontStyle: 'bold',
          color: '#5b4b3a',
        })
        .setOrigin(0, 0.5)
        .setAlpha(0.6)
        .setResolution(2)
        .setDepth(-9000);
    }
  }

  drawWalls() {
    const g = this.add.graphics().setDepth(-9500);
    const H = 90;
    const a = iso(0, 0);
    const b = iso(MAP_W, 0);
    const c = iso(0, MAP_H);
    g.fillStyle(0xf3e6cf, 1);
    g.fillPoints([{ x: a.x, y: a.y - H }, { x: b.x, y: b.y - H }, { x: b.x, y: b.y }, { x: a.x, y: a.y }], true);
    g.fillStyle(0xe6d5b8, 1);
    g.fillPoints([{ x: a.x, y: a.y - H }, { x: c.x, y: c.y - H }, { x: c.x, y: c.y }, { x: a.x, y: a.y }], true);
    // Ventanas en la pared derecha
    g.fillStyle(0xbfe0f2, 1);
    for (let i = 2; i < MAP_W - 1; i += 4) {
      const p = iso(i, 0);
      const q = iso(i + 2, 0);
      g.fillPoints([{ x: p.x, y: p.y - 70 }, { x: q.x, y: q.y - 70 }, { x: q.x, y: q.y - 30 }, { x: p.x, y: p.y - 30 }], true);
    }
    g.lineStyle(2, 0xcdb895, 1);
    g.lineBetween(a.x, a.y, b.x, b.y);
    g.lineBetween(a.x, a.y, c.x, c.y);
  }

  placeImage(key, tx, ty) {
    const p = iso(tx, ty);
    return this.add
      .image(p.x, p.y, key)
      .setOrigin(0.5, ANCHOR[key] ?? 0.9)
      .setDepth(p.y);
  }

  drawDecor() {
    const b = ZONES.break;
    this.placeImage('coffee', b.x + 3.4, b.y + 0.6);
    this.placeImage('sofa', b.x + 1.6, b.y + 4.4);
    this.placeImage('plant', b.x + 0.4, b.y + 0.4);
    this.placeImage('plant', ZONES.coordination.x + 6.5, ZONES.coordination.y + 0.4);
    this.placeImage('plant', ZONES.lab.x + 7.5, ZONES.lab.y + 5.5);
    this.placeImage('cabinet', ZONES.coordination.x + 0.4, ZONES.coordination.y + 4.6);
    this.placeImage('cabinet', ZONES.lab.x + 0.4, ZONES.lab.y + 0.4);
    const rb = iso(ZONES.review.x + 2.5, ZONES.review.y + 0.2);
    this.add.image(rb.x, rb.y, 'board').setOrigin(0.5, ANCHOR.board).setDepth(rb.y);
    const cb = iso(ZONES.coordination.x + 3.5, ZONES.coordination.y - 0.1);
    this.add.image(cb.x, cb.y, 'board').setOrigin(0.5, ANCHOR.board).setDepth(cb.y);
  }

  // -------------------------------------------------------------- cámara
  setupCamera() {
    const cam = this.cameras.main;
    const b = mapBounds();
    cam.setBounds(b.left - 400, b.top - 300, b.width + 800, b.height + 600);
    this.fitView();
    this.scale.on('resize', () => this.fitView());
    this.input.addPointer(1);
    let drag = null;
    let pinch = null;
    this.dragged = false;
    this.input.on('pointerdown', (p) => {
      drag = { x: p.x, y: p.y, sx: cam.scrollX, sy: cam.scrollY };
      this.dragged = false;
    });
    this.input.on('pointermove', (p) => {
      const p1 = this.input.pointer1;
      const p2 = this.input.pointer2;
      if (p1.isDown && p2.isDown) {
        const d = Phaser.Math.Distance.Between(p1.x, p1.y, p2.x, p2.y);
        if (!pinch) pinch = { d, z: cam.zoom };
        cam.setZoom(Phaser.Math.Clamp((pinch.z * d) / pinch.d, 0.35, 2.5));
        this.dragged = true;
        return;
      }
      pinch = null;
      if (!drag || !p.isDown) return;
      const dx = p.x - drag.x;
      const dy = p.y - drag.y;
      if (Math.abs(dx) + Math.abs(dy) > 6) this.dragged = true;
      if (this.dragged) {
        cam.scrollX = drag.sx - dx / cam.zoom;
        cam.scrollY = drag.sy - dy / cam.zoom;
      }
    });
    this.input.on('pointerup', (p, over) => {
      if (!this.dragged && (!over || over.length === 0)) this.store.select(null);
      drag = null;
    });
    this.input.on('wheel', (p, over, dx, dy) => {
      cam.setZoom(Phaser.Math.Clamp(cam.zoom * (dy > 0 ? 0.9 : 1.1), 0.35, 2.5));
    });
  }

  fitView() {
    const cam = this.cameras.main;
    const b = mapBounds();
    const fitW = this.scale.width / (b.width + 40);
    const fitH = this.scale.height / (b.height + 40);
    // En vertical (móvil) se prioriza el tamaño: la oficina se recorre arrastrando.
    const z = this.scale.width < 640 ? Math.min(fitH, fitW * 2) : Math.min(fitW, fitH);
    cam.setZoom(Phaser.Math.Clamp(z, 0.35, 1.6));
    cam.centerOn(b.left + b.width / 2, b.top + b.height / 2);
  }

  zoomBy(f) {
    const cam = this.cameras.main;
    cam.setZoom(Phaser.Math.Clamp(cam.zoom * f, 0.35, 2.5));
  }

  focus(id) {
    const a = this.actors.get(id);
    if (a) this.cameras.main.pan(a.root.x, a.root.y - 20, this.opts.reduceMotion() ? 0 : 400, 'Sine.easeInOut');
  }

  // -------------------------------------------------------------- actores
  syncAll() {
    const ents = this.store.entities;
    for (const [id, a] of this.actors) {
      if (!ents.has(id)) {
        this.destroyActor(a);
        this.actors.delete(id);
      }
    }
    let idleIdx = 0;
    const sorted = [...ents.values()].sort((a, b) => a.id.localeCompare(b.id));
    for (const e of sorted) {
      let a = this.actors.get(e.id);
      if (!a) {
        a = e.kind === 'external_process' ? this.createMachine(e) : this.createPerson(e);
        this.actors.set(e.id, a);
      }
      const goBreak = e.kind !== 'external_process' && e.status === 'idle';
      this.updateActor(a, e, goBreak ? idleIdx++ : -1);
    }
    this.updateSelection();
  }

  deskPos(e) {
    const d = e.desk || { zone: 'agents', slot: 0 };
    return deskTile(d.zone, d.slot);
  }

  makeBubble(x, y) {
    const t = this.add
      .text(x, y, '', {
        fontFamily: 'system-ui, sans-serif',
        fontSize: '11px',
        color: '#ffffff',
        backgroundColor: '#555555',
        padding: { x: 5, y: 2 },
      })
      .setOrigin(0.5, 1)
      .setResolution(2);
    return t;
  }

  makeLabel(x, y) {
    return this.add
      .text(x, y, '', {
        fontFamily: 'system-ui, sans-serif',
        fontSize: '10px',
        color: '#2b2b2b',
        backgroundColor: 'rgba(255,255,255,0.78)',
        padding: { x: 4, y: 1 },
      })
      .setOrigin(0.5, 0)
      .setResolution(2);
  }

  createPerson(e) {
    const t = this.deskPos(e);
    const dp = iso(t.x, t.y);
    const desk = this.add.image(dp.x, dp.y, 'desk').setOrigin(0.5, ANCHOR.desk).setDepth(dp.y);
    const screen = this.add.image(dp.x, dp.y - 31, 'screen').setDepth(dp.y + 0.1);
    const hue = entityHue(e.id);
    const seat = iso(t.x + 0.05, t.y + 0.8);
    const root = this.add.container(seat.x, seat.y).setDepth(seat.y);
    const ring = this.add.image(0, 0, 'ring').setVisible(false);
    const attn = this.add.image(0, 0, 'ring').setTint(0xff8a1f).setVisible(false);
    const shadow = this.add.image(0, 0, 'shadow');
    const body = this.add.image(0, -13, 'body').setTint(hslInt(hue, 0.55, e.kind === 'subagent' ? 0.62 : 0.5));
    const head = this.add.image(0, -32, 'head');
    const hair = this.add.image(0, -37, 'hair').setTint(hslInt((hue + 140) % 360, 0.4, 0.28));
    const bodyGroup = this.add.container(0, 0, [body, head, hair]);
    if (e.kind === 'claude_session') {
      // Distintivo de coordinación: pequeña insignia dorada
      const badge = this.add.circle(6, -18, 2.5, 0xf2c14e);
      bodyGroup.add(badge);
    }
    root.add([ring, attn, shadow, bodyGroup]);
    const bubble = this.makeBubble(seat.x, seat.y - 46);
    const label = this.makeLabel(seat.x, seat.y + 6);
    root.setSize(34, 50);
    root.setInteractive(new Phaser.Geom.Rectangle(-17, -48, 34, 54), Phaser.Geom.Rectangle.Contains);
    root.on('pointerup', () => {
      if (!this.dragged) this.store.select(e.id);
    });
    desk.setInteractive({ useHandCursor: true }).on('pointerup', () => {
      if (!this.dragged) this.store.select(e.id);
    });
    return { kind: 'person', id: e.id, desk, screen, root, ring, attn, bodyGroup, bubble, label, tweens: [], lastKey: null, deskTile: t, at: 'desk' };
  }

  createMachine(e) {
    const t = this.deskPos(e);
    const p = iso(t.x, t.y);
    const root = this.add.container(p.x, p.y).setDepth(p.y);
    const ring = this.add.image(0, 2, 'ring').setVisible(false).setScale(1.3);
    const attn = this.add.image(0, 2, 'ring').setVisible(false);
    const rack = this.add.image(0, 0, 'rack').setOrigin(0.5, ANCHOR.rack);
    const leds = [0, 1, 2].map((i) => this.add.image(-14 + i * 6, -40 + i * 3, 'led'));
    const chart = this.add.graphics();
    root.add([ring, attn, rack, ...leds, chart]);
    const bubble = this.makeBubble(p.x, p.y - 80);
    const label = this.makeLabel(p.x, p.y + 14);
    root.setSize(50, 80);
    root.setInteractive(new Phaser.Geom.Rectangle(-25, -75, 50, 85), Phaser.Geom.Rectangle.Contains);
    root.on('pointerup', () => {
      if (!this.dragged) this.store.select(e.id);
    });
    return { kind: 'machine', id: e.id, root, ring, attn, rack, leds, chart, bubble, label, tweens: [], lastKey: null, series: [], deskTile: t };
  }

  destroyActor(a) {
    this.stopTweens(a);
    for (const k of ['desk', 'screen', 'bubble', 'label', 'root']) a[k] && a[k].destroy();
  }

  stopTweens(a) {
    for (const tw of a.tweens) tw.remove();
    a.tweens = [];
    if (a.bodyGroup) {
      a.bodyGroup.setPosition(0, 0);
      a.bodyGroup.setScale(1);
    }
  }

  updateActor(a, e, breakIdx) {
    const info = statusInfo(e.status);
    const color = hexToInt(info.color);
    const reduce = this.opts.reduceMotion();
    const t = this.deskPos(e);

    // Si cambia el puesto (p. ej. tras archivar/reactivar) se reubica.
    if (t.x !== a.deskTile.x || t.y !== a.deskTile.y) {
      a.deskTile = t;
      const p = iso(t.x, t.y);
      if (a.kind === 'machine') {
        a.root.setPosition(p.x, p.y).setDepth(p.y);
      } else {
        a.desk.setPosition(p.x, p.y).setDepth(p.y);
        a.screen.setPosition(p.x, p.y - 31).setDepth(p.y + 0.1);
        a.at = null;
      }
    }

    const tags = originTags(e);
    a.label.setText(`${e.display_name}${tags.length ? '  [' + tags.join(', ') + ']' : ''}`);
    const bubbleText = e.kind === 'external_process' ? `${info.icon} ${info.label}` : `${info.icon} ${e.current_tool && e.status === 'working' ? e.current_tool : info.label}`;
    a.bubble.setText(bubbleText);
    a.bubble.setBackgroundColor(info.color);
    a.attn.setVisible(needsAttention(e));

    if (a.kind === 'person') {
      a.screen.setTint(e.status === 'working' ? 0x9fe3b0 : e.status === 'error' ? 0xff8a80 : e.status === 'idle' || e.status === 'stale' ? 0x50535c : 0xbcd7f5);
      const dim = e.status === 'stale' || e.status === 'unknown' || (e.status === 'completed' && e.ended);
      a.root.setAlpha(dim ? 0.65 : 1);
      // Posición: escritorio o zona de descanso
      const target = breakIdx >= 0 ? breakSpot(breakIdx) : { x: t.x + 0.05, y: t.y + 0.8 };
      const where = breakIdx >= 0 ? `break${breakIdx}` : 'desk';
      if (a.at !== where) {
        a.at = where;
        const p = iso(target.x, target.y);
        if (a.walk) a.walk.remove();
        const move = (x, y) => {
          a.root.setPosition(x, y).setDepth(y);
          a.bubble.setPosition(x, y - 46).setDepth(y + 1000);
          a.label.setPosition(x, y + 6).setDepth(y + 999);
        };
        if (reduce || !a.placed) move(p.x, p.y);
        else {
          const from = { x: a.root.x, y: a.root.y };
          const dist = Phaser.Math.Distance.Between(from.x, from.y, p.x, p.y);
          const proxy = { t: 0 };
          a.walk = this.tweens.add({
            targets: proxy,
            t: 1,
            duration: Math.min(4000, dist * 6),
            ease: 'Sine.easeInOut',
            onUpdate: () => move(from.x + (p.x - from.x) * proxy.t, from.y + (p.y - from.y) * proxy.t + Math.sin(proxy.t * Math.PI * 10) * -1.5),
          });
        }
        a.placed = true;
      }
    } else {
      a.rack.setTint(e.status === 'running' ? 0xffffff : 0x9a9aa6);
      for (const l of a.leds) l.setTint(e.status === 'running' ? 0x6dff9a : 0x555555);
      a.bubble.setDepth(a.root.y + 1000);
      a.label.setDepth(a.root.y + 999);
      a.root.setAlpha(e.status === 'exited' ? 0.6 : 1);
      if (e.status !== 'running') a.chart.clear();
    }

    const key = `${e.status}|${e.detail}|${reduce}|${a.at}`;
    if (key === a.lastKey) return;
    const prev = a.lastKey;
    a.lastKey = key;
    this.stopTweens(a);
    if (reduce || a.kind !== 'person') return;
    const g = a.bodyGroup;
    const r = 0.85 + Math.random() * 0.3; // variación para no sincronizar a todos
    switch (e.status) {
      case 'working':
        a.tweens.push(this.tweens.add({ targets: g, y: -1.6, duration: 170 * r, yoyo: true, repeat: -1, ease: 'Sine.easeInOut' }));
        break;
      case 'waiting':
      case 'idle':
        a.tweens.push(this.tweens.add({ targets: g, scaleY: 1.025, duration: 1500 * r, yoyo: true, repeat: -1, ease: 'Sine.easeInOut' }));
        break;
      case 'completed':
        if (prev && !prev.startsWith('completed')) {
          a.tweens.push(this.tweens.add({ targets: g, y: -9, duration: 200, yoyo: true, repeat: 1, ease: 'Quad.easeOut' }));
          this.sparkle(a.root.x, a.root.y - 50, '✓', '#4a90d9');
        }
        break;
      case 'error':
        a.tweens.push(this.tweens.add({ targets: g, x: 2, duration: 60, yoyo: true, repeat: 5 }));
        this.sparkle(a.root.x, a.root.y - 50, '!', '#e0524a');
        break;
      default:
        break;
    }
    if (needsAttention(e)) {
      a.tweens.push(this.tweens.add({ targets: a.attn, scale: 1.25, alpha: 0.4, duration: 700, yoyo: true, repeat: -1 }));
    }
  }

  sparkle(x, y, glyph, color) {
    if (this.opts.reduceMotion()) return;
    const t = this.add.text(x, y, glyph, { fontFamily: 'system-ui', fontSize: '18px', color, fontStyle: 'bold' }).setOrigin(0.5).setDepth(1e6).setResolution(2);
    this.tweens.add({ targets: t, y: y - 26, alpha: 0, duration: 1100, onComplete: () => t.destroy() });
  }

  updateSelection() {
    for (const [id, a] of this.actors) a.ring.setVisible(id === this.store.selected).setTint(0x2f7de1);
  }

  // Actividad ambiental de pantallas y máquinas (solo decorativa, ligada al estado).
  ambientTick() {
    const reduce = this.opts.reduceMotion();
    for (const [id, a] of this.actors) {
      const e = this.store.entities.get(id);
      if (!e) continue;
      if (a.kind === 'person' && e.status === 'working' && !reduce) {
        a.screen.setAlpha(0.75 + Math.random() * 0.25);
      } else if (a.kind === 'person') {
        a.screen.setAlpha(1);
      } else if (a.kind === 'machine' && e.status === 'running') {
        a.series.push(Math.random());
        if (a.series.length > 8) a.series.shift();
        a.chart.clear();
        a.chart.lineStyle(1.5, 0x6dff9a, 1);
        a.chart.beginPath();
        a.series.forEach((v, i) => {
          const x = 3 + i * 2;
          const y = -22 - i * 1.0 - v * 8;
          if (i === 0) a.chart.moveTo(x, y);
          else a.chart.lineTo(x, y);
        });
        a.chart.strokePath();
        if (!reduce) a.leds.forEach((l) => l.setAlpha(Math.random() > 0.3 ? 1 : 0.3));
      }
    }
  }
}

export function startGame(container, store, opts) {
  const scene = new OfficeScene(store, opts);
  const game = new Phaser.Game({
    type: Phaser.AUTO,
    parent: container,
    backgroundColor: opts.theme === 'night' ? '#1f2230' : '#f6efe3',
    scale: { mode: Phaser.Scale.RESIZE, width: container.clientWidth, height: container.clientHeight },
    fps: { target: 30, limit: 30 },
    render: { antialias: true, powerPreference: 'low-power' },
    banner: false,
    scene,
  });
  document.addEventListener('visibilitychange', () => {
    // Sin pestaña visible no se dibuja: ahorro de CPU/batería.
    if (document.hidden) game.loop.sleep();
    else if (document.getElementById('list-view')?.hidden !== false) game.loop.wake();
  });
  return { game, scene };
}

