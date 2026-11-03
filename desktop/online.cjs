// The renderer still uses its local origin. Only these multiplayer endpoints
// cross the network; game assets and saves never go through this proxy.
const http = require('node:http');
const https = require('node:https');
const { pipeline } = require('node:stream');
const ROUTES = new Set(['/health', '/players', '/seen', '/names', '/friends', '/vault']);
function normalizeServer(value) {
  if (typeof value !== 'string' || value.length > 2048) throw Error('Enter a valid server address.');
  value = value.trim();
  if (!value) return '';
  const u = new URL(value.includes('://') ? value : `http://${value}`);
  if (!['http:', 'https:'].includes(u.protocol) || u.username || u.password || u.search || u.hash || u.pathname !== '/') {
    throw Error('Use a server address such as http://192.168.1.20:8080, without a path or password.');
  }
  return u.origin;
}
function createOnline(getServer) {
  const active = new Set();
  function track(socket) { active.add(socket); socket.once('close', () => active.delete(socket)); return socket; }
  function request(req, url, websocket) {
    const headers = { host: url.host, origin: url.origin };
    for (const key of websocket ? ['sec-websocket-key', 'sec-websocket-version', 'sec-websocket-protocol'] : ['content-type', 'content-length', 'authorization', 'if-match', 'if-none-match']) {
      if (req.headers[key]) headers[key] = req.headers[key];
    }
    if (websocket) { headers.connection = 'Upgrade'; headers.upgrade = 'websocket'; }
    return (url.protocol === 'https:' ? https : http).request(url, { method: req.method, headers });
  }
  return {
    close() { for (const socket of active) socket.destroy(); active.clear(); },
    handles(pathname) { return ROUTES.has(pathname); },
    http(req, res) {
      const base = getServer();
      const local = new URL(req.url, 'http://localhost');
      if (!base) {
        if (local.pathname === '/players') { res.setHeader('Content-Type', 'application/json'); return res.end(JSON.stringify({ players: 0, online: 0, roam: 0, full: false, queue: 0, roamBusy: false })); }
        res.writeHead(404); return res.end('Online server not configured');
      }
      const upstream = request(req, new URL(local.pathname + local.search, base), false);
      upstream.on('socket', track);
      upstream.setTimeout(15000, () => upstream.destroy(Error('Online server timed out')));
      upstream.on('error', () => { if (!res.headersSent) res.writeHead(502); res.end('Online server unavailable'); });
      res.on('close', () => upstream.destroy());
      upstream.on('response', remote => {
        // Never relay redirects, cookies, scripts or another site's policies.
        if (remote.statusCode >= 300 && remote.statusCode < 400 && remote.statusCode !== 304) {
          remote.destroy(); res.writeHead(502); return res.end('Use the final server address (redirects are disabled)');
        }
        for (const key of ['content-type', 'content-length', 'etag', 'retry-after', 'x-vault-version']) {
          if (remote.headers[key]) res.setHeader(key, remote.headers[key]);
        }
        res.writeHead(remote.statusCode); pipeline(remote, res, () => {});
      });
      pipeline(req, upstream, () => {});
    },
    upgrade(req, socket, head, origin) {
      const reject = () => socket.end('HTTP/1.1 403 Forbidden\r\nConnection: close\r\nContent-Length: 0\r\n\r\n');
      const base = getServer();
      if (!base || req.headers.host !== new URL(origin).host || req.headers.origin !== origin || req.method !== 'GET'
          || new URL(req.url, origin).pathname !== '/lan' || !req.url.startsWith('/lan')) return reject();
      track(socket);
      const local = new URL(req.url, origin);
      const upstream = request(req, new URL(local.pathname + local.search, base), true);
      upstream.setTimeout(10000, () => upstream.destroy());
      upstream.on('error', () => socket.destroy());
      socket.on('error', () => upstream.destroy());
      socket.on('close', () => upstream.destroy());
      upstream.on('response', res => { res.resume(); socket.end(`HTTP/1.1 ${res.statusCode} Unavailable\r\nConnection: close\r\nContent-Length: 0\r\n\r\n`); });
      upstream.on('upgrade', (res, remote, pre) => {
        track(remote); remote.setTimeout(0); remote.setNoDelay(true); socket.setNoDelay(true);
        const headers = ['HTTP/1.1 101 Switching Protocols', 'Upgrade: websocket', 'Connection: Upgrade'];
        for (const key of ['sec-websocket-accept', 'sec-websocket-protocol']) if (res.headers[key]) headers.push(`${key}: ${res.headers[key]}`);
        socket.write(headers.join('\r\n') + '\r\n\r\n');
        if (pre.length) socket.write(pre);
        if (head.length) remote.write(head);
        pipeline(remote, socket, () => remote.destroy());
        pipeline(socket, remote, () => socket.destroy());
      });
      upstream.end();
    },
  };
}
async function checkServer(value) {
  const address = normalizeServer(value);
  if (!address) throw Error('Enter a server address first.');
  return new Promise((resolve, reject) => {
    const u = new URL('/health', address);
    const req = (u.protocol === 'https:' ? https : http).get(u, res => {
      let body = '';
      res.on('error', reject);
      res.on('aborted', () => reject(Error('Server closed the connection before answering.')));
      res.on('data', chunk => { body += chunk; if (body.length > 8192) req.destroy(Error('Invalid server response')); });
      res.on('end', () => {
        try {
          const data = JSON.parse(body);
          if (res.statusCode !== 200 || data.service !== 'egyuttparkolas-online' || data.protocol !== 1) throw Error('This is not a compatible Egyuttparkolas server.');
          resolve({ address, message: 'Server is available. Save the address, then press Play.' });
        } catch (e) { reject(e); }
      });
    });
    req.setTimeout(8000, () => req.destroy(Error('Server did not answer. Check the address, port and firewall.')));
    req.on('error', reject);
  });
}
module.exports = { normalizeServer, createOnline, checkServer };
