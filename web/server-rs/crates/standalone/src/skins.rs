//! Session-owned baked car skins. Bounded RAM only; no client-supplied paths.
use std::{collections::HashMap, time::{Duration, Instant}};
use base64::{Engine, engine::general_purpose::STANDARD};
use bytes::Bytes;
use serde_json::{Map, Value, json};


const MAX_PNG: usize = 4_300_000;
const MAX_CACHE: usize = 320 * 1024 * 1024;
struct Skin { version: u64, reply: Bytes }
#[derive(Default)]
pub struct Skins {
    images: HashMap<u32, Skin>, put_at: HashMap<u32, Instant>, get_at: HashMap<u32, Instant>, version: u64,
}
impl Skins {
    pub fn remove(&mut self, vip: u32) { self.images.remove(&vip); self.put_at.remove(&vip); self.get_at.remove(&vip); }
    pub fn message(&mut self, vip: u32, m: &Map<String, Value>) -> Option<Bytes> {
        match m.get("t").and_then(Value::as_str) {
            Some("skin-hello") => { return Some(Bytes::from_static(b"{\"t\":\"skin-ready\",\"maxSize\":1024}")); }
            Some("skin-put") => {
                if self.put_at.get(&vip).is_some_and(|t| t.elapsed() < Duration::from_secs(5)) { return None; }
                self.put_at.insert(vip, Instant::now());
                let Some(png) = m.get("png").and_then(Value::as_str).filter(|p| p.len() <= 5_800_000) else { return None };
                let Some(digest) = m.get("digest").and_then(Value::as_str).filter(|s| s.len() == 64 && s.bytes().all(|b| b.is_ascii_hexdigit())) else { return None };
                let Ok(data) = STANDARD.decode(png) else { return None };
                if data.len() < 33 || data.len() > MAX_PNG || &data[..8] != b"\x89PNG\r\n\x1a\n" || &data[12..16] != b"IHDR"
                    || (data[16..24] != [0,0,2,0,0,0,2,0] && data[16..24] != [0,0,4,0,0,0,4,0]) { return None; }
                let used: usize = self.images.iter().filter(|(id, _)| **id != vip).map(|(_, s)| s.reply.len()).sum();
                if used + png.len() + 128 > MAX_CACHE { return None; }
                self.version += 1;
                let reply = Bytes::from(json!({"t":"skin", "vip":vip,"version":self.version,"png":png}).to_string());
                self.images.insert(vip, Skin { version: self.version, reply });
                return Some(Bytes::from(json!({"t":"skin-saved","digest":digest}).to_string()));
            }
            Some("skin-get") => {
                if self.get_at.get(&vip).is_some_and(|t| t.elapsed() < Duration::from_millis(900)) { return None; }
                self.get_at.insert(vip, Instant::now());
                // One image per request keeps artwork out of the gameplay's send queue bursts.
                let Some(id) = m.get("vip").and_then(Value::as_u64).and_then(|v| u32::try_from(v).ok()) else { return None };
                let version = m.get("version").and_then(Value::as_u64).unwrap_or(0);
                if let Some(skin) = self.images.get(&id) {
                    if skin.version != version { return Some(skin.reply.clone()); }
                } else { return Some(Bytes::from(json!({"t":"skin","vip":id,"version":0}).to_string())); }
            }
            _ => {}
        }
        None
    }
}

