# Mazda MX-5 NA (1994)

The supplied `custom/cars/Mazda Miata MX-5 94` mod is a replacement for
`MIATA`. The desktop game instead installs it as `CARS/MX5NA`, car type 46.
The original Miata NB remains type 4 with its original assets and physics.

The two popup-headlight housings use fixed dark trim (`MX5NA_SKIN4`, MOLDINGS)
instead of CARSKIN. `tools/fix_mx5na_lamp_housings.py` changes only these two
housing material bindings and their separate UVs. The right circular lamp rim
also uses the left rim's fixed texture and shader instead of CARSKIN; its UVs
and geometry remain intact. Round optics and paintable lids retain their original
materials, geometry and UVs. The addon builder applies this fix,
and the editor includes the lids while excluding the housings from vinyl paint.

`tools/build_mx5na_luggage_rack.py` replaces the additional geometry in
`MX5NA_STYLE01_BRAKELIGHT_A` (the legacy CRIMSON solid) with a silver trunk luggage
rack: rounded tubular perimeter, five slats, cross supports, four mounting feet
and a low raised stop at the rear (negative X, license-plate side). The slot's stock interior is retained. The rack uses the
dedicated silver texture in the unused `MX5NA_DOOR_HANDLE` preload slot and fixed
trim shading, independently of
body paint. The constant silver DXT1 texture has matching mipmaps; all twelve
original compressed texture blobs are retained byte for byte.
`tools/move_mx5na_rack_to_spoiler.py` converts the rack into the spoiler mount's
local coordinates after the tint consolidation. At database load, `regional.c`
reuses the NA's existing part record/index for Spoilers / EDOLIX, copying only
EDOLIX's category, rating, name and attributes. Its NA owner, geometry and saved
identifier remain intact. The shared normal/carbon EDOLIX entries are filtered
from the NA's spoiler list; other cars keep their originals. The NA's Taillights
category is available again; normal rear-light selections are retained. Older saves with the rack
in the taillight slot migrate it to a stock/empty spoiler slot; an already chosen
non-stock spoiler takes precedence. Install the geometry and runtime together.
`tests/mx5na_rack_slot.c` checks metadata, filtering and old-save migration.

`tools/remove_mx5na_stock_spoiler.py` empties the draw ranges of the separate
`MX5NA_KIT00_SPOILER_A` ducktail. Its part identity remains valid; the complete
trunk surface, stock taillights and the other 25 solids remain byte-identical.
The addon builder includes both changes; no global parts, textures or Miata NB
assets change.

`tools/fix_mx5na_nb_taillights.py` fits the NB's stock and 14 selectable rear lamps (LOD A/B/C)
to the NA's original lens apertures. It disables BODY material 14 and
HEADLIGHT_LEFT materials 5–11, which held the old rear optics, while preserving
the popup headlights, body panels, rack and trunk audio. Positions are scaled
per axis to the original openings and normals use the inverse scale.
All 30 NB OFF and GLASS_OFF textures are imported under MX5NA names, preserving
the standard BRAKELIGHT_LEFT/RIGHT bindings and brake-light shaders. Existing
NA textures and the NB files are untouched. `tools/car-textures` uses the
converter's Binarius codec for both HUFF and JDLZ blobs; imported texture
directory entries retain the required 0x100 flag.
`tools/restore_mx5na_tail_parts.py` appends missing NB choices using
`tools/car-parts`, then transplants only the parts chunk and verifies existing
saved-part indices. CRIMSON uses STYLE15 on the NA, leaving STYLE01 dedicated
to the EDOLIX rack. The Taillights category is enabled and normal selections
are no longer forced back to stock.

`tools/fix_mx5na_trunk_audio.py` imports the NB's eight trunk-audio solids
(stock, standard, tuned and custom, each with its unlit companion), including
all equipment mounts. They are translated by (+0.17, 0, -0.048) metres to match
the NA deck. Existing shared audio materials and the already-present NA layout
part records are retained. The original BODY's shallow fixed boot liner (66
triangles in material 5) is removed because it covers the audio layouts and
speakers. All other BODY data and the other 26 original solids are unchanged.

