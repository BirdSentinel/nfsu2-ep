const fs = require('node:fs');
const path = require('node:path');

function* chunks(bytes, start = 0, end = bytes.length) {
  while (start + 8 <= end) {
    const next = start + 8 + bytes.readUInt32LE(start + 4);
    if (next > end) throw Error('Invalid menu bundle');
    yield { id: bytes.readUInt32LE(start), start, payload: start + 8, end: next };
    start = next;
  }
}

function replaceTexture(bytes, hash, png, width, height, decodePNG) {
  for (const pack of chunks(bytes)) {
    if (pack.id !== 0xb3300000) continue;
    const children = [...chunks(bytes, pack.payload, pack.end)];
    const info = children.find(c => c.id === 0xb3310000);
    const data = children.find(c => c.id === 0xb3320000);
    if (!info || !data) continue;
    const records = [...chunks(bytes, info.payload, info.end)];
    const table = records.find(c => c.id === 0x33310004);
    const formats = records.find(c => c.id === 0x33310005);
    if (!table || !formats) continue;
    for (let q = table.payload, index = 0; q + 124 <= table.end; q += 124, index++) {
      if (bytes.readUInt32LE(q + 36) !== hash) continue;
      const pixels = [...chunks(bytes, data.payload, data.end)].find(c => c.id === 0x33320002);
      if (!pixels || pixels.end !== data.end || data.end !== pack.end) throw Error('Unsupported menu texture layout');
      const levels = bytes[q + 78];
      if (!levels || levels > 12) throw Error('Invalid menu mip count');
      const chain = [];
      for (let level = 0; level < levels; level++) {
        const w = Math.max(1, width >> level), h = Math.max(1, height >> level);
        const rgba = decodePNG(png, w, h);
        if (rgba.length !== w * h * 4) throw Error('Invalid PNG pixels');
        const bgra = Buffer.alloc(rgba.length);
        for (let i = 0; i < rgba.length; i += 4) {
          bgra[i] = rgba[i + 2]; bgra[i + 1] = rgba[i + 1]; bgra[i + 2] = rgba[i]; bgra[i + 3] = 255;
        }
        chain.push(bgra);
      }
      const payload = Buffer.concat(chain), padding = Buffer.alloc((128 - payload.length % 128) % 128);
      const extra = Buffer.concat([payload, padding]);
      const result = Buffer.concat([bytes.subarray(0, pixels.end), extra, bytes.subarray(pixels.end)]);
      const base = Math.ceil(pixels.payload / 128) * 128;
      result.writeUInt32LE(pixels.end - base, q + 0x30);
      result.writeUInt32LE(payload.length, q + 0x38);
      result.writeUInt32LE(width * height * 4, q + 0x40);
      result.writeUInt16LE(width, q + 0x44); result.writeUInt16LE(height, q + 0x46);
      result[q + 0x48] = Math.log2(width); result[q + 0x49] = Math.log2(height);
      result.writeUInt32LE(21, formats.payload + index * 32 + 20); // A8R8G8B8
      for (const chunk of [pack, data, pixels]) result.writeUInt32LE(bytes.readUInt32LE(chunk.start + 4) + extra.length, chunk.start + 4);
      return result;
    }
  }
  throw Error('Menu texture not found');
}

function prepareMenuBackground(root, data, decodePNG) {
  if (!decodePNG) return;
  const key = 'frontend/platforms/showroom.bin', original = data.files.get(key);
  if (!original) return;
  let bytes;
  for (const [name, hash, w, h] of [['menu-background', 0x4d5565d8, 2048, 1024], ['menu-floor', 0x957c075e, 512, 512]]) {
    const file = path.join(root, 'custom', name + '.png');
    if (!fs.existsSync(file)) continue;
    try {
      bytes = replaceTexture(bytes || original.buffer || fs.readFileSync(original.abs), hash, fs.readFileSync(file), w, h, decodePNG);
    } catch (error) { console.warn(`Custom ${name}: ${error.message}`); }
  }
  if (bytes) {
    data.files.set(key, { buffer: bytes, size: bytes.length });
    const entry = data.entries.find(e => e.p.toLowerCase() === key);
    entry.s = bytes.length; entry.m = Date.now() / 1000;
  }
}
module.exports = { prepareMenuBackground, replaceTexture };

