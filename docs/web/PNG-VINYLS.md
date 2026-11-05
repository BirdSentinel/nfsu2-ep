# PNG vinyl replacements (portable Electron app)

For a shared artwork automatically projected onto the available stock cars,
open `VinylStudio/index.html` beside the game. It works offline and exports
per-car PNGs or a ZIP with the correct folder structure. Save a project JSON
before closing the editor to retain your artwork and placement settings.

Close the app, place a PNG in the car's VINYLS folder, then launch the app again.
For the Nissan 240SX, use this path inside your portable folder:

```text
game/CARS/240SX/VINYLS/240SX_CONTEST_01.png
```

Create the VINYLS directory if needed. Keep VINYLS.BIN beside that directory.
In the game choose the 240SX, then Graphics Shop > Vinyls > Contest > AinGide
and Install Vinyl. The existing slot keeps its name and unlock requirements;
the PNG replaces its appearance. Save your customization normally.

Use a transparent 1024 x 1024 PNG (512 x 512 remains supported). Transparent pixels show the car's paint;
partially transparent pixels blend with it. The image follows the car's existing
UV layout, so a logo may need positioning on a car-specific texture template.
Other image sizes are resized to 512 x 512 (and stretched if not square).
The original indexed texture format limits the converted artwork to 256 colors.
Images must be at most 4096 x 4096 and 32 MB.

For another car, change both directory and filename prefix to its internal car
name. Example: `game/CARS/PEUGOT/VINYLS/PEUGOT_CONTEST_01.png` for the Peugeot 206.
Each PNG name must match an existing texture with a matching `_MASK` texture in
that car's archive. The app generates the mask from PNG transparency: do not
supply a separate `_MASK.png`.

Other existing slots can also be replaced, for example `240SX_BODY_07.png` for
Body 7. However, recolorable categories such as Body treat image channels as
color weights and apply the game's chosen vinyl colors. Use CONTEST_01 for
normal full-color artwork; its AinGide slot was verified in the running game.

After editing, replacing, or removing a PNG, fully close and restart the app.
Removing it restores the original texture. There is no need to edit VINYLS.BIN,
convert images manually, install software, or clear the game's cache. Keep the
PNGs with the game when copying the portable folder to a USB drive.

Invalid images or unknown slot names produce a warning and retain the original
vinyl. See `UserData/vinyl-overrides.log` for loading results. This feature is
provided by the portable Electron app; the ordinary browser server does not
prepare PNG replacements.

## Implementation

The optional offline `VinylStudio` editor supports PNG/JPG decal libraries,
placement on the actual 3D body, independent layers per car, and transferring
layouts between cars. Launch `Open-Vinyl-Studio.cmd` to refresh its `decals`
folder. Save `.epvinyl` projects to preserve editable layers and embedded images.
Export is 1024×1024 PNG, individually or in a ZIP with the game's folder structure.
See `VinylStudio/README.md` for controls and UV limitations.

`desktop/vinyls.cjs` validates texture hashes against each original archive,
quantizes the PNG, generates seven (512) or eight (1024) mip levels and its alpha mask, and serves
virtual VPX1 files. Their content hashes invalidate cached data after edits.
`runtime/web/vinyl_png.c` substitutes the indexed image and palette after the
game decompresses a compatible 512-square vinyl. Original archive files,
texture metadata and saved part selection remain intact. For 1024 input, a
second virtual `.vph` keeps the full-resolution indexed image and palette. The
32-bit car-skin compositor evaluates four subpixel phases in its safe retail
buffers and interleaves the results into a 1024 GPU texture with mipmaps.

New clients and the updated standalone server share 1024 skins without resizing.
When connected to an older server, the client sends a 512 compatibility image.
Existing projects can be opened and exported again for a true 1024 render;
resizing an old PNG cannot restore detail absent from its pixels.

Run verification with:

```text
node --test desktop/server.test.cjs desktop/vinyls.test.cjs
```
