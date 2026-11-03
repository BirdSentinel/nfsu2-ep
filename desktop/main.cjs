const { app, BrowserWindow, WebContentsView, dialog, session, nativeImage, ipcMain } = require('electron');
const fs = require('node:fs');
const path = require('node:path');
const { startServer } = require('./server.cjs');
const root = app.isPackaged ? path.dirname(process.execPath) : path.resolve(__dirname, '../out/portable/Egyuttparkolas');
const studioMode = process.argv.includes('--vinyl-studio');
const profile = path.join(root, 'UserData');
// A fixed origin keeps OPFS saves available after every launch and drive-letter change.
const origin = 'http://127.0.0.1:18742';
const title = 'Együttparkolás';
app.setName(title);
app.setAppUserModelId('hu.egyuttparkolas.portable');
let server, win;
let studioWindow, studioVisible = false, requestedStudio = studioMode;
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
  studioWindow = new WebContentsView({ webPreferences: { preload: path.join(__dirname, 'studio-preload.cjs'), contextIsolation: true, sandbox: true, nodeIntegration: false } });
  win.contentView.addChildView(studioWindow);
  studioVisible = true;
  sizeStudio();
  ipcMain.removeHandler('studio:library');
  ipcMain.handle('studio:library', async (event, revision) => {
    if (!studioWindow || event.sender !== studioWindow.webContents) throw Error('Invalid library request');
    const result = await read();
    return result.revision === revision ? { revision, images: null } : result;
  });
  for (const channel of ['studio:launcher', 'studio:export']) ipcMain.removeHandler(channel);
  ipcMain.handle('studio:launcher', event => {
    if (event.sender !== studioWindow.webContents) throw Error('Invalid editor request');
    showLauncher();
  });
  let exporting = false;
  ipcMain.handle('studio:export', async (event, entries) => {
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
try {
  fs.mkdirSync(profile, { recursive: true });
  const probe = path.join(profile, '.write-test'); fs.writeFileSync(probe, ''); fs.unlinkSync(probe);
  app.setPath('userData', profile);
  app.setPath('sessionData', profile);
  app.setPath('crashDumps', path.join(profile, 'crashes'));
} catch (e) {
  dialog.showErrorBox('Cannot write portable saves', `Keep the game on a writable drive.\n${e.message}`);
  app.exit(1);
}
if (!app.requestSingleInstanceLock()) app.quit();
else {
  app.on('second-instance', (_event, argv) => {
    if (argv.includes('--vinyl-studio')) openStudio().catch(e => dialog.showErrorBox('Cannot open Vinyl Studio', e.message));
    else showLauncher();

  });
  app.whenReady().then(async () => {
    for (const p of ['game/SPEED2.EXE', 'web/index.html', 'web/game.wasm', 'web/game.json']) {
      if (!fs.existsSync(path.join(root, p))) throw new Error(`Missing ${p}. Copy the entire portable folder, including game and web.`);
    }
    server = await startServer(root, 18742, png => {
      let image = nativeImage.createFromBuffer(png);
      if (image.isEmpty()) throw Error('PNG could not be decoded');
      image = image.resize({ width: 512, height: 512, quality: 'best' });
      // Electron's Windows bitmap is premultiplied BGRA; our encoder takes straight RGBA.
      const bitmap = image.toBitmap(), rgba = Buffer.alloc(bitmap.length);
      for (let i = 0; i < bitmap.length; i += 4) {
        const a = bitmap[i + 3]; rgba[i + 3] = a;
        for (let c = 0; c < 3; c++) rgba[i + c] = a ? Math.min(255, Math.round(bitmap[i + 2 - c] * 255 / a)) : 0;
      }
      return rgba;
    });
    fs.writeFileSync(path.join(profile, 'vinyl-overrides.log'), server.vinylNotes.join('\n') + '\n');
    const errors = server.vinylNotes.filter(n => n.startsWith('ERROR'));
    if (errors.length) dialog.showMessageBoxSync({ type: 'warning', message: 'Some PNG vinyls could not be loaded',
      detail: errors.join('\n'), buttons: ['Continue with original vinyls'] });
    // Offline local play: never load remote content into the desktop renderer.
    session.defaultSession.webRequest.onBeforeRequest((details, cb) => {
      cb({ cancel: details.webContentsId !== studioWindow?.webContents.id && !details.url.startsWith(origin + '/') && !/^(blob:|data:)/.test(details.url) });
    });
    session.defaultSession.setPermissionRequestHandler((_wc, permission, cb) => cb(['fullscreen', 'pointerLock'].includes(permission)));
    win = new BrowserWindow({ title, icon: path.join(root, 'icon.png'), width: 1280, height: 800, autoHideMenuBar: true,
      webPreferences: { preload: path.join(__dirname, 'launcher-preload.cjs'), nodeIntegration: false, contextIsolation: true, sandbox: true, backgroundThrottling: false } });
    ipcMain.handle('launcher:studio', event => {
      if (event.sender !== win.webContents) throw Error('Invalid launcher request');
      return openStudio();
    });
    win.setMenu(null);
    win.on('resize', sizeStudio);
    win.on('close', event => {
      if (studioWindow && !studioWindow.webContents.isDestroyed() && !confirmStudioClose()) event.preventDefault();
    });
    win.on('closed', () => {
      if (studioWindow && !studioWindow.webContents.isDestroyed()) studioWindow.webContents.close({ waitForBeforeUnload: false });
      studioWindow = null;
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
    await win.loadURL(origin + '/?localPlayers=2');
    if (requestedStudio) await openStudio();
  }).catch(e => {
    dialog.showErrorBox('Cannot start Egyuttparkolas', e.code === 'EADDRINUSE'
      ? 'Port 18742 is already in use. Close the other copy of the game or the application using this port, then try again.' : e.message);
    app.quit();
  });
  app.on('window-all-closed', () => app.quit());
  app.on('will-quit', () => { server?.closeAllConnections(); server?.close(); });
}
