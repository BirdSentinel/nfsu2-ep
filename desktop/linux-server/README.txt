Együttparkolás – Linux Docker szerver (x86-64)

Ubuntu Server 24.04 LTS, előtelepített Docker Engine + Compose plugin.
A szerver már le van fordítva. A VPS-en nem kell Rust, játékfájl vagy fordítás.
A Docker-image létrehozása csak a mellékelt programot másolja be, nincs letöltés.

INDÍTÁS
1. Töltsd fel az Egyuttparkolas-Server-Linux.tar.gz fájlt a VPS-re (pl. WinSCP).
2. SSH terminálban:
   tar -xzf Egyuttparkolas-Server-Linux.tar.gz
   cd Egyuttparkolas-Server-Linux
   sudo bash start.sh
3. A szolgáltató tűzfalában engedélyezd a bejövő TCP 8080 portot.
4. A Windows kliens launcherében: Online → Connection → Server address:
   http://A-VPS-NYILVANOS-IP-CIME:8080
   Test connection, majd Save & reload launcher. Play online legyen bekapcsolva;
   a közös városi autózás automatikus. Mindenki ugyanazt a szervercímet használja.
   A játékban lépjetek be a karrier free roamba; nincs külön szoba vagy crew.

A terminált bezárhatod: a szerver háttérben fut. A VPS újraindítása után a
Docker szolgáltatás indulásával automatikusan visszaindul, hacsak kézzel nem
állítottad le. Docker Engine legyen automatikus indulásra engedélyezve.

KEZELÉS (a csomag könyvtárában)
Állapot:       sudo docker compose ps
Napló:         sudo docker compose logs -f --tail=100
Leállítás:     sudo docker compose stop
Újraindítás:   sudo docker compose restart
Ismét indítás: sudo docker compose up -d
Ellenőrzés:    http://A-VPS-NYILVANOS-IP-CIME:8080/health

ADATOK ÉS BEÁLLÍTÁSOK
Az első indítás létrehozza a data/server.json fájlt és a data/state mappát.
A data mappa megmarad konténercsere, leállítás és frissítés után is.
Biztonsági mentéshez állítsd le a szervert, és mentsd az egész data mappát.
A mappa UID 10001 tulajdonban van; a fájlkezeléshez szükség lehet sudo-ra.
Frissítéskor a csomagot a meglévő könyvtárba bontsd ki, és ismét start.sh.
A start.sh nem írja felül a meglévő konfigurációt vagy mentéseket.

Alapból 49 játékos van engedélyezve, egy közös sessionben. Ez a játék technikai
korlátja, nem a VPS mért kapacitása. A frissített kliens szükséges mindenkinél.
Régebbi telepítésnél a data/server.json megmarad: a max_players értékét állítsd
49-re, ha ott még 16 szerepel, majd indítsd újra a szervert.
A data/server.json max_players értéke módosítható leállítás után.
A bind maradjon 0.0.0.0, a belső port 8080. Más nyilvános porthoz írj a
compose.yaml mellé egy .env fájlt, például EP_PORT=9090 tartalommal, majd start.sh.
Ilyenkor a launcher címében és a szolgáltató tűzfalában is a 9090-et használd.
A start.sh végén megjelenő cím példájában az alapértelmezett 8080 szerepel.

A konténer legfeljebb 512 MB RAM-ot és 1 CPU-t használhat. A készülék tényleges
játékoskapacitása a VPS CPU-teljesítményétől és a forgalomtól függ.
Az egyedi vinylek továbbítása működik, frissített Windows kliensekkel.
A szerver a játékfájlokat nem tárolja; a játék mindenkinél helyben fut.
A közvetlen kapcsolat HTTP/WebSocket. HTTPS-hez külön, WebSocketet továbbító
TLS proxy használható. Domain nem szükséges a közvetlen IP-s kapcsolathoz.

ÚJRAFORDÍTÁS (fejlesztői gépen, nem az 1 GB-os VPS-en)
A projekt gyökerében, Linux Rust toolchainnel:
  rustup target add x86_64-unknown-linux-musl
  bash desktop/build-linux-server.sh
A csomag az out/portable mappába kerül.
