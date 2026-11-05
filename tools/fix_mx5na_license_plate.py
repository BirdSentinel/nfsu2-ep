"""Fit the retail rear plate into the NA recess, retaining its stock UVs."""
import argparse
import struct
from pathlib import Path
from fix_mx5na_doors import CH, NH, A, groups, build, leaves, chunk
from build_golf_fangs import rebuild


def geometry(source, plates, destination):
    data = source.read_bytes()
    donor = plates.read_bytes()
    solids = {struct.unpack_from('<I', data, p + 24)[0]: data[p-8:e]
              for t, p, e in CH(data, 8) if t == 0x80134010}
    plate = next(donor[p-8:e] for t, p, e in CH(donor, 8)
                 if t == 0x80134010)
    fitted = []
    for mat, tex, shader, tris in groups(plate):
        faces = []
        for tri in tris:
            face = []
            for raw in tri:
                v = bytearray(raw)
                x, y, z = struct.unpack_from('<3f', v)
                # The NA recess is above the bumper, between the tail lamps.
                # Rigid translation preserves the original 2:1 plate and UVs.
                struct.pack_into('<3f', v, 0, x - 1.851, y - .00131, z + .511)
                face.append(bytes(v))
            faces.append(face)
        fitted.append((mat, tex, shader, faces))
    changed = 0
    for lod in 'ABC':
        name = 'MX5NA_KIT00_BODY_' + lod
        key = NH(name)
        if key not in solids:
            continue
        original = solids[key]
        gs = [g for g in groups(original)
              if struct.unpack_from('<I', g[1])[0] != NH('LICENSE_PLATE')]
        solid = bytearray(build(original, name, gs + fitted))
        ll = leaves(original)
        if 0x13401a in ll:
            p, e = ll[0x13401a]
            pos = len(solid) + 8
            solid += chunk(0x13401a, b'\x11' * (A(pos, 16)-pos) + original[A(p, 16):e])
            struct.pack_into('<I', solid, 4, len(solid)-8)
        solids[key] = solid
        changed += 1
    assert changed, 'No MX5NA body found'
    destination.write_bytes(rebuild(data, solids))
    print(f'Fitted retail license plate to {changed} MX5NA body LODs')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'plates', 'destination'):
        p.add_argument(name, type=Path)
    a = p.parse_args()
    geometry(a.source, a.plates, a.destination)
