# Playing on Windows through WSL

The browser runs on Windows. The existing Linux build and local Rust server run
inside Ubuntu on WSL 2. This is not a standalone Windows executable.

After the first build, double-click `Play-Egyuttparkolas.cmd` at the repository
root. It starts the server if needed and opens Chrome (or the default browser)
at `http://localhost:8080/`. Press **Play** on the page. The server continues
running when the browser closes, so opening the launcher again is quick.

The launcher defaults to:

- Ubuntu, with the build at `/root/nfsu2-ep`.
- Game files at `C:\Games\Need for Speed Underground 2`.
- Port 8080, accessible locally.
- Server logs in `out/windows/server.log` and `server-error.log` in this checkout.

To override these settings, run PowerShell from the repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\web\start-windows.ps1 -Data 'D:\Games\Need for Speed Underground 2' -Port 8081
```

The launcher requires a completed build; it does not install dependencies or
compile the game. The Linux build needs Python 3 with the repository's
`requirements.txt`, Node.js 20+, Rust, a C compiler, and wasi-sdk 34 in `deps/`.
The original `SPEED2.EXE` must match the hash documented in the main README.

The initial build commands, inside the Linux source copy, are:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
web/gen.sh '/mnt/c/Games/Need for Speed Underground 2/SPEED2.EXE'
J=4 web/build.sh
(cd web && npm ci --no-audit --no-fund && npm run build)
web/server-rs/build.sh
```

Keep the Linux source copy synchronized when changing the Windows checkout,
then rerun the relevant build commands. Generated game code and build output
stay in the Linux copy. Neither the launcher nor the build modifies the original
game files.
