// From the repository root: node desktop/multi-client-smoke.cjs
// Set EP_MULTI_GAME=1 to also start two actual games. Uses only the output test profile.
const { _electron: electron } = require('../web/node_modules/playwright');
const fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const main = 'out/portable/Egyuttparkolas/resources/app/main.cjs', original = fs.readFileSync(main, 'utf8');
const root = path.resolve('out/portable/Egyuttparkolas');
const configs = ['UserData/connection.json', 'UserData/Clients/2/connection.json'].map(p => path.join(root, p));
const previous = configs.map(p => fs.existsSync(p) ? fs.readFileSync(p) : null);
const exe = path.join(root, 'Egyuttparkolas.exe');
const hostDir = path.resolve('out/windows/multi-host'); fs.mkdirSync(hostDir, { recursive: true });
fs.copyFileSync('out/portable/Egyuttparkolas-Server/Egyuttparkolas-Server.exe', path.join(hostDir, 'server.exe'));
fs.writeFileSync(path.join(hostDir, 'server.json'), JSON.stringify({ bind: '127.0.0.1', port: 19845, max_players: 16 }));
let app, host;
async function another() {
  const opened = app.waitForEvent('window');
  const child = spawn(exe, [], { windowsHide: true, stdio: 'ignore' });
  child.on('error', e => { throw e; });
  const page = await opened; await page.waitForFunction(() => window.__nfsu2);
  return page;
}
async function join(page) {
  return page.evaluate(() => new Promise((resolve, reject) => {
    const ws = window.testSocket = new WebSocket(`ws://${location.host}/lan`);
    const timer = setTimeout(() => reject(Error('No welcome')), 8000);
    ws.onopen = () => ws.send(JSON.stringify({ t: 'hello', lan: 1, name: `Window${window.desktopGame.instanceId}` }));
    ws.onmessage = ({ data }) => { if (typeof data === 'string' && JSON.parse(data).t === 'welcome') { clearTimeout(timer); resolve(JSON.parse(data).vip); } };
    ws.onerror = reject;
  }));
}
(async () => {
  fs.writeFileSync(main, original.replaceAll('18742', '19742'));
  fs.writeFileSync(configs[0], JSON.stringify({ server: 'http://127.0.0.1:19845', online: true }));
  if (fs.existsSync(configs[1])) fs.unlinkSync(configs[1]);
  try {
    host = spawn(path.join(hostDir, 'server.exe'), [], { windowsHide: true, stdio: 'ignore' });
    app = await electron.launch({ executablePath: exe, args: [] });
    const first = await app.firstWindow(); await first.waitForFunction(() => window.__nfsu2);
    const second = await another();
    assert.equal(await first.evaluate(() => window.desktopGame.instanceId), 1);
    assert.equal(await second.evaluate(() => window.desktopGame.instanceId), 2);
    assert.notEqual(new URL(first.url()).port, new URL(second.url()).port);
    assert.equal(await second.evaluate(() => window.desktopGame.connection.server), 'http://127.0.0.1:19845');
    for (const [page, text] of [[first, 'first'], [second, 'second']]) {
      await page.evaluate(async text => {
        localStorage.setItem('multi-marker', text);
        const root = await navigator.storage.getDirectory();
        const file = await root.getFileHandle('multi-marker.txt', { create: true });
        const stream = await file.createWritable(); await stream.write(text); await stream.close();
      }, text);
    }
    assert.equal(await first.evaluate(() => localStorage.getItem('multi-marker')), 'first');
    assert.equal(await second.evaluate(() => localStorage.getItem('multi-marker')), 'second');
    if (process.env.EP_MULTI_GAME === '1') {
      for (const page of [first, second]) {
        await page.click('button.tab[data-tab="online"]');
        await page.check('#set-roam');
        await page.waitForFunction(() => window.__nfsu2.env().NFSU2_ROAM === '1');
        await page.click('#play');
      }
      for (const page of [first, second]) {
        await page.waitForFunction(() => window.__nfsu2.log.text().includes("the server's free-roam hub answers"), null, { timeout: 45000 });
      }
      const counts = await first.evaluate(async () => (await (await fetch('/players')).json()));
      assert.equal(counts.players, 2);
      console.log('PASS: two real games running simultaneously and both receiving free-roam hub responses.', counts);
      return;
    }
    const ids = await Promise.all([join(first), join(second)]); assert.notEqual(...ids);
    await first.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
    await second.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
    await first.waitForFunction(() => document.querySelector('#players-all').textContent === '2');
    await second.waitForFunction(() => document.querySelector('#players-all').textContent === '2');
    await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows().find(w => !w.getTitle().includes('Player 2')).destroy());
    await second.waitForTimeout(300);
    assert.equal(await second.evaluate(async () => (await (await fetch('/players')).json()).players), 1);
    const reopened = await another();
    assert.equal(await reopened.evaluate(() => window.desktopGame.instanceId), 1);
    assert.equal(await reopened.evaluate(() => localStorage.getItem('multi-marker')), 'first');
    assert.equal(await reopened.evaluate(async () => (await (await (await navigator.storage.getDirectory()).getFileHandle('multi-marker.txt')).getFile()).text()), 'first');
    // Per-instance Studio IPC reaches the correct window and can return to its launcher.
    await second.click('#vinyl-studio-btn');
    await second.waitForTimeout(600);
    const views = await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows().map(w => ({ title: w.getTitle(), children: w.contentView.children.length })));
    assert.equal(views.find(w => w.title.includes('Player 2')).children, 1);
    assert.equal(views.find(w => !w.title.includes('Player 2')).children, 0);
    console.log('PASS: repeated EXE launch, distinct origins/profiles, inherited server, two real player counts, closing one preserves the other, profile reuse, isolated Studio.', ids);
  } finally {
    if (app) { await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows().forEach(w => w.destroy())).catch(() => {}); await app.close().catch(() => {}); }
    if (host) { host.kill(); await new Promise(r => host.exitCode !== null ? r() : host.once('exit', r)); }
    fs.writeFileSync(main, original);
    configs.forEach((p, i) => { if (previous[i]) fs.writeFileSync(p, previous[i]); else if (fs.existsSync(p)) fs.unlinkSync(p); });
  }
})().catch(e => { console.error(e); process.exitCode = 1; });
