// Developer diagnostic: launch the app with --remote-debugging-port=18743 first.
// This is not shipped in the portable folder.
const fs = require('node:fs');
(async () => {
  const targets = await (await fetch('http://127.0.0.1:18743/json')).json();
  const page = targets.find(t => t.type === 'page');
  if (!page) throw new Error('No Electron page');
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((ok, no) => { ws.onopen = ok; ws.onerror = no; });
  let seq = 0;
  const pending = new Map();
  const logs = [];
  ws.onmessage = e => { const m = JSON.parse(e.data); if (m.method === 'Runtime.consoleAPICalled') logs.push(m.params.args.map(a => a.value ?? a.description).join(' ')); if (m.id) { pending.get(m.id)?.(m); pending.delete(m.id); } };
  const call = (method, params = {}) => new Promise(resolve => { const id = ++seq; pending.set(id, resolve); ws.send(JSON.stringify({ id, method, params })); });
  const expression = process.argv[2] || `JSON.stringify({url:location.href,isolated:crossOriginIsolated,gpu:!!navigator.gpu,playDisabled:document.querySelector('#play')?.disabled,text:document.body.innerText.slice(-4000)})`;
  if (expression === 'close') { await call('Browser.close'); return; }
  if (expression.startsWith('logs')) { await call('Runtime.enable'); console.log((expression.startsWith('logs:') ? logs.filter(s => s.includes(expression.slice(5))) : logs.slice(-40)).join('\n')); }
  else if (expression.startsWith('key:')) {
    await call('Page.bringToFront');
    for (const key of expression.slice(4).split(',')) {
    const code = { Enter: 13, Escape: 27, ArrowDown: 40, ArrowRight: 39, ArrowLeft: 37, ArrowUp: 38 }[key];
    await call('Input.dispatchKeyEvent', { type: 'keyDown', key, code: key, windowsVirtualKeyCode: code });
    await new Promise(resolve => setTimeout(resolve, key === 'ArrowUp' ? 3000 : 120));
    await call('Input.dispatchKeyEvent', { type: 'keyUp', key, code: key, windowsVirtualKeyCode: code });
    await new Promise(resolve => setTimeout(resolve, 1200));
    }
  } else console.log(JSON.stringify(await call('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true }), null, 2));
  if (process.argv[3]) {
    const shot = await call('Page.captureScreenshot');
    fs.writeFileSync(process.argv[3], Buffer.from(shot.result.data, 'base64'));
  }
  ws.close();
})().catch(e => { console.error(e); process.exitCode = 1; });
