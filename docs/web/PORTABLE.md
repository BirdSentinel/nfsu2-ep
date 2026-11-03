# Portable Windows app

Copy the entire `Egyuttparkolas` folder to a writable USB drive, then double-click
`Egyuttparkolas.exe`. Press **Play** in the app. No installation, administrator
rights, WSL, Node.js, Rust, browser, or internet connection is required on the
computer where you play. F11 toggles fullscreen. Local single-player and the
in-game Split Screen menu are supported; online services are disabled.

Requires 64-bit Windows 10/11, a WebGPU-capable GPU and working graphics driver,
and enough RAM for the game (8 GB or more recommended). This cannot promise
compatibility with every Windows computer, old graphics hardware, or machines
whose policy blocks unsigned applications or USB executables.

Keep `game`, `web`, `resources`, all runtime DLLs and other files beside the EXE.
`UserData` is created beside it and holds saves, settings and caches. Copy this
folder too when moving the game. Close the app before copying or ejecting the
drive; never run two copies simultaneously. Do not delete `UserData` unless you
intend to erase your saves. Existing browser saves can be exported from the
browser version's Saves panel and imported into the app's Saves panel.

Allow extra free space for the game's data cache (potentially another copy of
the game data). A fast USB 3 SSD or copying the folder to the target PC improves
loading. The internal server listens only on 127.0.0.1:18742 and exits with the
app. A fixed port keeps saved data attached to the same origin when drive letters
change. If that port is occupied, close the conflicting app and retry.

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
