const fs = require('node:fs/promises');
const path = require('node:path');

function createLibraryReader(root) {
  let previous = '', cached = [];
  return async () => {
    const files = [];
    async function walk(folder) {
      for (const entry of (await fs.readdir(folder, { withFileTypes: true })).sort((a,b)=>a.name.localeCompare(b.name))) {
        if (entry.isSymbolicLink()) continue;
        const file = path.join(folder, entry.name);
        if (entry.isDirectory()) await walk(file);
        else if (entry.isFile() && /\.(png|jpe?g)$/i.test(entry.name)) {
          const stat = await fs.stat(file);
          files.push({ file, name: path.relative(root, file), size: stat.size, time: stat.mtimeMs });
        }
      }
    }
    await fs.mkdir(root, { recursive: true });
    await walk(root);
    let total = 0;
    const selected = files.filter(f => {
      if (f.size > 32 * 1024 * 1024 || total + f.size > 64 * 1024 * 1024) return false;
      total += f.size;
      return true;
    }).slice(0, 128);
    const revision = JSON.stringify(selected);
    if (revision !== previous) {
      const images = [];
      for (const f of selected) {
        const mime = /\.png$/i.test(f.name) ? 'image/png' : 'image/jpeg';
        images.push({ name: f.name, url: `data:${mime};base64,${(await fs.readFile(f.file)).toString('base64')}` });
      }
      cached = images;
      previous = revision;
    }
    return { revision, images: cached };
  };
}
module.exports = { createLibraryReader };
