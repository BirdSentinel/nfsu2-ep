"""Add the missing NA roof-scoop mount using the stock NB marker as a donor."""
import argparse
import math
from pathlib import Path
import runpy
import struct


def patch(source, donor, destination):
    h = runpy.run_path(str(Path(__file__).with_name('vinyl-models.py')))
    key = h['namehash']('ROOF_SCOOP')
    marker = None
    for name, b, leaves, hp in h['objects'](donor):
        if name != 'MIATA_BASE_A':
            continue
        p, e = leaves[0x13401a]
        for q in range(h['align'](p, 16), e, 80):
            if struct.unpack_from('<I', b, q)[0] == key:
                marker = bytearray(b[q:q + 80])
    assert marker is not None, 'NB roof-scoop marker not found'
    x, y = struct.unpack_from('<2f', marker, 64)
    # Scoop models extend ~44 cm backwards from their FRONT mounting origin.
    # Move towards the windscreen and fit the whole base, not the local tangent
    # at the origin (which can lift the back of long scoops above the roof).
    x += .18
    triangles = []
    for name, b, leaves, hp in h['objects'](source):
        if name != 'MX5NA_KIT00_BODY_A':
            continue
        vp = h['align'](leaves[0x134b01][0], 128)
        ip, ie = leaves[0x134b03]; ip = h['align'](ip, 16)
        for q in range(ip, ie, 6):
            ids = struct.unpack_from('<3H', b, q)
            triangles.append([struct.unpack_from('<3f', b, vp+i*36) for i in ids])

    def roof_height(px):
        heights = []
        for a, c, d in triangles:
            det = (c[0]-a[0])*(d[1]-a[1])-(d[0]-a[0])*(c[1]-a[1])
            if abs(det) < 1e-9:
                continue
            u = ((px-a[0])*(d[1]-a[1])-(d[0]-a[0])*(y-a[1]))/det
            v = ((c[0]-a[0])*(y-a[1])-(px-a[0])*(c[1]-a[1]))/det
            if min(u, v, 1-u-v) >= -1e-5:
                height = a[2]+u*(c[2]-a[2])+v*(d[2]-a[2])
                if height > .9:
                    heights.append(height)
        assert heights, 'No NA roof surface under scoop footprint'
        return max(heights)

    samples = [(dx, roof_height(x+dx)) for dx in (-.44,-.36,-.28,-.20,-.12,-.04,0)]
    mx = sum(p[0] for p in samples)/len(samples)
    mz = sum(p[1] for p in samples)/len(samples)
    slope = sum((px-mx)*(pz-mz) for px,pz in samples)/sum((px-mx)**2 for px,_ in samples)
    # A 3 mm overlap closes the seam without burying the scoop intake.
    z = min(pz-slope*px for px,pz in samples)-.003
    cosine = 1/math.sqrt(1+slope*slope); sine = slope*cosine
    struct.pack_into('<16f', marker, 16, cosine,0,sine,0, 0,1,0,0,
                     -sine,0,cosine,0, x,y,z,1)
    data = source.read_bytes(); result = bytearray(data); found = False
    for name, b, leaves, hp in h['objects'](source):
        if name != 'MX5NA_BASE_A':
            continue
        p, e = leaves[0x13401a]
        for q in range(h['align'](p,16), e, 80):
            if struct.unpack_from('<I',b,q)[0] == key:
                result[q:q+80] = marker
                destination.parent.mkdir(parents=True,exist_ok=True)
                destination.write_bytes(result)
                print(f'Roof scoop mount: ({x:.5f}, {y:.5f}, {z:.5f}), pitch {math.degrees(math.atan(slope)):.2f} deg')
                return
        # 80 marker bytes + a 48-byte padding chunk: downstream vertex-buffer
        # alignment remains unchanged (128-byte boundaries).
        result[e:e] = marker + struct.pack('<II',0,40) + bytes(40)
        struct.pack_into('<I',result,p-4,e-p+80)
        for tag, start, end in h['chunks'](data,8,len(data)):
            if tag == 0x80134010 and start <= hp < end:
                struct.pack_into('<I',result,start-4,end-start+128)
        struct.pack_into('<I',result,4,len(result)-8)
        records = {}
        for tag, start, end in h['chunks'](result,8,len(result)):
            if tag == 0x80134010:
                objkey = struct.unpack_from('<I',result,start+24)[0]
                records[objkey] = (start-8,end-start+8)
        for tag,p0,e0 in h['walk'](result):
            if tag == 0x134004:
                for q in range(p0,e0,24):
                    objkey = struct.unpack_from('<I',result,q)[0]
                    offset,size = records[objkey]
                    struct.pack_into('<III',result,q+4,offset,size,size)
        found = True
        break
    assert found, 'NA base solid not found'
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_bytes(result)
    print(f'Roof scoop mount: ({x:.5f}, {y:.5f}, {z:.5f}), pitch {math.degrees(math.atan(slope)):.2f} deg')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path); p.add_argument('donor',type=Path)
    p.add_argument('destination',type=Path)
    a = p.parse_args(); patch(a.source,a.donor,a.destination)
