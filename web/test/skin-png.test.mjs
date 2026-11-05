import test from 'node:test';
import assert from 'node:assert/strict';
import { inflateSync, deflateSync } from 'node:zlib';
import { encodeSkinPng, decodeSkinPng } from '../src/gpu/skin-png.ts';

test('1024 skin preserves individual adjacent pixels through the online codec', async () => {
  const pixels = new Uint8Array(1024 * 1024 * 4);
  for (let i = 0; i < pixels.length; i++) pixels[i] = (i * 73 + Math.floor(i / 4096)) & 255;
  const png = await encodeSkinPng(pixels);
  assert.equal(new DataView(await png.arrayBuffer()).getUint32(16), 1024);
  assert.deepEqual(await decodeSkinPng(png), pixels);
  await assert.rejects(encodeSkinPng(new Uint8Array(2048 * 2048 * 4)), /Invalid skin size/);
});

test('online car skins preserve RGB even with zero alpha, and every material alpha value', async () => {
  const pixels = new Uint8Array(512 * 512 * 4);
  for (let i = 0; i < pixels.length; i += 4) {
    pixels[i] = 239; pixels[i + 1] = 83; pixels[i + 2] = 17;
    pixels[i + 3] = (i / 4) % 256;
  }
  const png = await encodeSkinPng(pixels);
  // Independently inspect PNG scanlines: Canvas would turn the first pixel black.
  const bytes = Buffer.from(await png.arrayBuffer());
  assert.equal(bytes.readUInt32BE(16), 512);
  assert.equal(bytes.readUInt32BE(20), 512);
  const n = bytes.readUInt32BE(33);
  const raw = inflateSync(bytes.subarray(41, 41 + n));
  assert.deepEqual([...raw.subarray(1, 5)], [239, 83, 17, 0]);
  assert.deepEqual(await decodeSkinPng(png), pixels);
});

test('skin decoder rejects truncated and oversized decompressed pixel data', async () => {
  const png = await encodeSkinPng(new Uint8Array(512 * 512 * 4));
  const bytes = Buffer.from(await png.arrayBuffer());
  await assert.rejects(decodeSkinPng(new Blob([bytes.subarray(0, 60)])));
  const compressed = deflateSync(Buffer.alloc(512 * 2049 + 1));
  const idat = Buffer.alloc(12 + compressed.length);
  idat.writeUInt32BE(compressed.length); idat.write('IDAT', 4); compressed.copy(idat, 8);
  await assert.rejects(decodeSkinPng(new Blob([bytes.subarray(0, 33), idat])), /Oversized/);
});
