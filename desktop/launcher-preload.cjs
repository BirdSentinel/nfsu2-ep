const { ipcRenderer, contextBridge } = require('electron');
const instanceId = Number(process.argv.find(value => /^--ep-instance=\d+$/.test(value))?.split('=')[1] || 1);
const channel = name => `${name}:${instanceId}`;
const connection = ipcRenderer.sendSync(channel('launcher:connection'));
contextBridge.exposeInMainWorld('desktopGame', { localFiles: true, connection, instanceId });
window.addEventListener('DOMContentLoaded', () => {
  const theme = document.createElement('style');
  theme.id = 'ep-launcher-theme';
  theme.textContent = `
    .app [data-tab="other"] { display:none !important; }
    #desktop-server-address { background:var(--field); color:var(--text); border:2px solid var(--edge); border-radius:8px; padding:10px 12px; min-height:42px; font:inherit; }
    #desktop-server-address:focus { outline:2px solid var(--lime); outline-offset:2px; }
    #desktop-server-status { color:var(--muted); overflow-wrap:anywhere; }
    html:root {
      --bg:#0b0d10; --frame:#12181e; --panel:#15191e; --field:#1c252e;
      --line:#303943; --edge:#718596; --text:#ffffff; --muted:#bac6d1;
      --lime:#69c9f2; --lime-fill:#12384b; --lime-glow:rgba(24,148,202,.3);
      --ep-blue:#1894ca;
    }
    html body { background:radial-gradient(1200px 480px at 50% -160px,#203444,transparent 70%) no-repeat,var(--bg); }
    .app .panel,.app .top { border:1px solid var(--line); }
    .app .bar-fill { background:var(--ep-blue); }
    .app .play,#vinyl-studio-btn {
      background:var(--ep-blue); color:#060807; border-color:var(--ep-blue);
      box-shadow:0 0 12px rgba(24,148,202,.22);
    }
    .app .play:hover:not(:disabled),#vinyl-studio-btn:hover { background:#36afe1; border-color:#69c9f2; }
    .app .play:disabled { background:var(--field); color:var(--edge); border-color:var(--line); box-shadow:none; }
    .app .switch:checked { background:radial-gradient(circle at calc(100% - 14px) 50%,#fff 8px,transparent 9px) no-repeat,var(--ep-blue); border-color:var(--ep-blue); box-shadow:0 0 10px rgba(24,148,202,.3); }
  `;
  document.head.append(theme);
  const onlinePane = document.querySelector('#online');
  if (onlinePane) {
    const box = document.createElement('section');
    box.id = 'desktop-server';
    box.style.cssText = 'padding:0 0 20px;margin:0 0 20px;border-bottom:1px solid var(--line)';
    box.innerHTML = `<h3>Connection</h3>
      <label style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:20px">Play online (one player per window)<input class="switch" id="desktop-online" type="checkbox"></label>
      <label for="desktop-server-address">Server address</label>
      <input id="desktop-server-address" type="text" placeholder="http://192.168.1.20:8080" spellcheck="false" autocomplete="off" style="display:block;width:100%;box-sizing:border-box;margin:8px 0 12px">
      <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn" type="button" id="desktop-server-test">Test connection</button><button class="btn" type="button" id="desktop-server-save">Save & reload launcher</button></div>
      <p id="desktop-server-status" role="status" style="font-size:13px;margin-top:12px"></p>`;
    onlinePane.prepend(box);
    const address = box.querySelector('#desktop-server-address'), enabled = box.querySelector('#desktop-online');
    const status = box.querySelector('#desktop-server-status');
    address.value = connection.server; enabled.checked = connection.online;
    status.textContent = connection.online ? `Online server: ${connection.server}. Game files stay on this PC.` : 'Offline mode: single player and local split screen. Enable online to connect to a server.';
    box.querySelector('#desktop-server-test').onclick = async event => {
      const button = event.currentTarget; button.disabled = true; status.textContent = 'Testing server…';
      try { status.textContent = (await ipcRenderer.invoke(channel('launcher:check-server'), address.value)).message; }
      catch (error) { status.textContent = error.message; }
      finally { button.disabled = false; }
    };
    box.querySelector('#desktop-server-save').onclick = async event => {
      const button = event.currentTarget; button.disabled = true;
      try {
        await ipcRenderer.invoke(channel('launcher:save-connection'), { server: address.value, online: enabled.checked });
        location.reload();
      } catch (error) { status.textContent = error.message; button.disabled = false; }
    };
  }
  const changelog = document.querySelector('#changelog-btn');
  const donate = document.querySelector('#donate-btn');
  const host = changelog?.parentElement;
  if (!host) return;
  // Keep the hidden nodes available to the web launcher's existing handlers.
  for (const node of [changelog, donate, ...host.querySelectorAll('a[href*="discord"]')]) {
    if (node) node.style.setProperty('display', 'none', 'important');
  }
  const button = document.createElement('button');
  button.id = 'vinyl-studio-btn';
  button.className = changelog.className;
  button.textContent = 'Vinyl Studio';
  button.onclick = () => ipcRenderer.invoke(channel('launcher:studio')).catch(error => { button.title = error.message; });
  host.append(button);
});
