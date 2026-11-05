"""Rasterize NB vinyl coordinates into the existing NA paint atlas.

No model vertices/UVs or user-authored NA PNG overrides are changed.
"""
import argparse
import struct
from pathlib import Path
import numpy as np
from fix_mx5na_doors import CH, NH, groups


def paint_triangles(path):
    data = path.read_bytes()
    for tag, p, e in CH(data, 8):
        if tag != 0x80134010:
            continue
        name = data[p+172:e].split(b'\0')[0].decode('ascii')
        if '_KIT00_' not in name or not name.endswith('_A'):
            continue
        for _, _, shader, triangles in groups(data[p-8:e]):
            if struct.unpack_from('<I', shader)[0] != NH('CARSKIN'):
                continue
            for tri in triangles:
                yield np.array([struct.unpack('<6fI2f', v) for v in tri])


def projections(triangles):
    """Recover the five planar atlas charts; reject trim/underside islands."""
    buckets = [[] for _ in range(5)]  # top, left, right, front, rear
    for tri in triangles:
        n = tri[:, 3:6].mean(0)
        axis = np.argmax(abs(n))
        if axis == 2 and n[2] < 0:
            continue
        chart = 0 if axis == 2 else (1 if n[1] > 0 else 2) if axis == 1 else (3 if n[0] > 0 else 4)
        buckets[chart].extend(tri)
    result = []
    for bucket in buckets:
        v = np.array(bucket)
        x, y = np.c_[v[:, :3], np.ones(len(v))], v[:, -2:]
        rng, best = np.random.default_rng(9), []
        for _ in range(1000):
            ids = rng.choice(len(v), 4, replace=False)
            c = np.linalg.lstsq(x[ids], y[ids], rcond=None)[0]
            inside = np.flatnonzero(np.max(abs(x @ c-y), axis=1) < .006)
            if len(inside) > len(best):
                best = inside
        assert len(best) > len(v) * .45, 'Unrecognized paint atlas'
        result.append(np.linalg.lstsq(x[best], y[best], rcond=None)[0])
    return result


def make_map(na, nb):
    target = list(paint_triangles(na))
    original = projections(target)
    donor = projections(list(paint_triangles(nb)))
    uvmap = np.full((512, 512, 2), np.nan, dtype=np.float32)
    quality = np.full((512, 512), np.inf)
    for tri in target:
        xyz = np.c_[tri[:, :3], np.ones(3)]
        uv = tri[:, -2:]
        errors = [np.max(abs(xyz @ c-uv)) for c in original]
        chart = int(np.argmin(errors))
        if errors[chart] > .025:
            continue  # unpainted trim swatches and donor interior returns
        # NB and NA are equally wide. Align their longitudinal origin and
        # beltline/hood height, retaining physical motif size across panels.
        xyz[:, 0] -= .14
        xyz[:, 2] += .055
        source_uv = xyz @ donor[chart]
        px = uv * 512 - .5
        lo = np.maximum(0, np.floor(px.min(0)).astype(int))
        hi = np.minimum(511, np.ceil(px.max(0)).astype(int))
        if np.any(hi < lo):
            continue
        matrix = np.c_[px, np.ones(3)].T
        if abs(np.linalg.det(matrix)) < 1e-7:
            continue
        yy, xx = np.mgrid[lo[1]:hi[1]+1, lo[0]:hi[0]+1]
        weights = np.linalg.solve(matrix, np.array([xx.ravel(), yy.ravel(), np.ones(xx.size)]))
        inside = (weights.min(0) >= -1e-5)
        x, y = xx.ravel()[inside], yy.ravel()[inside]
        better = errors[chart] < quality[y, x]
        x, y = x[better], y[better]
        uvmap[y, x] = (weights[:, inside][:, better].T @ source_uv)
        quality[y, x] = errors[chart]
    valid = np.isfinite(uvmap[:, :, 0])
    for _ in range(4):
        previous = uvmap.copy()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            shifted = np.roll(previous, (dy, dx), axis=(0, 1))
            if dy == 1: shifted[0] = np.nan
            if dy == -1: shifted[-1] = np.nan
            if dx == 1: shifted[:, 0] = np.nan
            if dx == -1: shifted[:, -1] = np.nan
            gutter = ~np.isfinite(uvmap[:, :, 0]) & np.isfinite(shifted[:, :, 0])
            uvmap[gutter] = shifted[gutter]
    assert valid.sum() > 60000, f'Incomplete NA atlas coverage: {valid.sum()}'
    print(f'Mapped {valid.sum()} paint pixels')
    return uvmap


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for n in ('na', 'nb', 'output'):
        p.add_argument(n, type=Path)
    a = p.parse_args()
    make_map(a.na, a.nb).astype('<f4').tofile(a.output)

