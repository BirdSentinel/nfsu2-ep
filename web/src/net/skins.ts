import type { NetProcess } from './index';

// The authenticated LAN connection owns uploads. Artwork is never written into
// another driver's game directory and never keyed only by car/vinyl name.
export class SkinSync {
  send: ((message: object) => boolean) | null = null;
  remote = new Map<number, { version: number; png: Blob }>();
  wanted = new Set<number>();
  private lastAsk = 0;
  private nextPeer = 0;
  private digest = '';
  private generation = 0;
  private busy = false;
  ready = false;
  reset() { this.generation++; this.digest = ''; this.remote.clear(); this.ready = false; }
  receive(m: any) {
    if (m.t === 'skin-reset') { this.reset(); return; }
    if (m.t === 'skin-ready') { this.ready = true; return; }
    if (m.t === 'skin-saved') { if (typeof m.digest === 'string') this.digest = m.digest; return; }
    if (m.t !== 'skin' || !Number.isInteger(m.vip) || !this.wanted.has(m.vip)) return;
    if (!m.png) { this.remote.delete(m.vip); return; }
    if (typeof m.png !== 'string' || m.png.length > 1500000 || !Number.isSafeInteger(m.version)) return;
    try {
      const data = Uint8Array.from(atob(m.png), c => c.charCodeAt(0));
      const v = new DataView(data.buffer);
      if (data.length < 33 || v.getUint32(0) !== 0x89504e47 || v.getUint32(4) !== 0x0d0a1a0a || v.getUint32(16) !== 512 || v.getUint32(20) !== 512) return;
      this.remote.set(m.vip, { version: m.version, png: new Blob([data], { type: 'image/png' }) });
    } catch { /* invalid remote artwork: keep the game's own skin */ }
  }
  poll(peers: number[]) {
    this.wanted = new Set(peers.slice(0, 48));
    for (const vip of this.remote.keys()) if (!this.wanted.has(vip)) this.remote.delete(vip);
    if (!this.ready || !this.wanted.size || performance.now() - this.lastAsk < 1000) return;
    this.lastAsk = performance.now();
    const vip = [...this.wanted][this.nextPeer++ % this.wanted.size];
    this.send?.({ t: 'skin-get', vip, version: this.remote.get(vip)?.version ?? 0 });
  }
  async publish(png: Blob) {
    if (!this.ready || this.busy || png.size > 1100000) return;
    this.busy = true;
    const gen = this.generation;
    try {
      const bytes = new Uint8Array(await png.arrayBuffer());
      const digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), x => x.toString(16).padStart(2, '0')).join('');
      if (gen !== this.generation || digest === this.digest) return;
      let text = ''; for (let p = 0; p < bytes.length; p += 8192) text += String.fromCharCode(...bytes.subarray(p, p + 8192));
      this.send?.({ t: 'skin-put', digest, png: btoa(text) });
    } finally { this.busy = false; }
  }
}
const states = new WeakMap<NetProcess, SkinSync>();
export function skinsFor(proc: NetProcess): SkinSync {
  let state = states.get(proc);
  if (!state) { state = new SkinSync(); states.set(proc, state); }
  return state;
}
