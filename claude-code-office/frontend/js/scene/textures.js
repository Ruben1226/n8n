// Sprites provisionales originales, dibujados por código (sin assets de
// terceros). Para sustituirlos por arte final, carga imágenes con las mismas
// claves en preload() (ver README, «Sustituir sprites»).

function isoBox(g, cx, cy, hw, hh, h, top, left, right) {
  g.fillStyle(left, 1);
  g.fillPoints(
    [
      { x: cx - hw, y: cy - h },
      { x: cx, y: cy - h + hh },
      { x: cx, y: cy + hh },
      { x: cx - hw, y: cy },
    ],
    true,
  );
  g.fillStyle(right, 1);
  g.fillPoints(
    [
      { x: cx, y: cy - h + hh },
      { x: cx + hw, y: cy - h },
      { x: cx + hw, y: cy },
      { x: cx, y: cy + hh },
    ],
    true,
  );
  g.fillStyle(top, 1);
  g.fillPoints(
    [
      { x: cx, y: cy - h - hh },
      { x: cx + hw, y: cy - h },
      { x: cx, y: cy - h + hh },
      { x: cx - hw, y: cy - h },
    ],
    true,
  );
}

function make(scene, key, w, h, draw) {
  if (scene.textures.exists(key)) return;
  const g = scene.make.graphics({ x: 0, y: 0, add: false });
  draw(g, w, h);
  g.generateTexture(key, w, h);
  g.destroy();
}

export const ANCHOR = {}; // key -> originY para que la base quede en la casilla

