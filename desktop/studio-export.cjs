const fs = require('node:fs/promises');
const path = require('node:path');
const crypto = require('node:crypto');

async function exportToGame(root, entries, validate) {
  if (!Array.isArray(entries) || !entries.length || entries.length > 64) throw Error('Invalid export list');
  const checked = [], seen = new Set();
  async function noLink(file, optional = false) {
    try { if ((await fs.lstat(file)).isSymbolicLink()) throw Error('Linked export paths are not supported'); }
    catch (e) { if (!optional || e.code !== 'ENOENT') throw e; }
  }
  await noLink(path.join(root, 'game'));
  const cars = path.join(root, 'game', 'CARS');
  await noLink(cars);
  for (const entry of entries) {
    if (!entry || !/^[A-Z0-9_]{1,40}$/.test(entry.car) || seen.has(entry.car)) throw Error('Invalid car');
    seen.add(entry.car);
    const car = path.join(cars, entry.car), folder = path.join(car, 'VINYLS');
    await noLink(car); await fs.access(path.join(car, 'VINYLS.BIN'));
    await noLink(folder, true);
    const target = path.join(folder, `${entry.car}_CONTEST_01.png`);
    await noLink(target, true);
    const bytes = Buffer.from(entry.bytes);
    if (bytes.length > 8 * 1024 * 1024 || bytes.length < 24 || bytes.subarray(0,8).toString('hex') !== '89504e470d0a1a0a' || ![512, 1024].includes(bytes.readUInt32BE(16)) || bytes.readUInt32BE(20) !== bytes.readUInt32BE(16)) throw Error('Expected a 512x512 or 1024x1024 PNG');
    validate(bytes);
    checked.push({ car: entry.car, folder, target, bytes });
  }
  const backup = path.join(root, 'UserData', 'VinylBackups', `${Date.now()}-${crypto.randomUUID()}`);
  const written = [];
  for (const entry of checked) {
    await fs.mkdir(entry.folder, { recursive: true });
    try {
      await fs.access(entry.target);
      await fs.mkdir(backup, { recursive: true });
      await fs.copyFile(entry.target, path.join(backup, `${entry.car}_CONTEST_01.png`));
    } catch (e) { if (e.code !== 'ENOENT') throw e; }
    const temporary = entry.target + '.' + crypto.randomUUID() + '.tmp';
    try { await fs.writeFile(temporary, entry.bytes, { flag: 'wx' }); await fs.rename(temporary, entry.target); }
    finally { await fs.rm(temporary, { force: true }); }
    written.push(path.relative(root, entry.target));
  }
  return { written };
}
module.exports = { exportToGame };
