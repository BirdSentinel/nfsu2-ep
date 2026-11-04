const { contextBridge, ipcRenderer } = require('electron');
const instanceId = Number(process.argv.find(value => /^--ep-instance=\d+$/.test(value))?.split('=')[1] || 1);
const channel = name => `${name}:${instanceId}`;
contextBridge.exposeInMainWorld('studioLibrary', {
  read: revision => ipcRenderer.invoke(channel('studio:library'), revision),
  projects: {
    list: () => ipcRenderer.invoke(channel('studio:projects:list')),
    open: name => ipcRenderer.invoke(channel('studio:projects:open'), name),
    save: project => ipcRenderer.invoke(channel('studio:projects:save'), project)
  },
  launcher: () => ipcRenderer.invoke(channel('studio:launcher')),
  export: entries => ipcRenderer.invoke(channel('studio:export'), entries)
});
