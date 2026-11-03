const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { startServer } = require('./server.cjs');

test('portable asset server: game reads, isolation, ranges and restricted files', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'portable-game-'));
  fs.mkdirSync(path.join(root, 'game/CARS'), { recursive: true });
  fs.mkdirSync(path.join(root, 'web'));
  fs.writeFileSync(path.join(root, 'web/index.html'), '<html>game</html>');
  fs.writeFileSync(path.join(root, 'web/game.wasm'), 'wasm');
  fs.writeFileSync(path.join(root, 'game/CARS/test.bin'), Buffer.alloc((1 << 20) + 7, 42));
  fs.writeFileSync(path.join(root, 'game/private.txt'), 'private');
  const server = await startServer(root, 0), base = `http://127.0.0.1:${server.address().port}`;
  try {
    const page = await fetch(base);
    assert.equal(page.headers.get('cross-origin-embedder-policy'), 'require-corp');
    assert.equal(page.headers.get('cross-origin-opener-policy'), 'same-origin');
    assert.match(await page.text(), /game/);
    const manifest = await (await fetch(base + '/data-manifest')).json();
    assert.equal(manifest.files.length, 2);
    assert.equal(manifest.blocks.size, 1 << 20);
    const block = await fetch(base + '/data-blocks/cars/test.bin?b=1&n=1');
    assert.equal(block.status, 200); assert.equal((await block.arrayBuffer()).byteLength, 7);
    const range = await fetch(base + '/data/CARS/test.bin', { headers: { Range: 'bytes=2-4' } });
    assert.equal(range.status, 206); assert.equal((await range.arrayBuffer()).byteLength, 3);
    assert.equal((await fetch(base + '/data/CARS/test.bin', { headers: { Range: 'bytes=9999999-' } })).status, 416);
    assert.equal((await fetch(base + '/data-blocks/CARS/test.bin?b=0&n=9')).status, 400);
    assert.equal((await fetch(base + '/data/private.txt')).status, 404);
    assert.equal((await fetch(base + '/data/%2e%2e%5cprivate.txt')).status, 400);
    assert.equal((await fetch(base + '/', { headers: { Origin: 'https://example.com' } })).status, 403);
    assert.equal((await fetch(base + '/', { method: 'POST' })).status, 405);
    assert.equal((await fetch(base + '/game.wasm')).headers.get('content-type'), 'application/wasm');
    assert.equal((await fetch(base + '/game.wasm', { method: 'HEAD' })).headers.get('content-length'), '4');
  } finally {
    server.closeAllConnections(); await new Promise(resolve => server.close(resolve));
    fs.rmSync(root, { recursive: true, force: true });
  }
});
