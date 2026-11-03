//! Portable multiplayer host. No game files, browser, Node, Docker or installer.
use std::{io, path::PathBuf, sync::Arc, time::Duration};
use bytes::Bytes;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use tokio::{io::{AsyncReadExt, AsyncWriteExt}, net::{TcpListener, TcpStream}, sync::Semaphore};
use nfsu2_lan::{AttachOpts, LanOptions, LanSwitch};
use nfsu2_online::{OnlineHost, OnlineOptions};
use nfsu2_roam::{RoamHub, RoamOptions};
use nfsu2_util::log;
mod skins;
use std::sync::Mutex;

#[derive(Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
struct Config { bind: String, port: u16, max_players: usize }
impl Default for Config {
    fn default() -> Self { Self { bind: "0.0.0.0".into(), port: 8080, max_players: 128 } }
}

struct Server { lan: Arc<LanSwitch>, roam: Arc<RoamHub>, skins: Arc<Mutex<skins::Skins>> }
fn lan_address() -> Option<std::net::IpAddr> {
    // UDP connect only asks the OS which local interface its default route uses;
    // it sends no packets and does not require an Internet service to answer.
    let socket = std::net::UdpSocket::bind("0.0.0.0:0").ok()?;
    socket.connect("192.0.2.1:9").ok()?;
    Some(socket.local_addr().ok()?.ip())
}
async fn answer(s: &mut TcpStream, code: u16, body: &str, head: bool) -> io::Result<()> {
    let reason = match code { 200 => "OK", 204 => "No Content", 400 => "Bad Request", 403 => "Forbidden", 404 => "Not Found", 405 => "Method Not Allowed", _ => "Unavailable" };
    let h = format!("HTTP/1.1 {code} {reason}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nConnection: close\r\n\r\n", body.len());
    s.write_all(h.as_bytes()).await?;
    if !head { s.write_all(body.as_bytes()).await?; }
    s.shutdown().await
}

async fn connection(mut s: TcpStream, server: Arc<Server>, permit: tokio::sync::OwnedSemaphorePermit) -> io::Result<()> {
    let mut data = Vec::with_capacity(4096);
    let end = tokio::time::timeout(Duration::from_secs(5), async {
        loop {
            if let Some(i) = data.windows(4).position(|w| w == b"\r\n\r\n") { return Ok(i + 4); }
            if data.len() >= 8192 { return Err(io::Error::other("headers too large")); }
            let mut buf = [0; 2048];
            let n = s.read(&mut buf).await?;
            if n == 0 { return Err(io::Error::other("closed")); }
            data.extend_from_slice(&buf[..n]);
        }
    }).await??;
    let mut headers = [httparse::EMPTY_HEADER; 48];
    let mut req = httparse::Request::new(&mut headers);
    if !matches!(req.parse(&data[..end]), Ok(httparse::Status::Complete(_))) {
        return answer(&mut s, 400, "{}", false).await;
    }
    let header = |name: &str| req.headers.iter().find(|h| h.name.eq_ignore_ascii_case(name)).and_then(|h| std::str::from_utf8(h.value).ok());
    let method = req.method.unwrap_or("");
    let target = req.path.unwrap_or("");
    if !target.starts_with('/') || target.starts_with("//") || header("host").is_none() || header("transfer-encoding").is_some()
        || header("content-length").is_some_and(|s| s != "0") {
        return answer(&mut s, 400, "{}", false).await;
    }
    if !matches!(method, "GET" | "HEAD") { return answer(&mut s, 405, "{}", false).await; }
    // A random website must not connect through a visitor's browser. The desktop
    // proxy replaces Origin with the selected server's origin; native tools omit it.
    if let Some(origin) = header("origin") {
        let host = header("host").unwrap();
        if origin != format!("http://{host}") && origin != format!("https://{host}") {
            return answer(&mut s, 403, "{}", false).await;
        }
    }
    let (path, query) = target.split_once('?').unwrap_or((target, ""));
    let param = |key: &str| query.split('&').find_map(|p| {
        let (k, v) = p.split_once('=').unwrap_or((p, "")); (k == key).then_some(v)
    });
    match path {
        "/health" | "/" => answer(&mut s, 200, &json!({"service":"egyuttparkolas-online","protocol":1,"cloudSaves":false}).to_string(), method == "HEAD").await,
        "/players" => {
            let counts = server.lan.breakdown().await;
            let mut body = json!({"players":counts.players,"online":counts.online,"roam":server.roam.in_roam().min(counts.players),
                "full":server.lan.full(),"queue":server.lan.waiting(),"roamBusy":server.roam.crowded()});
            if let Some(room) = param("room").and_then(|v| v.parse::<u32>().ok()) { body["room"] = json!(server.roam.in_room(room)); }
            if let Some(crews) = param("crews") {
                let ids: Vec<u32> = crews.split(',').filter_map(|v| v.parse().ok()).take(4).collect();
                body["crews"] = json!(server.roam.in_crews(&ids));
            }
            answer(&mut s, 200, &body.to_string(), method == "HEAD").await
        }
        "/seen" => answer(&mut s, 204, "", true).await,
        "/lan" if method == "GET" => {
            let key = header("sec-websocket-key").unwrap_or("");
            let valid_key = key.len() == 24 && key.ends_with("==") && key.as_bytes()[..22].iter().all(|b| b.is_ascii_alphanumeric() || *b == b'+' || *b == b'/');
            if !valid_key || header("sec-websocket-version") != Some("13")
                || !header("upgrade").is_some_and(|v| v.eq_ignore_ascii_case("websocket"))
                || !header("connection").is_some_and(|v| v.split(',').any(|v| v.trim().eq_ignore_ascii_case("upgrade"))) {
                return answer(&mut s, 400, "{}", false).await;
            }
            let Ok(protocol) = nfsu2_ws::pick_protocol(header("sec-websocket-protocol")) else { return answer(&mut s, 400, "{}", false).await; };
            let response = nfsu2_ws::handshake_response(key, protocol.as_deref());
            let peer = s.peer_addr()?.ip().to_string();
            let skins = server.skins.clone();
            let opts = AttachOpts {
                resume: param("resume").is_some(), queue: param("queue").is_some(), group: Some(peer),
                on_join: Some(Box::new(|vip, _, count| log::line(&format!("{} connected ({count} players)", nfsu2_util::vip_str(vip))))),
                // This callback owns the connection permit until the switch releases it.
                on_leave: Some(Box::new(move |vip, _, count| { let _ = &permit; skins.lock().unwrap().remove(vip); log::line(&format!("{} disconnected ({count} players)", nfsu2_util::vip_str(vip))); })),
                ..Default::default()
            };
            tokio::time::timeout(Duration::from_secs(5), s.write_all(&response)).await??;
            s.set_nodelay(true)?;
            let (r, w) = s.into_split();
            server.lan.attach(r, w, Bytes::copy_from_slice(&data[end..]), opts);
            Ok(())
        }
        // Cloud saves/name claims are intentionally not offered by this portable host.
        // The game's own Online accounts/friends/race records remain in state/online.
        _ => answer(&mut s, 404, "{}", method == "HEAD").await,
    }
}

