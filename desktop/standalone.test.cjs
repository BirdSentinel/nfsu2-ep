// Run after building the Windows host. This launches only an isolated test copy.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path'), os = require('node:os');
const { spawn } = require('node:child_process');
const { WebSocket } = require('../web/node_modules/ws');
const { createOnline } = require('./online.cjs');
const { startServer } = require('./server.cjs');
const sleep = ms => new Promise(r => setTimeout(r, ms));
function testPNG(noisy) {
  const raw = Buffer.alloc(512 * (1 + 512 * 4));
  if (noisy) require('node:crypto').randomFillSync(raw);
  for (let y = 0; y < 512; y++) {
    raw[y * 2049] = 0;
    for (let x = 0; x < 512; x++) { const p = y * 2049 + 1 + x * 4; if (!noisy) raw[p] = 255; raw[p + 3] = 255; }
  }
  function chunk(name, data) {
    const b = Buffer.alloc(12 + data.length); b.writeUInt32BE(data.length); b.write(name, 4); data.copy(b, 8);
    let crc = 0xffffffff;
    for (const value of b.subarray(4, -4)) { crc ^= value; for (let i = 0; i < 8; i++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0); }
    b.writeUInt32BE((crc ^ 0xffffffff) >>> 0, b.length - 4); return b;
  }
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(512); ihdr.writeUInt32BE(512, 4); ihdr[8] = 8; ihdr[9] = 6;
  return Buffer.concat([Buffer.from('89504e470d0a1a0a', 'hex'), chunk('IHDR', ihdr), chunk('IDAT', require('node:zlib').deflateSync(raw)), chunk('IEND', Buffer.alloc(0))]).toString('base64');
}
async function until(fn) { for (let i = 0; i < 150; i++) { const result = await fn(); if (result) return result; await sleep(40); } throw Error('Timed out'); }
test('standalone host: two local clients exchange game packets and custom skins without game assets', { timeout: 25000 }, async () => {
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), 'ep-native-host-'));
  const executable = path.join(folder, 'Egyuttparkolas-Server.exe');
  const external = process.env.EP_SERVER_TEST_URL;
  const port = Number(process.env.EP_SERVER_TEST_PORT || 19843);
  const endpoint = external || `http://127.0.0.1:${port}`;
  if (!external) fs.copyFileSync(path.resolve('web/server-rs/target/x86_64-pc-windows-gnu/ci/egyuttparkolas-server.exe'), executable);
  fs.writeFileSync(path.join(folder, 'server.json'), JSON.stringify({ bind: '127.0.0.1', port, max_players: 16 }));
  const host = external ? null : spawn(executable, [], { windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'] });
  let log = ''; host?.stdout.on('data', b => log += b); host?.stderr.on('data', b => log += b);
  const peers = [], servers = [], proxies = [];
  try {
    await until(async () => { try { return (await fetch(endpoint + '/health')).ok; } catch { return false; } });
    assert.equal((await fetch(endpoint + '/data/SPEED2.EXE')).status, 404);
    assert.equal((await fetch(endpoint + '/game.wasm')).status, 404);
    assert.equal((await fetch(endpoint + '/players', { headers: { origin: 'https://evil.example' } })).status, 403);
    for (let i = 0; i < 2; i++) {
      const root = path.join(folder, `client${i}`); fs.mkdirSync(path.join(root, 'game'), { recursive: true }); fs.mkdirSync(path.join(root, 'web'));
      fs.writeFileSync(path.join(root, 'game/SPEED2.EXE'), `local-${i}`);
      const proxy = createOnline(() => endpoint); proxies.push(proxy);
      const server = await startServer(root, 0, undefined, proxy); servers.push(server);
      const origin = `http://127.0.0.1:${server.address().port}`;
      const ws = new WebSocket(origin.replace('http:', 'ws:') + '/lan', { origin });
      const peer = { ws, messages: [], frames: [], origin }; peers.push(peer);
      ws.on('error', error => peer.error = error);
      ws.on('open', () => ws.send(JSON.stringify({ t: 'hello', name: `Test${i}`, lan: 1 })));
      ws.on('message', (body, binary) => binary ? peer.frames.push(Buffer.from(body)) : peer.messages.push(JSON.parse(body)));
      peer.vip = (await until(() => peer.messages.find(m => m.t === 'welcome'))).vip;
      assert.equal(await (await fetch(origin + '/data/SPEED2.EXE')).text(), `local-${i}`);
    }
    await until(() => peers[0].messages.some(m => ['peers', 'delta'].includes(m.t) && m.peers.some(p => p.vip === peers[1].vip)));
    const frame = Buffer.alloc(16 + 4); frame[0] = 3; frame.writeUInt32BE(peers[1].vip >>> 0, 8);
    frame.writeUInt16BE(9999, 12); frame.writeUInt16BE(9999, 14); frame.write('TEST', 16);
    peers[0].ws.send(frame);
    const got = await until(() => peers[1].frames.find(b => b.subarray(16).toString() === 'TEST'));
    assert.equal(got.readUInt32BE(4), peers[0].vip >>> 0);
    const counts = await (await fetch(peers[0].origin + '/players')).json(); assert.equal(counts.players, 2);
    // Same car/vinyl slot, different session-owned designs; no files on the host.
    const pngs = [testPNG(false), testPNG(true)];
    for (let i = 0; i < 2; i++) {
      peers[i].ws.send(JSON.stringify({ t: 'skin-hello' }));
      await until(() => peers[i].messages.some(m => m.t === 'skin-ready'));
      peers[i].ws.send(JSON.stringify({ t: 'skin-put', vip: peers[1-i].vip, digest: String(i).repeat(64), png: pngs[i] }));
      await until(() => peers[i].messages.some(m => m.t === 'skin-saved'));
    }
    for (let i = 0; i < 2; i++) {
      peers[i].ws.send(JSON.stringify({ t: 'skin-get', vip: peers[1-i].vip, version: 0 }));
      const skin = await until(() => peers[i].messages.find(m => m.t === 'skin'));
      assert.equal(skin.png, pngs[1-i], 'An upload cannot replace another player\'s design');
    }
    peers[0].ws.close(); await until(async () => (await (await fetch(peers[1].origin + '/players')).json()).players === 1);
    await sleep(1000);
    peers[1].ws.send(JSON.stringify({ t: 'skin-get', vip: peers[0].vip, version: 0 }));
    await until(() => peers[1].messages.some(m => m.t === 'skin' && m.version === 0 && !m.png));
    console.log('Two distinct PNGs delivered through the authenticated LAN; spoofed owner ignored; disconnect evicts artwork.');
    console.log('Native host has two clients; packet delivered; assets remain local.', counts);
  } catch (error) { error.message += '\nServer output:\n' + log; throw error; }
  finally {
    for (const peer of peers) peer.ws.terminate();
    for (const proxy of proxies) proxy.close();
    for (const server of servers) { server.closeAllConnections(); await new Promise(r => server.close(r)); }
    if (host) { host.kill(); await new Promise(r => host.exitCode !== null ? r() : host.once('exit', r)); }
    fs.rmSync(folder, { recursive: true, force: true });
  }
});