`tools/fix_mx5na_roof_scoop.py` adds the missing `ROOF_SCOOP` mount to
`MX5NA_BASE_A`, using the original MIATA (NB) marker as the donor. Its height
and pitch are fitted across the scoop's full 44 cm base on the NA hardtop,
18 cm forward of the donor position. A 3 mm overlap closes the mounting seam.
All existing mounts, mesh buffers and other solids are retained.

`tools/fix_mx5na_window_tint.py` consolidates the original driver, seats, other
interior and cabin glass in BASE, with the glass drawn after the opaque cabin.
The addon's original seats were in ROOF/BRAKELIGHT and could draw after the
BODY glass. Their old draw ranges are disabled; CRIMSON uses the same shared
seats. Vertex attributes, textures and shaders are preserved. This patch runs
last in the addon builder. `tests/mx5na_window_tint.py` compares all stock cabin
and body triangles before/after; `tests/scripts/mx5na_window_tint.txt` previews
Light Green through Dark Black from the rear.

`runtime/regional.c` recognizes this specific extra record, extends the retail
car-count operands through the lifter, supplies the donor's sound and performance
rating curves, and adds the new stock car immediately after MIATA. It is initially
unlocked, including when loading older profiles. The retail 48 stock slots and
16000 absent-part sentinel remain unchanged.

Build the asset pack in a separate staging folder with `tools/build_mx5na.py`:

```powershell
python tools/build_mx5na.py --game D:/Games/Egyuttparkolas/game `
  --mod 'D:/Games/Egyuttparkolas/custom/cars/Mazda Miata MX-5 94' `
  --converter out/addcars-source `
  --dotnet out/addcars-source/dotnet/dotnet.exe --output out/mx5na
```

The converter dependency is [nfsu2-addcars](https://github.com/pauliquib/nfsu2-addcars),
with its `u2tool` compiled against the Binarius libraries. The car-count locations
were checked against [NFSU2Unlimiter](https://github.com/nlgxzef/NFSU2Unlimiter).
These tools are used during conversion; the game does not load ASI plugins.

The builder transplants only the car, skin and part chunks. It preserves all
unrelated career/unlock data, the original 46 CarTypeInfo records byte for byte,
and verifies the existing part identifiers at their saved indices. Do not rerun it
against an already extended database. Keep the original game databases in a
backup before installing the staged GLOBALB.LZC, FRONTB.LZC, ENGLISH.BIN and
MX5NA folder, together with a runtime rebuilt using `web/gen.sh` and `web/build.sh`.

Checks: `tests/mx5na_stock.c` verifies older profiles, ordering and idempotence;
`tests/scripts/qr_mx5na.txt` verifies the stock list and drives type 46 in Quick
Race without an unlock cheat.

## Vinyl Studio

`fix_mx5na_decals.py` supplies the missing NB decal meshes for both windows,
both doors, both quarter panels and the hood layouts. It subdivides the donor
patches and projects them onto the actual NA glass/paint triangles, keeping the
slot texture bindings and UVs. A 2 mm normal offset prevents surface overlap.
Existing car solids are retained byte for byte. `tests/mx5na_decals.py` validates
the source/donor/staged geometry triple.

The supplied mod has no vinyl pack. Build an independent donor pack fitted to
the NA's paint UV atlas (Python requires NumPy):

```powershell
python tools/build_mx5na_vinyl.py --game D:/Games/Egyuttparkolas/game `
  --converter out/addcars-source --dotnet out/addcars-source/dotnet/dotnet.exe `
  --output out/mx5na-vinyl
