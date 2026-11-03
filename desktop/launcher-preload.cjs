const { ipcRenderer } = require('electron');
window.addEventListener('DOMContentLoaded', () => {
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
  button.onclick = () => ipcRenderer.invoke('launcher:studio').catch(error => { button.title = error.message; });
  host.append(button);
});
