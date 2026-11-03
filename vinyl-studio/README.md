# Együttparkolás Vinyl Studio 2

Offline, telepítés nélkül használható decal-szerkesztő. Indítsd az
`Open-Vinyl-Studio.cmd` fájlt, vagy nyisd meg az `index.html`-t Chrome/Edge-ben.
A teljes mappát együtt másold: a `models.js` tartalmazza a játékból kiolvasott
29 gyári karosszériát. Internet és szerver nem szükséges.

## Képek és szerkesztés

1. Másold a PNG/JPG/JPEG képeket a `decals` mappába (almappák is lehetnek).
   Az indító újraépíti a képtárat. Már megnyitott oldalon a Mappa betöltése,
   PNG/JPG gomb vagy fájlbehúzás használható. JPG-nél a háttér nem átlátszó.
2. Válassz autót, majd képet. Kattints a modell fényezhető felületére.
   Kijelölés módban a matricát húzással helyezheted át; az Áthelyezés gombbal
   másik felületre kattinthatsz. Jobb gomb vagy Alt+húzás forgatja a nézetet,
   görgővel nagyíthatsz. Az előre beállított nézetek a tetőt is elérhetővé teszik.
3. A jobb oldalon külön szélesség és magasság, forgatás, tükrözés, áttetszőség
   és vetítési mélység állítható. A mélységet csökkentsd, ha a kép nem kívánt
   közeli felületre is átvetül. A méretarányzár kikapcsolásával nyújtható a kép.
4. A réteglistában kijelölhetsz, átnevezhetsz, elrejthetsz, rendezhetsz,
   másolhatsz és törölhetsz. A legfelső réteg látszik legfelül.
   Ctrl+Z / Ctrl+Y: visszavonás / újra. Autóváltáskor a tervek megmaradnak.
5. Az Átadás másik autóra gomb másolatot készít, az eredeti terv megmarad.
   A célmodell arányaihoz igazítja és felületére illeszti a matricákat.
   Ezt követően a cél autón külön finomíthatod őket. A cél meglévő rétegeit
   alapból megtartja; cserélésüket külön jelölőnégyzettel kérheted.

## Mentés és export

A **.epvinyl** projekt minden autó rétegeit és a felhasznált képeket egyetlen
fájlban tárolja, így később teljesen szerkeszthetően visszatölthető. Nincs
automatikus mentés. A korábbi projektformátumok nem támogatottak.

Az export **512×512-es, átlátszó PNG**. Az aktuális autót külön, vagy minden
réteggel rendelkező autót ZIP-ben mentheted. A ZIP kész könyvtárszerkezetet ad:
`game/CARS/<AUTÓ>/VINYLS/<AUTÓ>_CONTEST_01.png`. Az eredeti VINYLS.BIN-hez a
szerkesztő nem nyúl. Másolás előtt mentsd el a meglévő saját PNG-ket.
Játék újraindítása után: Vinyls → Contest → AinGide. Zárolt elemhez a launcher
Game lapján kapcsold be az Unlock everything opciót.

Az előnézet és az export ugyanazt az UV-ra számolt textúrát használja.
A játék 256 színű belső formátumra alakítja a PNG-t, ezért a színek eltérhetnek.
Közösen használt gyári UV-területek, varratok és más body kitek miatt játékbeli
ellenőrzés szükséges. Üveg, kerék és nem fényezhető részek nem kapnak vinyl-t.
Az autók közötti átvitel kiindulópont; eltérő formáknál kézi igazítás kellhet.

## EPVINYL v2 formátum

UTF-8 JSON: `format: "EPVINYL"`, `version: 2`, `resolution: 512`.
Az `assets` lista azonosítót, nevet és beágyazott PNG data URL-t tárol.
A `cars` objektum autókódonként alulról felfelé rendezett réteglistát tartalmaz.
Egy decal az `assetId` mellett 3D pozíciót, normált, érintőirányt, szélességet,
magasságot, forgatást, mélységet, áttetszőséget, tükrözést és láthatóságot ment.
A 3D méretek a modell egységeiben vannak; a felület centimétert mutat.
A `kind: "uv"` réteg a régi projektek teljes raszteres alaptextúrája.
Maximum 128 kép, 24 millió összes képpont, autónként 64 réteg; a betöltött
képek legnagyobb oldala legfeljebb 2048 pixel. A projekt nem függ külső képfájloktól.

## Fejlesztés

`python tools/vinyl-models.py "D:/Games/Egyuttparkolas/game" out/vinyl-studio/models.js`

Másold mellé e forrásmappa futtatáshoz szükséges fájljait és a `decals` mappát.
A modellek saját játékadatok, csak az ignorált `out` könyvtárban maradnak.
Tesztek: `node --test vinyl-studio/core.test.cjs vinyl-studio/decals.test.cjs`.
A megvalósítás külső futásidejű függőség nélkül működik.

## Opposite-side decals

Each 3D decal has two independent settings: **Copy to opposite side** adds a
linked copy across the car's center plane; **Mirror opposite-side texture**
reverses the copied artwork. Leave texture mirroring off for readable lettering.
Both copies share the same layer order, opacity, size and visibility. You can
select and drag either side. These settings are included in PNG/ZIP export,
car-to-car transfer and `.epvinyl` saves (`mirrorSide` and `mirrorTexture`).

Shared UV areas and asymmetric bodywork can still affect the result.

The corrected viewer and decal projection use a consistent coordinate basis.
Projects must include `coordinateSystem: "right-handed-v1"`. Older projects are
not supported or converted. Create a new project and re-export the PNG files.

## Launcher integration and game export

In the portable Electron app, the launcher header opens Vinyl Studio. Use
**Game launcher** in the editor to return in the same window. Closing the editor
always asks for confirmation; confirming destroys it and discards unsaved work. **Current car → Game** and **All edited cars → Game** save 512×512 PNGs
straight into `game/CARS/<CAR>/VINYLS/<CAR>_CONTEST_01.png`. Existing PNGs are
backed up in `UserData/VinylBackups` before replacement. Save `.epvinyl`
separately to keep editable layers. Return to the launcher and restart the game
to load changed vinyls. Browser-only mode still downloads PNG/ZIP files.