export function buildTextures(scene, zones) {
  for (const [name, z] of Object.entries(zones)) {
    make(scene, `tile-${name}`, 64, 32, (g) => {
      g.fillStyle(z.floor, 1);
      g.fillPoints([{ x: 32, y: 0 }, { x: 64, y: 16 }, { x: 32, y: 32 }, { x: 0, y: 16 }], true);
      g.lineStyle(1, 0x000000, 0.08);
      g.strokePoints([{ x: 32, y: 0 }, { x: 64, y: 16 }, { x: 32, y: 32 }, { x: 0, y: 16 }], true);
    });
  }
  make(scene, 'tile-corridor', 64, 32, (g) => {
    g.fillStyle(0xcdbfa8, 1);
    g.fillPoints([{ x: 32, y: 0 }, { x: 64, y: 16 }, { x: 32, y: 32 }, { x: 0, y: 16 }], true);
    g.lineStyle(1, 0x000000, 0.06);
    g.strokePoints([{ x: 32, y: 0 }, { x: 64, y: 16 }, { x: 32, y: 32 }, { x: 0, y: 16 }], true);
  });

  // Escritorio con monitor (base en y=46 de 60).
  make(scene, 'desk', 72, 60, (g) => {
    isoBox(g, 36, 46, 30, 15, 16, 0xb98a5a, 0x8f6640, 0xa3774c);
    // Monitor
    g.fillStyle(0x2d2f36, 1);
    g.fillRect(27, 8, 22, 15);
    g.fillStyle(0x45474f, 1);
    g.fillRect(36, 23, 4, 6);
    g.fillRect(32, 28, 12, 2);
  });
  ANCHOR.desk = 46 / 60;

  make(scene, 'screen', 18, 11, (g) => {
    g.fillStyle(0xffffff, 1);
    g.fillRect(0, 0, 18, 11);
  });

  make(scene, 'chair', 30, 34, (g) => {
    isoBox(g, 15, 26, 10, 5, 8, 0x5a6a8a, 0x3f4b63, 0x4a5874);
    g.fillStyle(0x4a5874, 1);
    g.fillRect(6, 4, 18, 14);
  });
  ANCHOR.chair = 26 / 34;

  // Personaje: piezas blancas que se tiñen por entidad.
  make(scene, 'body', 22, 26, (g) => {
    g.fillStyle(0xffffff, 1);
    g.fillRoundedRect(2, 0, 18, 18, 6);
    g.fillStyle(0xdddddd, 1);
    g.fillRect(5, 17, 5, 9);
    g.fillRect(12, 17, 5, 9);
  });
  make(scene, 'head', 16, 16, (g) => {
    g.fillStyle(0xf2c9a0, 1);
    g.fillCircle(8, 8, 7.5);
  });
  make(scene, 'hair', 16, 9, (g) => {
    g.fillStyle(0xffffff, 1);
    g.fillEllipse(8, 5, 16, 10);
  });
  make(scene, 'shadow', 30, 12, (g) => {
    g.fillStyle(0x000000, 0.18);
    g.fillEllipse(15, 6, 30, 12);
  });
  make(scene, 'ring', 46, 22, (g) => {
    g.lineStyle(3, 0xffffff, 1);
    g.strokeEllipse(23, 11, 42, 18);
  });

  // Máquina del laboratorio (proceso externo).
  make(scene, 'rack', 56, 84, (g) => {
    isoBox(g, 28, 70, 22, 11, 52, 0x6c7488, 0x3c4252, 0x4c5366);
    g.fillStyle(0x1d2030, 1);
    g.fillPoints([{ x: 30, y: 30 }, { x: 48, y: 21 }, { x: 48, y: 38 }, { x: 30, y: 47 }], true);
  });
  ANCHOR.rack = 70 / 84;
  make(scene, 'led', 6, 6, (g) => {
    g.fillStyle(0xffffff, 1);
    g.fillCircle(3, 3, 2.5);
  });

  // Decoración
  make(scene, 'plant', 34, 52, (g) => {
    isoBox(g, 17, 44, 9, 4.5, 10, 0xb5643c, 0x8c4a2b, 0x9e5533);
    g.fillStyle(0x3f9a54, 1);
    g.fillCircle(17, 20, 10);
    g.fillStyle(0x52b56a, 1);
    g.fillCircle(11, 26, 7);
    g.fillCircle(23, 25, 7);
    g.fillCircle(17, 12, 6);
  });
  ANCHOR.plant = 44 / 52;
  make(scene, 'coffee', 44, 62, (g) => {
    isoBox(g, 22, 52, 18, 9, 22, 0xd8d8d8, 0xa9a9a9, 0xbdbdbd);
    isoBox(g, 22, 30, 11, 5.5, 22, 0x3a3a3a, 0x222222, 0x2e2e2e);
    g.fillStyle(0xe14b3b, 1);
    g.fillCircle(27, 22, 2);
    g.fillStyle(0xffffff, 1);
    g.fillRect(19, 33, 6, 6);
  });
  ANCHOR.coffee = 52 / 62;
  make(scene, 'sofa', 84, 50, (g) => {
    isoBox(g, 42, 38, 36, 18, 12, 0x7e5fb8, 0x5d4590, 0x6c51a3);
    isoBox(g, 30, 26, 24, 12, 14, 0x8d6fc8, 0x5d4590, 0x6c51a3);
  });
  ANCHOR.sofa = 38 / 50;
  make(scene, 'board', 70, 70, (g) => {
    g.fillStyle(0x8a8f99, 1);
    g.fillPoints([{ x: 4, y: 30 }, { x: 66, y: 0 }, { x: 66, y: 34 }, { x: 4, y: 64 }], true);
    g.fillStyle(0xfafafa, 1);
    g.fillPoints([{ x: 7, y: 31 }, { x: 63, y: 4 }, { x: 63, y: 32 }, { x: 7, y: 59 }], true);
    g.lineStyle(2, 0x4a90d9, 1);
    g.lineBetween(14, 40, 40, 26);
    g.lineStyle(2, 0xe0524a, 1);
    g.lineBetween(16, 48, 52, 30);
    g.lineStyle(2, 0x3fae6a, 1);
    g.lineBetween(20, 52, 34, 45);
  });
  ANCHOR.board = 64 / 70;
  make(scene, 'cabinet', 40, 66, (g) => {
    isoBox(g, 20, 56, 16, 8, 40, 0x9aa3ad, 0x6f7781, 0x838c96);
    g.lineStyle(1, 0x50565e, 1);
    for (let i = 0; i < 3; i++) g.lineBetween(4, 26 + i * 12, 20, 34 + i * 12);
  });
  ANCHOR.cabinet = 56 / 66;
}
