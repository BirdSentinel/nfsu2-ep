const { app, BrowserWindow, WebContentsView, dialog, session, nativeImage, ipcMain } = require('electron');
const fs = require('node:fs');
const path = require('node:path');
const { startServer } = require('./server.cjs');
const { normalizeServer, createOnline, checkServer } = require('./online.cjs');
const root = app.isPackaged ? path.dirname(process.execPath) : path.resolve(__dirname, '../out/portable/Egyuttparkolas');
const studioMode = process.argv.includes('--vinyl-studio');
const profile = path.join(root, 'UserData');
app.setName('Együttparkolás');
app.setAppUserModelId('hu.egyuttparkolas.portable');
app.commandLine.appendSwitch('disable-http-cache');
try {
  fs.mkdirSync(profile, { recursive: true });
  const probe = path.join(profile, `.write-test-${process.pid}`); fs.writeFileSync(probe, ''); fs.unlinkSync(probe);
  app.setPath('userData', profile);
  app.setPath('sessionData', profile);
  app.setPath('crashDumps', path.join(profile, 'crashes'));
} catch (e) {
  dialog.showErrorBox('Cannot write portable saves', `Keep the game on a writable drive.\n${e.message}`);
  app.exit(1);
}

const clients = new Map();
function launchClient(initiallyStudio = false) {
  let id = 1;
  while (clients.has(id)) id++;
  clients.set(id, null);
  void createClient(id, initiallyStudio).catch(error => {
    clients.delete(id);
    dialog.showErrorBox('Cannot start Egyuttparkolas', error.message);
    if (!clients.size) app.quit();
  });
}

