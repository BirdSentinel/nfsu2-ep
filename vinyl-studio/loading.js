'use strict';
(async () => {
  try {
    // Let the loading screen paint before parsing the large model catalog.
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    for (const file of ['models.js', 'library.js', 'core.js', 'decals.js', 'viewer.js', 'app.js', 'projects.js']) {
      await new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = file;
        script.onload = resolve;
        script.onerror = () => reject(new Error('Could not load ' + file));
        document.body.append(script);
      });
    }
    await window.studioStartup;
    await document.fonts.ready;
    await Promise.all([...document.images].map(image => image.decode().catch(() => {})));
    window.VinylStudio.viewer.draw();
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    document.body.removeAttribute('data-loading');
    document.getElementById('studioLoading').hidden = true;
  } catch (error) {
    document.getElementById('loadingMessage').textContent = 'Unable to load the editor: ' + error.message;
    document.querySelector('.loading-ring').hidden = true;
    document.getElementById('loadingRetry').hidden = false;
  }
})();
