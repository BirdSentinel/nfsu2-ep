// Car-skin alpha is shader data, not image transparency. Canvas/ImageBitmap
// premultiplication destroys RGB where alpha is zero. Keep all four bytes raw.
const MAX_PNG = 4_300_000;
const signature = new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10]);
function chunk(name: string, data: Uint8Array): Uint8Array<ArrayBuffer> {
  const out = new Uint8Array(data.length + 12), v = new DataView(out.buffer);
  v.setUint32(0, data.length);
  for (let i = 0; i < 4; i++) out[4 + i] = name.charCodeAt(i);
  out.set(data, 8);
  let crc = 0xffffffff;
  for (const b of out.subarray(4, out.length - 4)) {
    crc ^= b;
    for (let k = 0; k < 8; k++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
  }
  v.setUint32(out.length - 4, (crc ^ 0xffffffff) >>> 0);
  return out;
}
export async function encodeSkinPng(rgba: Uint8Array): Promise<Blob> {
  const SIZE = Math.sqrt(rgba.length / 4), ROW = SIZE * 4, RAW = (ROW + 1) * SIZE;
  if (SIZE !== 512 && SIZE !== 1024) throw new Error('Invalid skin size');
  const scan = new Uint8Array(RAW);
  for (let y = 0; y < SIZE; y++) scan.set(rgba.subarray(y * ROW, (y + 1) * ROW), y * (ROW + 1) + 1);
  const compressed = new Uint8Array(await new Response(new Blob([scan]).stream().pipeThrough(new CompressionStream('deflate'))).arrayBuffer());
  const header = new Uint8Array(13), h = new DataView(header.buffer);
  h.setUint32(0, SIZE); h.setUint32(4, SIZE); header[8] = 8; header[9] = 6;
  return new Blob([signature, chunk('IHDR', header), chunk('IDAT', compressed), chunk('IEND', new Uint8Array())], { type: 'image/png' });
}
// Accept only our bounded, filter-zero RGBA wire format, not arbitrary images.
export async function decodeSkinPng(png: Blob): Promise<Uint8Array<ArrayBuffer>> {
  if (png.size > MAX_PNG) throw new Error('Skin too large');
  const bytes = new Uint8Array(await png.arrayBuffer()), view = new DataView(bytes.buffer);
  if (!signature.every((b, i) => bytes[i] === b)) throw new Error('Invalid PNG');
  const parts: Uint8Array<ArrayBuffer>[] = [];
  let header = false, SIZE = 0;
  for (let at = 8; at + 12 <= bytes.length;) {
    const n = view.getUint32(at), end = at + 12 + n;
    if (end > bytes.length) throw new Error('Truncated PNG');
    const type = String.fromCharCode(...bytes.subarray(at + 4, at + 8));
    if (type === 'IHDR') {
      if (header || at !== 8 || n !== 13 || ![512, 1024].includes(view.getUint32(at + 8)) || view.getUint32(at + 12) !== view.getUint32(at + 8) || bytes[at + 16] !== 8 || bytes[at + 17] !== 6 || bytes[at + 18] || bytes[at + 19] || bytes[at + 20]) throw new Error('Invalid skin format');
      SIZE = view.getUint32(at + 8); header = true;
    } else if (type === 'IDAT') parts.push(bytes.slice(at + 8, at + 8 + n));
    at = end;
  }
  if (!header || !parts.length) throw new Error('Missing skin pixels');
  const ROW = SIZE * 4, RAW = (ROW + 1) * SIZE;
  const reader = new Blob(parts).stream().pipeThrough(new DecompressionStream('deflate')).getReader();
  const scan = new Uint8Array(RAW); let used = 0;
  try {
    for (;;) {
      const { done, value } = await reader.read(); if (done) break;
      if (used + value.length > RAW) throw new Error('Oversized skin pixels');
      scan.set(value, used); used += value.length;
    }
  } finally { await reader.cancel(); }
  if (used !== RAW) throw new Error('Truncated skin pixels');
  const rgba = new Uint8Array(ROW * SIZE);
  for (let y = 0; y < SIZE; y++) {
    if (scan[y * (ROW + 1)] !== 0) throw new Error('Unsupported skin filter');
    rgba.set(scan.subarray(y * (ROW + 1) + 1, (y + 1) * (ROW + 1)), y * ROW);
  }
  return rgba;
}