```

Install its `CARS/MX5NA/VINYLS.BIN` in the game's MX5NA folder. Regenerate
`models.js` with `tools/vinyl-models.py` against that game directory and install
it with the current Vinyl Studio sources. The NA is listed immediately after
the NB, using its own geometry and CARSKIN UVs. Export writes
`game/CARS/MX5NA/VINYLS/MX5NA_CONTEST_01.png`; after restarting the game, select
Vinyls > Contest > AinGide on the NA. The NB's pack and artwork are independent.

The NA atlas has different panel placement and orientation from the NB atlas.
`mx5na_vinyl_map.py` recovers their five paint projections and rasterizes the NB
coordinates into the existing NA UV islands, with gutters around panel edges.
`fit-vinyl-atlas` applies that map to all seven indexed mip levels of every
vinyl and mask, retaining palettes, hashes and texture metadata. Every compressed
blob is decoded again and compared before saving. Rebuild from the NB source,
not an already fitted NA pack. The geometry and user-authored NA PNG overrides
are unchanged; the full car conversion should run before this vinyl builder.

Binarius-authored vinyl packs have no 64-byte padding before the palette.
`runtime/web/vinyl_png.c` supports both retail and addon layouts, preserving
texture metadata and bounds. `tests/vinyl_png_layout.c` checks both layouts
against a VPX fixture produced by `desktop/vinyls.cjs`.
`tests/scripts/mx5na_vinyl.txt` opens the separate NA's Contest/AinGide preview;
its session-only unlock flag is set after choosing the NA, so the initial car
selection follows the regular unlocked order. Supply the exported PNG and its
generated VPX pair when checking the replacement log and preview.

The NB taillight importer fits each design and LOD's lateral/vertical contour
to the NA's original lens silhouette using a normalized radial deformation.
Depth follows the original curved lens surface with a 2 mm outward offset;
normals follow the deformation's inverse-transpose Jacobian. This preserves
the donor optics and UVs while seating the outer rim in the NA aperture.
The complete outer body and trunk remain unchanged. It also imports
the retail FE/IG shadow images and rebases every compressed texture's image and
palette offsets into non-overlapping ranges. Those offsets address the shared
decompressed image arena, so retaining donor offsets can overwrite the shadow
with lamp/atlas pixels. Pixel payloads of unrelated NA textures remain unchanged.
`tests/mx5na_nb_taillights.py` checks range separation and payload preservation.

`fix_mx5na_audio_clearance.py` fits the NB trunk-audio shell's rear section
inside the NA boot. The imported painted inner return, rather than the trunk
lid, projected into the rear lamp openings. All four audio layouts and their
unlit meshes use the same fit; mounting positions follow the deformation.
The original outer BODY and TRUNK meshes remain byte-for-byte unchanged.
Apply this once after importing fresh NB audio geometry, as the builder does.
The earlier trunk-lip deletion has been removed and the complete lid restored.

## 240SX aftermarket headlights

`fit_mx5na_240sx_headlights.py` imports all 14 240SX headlight styles as separate
NA parts, with both sides and three LODs (missing donor LODs reuse an available
mesh). Each original donor mesh gets one similarity transform: uniform 0.90
scale, rotation between the donor and NA mounting planes, and translation.
Lens/cover triangles, optical UVs and proportions stay intact; normals receive
only the same rotation. Do not warp the optical meshes to the aperture or
subdivide them: that distorts the lids and reflected highlights.

A separate dark adapter surround connects the donor footprint to the measured
NA aperture. Only this surround follows the curved body edge. It uses the NA
stock housing material and leaves all body triangles intact.
The adapter's inner edge follows the actual donor rim height, rather than
the fitted mounting plane. Both sides select `MX5NA_SKIN4` / `MOLDINGS` by
name and sample the black trim at (130.5, 230.5) in its 512-square atlas;
stock material indices differ by side and must not be used as identifiers.
Painted donor covers sample the NA stock lid's paint region instead of the incompatible
240SX skin atlas. `tests/mx5na_headlight_mount.py` verifies all 84 meshes against
the original donor, including a uniform-scale/orthogonal-transform check for
every vertex, unchanged optical UVs and topology, and rotated normals.
The stock NA optics, black housings and paintable covers keep their geometry
and UVs. BODY material 13's circular lenses move into the stock lamp pair so
they cannot overlap the aftermarket lamps. No outer body triangles are removed.

The 26 donor optical textures use NA-specific names with rebased image offsets.
The part database helper appends the donor choices without moving existing
saved-part indices. The builder runs both imports; the stock NA remains the
default. `tests/mx5na_240sx_headlights.py` verifies model isolation, preservation
of the original stock surfaces and texture-memory separation.

The MX5NA stock front and rear lamps receive level-3 visual reputation, matching
USHAR and BOLT respectively. The lifter changes the level read only inside
CalculatePartVisualRep (0x5142F1), for car type 46 and the two exact stock part
hashes. Database levels remain zero, preserving stock installation, unlocks,
prices, geometry and saved-part indices. Other cars and aftermarket parts use
the original calculation.

### Opening doors

`fix_mx5na_doors.py` separates the NA exterior door skins, handles, quarter
frames and side glass from BODY/BASE into the NB-compatible DOOR_LEFT/RIGHT
A/B/C solids. Exterior vertices and UVs are retained exactly. The cabin sidewall
is clipped at the door silhouette so its upholstery moves with the door;
the floor and surrounding cabin remain fixed. NB inner panels and sills supply
the missing shell, fitted to the NA door envelope with corrected normals.

The renamed NB animations retain their rotation tracks. Regular, scissor and
suicide hinge positions are mapped to the NA envelope; scissor translation
keys receive the same offset as their pivots. Hood and trunk animations remain
unchanged. Existing door-style records and saved part indices are retained.
`tests/mx5na_doors.py` checks exterior conservation, unrelated solids, attachment
markers and LODs. `tests/scripts/mx5na_doors.txt` exercises both door styles and
closure through the game's frontend animation function in a disposable profile.

The beltline seal is connected to the hardtop seal in the source mesh. Its
76 low horizontal triangles per side move with the door; the upper roof seal
stays fixed. NB panel and sill widths are fitted inside the NA upholstery
(abs(y) < 0.68), with inverse-scale normal correction, so their edges do not
pierce the painted skin. The geometry test covers both regression cases.

The NA door skin is now a closed shell: a full-depth backing at abs(y)=0.665 preserves its
exact contour, and walls join all 67 welded boundary edges to that backing.
This adds 499 triangles per side in every door LOD. The original upholstery
is projected onto abs(y)=0.6645, only 0.5 mm in front of the backing, retaining
its XZ coverage and UVs without a floating liner. Its normals face inward.
NB support panels sit behind the backing at abs(y)>=0.666; sills remain fixed.
No exterior vertices move. The regression
test requires exactly two adjacent faces at every welded shell edge, preventing
open rims without widening the panels through the painted surface.


### Engine bay and hood hinge

`fix_mx5na_engine.py` imports the NB stock engine (A/B), both upgraded
engines and their unlit engine-bay shells. Geometry is fitted between the NA
hood's rear edge and front opening, retaining donor topology and UVs and
correcting normals for the fitting transform. The level-3 engine's ten neon
attachment markers receive the same transform and are present on every main
engine variant/LOD, including the frontend's stock-mesh fallback. Texture names match the
existing engine parts' TEXTURE_NAME attributes; all image offsets are rebased.

The six hood animation pivots are fitted to the NA. The regular rear hinge
is at (0.525876, 0, 0.603568), the midpoint of the actual rear hood corners.
Rotation tracks and all door/trunk animation bytes remain unchanged. The
engine importer removes only 156 upper black molding faces from the old sealed
engine-bay insert. All other surfaces are retained, including the fitted doors,
lamps and trunk rack. Engine Neon retains the game's normal upgrade requirement.
`tests/mx5na_engine.py` checks the imported surfaces, neon markers, unrelated
solids and animation isolation.


