"""Supply NB decal slots fitted onto the NA's actual exterior surfaces."""
import argparse
import struct
from pathlib import Path
import numpy as np
from fix_mx5na_doors import CH, NH, groups, build
from build_golf_fangs import rebuild

NAMES = ['FRONT_WINDOW_WIDE_MEDIUM', 'REAR_WINDOW_WIDE_MEDIUM',
         'HOOD_RECT_MEDIUM', 'HOOD_RECT_SMALL'] + [
             f'{side}_{part}' for side in ('LEFT', 'RIGHT')
             for part in ('DOOR_RECT_MEDIUM', 'QUARTER_RECT_MEDIUM', 'QUARTER_RECT_SMALL')]


def solids(data):
    return {struct.unpack_from('<I', data, p+24)[0]: data[p-8:e]
            for t, p, e in CH(data, 8) if t == 0x80134010}


def subdivide(tri, depth=2):
    if not depth:
        return [tri]
    def midpoint(a, b):
        v = bytearray(a)
        for off in (0, 4, 8, 12, 16, 20, 28, 32):
            struct.pack_into('<f', v, off, (struct.unpack_from('<f', a, off)[0]+struct.unpack_from('<f', b, off)[0])/2)
        return bytes(v)
    a, b, c = tri
    ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
    return [face for t in ((a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca))
            for face in subdivide(t, depth-1)]


def patch(source, donor, destination):
    data = source.read_bytes()
    target, stock = solids(data), solids(donor.read_bytes())
    for suffix in NAMES:
        side = 1 if suffix.startswith('LEFT') else -1
        if 'WINDOW' in suffix:
            part, shader, axis = 'BASE_A', 'WINDSHIELD', 0
        elif 'DOOR' in suffix:
            part, shader, axis = f'KIT00_DOOR_{"LEFT" if side == 1 else "RIGHT"}_A', 'CARSKIN', 1
        elif 'HOOD' in suffix:
            part, shader, axis = 'KIT00_HOOD_A', 'CARSKIN', 2
        else:
            part, shader, axis = 'KIT00_BODY_A', 'CARSKIN', 1
        surfaces = []
        for _, _, sh, triangles in groups(target[NH('MX5NA_'+part)]):
            if struct.unpack_from('<I', sh)[0] != NH(shader):
                continue
            for tri in triangles:
                v = np.array([struct.unpack('<6fI2f', w) for w in tri])
                center = v[:, :3].mean(0)
                if 'WINDOW' in suffix and (center[0] > 0) != suffix.startswith('FRONT'):
                    continue
                if axis == 1 and center[1]*side < .5:
                    continue
                surfaces.append(v)
        surfaces = np.array(surfaces)
        axes = [i for i in range(3) if i != axis]
        coords = surfaces[:, :, axes]
        a, u, v = coords[:, 0], coords[:, 1]-coords[:, 0], coords[:, 2]-coords[:, 0]
        determinant = u[:, 0]*v[:, 1]-u[:, 1]*v[:, 0]
        usable = abs(determinant) > 1e-10
        fitted = []
        template = stock[NH('MIATA_DECAL_'+suffix+'_A')]
        for mat, tex, sh, triangles in groups(template):
            faces = []
            for tri in triangles:
                for small in subdivide(tri):
                    face = []
                    for raw in small:
                        out = bytearray(raw)
                        p = np.array(struct.unpack_from('<3f', raw))
                        if 'WINDOW' in suffix:
                            p[1] *= .87
                            p[2] -= .085 if suffix.startswith('FRONT') else .105
                        elif axis == 2:
                            p[0] = .525876+(p[0]-.370098)*.92262
                        else:
                            p[0] = p[0]*.85 + .14 if 'DOOR' in suffix else p[0]+.08
                            p[2] -= .055
                        d = p[axes]-a
                        with np.errstate(divide='ignore', invalid='ignore'):
                            s = (d[:, 0]*v[:, 1]-d[:, 1]*v[:, 0])/determinant
                            t = (u[:, 0]*d[:, 1]-u[:, 1]*d[:, 0])/determinant
                        weights = np.c_[1-s-t, s, t]
                        candidates = np.flatnonzero(usable & (weights.min(1) >= -1e-5))
                        if not len(candidates):
                            raise ValueError(f'{suffix}: decal outside target surface at {p}')
                        hits = np.einsum('ij,ijk->ik', weights[candidates], surfaces[candidates, :, :3])
                        outward = side if axis == 1 else (-1 if suffix.startswith('REAR') else 1)
                        ix = candidates[np.argmax(hits[:, axis]*outward)]
                        position = weights[ix] @ surfaces[ix, :, :3]
                        normal = weights[ix] @ surfaces[ix, :, 3:6]
                        normal /= max(np.linalg.norm(normal), 1e-9)
                        position += normal*.002
                        struct.pack_into('<6f', out, 0, *position, *normal)
                        face.append(bytes(out))
                    faces.append(face)
            fitted.append((mat, tex, sh, faces))
        name = 'MX5NA_DECAL_'+suffix+'_A'
        target[NH(name)] = build(template, name, fitted)
        print(name, sum(len(g[3]) for g in fitted), 'triangles')
    destination.write_bytes(rebuild(data, target))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for n in ('source', 'donor', 'destination'):
        p.add_argument(n, type=Path)
    a = p.parse_args()
    patch(a.source, a.donor, a.destination)
