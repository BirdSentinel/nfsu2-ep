"""Put the NA rack in spoiler-marker coordinates, for its EDOLIX slot.
Run after building the rack and tint fix. No shared spoiler pack is changed.
"""
from pathlib import Path
import argparse, runpy, struct

def patch(source, destination):
    h=runpy.run_path(str(Path(__file__).with_name('vinyl-models.py')));a=h['align'];nh=h['namehash']
    d=source.read_bytes();out=bytearray(d);objects=list(h['objects'](source))
    base=next(o for o in objects if o[0]=='MX5NA_BASE_A');_,b,l,_=base;p,e=l[0x13401a]
    marker=next(q for q in range(a(p,16),e,80) if struct.unpack_from('<I',b,q)[0]==nh('SPOILER'))
    matrix=struct.unpack_from('<16f',b,marker+16)
    assert matrix[:12]==(1,0,0,0,0,1,0,0,0,0,1,0), 'Unexpected rotated spoiler marker'
    shift=matrix[12:15]
    _,b,l,hp=next(o for o in objects if o[0]=='MX5NA_STYLE01_BRAKELIGHT_A')
    vp,ve=l[0x134b01];vp=a(vp,128);mp,me=l[0x134b02];mp=a(mp,16);ip,_=l[0x134b03];ip=a(ip,16)
    assert struct.unpack_from('<I',b,mp+12)[0]==0,'Run tint consolidation before moving rack'
    q=mp+60;n=struct.unpack_from('<I',b,q+12)[0];first=struct.unpack_from('<I',b,q+52)[0]
    ids=set(struct.unpack_from('<'+'H'*n,b,ip+first*2));assert n==3720
    points=[]
    for i in ids:
        p=vp+i*36;xyz=struct.unpack_from('<3f',b,p)
        assert xyz[0]<-1, 'Rack is already in spoiler coordinates'
        xyz=tuple(v-s for v,s in zip(xyz,shift));points.append(xyz);struct.pack_into('<3f',out,p,*xyz)
    for offset,fn in [(0,min),(16,max)]:
        bounds=tuple(fn(p[k] for p in points) for k in range(3))
        struct.pack_into('<3f',out,q+offset,*bounds)
        struct.pack_into('<3f',out,hp+32+offset,*bounds)
    destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(out)
    print('Rack moved to spoiler marker coordinates:',shift)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('destination',type=Path);v=p.parse_args();patch(v.source,v.destination)
