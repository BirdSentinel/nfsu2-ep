"""Make only the NA popup-headlight housings use fixed dark plastic.

Keeps the round optics, body-colored lids, mesh indices and normals intact.
Uses the existing MX5NA_SKIN4 dark trim atlas and MOLDINGS material; no shared
texture is changed. Input is the separate MX5NA GEOMETRY.BIN, output is staged.
"""
import argparse
from pathlib import Path
import runpy
import struct


def patch(source, destination):
    helpers = runpy.run_path(str(Path(__file__).with_name('vinyl-models.py')))
    align, namehash = helpers['align'], helpers['namehash']
    original = source.read_bytes()
    result = bytearray(original)
    changed = []
    for name, data, leaves, _ in helpers['objects'](source):
        if not name.startswith('MX5NA_KIT00_HEADLIGHT_'):
            continue
        group = 3 if 'LEFT' in name else 4
        vp, _ = leaves[0x134b01]; vp = align(vp, 128)
        ip, _ = leaves[0x134b03]; ip = align(ip, 16)
        mp, me = leaves[0x134b02]; mp = align(mp, 16)
        tp, _ = leaves[0x134012]
        sp, _ = leaves[0x134013]
        assert struct.unpack_from('<I', data, tp + 8)[0] == namehash('MX5NA_SKIN4')
        assert struct.unpack_from('<I', data, sp + 8)[0] == namehash('MOLDINGS')
        q = mp + group * 60
        count, = struct.unpack_from('<I', data, q + 12)
        assert count == 561, 'Unexpected housing mesh'
        assert struct.unpack_from('<2I', data, q + 28) in ((0, 0), (1, 1))
        def vertices(at):
            n, = struct.unpack_from('<I', data, at + 12)
            first, = struct.unpack_from('<I', data, at + 52)
            return set(struct.unpack_from('<' + 'H' * n, data, ip + first * 2))
        selected = vertices(q)
        assert len(selected) == 144
        for at in range(mp, me, 60):
            if at != q:
                assert not selected.intersection(vertices(at)), 'Housing shares vertices with optics or lid'
        # Texture and shader indices, matching the existing fixed trim material.
        struct.pack_into('<2I', result, q + 28, 1, 1)
        # Center of a dark, unmarked region of the existing 512-square atlas.
        for index in selected:
            struct.pack_into('<2f', result, vp + index * 36 + 28, 130.5 / 512, 230.5 / 512)
        changed.append((name, len(selected)))
    assert len(changed) == 2, 'Expected both NA headlights'
    assert len(original) == len(result)
    result = match_lamp_ring(source, result, helpers)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(result)
    return changed


def match_lamp_ring(source, data, h):
    """Give the right circular rim the same fixed material as the left rim."""
    align, chunks = h['align'], h['chunks']
    chunk = lambda tag, body: struct.pack('<II', tag, len(body)) + body
    objects = list(h['objects'](source))
    left = next(o for o in objects if o[0].startswith('MX5NA_KIT00_HEADLIGHT_LEFT'))
    right = next(o for o in objects if o[0].startswith('MX5NA_KIT00_HEADLIGHT_RIGHT'))
    _, _, ll, _ = left
    _, _, l, hp = right
    donor = align(ll[0x134b02][0], 16) + 4 * 60
    ti, si = struct.unpack_from('<2I', data, donor + 28)
    texture = data[ll[0x134012][0]+ti*8:ll[0x134012][0]+ti*8+8]
    shader = data[ll[0x134013][0]+si*8:ll[0x134013][0]+si*8+8]
    tex = bytearray(data[slice(*l[0x134012])])
    shaders = bytearray(data[slice(*l[0x134013])])
    def entry(table, value):
        for i in range(0, len(table), 8):
            if table[i:i+8] == value: return i//8
        index = len(table)//8
        table.extend(value)
        return index
    ti, si = entry(tex, texture), entry(shaders, shader)
    mp, me = l[0x134b02]; mp = align(mp, 16)
    mats = bytearray(data[mp:me])
    assert struct.unpack_from('<I', mats, 60+12)[0] == 144
    struct.pack_into('<2I', mats, 60+28, ti, si)
    info = bytearray(data[hp:l[0x134011][1]])
    info[25], info[26] = len(tex)//8, len(shaders)//8
    prefix = bytearray(chunk(0x134011, info)+chunk(0x134012, tex)+chunk(0x134013, shaders))
    if 0x13401a in l:
        p,e=l[0x13401a];pos=8+len(prefix)+8
        prefix+=chunk(0x13401a,b'\x11'*(align(pos,16)-pos)+data[align(p,16):e])
    mesh = bytearray(chunk(0x134900,data[slice(*l[0x134900])]))
    ms=8+len(prefix)+8
    for tag, alignment in [(0x134b01,128),(0x134b02,16),(0x134b03,16)]:
        p,e=l[tag];payload=mats if tag==0x134b02 else data[align(p,alignment):e]
        pos=ms+len(mesh)+8
        mesh+=chunk(tag,b'\x11'*(align(pos,alignment)-pos)+payload)
    replacement=chunk(0x80134010,prefix+chunk(0x80134100,mesh))
    target=struct.unpack_from('<I',data,hp+16)[0]
    out=bytearray(data[:8]);records=[];index_at=None
    for tag,p,e in chunks(data,8,len(data)):
        if tag==0x80134010:
            if len(out)%128:out+=chunk(0,bytes((-(len(out)+8))%128))
            key=struct.unpack_from('<I',data,p+24)[0]
            solid=replacement if key==target else data[p-8:e]
            records.append((key,len(out),len(solid)));out+=solid
        elif tag!=0 or not records:
            off=len(out);out+=data[p-8:e]
            if tag==0x80134001:
                for t,a,z in chunks(data,p,e):
                    if t==0x134004:index_at=off+a-(p-8)
    bykey={k:(o,s) for k,o,s in records}
    for i in range(len(records)):
        q=index_at+i*24;k=struct.unpack_from('<I',out,q)[0];o,s=bykey[k]
        struct.pack_into('<3I',out,q+4,o,s,s)
    struct.pack_into('<I',out,4,len(out)-8)
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    if args.source.resolve() == args.destination.resolve():
        parser.error('Use a separate output file; keep the source as backup')
    print(patch(args.source, args.destination))
