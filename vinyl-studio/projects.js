'use strict';
(() => {
  const store = window.studioLibrary?.projects;
  let currentName = '';
  $('closeProjects').onclick = () => $('projectsDialog').close();
  $('cancelSave').onclick = () => $('saveDialog').close();
  $('importProject').onclick = () => { $('projectsDialog').close(); $('loadProject').value = ''; $('loadProject').click(); };
  $('loadProject').addEventListener('change', () => { currentName = ''; });
  $('openProjects').onclick = async () => {
    if (busy) return;
    if (!store) { $('loadProject').value = ''; $('loadProject').click(); return; }
    $('projectsDialog').showModal();
    $('projectList').replaceChildren();
    $('projectsMessage').textContent = 'Loading projects…';
    try {
      const files = await store.list();
      $('projectsMessage').textContent = files.length ? '' : 'No saved projects yet. Use Save project to create one.';
      for (const file of files) {
        const button = document.createElement('button'), label = document.createElement('span'), detail = document.createElement('small');
        label.textContent = file.name;
        detail.textContent = new Date(file.modified).toLocaleString() + ' · ' + (file.size / 1024).toFixed(0) + ' KB';
        button.append(label, detail);
        button.onclick = async () => {
          if (busy || (dirty && !confirm('Replace your unsaved work with this project?'))) return;
          busy = true;
          $('projectsMessage').textContent = 'Opening project…';
          try {
            await readProject(JSON.parse(await store.open(file.name)));
            currentName = file.name;
            $('projectsDialog').close();
            status('Opened ' + file.name);
          } catch (error) { $('projectsMessage').textContent = 'Loading error: ' + error.message; }
          finally { busy = false; renderInspector(); }
        };
        $('projectList').append(button);
      }
    } catch (error) { $('projectsMessage').textContent = error.message; }
  };
  if (!store) return; // Keep browser download support when used outside the desktop app.
  $('saveProject').onclick = () => {
    if (busy) return;
    $('projectName').value = currentName.replace(/\.epvinyl$/i, '') || 'My design';
    $('saveMessage').textContent = '';
    $('saveDialog').showModal();
    $('projectName').focus(); $('projectName').select();
  };
  $('saveForm').onsubmit = async event => {
    event.preventDefault();
    if (busy) return;
    busy = true; $('confirmSave').disabled = true; $('cancelSave').disabled = true;
    $('saveMessage').textContent = 'Saving…';
    try {
      const request = { name: $('projectName').value, json: JSON.stringify(project()) };
      let result = await store.save(request);
      if (result.exists) {
        if (!confirm('A project with this name already exists. Replace it?')) { $('saveMessage').textContent = 'Choose another name to keep both projects.'; return; }
        result = await store.save({ ...request, overwrite: true });
      }
      currentName = result.name; dirty = false;
      $('projectInfo').textContent = currentName + ' · Project saved';
      status('Saved to VinylStudio/vinyls/' + currentName);
      $('saveDialog').close();
    } catch (error) { $('saveMessage').textContent = 'Save failed: ' + error.message; }
    finally { busy = false; $('confirmSave').disabled = false; $('cancelSave').disabled = false; }
  };
})();
