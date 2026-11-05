"""Compare the original and staged local MX5NA geometry (no game assets included)."""
from collections import Counter
from pathlib import Path
import runpy
import struct
import sys

h = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'tools/vinyl-models.py'))
selected = {'MX5NA_BASE_A', 'MX5NA_KIT00_BODY_A', 'MX5NA_KIT00_ROOF_A',
            'MX5NA_KIT00_BRAKELIGHT_A'}


def surfaces(path):
    faces = Counter()
    for name, data, leaves, hp in h['objects'](path):
        if name.strip() not in selected:
            continue
        vp = h['align'](leaves[0x134b01][0], 128)
        ip = h['align'](leaves[0x134b03][0], 16)
        mp, me = leaves[0x134b02]
        tp, te = leaves[0x134012]; sp, se = leaves[0x134013]
        textures = [struct.unpack_from('<I', data, q)[0] for q in range(tp, te, 8)]
        shaders = [struct.unpack_from('<I', data, q)[0] for q in range(sp, se, 8)]
        for q in range(h['align'](mp, 16), me, 60):
            count = struct.unpack_from('<I', data, q+12)[0]
            texture, shader = struct.unpack_from('<2I', data, q+28)
            first = struct.unpack_from('<I', data, q+52)[0]
            for j in range(0, count, 3):
                ids = struct.unpack_from('<3H', data, ip+(first+j)*2)
                vertices = b''.join(data[vp+i*36:vp+(i+1)*36] for i in ids)
                faces[(textures[texture], shaders[shader], vertices)] += 1
    return faces


original, patched = map(Path, sys.argv[1:])
assert surfaces(original) == surfaces(patched), 'Visible geometry/material changed'
for name, data, leaves, hp in h['objects'](patched):
    if name != 'MX5NA_BASE_A':
        continue
    mp, me = leaves[0x134b02]
    assert (me-h['align'](mp, 16))//60 == 3
    q = me-60
    assert struct.unpack_from('<I', data, q+12)[0] == 1122
    assert struct.unpack_from('<I', data, q+32)[0] == 1
print('PASS: all stock cabin/body triangles, UVs, normals, colors, shaders and textures preserved; glass draws last in BASE')
