const fs = require('node:fs');
const path = require('node:path');
const { randomUUID } = require('node:crypto');
const LIMIT = 128 * 1024 * 1024;

function createProjectStore(directory) {
  function target(name) {
    if (typeof name !== 'string' || !name.trim() || name.length > 150 || /[<>:"/\\|?*\x00-\x1f]/.test(name)) throw Error('Choose a valid project name.');
    name = name.trim().replace(/\.epvinyl$/i, '');
    if (!name || /[. ]$/.test(name) || /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(name)) throw Error('Choose a valid project name.');
    fs.mkdirSync(directory, { recursive: true });
    const file = path.join(directory, name + '.epvinyl');
    if (fs.existsSync(file) && (!fs.lstatSync(file).isFile() || fs.lstatSync(file).isSymbolicLink())) throw Error('Invalid project file.');
    return file;
  }
  return {
    list() {
      fs.mkdirSync(directory, { recursive: true });
      return fs.readdirSync(directory, { withFileTypes: true }).filter(e => e.isFile() && /\.epvinyl$/i.test(e.name)).map(e => {
        const stat = fs.statSync(path.join(directory, e.name));
        return { name: e.name, modified: stat.mtimeMs, size: stat.size };
      }).sort((a, b) => b.modified - a.modified || a.name.localeCompare(b.name));
    },
    open(name) {
      const file = target(name);
      if (fs.statSync(file).size > LIMIT) throw Error('Projects must be no larger than 128 MB.');
      return fs.readFileSync(file, 'utf8');
    },
    save({ name, json, overwrite = false }) {
      const file = target(name);
      if (typeof json !== 'string' || Buffer.byteLength(json) > LIMIT) throw Error('Projects must be no larger than 128 MB.');
      const project = JSON.parse(json);
      if (project.format !== 'EPVINYL' || project.version !== 2 || !Array.isArray(project.assets) || !project.cars) throw Error('Invalid project.');
      if (fs.existsSync(file) && !overwrite) return { exists: true };
      const temporary = path.join(directory, '.' + randomUUID() + '.tmp');
      try {
        fs.writeFileSync(temporary, json, { flag: 'wx' });
        if (overwrite) fs.renameSync(temporary, file);
        else { fs.copyFileSync(temporary, file, fs.constants.COPYFILE_EXCL); fs.unlinkSync(temporary); }
      } finally { if (fs.existsSync(temporary)) fs.unlinkSync(temporary); }
      return { name: path.basename(file) };
    }
  };
}
module.exports = { createProjectStore };
