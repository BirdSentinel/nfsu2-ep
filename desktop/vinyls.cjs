// PNGs remain the user's source files. VPX1 is an in-memory transport to the
// WASM decompression hook, never a modification of the original VINYLS.BIN.
const fs = require('node:fs');
const crypto = require('node:crypto');
function hashName(name) {
  let h = 0xffffffff;
  for (const c of Buffer.from(name, 'ascii')) h = (Math.imul(h, 33) + c) >>> 0;
  return h;
}
function keysOfArchive(b) {
  const keys = new Set();
  function walk(start, end, depth) {
    if (depth > 8) throw Error('Archive nesting is too deep');
    for (let p = start; p < end;) {
      if (p + 8 > end) throw Error('Truncated archive header');
      const id = b.readUInt32LE(p), size = b.readUInt32LE(p + 4), next = p + 8 + size;
      if (next > end) throw Error('Truncated archive chunk');
      if (id === 0x33310003) {
        if (size % 24) throw Error('Invalid texture index');
        for (let q = p + 8; q < next; q += 24) keys.add(b.readUInt32LE(q));
      } else if (id & 0x80000000) walk(p + 8, next, depth + 1);
      p = next;
    }
  }
  walk(0, b.length, 0);
  return keys;
}

// Adaptive RGB palette: a 5-bit histogram, split along its widest color axis.
// Transparency lives in the paired mask, not in the artwork's palette alpha.
function paletteOf(rgba) {
  const hist = new Map();
  for (let i = 0; i < rgba.length; i += 4) {
    if (!rgba[i + 3]) continue;
    const key = (rgba[i] >> 3) << 10 | (rgba[i + 1] >> 3) << 5 | (rgba[i + 2] >> 3);
    let c = hist.get(key);
    if (!c) { c = [0, 0, 0, 0]; hist.set(key, c); }
    c[0] += rgba[i]; c[1] += rgba[i + 1]; c[2] += rgba[i + 2]; c[3]++;
  }
  const colors = [...hist.values()].map(c => [c[0] / c[3], c[1] / c[3], c[2] / c[3], c[3]]);
  if (!colors.length) return [[0, 0, 0]];
  const box = items => {
    const ranges = [0, 1, 2].map(k => Math.max(...items.map(c => c[k])) - Math.min(...items.map(c => c[k])));
    const axis = ranges.indexOf(Math.max(...ranges));
    return { items, axis, score: ranges[axis] * items.reduce((n, c) => n + c[3], 0) };
  };
  const boxes = [box(colors)];
  while (boxes.length < 256) {
    boxes.sort((a, b) => b.score - a.score);
    const b = boxes.find(b => b.items.length > 1);
    if (!b) break;
    boxes.splice(boxes.indexOf(b), 1);
    b.items.sort((a, c) => a[b.axis] - c[b.axis]);
    const half = b.items.reduce((n, c) => n + c[3], 0) / 2;
    let sum = 0, split = 1;
    for (; split < b.items.length; split++) { sum += b.items[split - 1][3]; if (sum >= half) break; }
    split = Math.min(split, b.items.length - 1);
    boxes.push(box(b.items.slice(0, split)), box(b.items.slice(split)));
  }
  return boxes.map(b => {
    const count = b.items.reduce((n, c) => n + c[3], 0);
    return [0, 1, 2].map(k => Math.round(b.items.reduce((n, c) => n + c[k] * c[3], 0) / count));
  });
}
function encode(rgba, mask = false) {
  const SIZE = Math.sqrt(rgba.length / 4);
  if (SIZE !== 512 && SIZE !== 1024) throw Error('Expected 512x512 or 1024x1024 RGBA pixels');
  const LEVELS = SIZE === 1024 ? 8 : 7;
  let PIXELS = 0; for (let w = SIZE, l = 0; l < LEVELS; l++, w /= 2) PIXELS += w * w;
  const palette = mask ? Array.from({ length: 256 }, (_, i) => [i, i, i]) : paletteOf(rgba);
  const result = Buffer.alloc(16 + PIXELS + 1024);
  result.write('VPX1'); result.writeUInt32LE(SIZE, 4); result.writeUInt32LE(SIZE, 8); result.writeUInt32LE(LEVELS, 12);
  palette.forEach((c, i) => { const p = 16 + PIXELS + i * 4; result[p] = c[2]; result[p + 1] = c[1]; result[p + 2] = c[0]; result[p + 3] = mask ? 255 : 0; });
  const nearest = new Map();
  let src = rgba, w = SIZE, at = 16;
  for (let level = 0; level < LEVELS; level++) {
    for (let i = 0; i < src.length; i += 4) {
      if (mask) { result[at++] = src[i + 3]; continue; }
      const key = src[i] << 16 | src[i + 1] << 8 | src[i + 2];
      let ix = nearest.get(key);
      if (ix === undefined) {
        let best = Infinity; ix = 0;
        palette.forEach((c, k) => { const d = (c[0] - src[i]) ** 2 + (c[1] - src[i + 1]) ** 2 + (c[2] - src[i + 2]) ** 2; if (d < best) { best = d; ix = k; } });
        nearest.set(key, ix);
      }
      result[at++] = ix;
    }
    const nw = w / 2, next = Buffer.alloc(nw * nw * 4);
    for (let y = 0; y < nw; y++) for (let x = 0; x < nw; x++) {
      const dst = (y * nw + x) * 4, positions = [(2*y*w+2*x)*4, (2*y*w+2*x+1)*4, ((2*y+1)*w+2*x)*4, ((2*y+1)*w+2*x+1)*4];
      const alpha = positions.reduce((n, p) => n + src[p + 3], 0);
      next[dst + 3] = Math.round(alpha / 4);
      for (let c = 0; c < 3; c++) next[dst + c] = alpha ? Math.round(positions.reduce((n, p) => n + src[p + c] * src[p + 3], 0) / alpha) : 0;
    }
    src = next; w = nw;
  }
  return result;
}

