// Geometría isométrica y distribución de zonas. Cambiar la oficina = editar
// este archivo; el backend solo asigna (zona, índice de puesto).

export const TILE_W = 64;
export const TILE_H = 32;
export const MAP_W = 22;
export const MAP_H = 15;

export function iso(x, y) {
  return { x: ((x - y) * TILE_W) / 2, y: ((x + y) * TILE_H) / 2 };
}

export const ZONES = {
  coordination: { x: 1, y: 1, w: 7, h: 5, cols: 3, label: 'Coordinación', floor: 0xead9b5 },
  agents: { x: 10, y: 1, w: 10, h: 6, cols: 4, label: 'Zona de agentes', floor: 0xd5e3c6 },
  lab: { x: 1, y: 8, w: 8, h: 6, cols: 4, label: 'Laboratorio de simulación', floor: 0xc8dbe7 },
  review: { x: 10, y: 9, w: 6, h: 5, cols: 3, label: 'Sala de revisión', floor: 0xe8d0da },
  break: { x: 17, y: 9, w: 4, h: 5, label: 'Zona de descanso', floor: 0xdcd2ea },
};

// Casilla del escritorio para (zona, puesto). Los índices por encima de la
// capacidad continúan en filas extra.
export function deskTile(zone, slot) {
  const z = ZONES[zone] || ZONES.agents;
  const col = slot % z.cols;
  const row = Math.floor(slot / z.cols);
  return { x: z.x + 1 + col * 2, y: z.y + 1 + row * 2 };
}

// Puestos de pie en la zona de descanso (para entidades inactivas).
export function breakSpot(i) {
  const z = ZONES.break;
  const spots = [
    [0.8, 1.6],
    [2.2, 1.2],
    [1.4, 2.8],
    [2.8, 2.6],
    [0.9, 3.8],
    [2.4, 4.0],
    [3.4, 3.4],
    [1.8, 0.6],
  ];
  const [dx, dy] = spots[i % spots.length];
  const ring = Math.floor(i / spots.length) * 0.3;
  return { x: z.x + dx + ring, y: z.y + dy + ring };
}

export function mapBounds() {
  const left = iso(0, MAP_H).x;
  const right = iso(MAP_W, 0).x;
  const top = iso(0, 0).y - 110;
  const bottom = iso(MAP_W, MAP_H).y + 20;
  return { left, right, top, bottom, width: right - left, height: bottom - top };
}
