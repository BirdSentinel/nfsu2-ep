/** Set only by the sandboxed Electron preload, before the launcher boots. */
export const localGameFiles = () =>
  (globalThis as typeof globalThis & { desktopGame?: { localFiles?: boolean } }).desktopGame?.localFiles === true;

export const desktopConnection = () =>
  (globalThis as typeof globalThis & { desktopGame?: { connection?: { server: string; online: boolean } } }).desktopGame?.connection;

// Cloud identities belong to the selected server, while local game saves stay shared.
export const serverStorageKey = (key: string) => {
  const connection = desktopConnection();
  return connection ? `${key}:server:${connection.online ? connection.server : 'offline'}` : key;
};
