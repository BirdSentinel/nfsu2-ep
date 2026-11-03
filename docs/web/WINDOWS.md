# Playing on Windows through WSL

For the standalone Electron app with no WSL or browser installation on the
target PC, use the [portable Windows build](PORTABLE.md).

The browser runs on Windows. The existing Linux build and local Rust server run
inside Ubuntu on WSL 2. This is not a standalone Windows executable.

For the legacy WSL/browser workflow, run `web/start-windows.ps1` from PowerShell.
It starts the server if needed and opens Chrome (or the default browser)
at `http://localhost:8080/?localPlayers=2`. Press **Play** on the page. The server continues
running when the browser closes, so opening the launcher again is quick.

The launcher defaults to:

- Ubuntu, with the build at `/root/nfsu2-ep`.
- Game files at `C:\Games\Need for Speed Underground 2`.
- Port 8080, accessible locally.
- Local play, with the player count chosen inside the game's Split Screen menu.
- Server logs in `out/windows/server.log` and `server-error.log` in this checkout.

To override these settings, run PowerShell from the repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\web\start-windows.ps1 -Data 'D:\Games\Need for Speed Underground 2' -Port 8081
```

## Local split-screen

Choose **Split Screen** in the main menu, then **2 Players**, **3 Players**, or
**4 Players** in the icon carousel. Left/right changes the choice, A/Cross confirms,
and B/Circle returns to the main menu. Next choose the game mode, track and race options. Each player
then presses and releases **Start** on their controller at their prompt, chooses
their own car and transmission, and confirms. The race starts after the final
player confirms. **Quick Race** remains the ordinary single-player flow.

One player can use the keyboard: press **Enter** at that player's Start prompt,
then use arrows and Enter to choose the car and transmission. The other players
join with their controllers. Drive with **WASD** or the **arrow keys**; **Space**
is the handbrake, **Shift** is nitrous, **C** changes camera, **B** looks back,
and **Q/E** shift down/up with manual transmission. **Esc** pauses.

Connect standard browser-compatible controllers. Their first Start presses assign
seats in player order; a controller used earlier to navigate the menus keeps its
seat. During car selection, only the current player's controller drives the menu.
Each player has independent driving input, camera and race position. Outrun is a
two-player mode; Circuit and Drag support two, three and four players.

Use the left stick to steer, RT to accelerate, and LT to brake. Start pauses;
A/Cross confirms menu choices. Reconnecting a controller restores its seat;
press Start on a replacement controller to take the first disconnected seat,
then release the button before driving.

The launcher opens local play with separate online/free-roam networking disabled.
Select the actual player count in the game, not through launcher arguments.
Each viewport has its own minimap in its lower-left corner, centered and rotated
around that player's car. All local racers appear with consistent colors:
P1 green, P2 red, P3 blue and P4 yellow (extra seats use purple and cyan).
Distant local racers stay on the map's edge. Per-controller vibration is not
implemented.

Split-screen rendering keeps headlight shader data per draw, re-aims the headlight
projector for each car, and uses separate speed-blur state and scene copies.
Player cells also clip effect draws and the downsampled nitrous-brightness passes.
Rain, glare creation and the effect-update loop follow each player's camera;
additional players have separate lighting-tint cache state.

The shared-engine port is derived from the MIT-licensed source in
`NFSU2-SplitScreen-main`, with attribution in `licenses/NFSU2-SplitScreen.txt`.
It runs the original game logic once, with a separate viewport for each player.

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
