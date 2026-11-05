"""Validate a staged decal-only geometry change against its source/donor."""
import sys
import struct
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from fix_mx5na_decals import solids, NAMES, NH, groups

source, donor, staged = [solids(Path(p).read_bytes()) for p in sys.argv[1:4]]
assert all(staged[k] == v for k, v in source.items())
assert set(staged)-set(source) == {NH('MX5NA_DECAL_'+n+'_A') for n in NAMES}
for name in NAMES:
    old = groups(donor[NH('MIATA_DECAL_'+name+'_A')])
    new = groups(staged[NH('MX5NA_DECAL_'+name+'_A')])
    assert len(old) == len(new)
    for a, b in zip(old, new):
        assert a[1:3] == b[1:3], 'Slot texture or shader changed'
        assert len(b[3]) == 16*len(a[3])
        v = np.array([struct.unpack('<6fI2f', raw) for tri in b[3] for raw in tri])
        uv = np.array([struct.unpack_from('<2f', raw, 28) for tri in a[3] for raw in tri])
        assert np.isfinite(v).all()
        assert np.max(abs(np.linalg.norm(v[:, 3:6], axis=1)-1)) < 1e-5
        assert np.allclose(v[:, -2:].min(0), uv.min(0))
        assert np.allclose(v[:, -2:].max(0), uv.max(0))
        if 'DOOR' in name:
            assert v[:, 0].min() > -.45 and v[:, 0].max() < .5
            assert v[:, 2].min() > .1 and v[:, 2].max() < .6
print('PASS original meshes unchanged; 10 decal surfaces, donor slots/UVs and fitted door bounds')
