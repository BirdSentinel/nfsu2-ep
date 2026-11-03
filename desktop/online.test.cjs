const { test } = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { once } = require('node:events');
const { createOnline, normalizeServer, checkServer } = require('./online.cjs');
const { startServer } = require('./server.cjs');
const { WebSocket, WebSocketServer } = require('../web/node_modules/ws');

test('server address validation', () => {
  assert.equal(normalizeServer('192.168.1.20:8080'), 'http://192.168.1.20:8080');
  assert.equal(normalizeServer(' https://play.example.com/ '), 'https://play.example.com');
  assert.equal(normalizeServer(''), '');
  for (const url of ['file:///x', 'ftp://example.com', 'http://a:b@example.com', 'http://example.com/path', 'https://example.com/?a=1']) assert.throws(() => normalizeServer(url));
});

test('only multiplayer routes are proxied; HTTP, WebSocket, offline and origin isolation', async () => {
  const requests = [];
  const remote = http.createServer((req, res) => {
    requests.push({ url: req.url, origin: req.headers.origin });
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify(req.url === '/health' ? { service: 'egyuttparkolas-online', protocol: 1 } : { players: 2, online: 1, roam: 1 }));
  });
  const ws = new WebSocketServer({ server: remote });
  ws.on('connection', socket => socket.on('message', (data, binary) => socket.send(data, { binary })));
  remote.listen(0, '127.0.0.1'); await once(remote, 'listening');
  let target = `http://127.0.0.1:${remote.address().port}`;
  const proxy = createOnline(() => target);
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'ep-online-'));
  fs.mkdirSync(path.join(root, 'game')); fs.mkdirSync(path.join(root, 'web'));
  fs.writeFileSync(path.join(root, 'game/SPEED2.EXE'), 'local-game');
  fs.writeFileSync(path.join(root, 'web/index.html'), 'local-launcher');
  const local = await startServer(root, 0, undefined, proxy);
  const origin = `http://127.0.0.1:${local.address().port}`;
  let client;
  try {
    assert.equal((await checkServer(target)).address, target);
    assert.equal((await (await fetch(origin + '/players')).json()).players, 2);
    assert.equal((await fetch(origin + '/data/SPEED2.EXE')).status, 200);
    assert.equal(await (await fetch(origin + '/data/SPEED2.EXE')).text(), 'local-game');
    assert.equal(await (await fetch(origin)).text(), 'local-launcher');
    assert.ok(requests.every(r => ['/players', '/health'].includes(r.url)));
    assert.equal(requests.find(r => r.url === '/players').origin, target);
    assert.equal((await fetch(origin + '/players', { headers: { origin: 'https://untrusted.example' } })).status, 403);
    client = new WebSocket(origin.replace('http:', 'ws:') + '/lan', { origin });
    await once(client, 'open');
    let next = once(client, 'message'); client.send('hello'); assert.equal(String((await next)[0]), 'hello');
    next = once(client, 'message'); client.send(Buffer.from([1, 2, 3])); assert.deepEqual((await next)[0], Buffer.from([1, 2, 3]));
    client.close(); await once(client, 'close');
    target = '';
    assert.equal((await (await fetch(origin + '/players')).json()).players, 0);
    assert.equal((await fetch(origin + '/vault')).status, 404);
    assert.equal(await (await fetch(origin + '/data/SPEED2.EXE')).text(), 'local-game');
  } finally {
    client?.terminate(); proxy.close(); ws.close();
    local.closeAllConnections(); remote.closeAllConnections();
    await Promise.all([new Promise(r => local.close(r)), new Promise(r => remote.close(r))]);
    fs.rmSync(root, { recursive: true, force: true });
  }
});
