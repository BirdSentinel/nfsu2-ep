# Együttparkolás – különálló Windows szerver

## Indítás

1. Másold az `Egyuttparkolas-Server` mappát a Windowsos szervergépre.
2. Indítsd az `Egyuttparkolas-Server.exe` fájlt. A konzolablak maradjon nyitva.
3. Ha a Windows tűzfal engedélyt kér, engedélyezd a kapcsolatokat azon a hálózaton, ahol játszotok.

Nem kell játékot, Node.js-t, Rustot, Dockert vagy WSL-t telepíteni a szervergépre.
A szerver Windows 10/11 x64-en fut. A kliens grafikai követelményei nem vonatkoznak rá.
A szerverhez nem kell a `game`, `web` vagy `UserData` mappa.

## Csatlakozás a játékból

A launcher **Online → Connection** részén:

1. Jelöld be a **Play online (one player per window)** kapcsolót.
2. A **Server address** mezőbe írd be a címet:
   - ugyanazon a gépen: `http://127.0.0.1:8080`;
   - helyi hálózaton: `http://A-SZERVERGÉP-HELYI-IP-CÍME:8080`;
   - interneten: `http://A-SZERVER-NYILVÁNOS-IP-CÍME:8080` vagy a rá mutató domain.
3. **Test connection**, majd **Save & reload launcher**, végül **Play**.

A közös városi autózáshoz az Online fülön kapcsold be a **Free roam with others** opciót is.
Minden játékos ugyanahhoz a szerverhez csatlakozzon; ha szobát adtok meg, az is egyezzen.
Az online mód ablakonként egy játékost használ. Ugyanazon a gépen az `Egyuttparkolas.exe`
ismételt indításával új kliensablak nyílik, külön mentési profillal és játékosazonosítóval.
Az új profil első induláskor átveszi az első kliens szervercímét; a játékosoknak adj eltérő neveket.
A **Playing now** a szerverhez csatlakozott játékokat számolja, a launcherben körülbelül
15 másodpercenként frissül. Önmagában a launcher megnyitása nem növeli a számot.
Az online kapcsoló kikapcsolásával visszatérsz az
offline egyjátékos / helyi osztott képernyős módhoz. Szervert csak a játékból kilépve válts.

A játékfájlokat a kliens továbbra is a saját `game` mappájából olvassa. Az online szerver
csak a többjátékos adatokat közvetíti. A klienseken egyező játékverziót használjatok.
A saját PNG vinyleket ez a kapcsolat nem tölti át automatikusan a többi játékoshoz.

## Elérés más gépekről

A szerver alapértelmezetten a **8080/TCP** porton figyel. Helyi hálózaton a Windows tűzfalnak
kell ezt átengednie. Az IP-címet az `ipconfig` parancs IPv4-cím sorában találod.
Internetes játékhoz otthoni routeren ezt a TCP portot továbbítani kell a szervergép helyi IP-címére.
CGNAT mögött közvetlen bejövő kapcsolat nem lehetséges; publikus IP vagy megfelelő VPN/továbbítás kell.
Ezt a program nem tudja automatikusan megoldani a szolgáltató vagy router helyett.

A közvetlen kapcsolat HTTP/WebSocket, titkosítás nélkül. HTTPS/WSS címet is elfogad a kliens,
ha a szerver elé saját TLS reverse proxyt teszel; a proxy továbbítsa a WebSocket kapcsolatokat is.

## Beállítások, mentés és leállítás

A `server.json` fájlban módosítható a port és a játékoskorlát. Állítsd le a szervert a szerkesztés előtt:

```json
{"bind":"0.0.0.0","port":8080,"max_players":128}
```

A `state` mappát a szerver hozza létre maga mellett. Ebben vannak az online statisztikák,
a játék Online módjának adatai, a címfoglalások és a naplók. Költöztetéskor ezt is másold át.
Leállítás: **Ctrl+C** a szerverablakban; várd meg a „Server stopped.” üzenetet.

Ez a csomag az eredeti virtuális LAN-kapcsolót, free-roam hubot és Online játékszervert használja.
A böngészős kiadás felhőmentési és névfoglalási szolgáltatását nem kínálja; a helyi játékmentések
a kliens `UserData` mappájában maradnak. A launcher felhőfiókhoz kötött barátlistája ezért nem elérhető;
a játék saját Online módjának barátkezelése a szerver része.

## Egyedi online vinylek

A frissített kliens és szerver automatikusan megosztja a játékos autójának kész,
512×512-es karosszéria-textúráját, így a Vinyl Studióból exportált és az autóra
felszerelt egyedi vinyl a többi játékosnál is megjelenik. Külön feltöltés nem kell.
A festés és a többi felszerelt vinylréteg együtt kerül át.

A képek a játékos aktuális kapcsolatához tartoznak, ezért ugyanazon autó ugyanazon
vinylhelyén is lehet két eltérő design. A fogadó kliens nem írja felül a saját
`game` mappáját. A szerver memóriában, legfeljebb 64 MB-ban tartja a képeket,
kilépéskor törli őket; a kliensek csak a megjelenő autók képeit kérik le.
Változás ellenőrzése 10 másodpercenként történik; a közeli autók mintái ezért rövid
késéssel érkezhetnek meg. A funkcióhoz a szervert és minden érintett klienst frissíteni kell.

## Fejlesztői újrafordítás

Csak a fordításhoz kell Rust és a célplatformhoz megfelelő linker:

```text
cd web/server-rs
cargo build -p egyuttparkolas-server --release
```

Windowsos Rust toolchainnel a keletkezett `target/release/egyuttparkolas-server.exe` fájlt
a `desktop/build-server.ps1 -Binary <fájl>` paranccsal lehet becsomagolni. Linuxról
`--target x86_64-pc-windows-gnu` és MinGW linker használható. A kész csomag futtatásához
ezek egyike sem szükséges. A szerver forrása: `web/server-rs/crates/standalone`.

