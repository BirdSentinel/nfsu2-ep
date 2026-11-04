// Separate OPFS root: never mounted as /save, enumerated by the game, or synced as active profiles.
import { listFiles, readBytes, removePath, writeFile, writeTogether, PROFILES_DIR } from './savefs';
import { coverOf } from './profile';
import { zip, unzip } from './zip';

const directory = (saveDir: string) => `${saveDir}~archives`;
export interface SaveArchive { id: string; name: string; mtime: number; size: number }
const owned = (path: string, name: string) => {
  const p = path.split('/');
  return p.length >= 3 && p[0] === PROFILES_DIR &&
    (coverOf(p[1])?.profile ?? p[1]).toLowerCase() === name.toLowerCase();
};
export async function listArchives(saveDir: string): Promise<SaveArchive[]> {
  return (await listFiles(directory(saveDir))).filter(f => /^[^/]+~[0-9a-f-]+\.zip$/.test(f.path))
    .map(f => ({ id: f.path, name: decodeURIComponent(f.path.split('~')[0]), mtime: f.mtime, size: f.size }))
    .sort((a, b) => b.mtime - a.mtime);
}
export async function archiveSave(saveDir: string, name: string): Promise<void> {
  const files = (await listFiles(saveDir)).filter(f => owned(f.path, name));
  if (!files.some(f => f.path.toLowerCase() === `${PROFILES_DIR}/${name}/${name}`.toLowerCase())) throw Error('Profile not found.');
  const entries = await Promise.all(files.map(async f => ({ name: f.path, data: await readBytes(saveDir, f.path), mtime: f.mtime })));
  const bytes = zip(entries), id = `${encodeURIComponent(name)}~${crypto.randomUUID()}.zip`;
  await writeFile(directory(saveDir), id, bytes);
  const check = await readBytes(directory(saveDir), id);
  if (check.length !== bytes.length || check.some((b, i) => b !== bytes[i])) throw Error('Archive verification failed; the active save was kept.');
  // The complete, verified archive exists before any active file is removed.
  for (const folder of new Set(files.map(f => f.path.split('/')[1]))) await removePath(saveDir, `${PROFILES_DIR}/${folder}`);
}
export async function restoreArchive(saveDir: string, archive: SaveArchive): Promise<void> {
  const entries = await unzip(await readBytes(directory(saveDir), archive.id));
  if (!entries.some(e => e.name.toLowerCase() === `${PROFILES_DIR}/${archive.name}/${archive.name}`.toLowerCase()) ||
      entries.some(e => !owned(e.name, archive.name) || e.name.split('/').some(p => p === '..' || p === '.')))
    throw Error('Invalid save archive.');
  const folders = new Set(entries.map(e => e.name.split('/')[1].toLowerCase()));
  if ((await listFiles(saveDir)).some(f => f.path.split('/')[0] === PROFILES_DIR && folders.has(f.path.split('/')[1]?.toLowerCase())))
    throw Error('A profile with this name already exists. Rename or archive it first.');
  await writeTogether(saveDir, entries.map(e => ({ path: e.name, data: e.data })));
  await deleteArchive(saveDir, archive);
}
export async function deleteArchive(saveDir: string, archive: SaveArchive): Promise<void> {
  if (!(await listArchives(saveDir)).some(a => a.id === archive.id)) throw Error('Archive not found.');
  await removePath(directory(saveDir), archive.id);
}