function prepareVinyls(data, decodePNG) {
  const originals = [...data.files.entries()];
  const archives = new Map(), prepared = new Map(), notes = [];
  for (const [rel, file] of originals) {
    const m = /^cars\/([a-z0-9_]+)\/vinyls\/([a-z0-9_]+)\.png$/i.exec(rel);
    if (!m) continue;
    const car = m[1].toUpperCase(), name = m[2].toUpperCase();
    try {
      if (name.length > 24 || !name.startsWith(car + '_')) throw Error(`Texture name must start with ${car}_ and fit 24 characters`);
      if (name.endsWith('_MASK')) throw Error('Use one artwork PNG with transparency; its mask is generated automatically');
      let keys = archives.get(car);
      if (!keys) {
        const archive = data.files.get(`cars/${car.toLowerCase()}/vinyls.bin`);
        if (!archive) throw Error('VINYLS.BIN is missing');
        keys = keysOfArchive(fs.readFileSync(archive.abs)); archives.set(car, keys);
      }
      if (!keys.has(hashName(name)) || !keys.has(hashName(name + '_MASK'))) throw Error('This archive has no matching artwork/mask pair');
      if (file.size > 32 * 1024 * 1024) throw Error('PNG exceeds 32 MB');
      const png = fs.readFileSync(file.abs);
      if (png.length < 24 || !png.subarray(0, 8).equals(Buffer.from('89504e470d0a1a0a', 'hex'))) throw Error('Not a PNG');
      const w = png.readUInt32BE(16), h = png.readUInt32BE(20);
      if (!w || !h || w > 4096 || h > 4096) throw Error('PNG dimensions must be between 1 and 4096');
      const size = w === 1024 && h === 1024 ? 1024 : 512;
      const rgba = decodePNG(png, size, size);
      for (const mask of [false, true]) {
        // Retail metadata truncates long labels (e.g. ESCALADE's _MASK).
        // Its hash remains complete, so use that stable ID for runtime lookup.
        const key = hashName(name + (mask ? '_MASK' : '')).toString(16).padStart(8, '0');
        const p = `CARS/${car}/VINYLS/${key}.vpx`, encoded = encode(rgba, mask);
        let buffer = encoded;
        if (size === 1024) {
          // Keep the retail allocation intact. The HD compositor reads the
          // full indexed image separately; older clients use mip 1 safely.
          const hd = `CARS/${car}/VINYLS/${key}.vph`;
          prepared.set(hd.toLowerCase(), { buffer: encoded, size: encoded.length });
          data.entries.push({ p: hd, s: encoded.length, m: parseInt(crypto.createHash('sha256').update(encoded).digest('hex').slice(0, 12), 16) });
          buffer = Buffer.concat([encoded.subarray(0, 16), encoded.subarray(16 + 1024 * 1024)]);
          buffer.writeUInt32LE(512, 4); buffer.writeUInt32LE(512, 8); buffer.writeUInt32LE(7, 12);
        }
        const stamp = parseInt(crypto.createHash('sha256').update(buffer).digest('hex').slice(0, 12), 16);
        prepared.set(p.toLowerCase(), { buffer, size: buffer.length });
        data.entries.push({ p, s: buffer.length, m: stamp });
      }
      notes.push(`Loaded ${car}/${name}.png (${size}x${size}; generated alpha mask)`);
    } catch (e) { notes.push(`ERROR ${car}/${name}.png: ${e.message}`); }
  }
  for (const [key, value] of prepared) data.files.set(key, value);
  return notes;
}
module.exports = { encode, hashName, keysOfArchive, prepareVinyls };
