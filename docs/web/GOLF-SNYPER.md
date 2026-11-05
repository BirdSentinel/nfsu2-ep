# GOLF SNYPER fang/tongue bumper

Build with `tools/build_golf_fangs.py CAR_DIR DECODED_TEXTURE_DIR OUTPUT_DIR`.
Decode the retail GOLF textures using the existing car-textures helper first.

Only GOLF_KIT01_FRONT_BUMPER_A/B/C (SNYPER) are replaced. Each retains the
matching stock bumper's surfaces, UVs and materials, with two closed ivory
fangs and a closed curved pink tongue added. The tongue has a rounded tip,
a shallow central groove, and a shaded 64x64 DXT1 atlas with mipmaps. Lower
LODs reduce accessory subdivisions. GOLF_DOOR_HANDLE was absent from both
the original texture pack and geometry; the new atlas uses this preloaded
suffix without changing any existing texture. All original image data is
preserved. The additional atlas occupies space after the retail image arena.
Retail compressed records, their absolute offsets and the data-container
chunks are retained; only the new atlas is added.

The fangs are centred at Y = +/-0.27 m, inset 32 mm and lowered 25 mm from
the first version. The tongue rolls over a 95 mm quarter-circle at the intake edge,
then hangs another 150 mm with a soft outward belly. Cross sections follow
the curve so the rolled root retains its thickness without becoming a wedge.

Retail `CarHeadersMemoryFile.bin` caches geometry offsets and lengths outside
the car's own pack. Reordering solids breaks that cache and causes exit 134
when selecting GOLF. The builder therefore preserves every retail solid slot,
fits the three replacement meshes inside their original allocations, and
retains all trailing animation chunks. It does not change the shared cache.

The STOCK choice, other tuning parts, car-part database and animations remain
unchanged. `tests/golf_fangs.py` verifies solid isolation, stock surface
preservation, manifold accessory meshes, normals, UVs, cached solid locations,
texture record locations, container structure and texture isolation.