async function createClient(id, initiallyStudio) {
  const profile = id === 1 ? path.join(root, 'UserData') : path.join(root, 'UserData', 'Clients', String(id));
  fs.mkdirSync(profile, { recursive: true });
  const partition = id === 1 ? undefined : 'persist:client-' + id;
  const clientSession = id === 1 ? session.defaultSession : session.fromPartition(partition);
  const port = 18742 + id - 1;
  const origin = 'http://127.0.0.1:' + port;
  const title = id === 1 ? 'Együttparkolás' : 'Együttparkolás — Player ' + id;
  const instanceArgument = '--ep-instance=' + id;
  const handles = new Set(), listeners = [];
  const channel = name => name + ':' + id;
  const ipc = {
    handle(name, fn) { ipcMain.handle(channel(name), fn); handles.add(name); },
    removeHandler(name) { ipcMain.removeHandler(channel(name)); handles.delete(name); },
    on(name, fn) { ipcMain.on(channel(name), fn); listeners.push([channel(name), fn]); },
  };
  const connectionFile = path.join(profile, 'connection.json');
    // Only copy connection preferences on a new test profile. Saves and identities stay separate.
    if (id !== 1 && !fs.existsSync(connectionFile)) {
      try { fs.copyFileSync(path.join(root, 'UserData', 'connection.json'), connectionFile, fs.constants.COPYFILE_EXCL); }
      catch (error) { if (!['ENOENT', 'EEXIST'].includes(error.code)) throw error; }
    }
  // First launch only: saved connection preferences below always take priority.
  let connection = { server: 'http://85.255.1.94:8080', online: true };
  try {
    const saved = JSON.parse(fs.readFileSync(connectionFile, 'utf8'));
    connection = { server: normalizeServer(saved.server || ''), online: saved.online === true };
  } catch { /* first start, or invalid settings: use the default connection */ }
  const online = createOnline(() => connection.online ? connection.server : '');
  let server, win;
  let studioWindow, studioVisible = false, requestedStudio = initiallyStudio;
  function sizeStudio() {
    if (!studioWindow || studioWindow.webContents.isDestroyed() || !win) return;
    const [width, height] = win.getContentSize();
    studioWindow.setBounds({ x: 0, y: 0, width, height });
  }
  function confirmStudioClose() {
    return dialog.showMessageBoxSync(win, { type: 'question', buttons: ['Keep editing', 'Close editor'], defaultId: 0, cancelId: 0,
      message: 'Close Vinyl Studio?', detail: 'The editor will close completely. Any unsaved project changes will be lost.' }) === 1;
  }
  function disposeStudio() {
    if (!studioWindow) return;
    const closing = studioWindow;
    studioWindow = null;
    studioVisible = false;
    win?.contentView.removeChildView(closing);
    if (!closing.webContents.isDestroyed()) closing.webContents.close({ waitForBeforeUnload: false });
  }
  function showLauncher() {
    requestedStudio = false;
    if (!win) return;
    if (studioWindow) { if (!confirmStudioClose()) return; disposeStudio(); }
    try { server?.refreshVinyls(); } catch (error) { dialog.showErrorBox('Cannot refresh vinyls', error.message); }
    win.show(); win.focus(); win.webContents.focus();
  }
  async function openStudio() {
    requestedStudio = true;
    if (!win) return;
    if (studioWindow && !studioWindow.webContents.isDestroyed()) { studioWindow.setVisible(true); studioVisible = true; sizeStudio(); win.show(); win.focus(); studioWindow.webContents.focus(); return; }
    const { createLibraryReader } = require('./studio-library.cjs');
    const read = createLibraryReader(path.join(root, 'VinylStudio', 'decals'));
    studioWindow = new WebContentsView({ webPreferences: { preload: path.join(__dirname, 'studio-preload.cjs'), partition, additionalArguments: [instanceArgument], contextIsolation: true, sandbox: true, nodeIntegration: false } });
    studioWindow.setBackgroundColor('#0b0d10');
    win.contentView.addChildView(studioWindow);
    studioVisible = true;
    sizeStudio();
    const projects = require('./studio-projects.cjs').createProjectStore(path.join(root, 'VinylStudio', 'vinyls'));
    for (const operation of ['list', 'open', 'save']) {
      const name = `studio:projects:${operation}`;
      ipc.removeHandler(name);
      ipc.handle(name, (event, value) => {
        if (!studioWindow || event.sender !== studioWindow.webContents) throw Error('Invalid editor request');
        return projects[operation](value);
      });
    }
    ipc.removeHandler('studio:library');
    ipc.handle('studio:library', async (event, revision) => {
      if (!studioWindow || event.sender !== studioWindow.webContents) throw Error('Invalid library request');
      const result = await read();
      return result.revision === revision ? { revision, images: null } : result;
    });
    for (const channel of ['studio:launcher', 'studio:export']) ipc.removeHandler(channel);
    ipc.handle('studio:launcher', event => {
      if (event.sender !== studioWindow.webContents) throw Error('Invalid editor request');
      showLauncher();
    });
    let exporting = false;
    ipc.handle('studio:export', async (event, entries) => {
      if (event.sender !== studioWindow.webContents || exporting) throw Error('Export unavailable');
      exporting = true;
      try {
        return await require('./studio-export.cjs').exportToGame(root, entries, bytes => {
          const image = nativeImage.createFromBuffer(bytes), size = image.getSize();
          if (image.isEmpty() || size.width !== 512 || size.height !== 512) throw Error('Invalid PNG');
        });
      } finally { exporting = false; }
    });
    studioWindow.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
    studioWindow.webContents.on('will-navigate', event => event.preventDefault());
    await studioWindow.webContents.loadFile(path.join(root, 'VinylStudio', 'index.html'));
    if (studioVisible) studioWindow.webContents.focus();
  }
  let cleaned = false;
  function cleanup() {
    if (cleaned) return;
    cleaned = true;
    online.close(); server?.closeAllConnections(); server?.close();
    for (const name of handles) ipcMain.removeHandler(channel(name));
    for (const [name, fn] of listeners) ipcMain.removeListener(name, fn);
    clients.delete(id);
  }
  clients.set(id, { openStudio, cleanup });
  try {
    // Remove only redundant browser caches, never OPFS save/settings storage.
    await clientSession.clearStorageData({ origin, storages: ['serviceworkers', 'cachestorage'] });
    await clientSession.clearCache();
    for (const p of ['game/SPEED2.EXE', 'web/index.html', 'web/game.wasm', 'web/game.json']) {
      if (!fs.existsSync(path.join(root, p))) throw new Error(`Missing ${p}. Copy the entire portable folder, including game and web.`);
    }
    server = await startServer(root, port, (png, width = 512, height = 512) => {
      let image = nativeImage.createFromBuffer(png);
      if (image.isEmpty()) throw Error('PNG could not be decoded');
      image = image.resize({ width, height, quality: 'best' });
      // Electron's Windows bitmap is premultiplied BGRA; our encoder takes straight RGBA.
      const bitmap = image.toBitmap(), rgba = Buffer.alloc(bitmap.length);
      for (let i = 0; i < bitmap.length; i += 4) {
        const a = bitmap[i + 3]; rgba[i + 3] = a;
        for (let c = 0; c < 3; c++) rgba[i + c] = a ? Math.min(255, Math.round(bitmap[i + 2 - c] * 255 / a)) : 0;
      }
      return rgba;
    }, online);
    fs.writeFileSync(path.join(profile, 'vinyl-overrides.log'), server.vinylNotes.join('\n') + '\n');
    const errors = server.vinylNotes.filter(n => n.startsWith('ERROR'));
    if (errors.length) dialog.showMessageBoxSync({ type: 'warning', message: 'Some PNG vinyls could not be loaded',
      detail: errors.join('\n'), buttons: ['Continue with original vinyls'] });
    // Assets stay local. Multiplayer leaves through the allowlisted Node proxy.
    clientSession.webRequest.onBeforeRequest((details, cb) => {
      cb({ cancel: details.webContentsId !== studioWindow?.webContents.id && !details.url.startsWith(origin + '/')
        && !details.url.startsWith(origin.replace('http:', 'ws:') + '/lan') && !/^(blob:|data:)/.test(details.url) });
    });
    clientSession.setPermissionRequestHandler((_wc, permission, cb) => cb(['fullscreen', 'pointerLock'].includes(permission)));
    win = new BrowserWindow({ title, icon: path.join(root, 'icon.png'), width: 1280, height: 800, autoHideMenuBar: true,
      show: false, backgroundColor: '#0b0d10',
      webPreferences: { preload: path.join(__dirname, 'launcher-preload.cjs'), partition, additionalArguments: [instanceArgument], nodeIntegration: false, contextIsolation: true, sandbox: true, backgroundThrottling: false } });
    ipc.handle('launcher:studio', event => {
      if (event.sender !== win.webContents) throw Error('Invalid launcher request');
      return openStudio();
    });
    ipc.on('launcher:connection', event => {
      event.returnValue = event.sender === win.webContents ? connection : { server: '', online: false };
    });
    ipc.handle('launcher:check-server', (event, value) => {
      if (event.sender !== win.webContents) throw Error('Invalid launcher request');
      return checkServer(value);
    });
    ipc.handle('launcher:save-connection', async (event, value) => {
      if (event.sender !== win.webContents) throw Error('Invalid launcher request');
      if (!await win.webContents.executeJavaScript('document.querySelector("#stage")?.hidden === true && !window.__nfsu2?.session')) throw Error('Exit the game before changing the server.');
      const next = { server: normalizeServer(value?.server), online: value?.online === true };
      if (next.online && !next.server) throw Error('Enter a server address first.');
      if (next.server === origin) throw Error('Use the online server port (normally 8080), not the local launcher port.');
      fs.mkdirSync(profile, { recursive: true });
      fs.writeFileSync(connectionFile + '.tmp', JSON.stringify(next, null, 2));
      fs.renameSync(connectionFile + '.tmp', connectionFile);
      online.close(); connection = next;
      return next;
    });
    win.setMenu(null);
    win.on('resize', sizeStudio);
    win.on('close', event => {
      if (studioWindow && !studioWindow.webContents.isDestroyed() && !confirmStudioClose()) event.preventDefault();
    });
    win.on('closed', () => {
      if (studioWindow && !studioWindow.webContents.isDestroyed()) studioWindow.webContents.close({ waitForBeforeUnload: false });
      studioWindow = null;
      cleanup();
    });
    win.on('page-title-updated', event => { event.preventDefault(); win.setTitle(title); });
    win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
    // The web game installs beforeunload while running. Electron otherwise
    // cancels window closure silently, leaving the portable drive locked.
    win.webContents.on('will-prevent-unload', event => {
      const choice = dialog.showMessageBoxSync(win, { type: 'question', buttons: ['Keep playing', 'Close game'],
        defaultId: 0, cancelId: 0, message: 'Close the game?', detail: 'Save your progress in the game before closing.' });
      if (choice === 1) event.preventDefault();
    });
    win.webContents.on('will-navigate', (event, url) => { if (new URL(url).origin !== origin) event.preventDefault(); });
    win.webContents.on('before-input-event', (event, input) => {
      if (input.type === 'keyDown' && input.key === 'F11') { event.preventDefault(); win.setFullScreen(!win.isFullScreen()); }
    });
    // Open the local origin without the launcher/game workers running so the
    // obsolete OPFS game-data cache can be removed without touching saves.
    await win.loadURL(origin + '/desktop-storage-init');
    await win.webContents.executeJavaScript(`(async () => {
      const storage = await navigator.storage.getDirectory();
      try { await storage.removeEntry('cache', { recursive: true }); }
      catch (error) { if (error.name !== 'NotFoundError') throw error; }
    })()`);
    await win.loadURL(origin + '/');
    if (requestedStudio) await openStudio();
    // The preload applies the desktop theme at DOMContentLoaded. Wait for a
    // themed frame before showing the native window, including direct editor entry.
    const initialContents = studioVisible ? studioWindow.webContents : win.webContents;
    await initialContents.executeJavaScript('new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))');
    win.show();
  } catch (error) {
    cleanup();
    if (win && !win.isDestroyed()) win.destroy();
    dialog.showErrorBox('Cannot start Egyuttparkolas', error.code === 'EADDRINUSE'
      ? 'Local port ' + port + ' is already in use. Close the application using that port and try again.' : error.message);
    if (!clients.size) app.quit();
  }
}

if (!app.requestSingleInstanceLock()) app.quit();
else {
  app.on('second-instance', async (_event, argv) => {
    await app.whenReady();
    if (argv.includes('--vinyl-studio')) {
      const first = [...clients.values()].find(Boolean);
      if (first) void first.openStudio().catch(error => dialog.showErrorBox('Cannot open Vinyl Studio', error.message));
      else launchClient(true);
    } else launchClient();
  });
  app.whenReady().then(() => launchClient(studioMode));
  app.on('window-all-closed', () => { if (!clients.size) app.quit(); });
  app.on('will-quit', () => { for (const client of [...clients.values()]) client?.cleanup(); });
}
