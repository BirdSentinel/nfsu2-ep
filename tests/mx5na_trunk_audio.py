"""Verify imported NB layouts, equipment mounts and untouched NA geometry."""
import runpy, struct, sys
from pathlib import Path

h = runpy.run_path('tools/vinyl-models.py')
align = h['align']
def solids(path):
    data = Path(path).read_bytes()
    return {struct.unpack_from('<I', data, p+24)[0]: data[p-8:e]
            for t,p,e in h['chunks'](data,8) if t == 0x80134010}

old, donor, new = map(solids, sys.argv[1:4])
assert len(new) == len(old) + 8
for key, blob in old.items():
    if key != h['namehash']('MX5NA_KIT00_BODY_A'):
        assert new[key] == blob, hex(key)
        continue
    expected=bytearray(blob)
    leaves={t:(p,e) for t,p,e in h['walk'](blob,8) if t>>28!=8}
    vp=align(leaves[0x134b01][0],128);ip=align(leaves[0x134b03][0],16)
    mp=align(leaves[0x134b02][0],16)+5*60
    count=struct.unpack_from('<I',blob,mp+12)[0];first=struct.unpack_from('<I',blob,mp+52)[0]
    kept=[];removed=0
    for j in range(0,count,3):
        ids=struct.unpack_from('<3H',blob,ip+(first+j)*2)
        points=[struct.unpack_from('<3f',blob,vp+i*36) for i in ids]
        if all(x < -1.2 and abs(y)<.56 and z>.515 for x,y,z in points):removed+=1
        else:kept.extend(ids)
    assert removed==66
    struct.pack_into('<I',expected,mp+12,len(kept))
    struct.pack_into('<'+'H'*len(kept),expected,ip+first*2,*kept)
    assert new[key]==expected, 'Changes outside the boot liner'
for i in range(4):
    for suffix in ['', '_UNLIT']:
        nb = donor[h['namehash'](f'MIATA_KIT{i:02}_TRUNK_AUDIO{suffix}_A')]
        na = new[h['namehash'](f'MX5NA_KIT{i:02}_TRUNK_AUDIO{suffix}_A')]
        leaves = {t:(p,e) for t,p,e in h['walk'](nb,8) if t>>28 != 8}
        for tag in [0x134012, 0x134013, 0x134b03]:
            p,e = leaves[tag]
            assert nb[p:e] == na[p:e]
        p,e = leaves[0x134b01]
        for q in range(align(p,128),e,36):
            v = struct.unpack_from('<3f',nb,q)
            w = struct.unpack_from('<3f',na,q)
            assert all(abs(b-a-s)<1e-6 for a,b,s in zip(v,w,(.17,0,-.048)))
            assert nb[q+12:q+36] == na[q+12:q+36]
        if 0x13401a in leaves:
            p,e = leaves[0x13401a]
            for q in range(align(p,16),e,80):
                assert nb[q:q+64] == na[q:q+64]
                v = struct.unpack_from('<3f',nb,q+64)
                w = struct.unpack_from('<3f',na,q+64)
                assert all(abs(b-a-s)<1e-6 for a,b,s in zip(v,w,(.17,0,-.048)))
print('PASS: 8 layouts, materials, mounts; only 66 liner triangles removed from original NA')
