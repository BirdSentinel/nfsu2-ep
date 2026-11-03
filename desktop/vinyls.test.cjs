const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { encode, hashName, keysOfArchive, prepareVinyls } = require('./vinyls.cjs');
const { startServer } = require('./server.cjs');
function pixels() {
  const rgba = Buffer.alloc(512 * 512 * 4);
  for (let i = 0; i < rgba.length; i += 4) { rgba[i] = 255; rgba[i + 3] = (i / 4) % 512 < 256 ? 255 : 0; }
  return rgba;
}
function archive() {
  const b = Buffer.alloc(8 + 48); b.writeUInt32LE(0x33310003); b.writeUInt32LE(48, 4);
  b.writeUInt32LE(hashName('240SX_BODY_07'), 8); b.writeUInt32LE(hashName('240SX_BODY_07_MASK'), 32);
  return b;
}
test('PNG encoder creates palette, seven mip levels and alpha mask', () => {
  const art = encode(pixels()), mask = encode(pixels(), true), palette = 16 + 349504;
  assert.equal(art.length, 350544); assert.equal(art.toString('ascii', 0, 4), 'VPX1');
  assert.equal(art.readUInt32LE(12), 7);
  const index = art[16]; assert.deepEqual([...art.subarray(palette + index * 4, palette + index * 4 + 4)], [0, 0, 255, 0]);
  assert.equal(mask[16], 255); assert.equal(mask[16 + 511], 0);
  assert.equal(mask[16 + 262144], 255); assert.equal(mask[16 + 262144 + 255], 0);
  assert.equal(mask[16 + 349504 - 1], 0);
  assert.deepEqual([...mask.subarray(palette + 128 * 4, palette + 128 * 4 + 4)], [128, 128, 128, 255]);
  assert.throws(() => encode(Buffer.alloc(4)), /512x512/);
});
test('archive key lookup is bounded and matches actual known texture hash', () => {
  assert.equal(hashName('240SX_BODY_07'), 0xd48e98f3);
  assert.equal(keysOfArchive(archive()).size, 2);
  assert.throws(() => keysOfArchive(archive().subarray(0, 40)), /Truncated/);
});
test('virtual overrides serve full and ranged reads; source archive is unchanged; removal restores originals', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'vinyl-png-'));
  const dir = path.join(root, 'game/CARS/240SX/VINYLS');
  fs.mkdirSync(dir, { recursive: true }); fs.mkdirSync(path.join(root, 'web'));
  const archivePath = path.join(dir, '../VINYLS.BIN'); fs.writeFileSync(archivePath, archive());
  const png = Buffer.alloc(24); Buffer.from('89504e470d0a1a0a', 'hex').copy(png); png.writeUInt32BE(512, 16); png.writeUInt32BE(512, 20);
  const imagePath = path.join(dir, '240SX_BODY_07.png'); fs.writeFileSync(imagePath, png);
  let server;
  try {
    server = await startServer(root, 0, () => pixels());
    assert.match(server.vinylNotes[0], /^Loaded/);
    const base = `http://127.0.0.1:${server.address().port}`;
    const manifest = await (await fetch(base + '/data-manifest')).json();
    assert.equal(manifest.files.filter(f => f.p.endsWith('.vpx')).length, 2);
    const res = await fetch(base + '/data/CARS/240SX/VINYLS/d48e98f3.vpx', { headers: { Range: 'bytes=0-15' } });
    assert.equal(res.status, 206); assert.equal(Buffer.from(await res.arrayBuffer()).toString('ascii', 0, 4), 'VPX1');
    const full = await fetch(base + '/data-blocks/CARS/240SX/VINYLS/ab25995e.vpx?b=0&n=1');
    assert.equal((await full.arrayBuffer()).byteLength, 350544);
    assert.deepEqual(fs.readFileSync(archivePath), archive());
    fs.unlinkSync(imagePath);
    server.refreshVinyls();
    assert.equal((await fetch(base + '/data/CARS/240SX/VINYLS/d48e98f3.vpx')).status, 404);
    fs.writeFileSync(imagePath, png);
    server.refreshVinyls();
    assert.equal((await fetch(base + '/data/CARS/240SX/VINYLS/d48e98f3.vpx')).status, 200);
    server.closeAllConnections(); await new Promise(r => server.close(r)); server = null;
    // Content changes must invalidate the browser's block cache, even when
    // the PNG has the same filesystem timestamp and length.
    server = await startServer(root, 0, () => { const p = pixels(); p[0] = 0; return p; });
    const changed = await (await fetch(`http://127.0.0.1:${server.address().port}/data-manifest`)).json();
    const artEntry = m => m.files.find(f => f.p.endsWith('/d48e98f3.vpx'));
    assert.notEqual(artEntry(manifest).m, artEntry(changed).m);
    server.closeAllConnections(); await new Promise(r => server.close(r)); server = null;
    fs.writeFileSync(imagePath, 'invalid image');
    server = await startServer(root, 0, () => { throw Error('decoder should not run'); });
    assert.match(server.vinylNotes[0], /ERROR.*Not a PNG/);
    server.closeAllConnections(); await new Promise(r => server.close(r)); server = null;
    fs.unlinkSync(imagePath);
    server = await startServer(root, 0, () => pixels());
    assert.equal(server.vinylNotes.length, 0);
    assert.equal((await fetch(`http://127.0.0.1:${server.address().port}/data/CARS/240SX/VINYLS/d48e98f3.vpx`)).status, 404);
  } finally { if (server) { server.closeAllConnections(); await new Promise(r => server.close(r)); } fs.rmSync(root, { recursive: true, force: true }); }
});

