# Portable Windows app

Copy the entire `Egyuttparkolas` folder to a writable USB drive, then double-click
`Egyuttparkolas.exe`. Press **Play** in the app. No installation, administrator
rights, WSL, Node.js, Rust, browser, or internet connection is required on the
computer where you play. F11 toggles fullscreen. Local single-player and the
in-game Split Screen menu are supported. For multiplayer, enable **Online → Connection →
Play online**, enter your server address, test it, and save. Online play uses one player
per window; turn it off to return to local split screen. The separate Windows server needs
no game files or installation; see `docs/web/ONLINE-SERVER.md` in the source repository
or its packaged `READ-ME.md`.

Requires 64-bit Windows 10/11, a WebGPU-capable GPU and working graphics driver,
and enough RAM for the game (8 GB or more recommended). This cannot promise
compatibility with every Windows computer, old graphics hardware, or machines
whose policy blocks unsigned applications or USB executables.

Keep `game`, `web`, `resources`, all runtime DLLs and other files beside the EXE.
`UserData` is created beside it and holds saves and settings. Copy this
folder too when moving the game. Close the app before copying or ejecting the
drive. Do not delete `UserData` unless you
intend to erase your saves. Existing browser saves can be exported from the
browser version's Saves panel and imported into the app's Saves panel.

Game assets are read from the bundled `game` folder as needed. The desktop app
does not preload or persist another copy of the game assets in browser storage;
only a bounded RAM cache is used during play. The launcher therefore has no
**Other** tab for preload/cache controls. On startup, old game-data, service-worker
and HTTP caches are removed automatically, preserving saves and settings.
A fast USB 3 SSD or copying the folder to the target PC improves loading.
Launching the EXE again opens another independent game window. Player 1 keeps the
original saves; Player 2 and later windows have their own persistent browser profiles
in `UserData/Partitions/client-N`, and connection preferences in `UserData/Clients/N`.
Only the selected server address/mode is copied from Player 1 when a new profile is
created; saves and player identities are separate. Use distinct player names when testing.
All windows read the same `game` folder, without copying its assets.
The local asset servers listen only on 127.0.0.1:18742, 18743, etc. and close with
their windows. Fixed ports per player keep saves available after restarts and drive-letter
changes. Closing one window does not stop the others. Close all windows before moving
the portable folder. The Vinyl Studio shortcut focuses an existing client's editor.

**Playing now** shows live counts from the selected online server, refreshed approximately
every 15 seconds while the launcher is visible. Opening the launcher alone is not counted;
the game must connect to the multiplayer switch. Offline mode shows zero online players.

## Building the portable folder (developer machine only)

Build `out/web/nfsu2.wasm`, `out/web/nfsu2.json` and `web/dist` using the project's
normal build instructions. These may be built in WSL and copied to Windows.
The Windows build machine also needs Python with Pillow to embed `desktop/icon.png`
in the executable. Use `-Python 'C:\path\to\python.exe'` to select that interpreter.
The generated app uses the same PNG for its window icon and keeps the window
title `Együttparkolás` even when the game changes the page title.
Then run from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File desktop/build-portable.ps1 -Data 'C:\Games\Need for Speed Underground 2'
```

The script downloads the pinned Windows x64 Electron runtime, verifies its
published SHA-256, and bundles it with the frontend, compiled module, licenses
and your game data in `out/portable/Egyuttparkolas`. It refuses to overwrite an
existing portable folder to protect saves. Optional `-Module` and `-Frontend`
arguments select other build input directories. Only the build machine needs
internet access. The generated folder includes your copyrighted game data;
keep it for your own use under your game's license, not as a public release.

For PNG vinyl replacements, see `PNG-VINYLS.md` in the portable folder (or
`docs/web/PNG-VINYLS.md` in the source repository).

Run the embedded server tests with `node --test desktop/server.test.cjs desktop/vinyls.test.cjs`.
