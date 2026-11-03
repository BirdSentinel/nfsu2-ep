// A local-only asset server embedded in Electron; no external runtime or service.
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const { pipeline } = require('node:stream');
const { Readable } = require('node:stream');
const { prepareVinyls } = require('./vinyls.cjs');
const ENTRIES = new Set('speed2.exe server.dll server.cfg cars credits frontend global langpacks languages memcard movies nis pfdata sdata sound speech subtitles texpacks tracks'.split(' '));
const BLOCK = 1 << 20;
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.wasm': 'application/wasm', '.png': 'image/png', '.svg': 'image/svg+xml', '.ico': 'image/x-icon', '.webmanifest': 'application/manifest+json' };

function inventory(root, game = false) {
  const files = new Map(), entries = [];
  function walk(rel) {
    for (const e of fs.readdirSync(path.join(root, rel), { withFileTypes: true })) {
      if (e.name.startsWith('.') || e.isSymbolicLink() || (!rel && game && !ENTRIES.has(e.name.toLowerCase()))) continue;
      const p = rel ? `${rel}/${e.name}` : e.name;
      if (e.isDirectory()) { entries.push({ p, d: 1 }); walk(p); }
      else if (e.isFile()) {
        const abs = path.join(root, p), st = fs.statSync(abs);
        entries.push({ p, s: st.size, m: st.mtimeMs / 1000 });
        files.set(p.toLowerCase(), { abs, size: st.size });
      }
    }
  }
  walk('');
  return { files, entries };
}

async function startServer(root, port = 18742, decodePNG) {
  let data = inventory(path.join(root, 'game'), true);
  const vinylNotes = decodePNG ? prepareVinyls(data, decodePNG) : [];
  const web = inventory(path.join(root, 'web'));
  let manifest = JSON.stringify({ files: data.entries, blocks: { url: '/data-blocks/', size: BLOCK, max: 8 } });
  const server = http.createServer((req, res) => {
    const origin = `http://127.0.0.1:${server.address().port}`;
    const reply = (code, body = '', type = 'text/plain') => {
      res.writeHead(code, { 'Content-Type': type, 'Content-Length': Buffer.byteLength(body) });
      res.end(req.method === 'HEAD' ? undefined : body);
    };
    res.setHeader('Cross-Origin-Opener-Policy', 'same-origin');
    res.setHeader('Cross-Origin-Embedder-Policy', 'require-corp');
    res.setHeader('Cross-Origin-Resource-Policy', 'same-origin');
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('Cache-Control', 'no-store');
    if (req.headers.host !== new URL(origin).host || (req.headers.origin && req.headers.origin !== origin)) return reply(403);
    if (!['GET', 'HEAD'].includes(req.method)) return reply(405);
    try {
      const url = new URL(req.url, origin), p = decodeURIComponent(url.pathname);
      if (p.includes('\\') || p.includes('\0') || p.split('/').some(x => x === '..' || x.includes(':'))) return reply(400);
      if (p === '/data-manifest') return reply(200, manifest, 'application/json');
      if (p === '/players') return reply(200, JSON.stringify({ players: 1, online: 0, roam: 0, full: false, queue: 0, roamBusy: false }), 'application/json');
      let file;
      const blocks = p.startsWith('/data-blocks/');
      if (blocks || p.startsWith('/data/')) file = data.files.get(p.slice(blocks ? 13 : 6).toLowerCase());
      else file = web.files.get((p === '/' ? 'index.html' : p.slice(1)).toLowerCase());
      if (!file) return reply(404);
      let start = 0, end = file.size - 1, status = 200;
      if (blocks) {
        const b = url.searchParams.get('b'), n = url.searchParams.get('n');
        if (!/^\d+$/.test(b || '') || !/^[1-8]$/.test(n || '')) return reply(400);
        start = Number(b) * BLOCK; end = Math.min(file.size - 1, start + Number(n) * BLOCK - 1);
      } else if (req.headers.range) {
        const m = /^bytes=(\d*)-(\d*)$/.exec(req.headers.range);
        if (!m || (!m[1] && !m[2])) return reply(416);
        start = m[1] ? Number(m[1]) : Math.max(0, file.size - Number(m[2]));
        end = m[1] && m[2] ? Math.min(end, Number(m[2])) : end;
        status = 206;
      }
      if ((file.size && (start > end || start >= file.size)) || !Number.isSafeInteger(start) || (blocks && !file.size)) {
        res.setHeader('Content-Range', `bytes */${file.size}`); return reply(416);
      }
      res.setHeader('Content-Type', MIME[path.extname(file.abs || '')] || 'application/octet-stream');
      res.setHeader('Accept-Ranges', 'bytes');
      res.setHeader('Content-Length', Math.max(0, end - start + 1));
      if (status === 206) res.setHeader('Content-Range', `bytes ${start}-${end}/${file.size}`);
      res.writeHead(status);
      if (req.method === 'HEAD' || !file.size) return res.end();
      pipeline(file.buffer ? Readable.from([file.buffer.subarray(start, end + 1)]) : fs.createReadStream(file.abs, { start, end }), res, () => {});
    } catch { if (!res.headersSent) reply(400); else res.destroy(); }
  });
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(port, '127.0.0.1', resolve); });
  server.vinylNotes = vinylNotes;
  server.refreshVinyls = () => {
    const next = inventory(path.join(root, 'game'), true);
    const notes = decodePNG ? prepareVinyls(next, decodePNG) : [];
    data = next;
    manifest = JSON.stringify({ files: data.entries, blocks: { url: '/data-blocks/', size: BLOCK, max: 8 } });
    server.vinylNotes = notes;
  };
  return server;
}
module.exports = { startServer, inventory, ENTRIES };