#[tokio::main]
async fn main() {
    if let Err(e) = run().await {
        eprintln!("Cannot start server: {e}\nPress Enter to close.");
        let _ = std::io::stdin().read_line(&mut String::new());
        std::process::exit(1);
    }
}
async fn run() -> Result<(), Box<dyn std::error::Error>> {
    let exe = std::env::current_exe()?;
    let root = exe.parent().unwrap();
    let config_path = root.join("server.json");
    let config: Config = if config_path.exists() { serde_json::from_slice(&std::fs::read(&config_path)?)? } else {
        let c = Config::default(); std::fs::write(&config_path, serde_json::to_vec_pretty(&c)?)?; c
    };
    if config.port == 0 || !(2..=14000).contains(&config.max_players) { return Err("Invalid port or max_players in server.json".into()); }
    let state: PathBuf = root.join("state"); std::fs::create_dir_all(&state)?;
    let _ = nfsu2_util::logfile::to_files(&state.join("logs"));
    let listener = TcpListener::bind((config.bind.as_str(), config.port)).await?;
    let online = OnlineHost::spawn(OnlineOptions {
        state_dir: Some(state.join("online")), log: Arc::new(|s, _| log::line(s)), tap: None, claims: None, deny: None,
    });
    let roam = RoamHub::spawn(RoamOptions::default(), Arc::new(|s| log::line(s)));
    let lan = LanSwitch::new(LanOptions { max_peers: config.max_players, max_text: 1_501_000, max_payload: 1_501_000, ..Default::default() }, "",
        Some(online.clone()), Some(roam.clone()), None, Some(state.join("lan-addresses.json")));
    online.attach_switch(lan.switch_send()); roam.attach_switch(lan.switch_send());
    let weak_lan = Arc::downgrade(&lan);
    let hub = roam.clone();
    let skins = Arc::new(Mutex::new(skins::Skins::default()));
    let skin_messages = skins.clone();
    lan.on_text(Box::new(move |vip, _, _, message| {
        if message.get("t").and_then(Value::as_str).is_some_and(|t| t.starts_with("skin-")) {
            let reply = skin_messages.lock().unwrap().message(vip, &message);
            if let (Some(lan), Some(reply)) = (weak_lan.upgrade(), reply) { lan.send_text(vip, reply); }
            return;
        }
        match message.get("t").and_then(|v| v.as_str()) {
            Some("room") => hub.room_name(vip, message.get("name").and_then(|v| v.as_str()).unwrap_or("").chars().take(80).collect()),
            Some("flying") => hub.flew(vip, message.get("s").and_then(|v| v.as_f64()).unwrap_or(0.0)),
            Some("friend") if message.get("op").and_then(|v| v.as_str()) == Some("list") => {
                if let Some(lan) = weak_lan.upgrade() {
                    lan.send_text(vip, Bytes::from_static(b"{\"t\":\"friend\",\"op\":\"list\",\"me\":null,\"friends\":[],\"asks\":[]}"));
                }
            }
            _ => {}
        }
    }));
    let server = Arc::new(Server { lan: lan.clone(), roam: roam.clone(), skins });
    let slots = Arc::new(Semaphore::new(config.max_players + 128));
    log::line(&format!("Egyuttparkolas online server\nListening on {}:{}\nOn this PC: http://127.0.0.1:{}\nOther PCs: http://<this PC's IP>:{}\nAllow TCP port {} through the firewall. Ctrl+C stops the server.\nGame files are not required.", config.bind, config.port, config.port, config.port, config.port));
    if config.bind == "0.0.0.0" {
        if let Some(ip) = lan_address() { log::line(&format!("Local network address: http://{ip}:{}", config.port)); }
    }
    loop {
        tokio::select! {
            _ = tokio::signal::ctrl_c() => break,
            accepted = listener.accept() => {
                let (s, _) = accepted?;
                if let Ok(permit) = slots.clone().try_acquire_owned() {
                    let server = server.clone();
                    tokio::spawn(async move { let _ = connection(s, server, permit).await; });
                }
            }
        }
    }
    lan.stop(); log::line("Server stopped.");
    Ok(())
}

