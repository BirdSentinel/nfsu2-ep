// PNG overrides are prepared afresh on launch; missing/broken images keep the game's texture.
const fs = require('node:fs');
const path = require('node:path');
const catalog = require('./billboards.json');

function prepareBillboards(root, data, decodePNG) {
  if (!decodePNG) return;
  for (const entry of catalog) {
    const file = path.join(root, 'custom', 'billboards', entry.file);
    if (!fs.existsSync(file)) continue;
    try {
      const rgba = decodePNG(fs.readFileSync(file), entry.width, entry.height);
      if (rgba.length !== entry.width * entry.height * 4) throw Error('Unexpected pixel size');
      const buffer = Buffer.alloc(rgba.length);
      for (let i = 0; i < rgba.length; i += 4) {
        buffer[i] = rgba[i + 2]; buffer[i + 1] = rgba[i + 1];
        buffer[i + 2] = rgba[i]; buffer[i + 3] = rgba[i + 3];
      }
      const p = `GLOBAL/custom-billboards/${entry.file.slice(0, -4)}.bgra`;
      data.files.set(p.toLowerCase(), { buffer, size: buffer.length });
      data.entries.push({ p, s: buffer.length, m: fs.statSync(file).mtimeMs / 1000 });
    } catch (error) {
      console.warn(`Custom billboard ${entry.file} could not be loaded: ${error.message}`);
    }
  }
}
module.exports = { prepareBillboards };
