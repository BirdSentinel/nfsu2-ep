const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('studioLibrary', {
  read: revision => ipcRenderer.invoke('studio:library', revision),
  launcher: () => ipcRenderer.invoke('studio:launcher'),
  export: entries => ipcRenderer.invoke('studio:export', entries)
});
