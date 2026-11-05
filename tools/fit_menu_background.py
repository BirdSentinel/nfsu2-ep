"""Center and enlarge the custom showroom photo plane without stretching its UVs."""
import argparse
import struct
from pathlib import Path
from build_menu_parking import v


def fit(data):
    out=bytearray(data); found=0
    for tag,p,e in v.walk(data):
        if tag!=0x80134010: continue
        leaves={tag:(a,z) for tag,a,z in v.walk(data,p,e) if tag>>28!=8}
        hp=v.align(leaves[0x134011][0],16)
        name=data[hp+164:leaves[0x134011][1]].split(b'\0')[0]
        if name!=b'BACKDROP': continue
        vp,ve=leaves[0x134b01];vp=v.align(vp,128)
        mp,me=leaves[0x134b02];mp=v.align(mp,16)
        points=[struct.unpack_from('<3f',data,q) for q in range(vp,ve,24)]
        # The photograph is the vertical plane, not its embedded floor quad.
        photo=points[:4]
        assert photo,'Not the custom two-plane backdrop'
        lo=min(a[0] for a in photo);hi=max(a[0] for a in photo);top=max(a[2] for a in photo)
        if abs(lo+30)<.001 and abs(hi-30)<.001 and abs(top-20)<.001: return data
        assert abs(lo+22.5)<.001 and abs(hi-16.5)<.001 and abs(top-13)<.001,(lo,hi,top)
        for i,(x,y,z) in enumerate(points):
            if i<4:
                points[i]=((x+3)*60/39,y,z*60/39)
                struct.pack_into('<3f',out,vp+i*24,*points[i])
        minimum=[min(a[k] for a in points) for k in range(3)]
        maximum=[max(a[k] for a in points) for k in range(3)]
        struct.pack_into('<3f',out,hp+32,*minimum);struct.pack_into('<3f',out,hp+48,*maximum)
        for q in range(mp,me,60):
            struct.pack_into('<3f',out,q,*minimum);struct.pack_into('<3f',out,q+16,*maximum)
        found+=1
    assert found==1,found
    return bytes(out)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('source');ap.add_argument('output');args=ap.parse_args()
    original=Path(args.source).read_bytes();result=fit(original)
    assert len(result)==len(original) and fit(result)==result
    Path(args.output).write_bytes(result)
    print('Centered 60 x 20 backdrop; uniform scale, unchanged UVs, textures and turntable')
