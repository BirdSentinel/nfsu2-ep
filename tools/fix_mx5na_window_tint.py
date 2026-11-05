"""Fix NA tint occlusion by drawing its opaque cabin and glass in BASE.

The addon put seats in ROOF/BRAKELIGHT, which can draw after the BODY glass.
Consolidate the existing cabin into BASE: original driver, other opaque interior,
then windshield. Preserve every vertex attribute and the original tint shader.
Stock and CRIMSON share the same seats, so keep one copy visible in BASE.
"""
import argparse
import runpy
import struct
from pathlib import Path


def patch(src, destination):
    h=runpy.run_path(str(Path(__file__).with_name('vinyl-models.py')));align=h['align'];chunks=h['chunks'];nh=h['namehash']
    data=src.read_bytes();edited=bytearray(data)
    chunk=lambda t,b:struct.pack('<II',t,len(b))+b
    for name,b,l,hp in h['objects'](src):
     if name!='MX5NA_KIT00_BODY_A':continue
     mp=align(l[0x134b02][0],16);q=mp+12*60;vp=align(l[0x134b01][0],128);ip=align(l[0x134b03][0],16);ct=struct.unpack_from('<I',b,q+12)[0];fi=struct.unpack_from('<I',b,q+52)[0]
     assert ct==1122, 'Unexpected NA cabin-glass geometry'
     ids=struct.unpack_from('<'+'H'*ct,b,ip+fi*2);used=sorted(set(ids));remap={v:i for i,v in enumerate(used)};gv=b''.join(b[vp+i*36:vp+(i+1)*36] for i in used);gi=[remap[i] for i in ids];gm=bytearray(b[q:q+60]);struct.pack_into('<I',gm,56,0xc180)
     points=[struct.unpack_from('<3f',gv,i*36) for i in range(len(used))]
     for o,f in [(0,min),(16,max)]:struct.pack_into('<3f',gm,o,*(f(p[k] for p in points) for k in range(3)))
     struct.pack_into('<I',edited,q+12,0)
    iv=bytearray();ii=[];im=None;it=None
    for name,b,l,hp in h['objects'](src):
     if name not in ['MX5NA_KIT00_ROOF_A ', 'MX5NA_KIT00_BRAKELIGHT_A', 'MX5NA_STYLE01_BRAKELIGHT_A']:continue
     vp=align(l[0x134b01][0],128);ip=align(l[0x134b03][0],16);q=align(l[0x134b02][0],16)
     ct=struct.unpack_from('<I',b,q+12)[0];fi=struct.unpack_from('<I',b,q+52)[0];ids=struct.unpack_from('<'+'H'*ct,b,ip+fi*2)
     struct.pack_into('<I',edited,q+12,0)
     if name=='MX5NA_STYLE01_BRAKELIGHT_A':continue
     used=sorted(set(ids));remap={v:i for i,v in enumerate(used)};offset=len(iv)//36
     iv+=b''.join(b[vp+i*36:vp+(i+1)*36] for i in used);ii += [offset+remap[i] for i in ids]
     assert it is None or it==b[l[0x134012][0]:l[0x134012][0]+8], 'Interior atlas mismatch'
     im=bytearray(b[q:q+60]);it=b[l[0x134012][0]:l[0x134012][0]+8]
    for name,b,l,hp in h['objects'](src):
     if name!='MX5NA_BASE_A':continue
     assert len(ii)==3189 and len(iv)>0, 'Missing stock interior surfaces'
     vp,ve=l[0x134b01];vp=align(vp,128);ip,ie=l[0x134b03];ip=align(ip,16);mp,me=l[0x134b02];mp=align(mp,16)
     nv=(ve-vp)//36;ix=list(struct.unpack('<'+'H'*((ie-ip)//2),b[ip:ie]));interiorfirst=len(ix);ix += [nv+i for i in ii];first=len(ix);ix += [nv+len(iv)//36+i for i in gi];vs=b[vp:ve]+iv+gv
     mats=bytearray(b[mp:me]);struct.pack_into('<2I',gm,28,1,1);struct.pack_into('<I',gm,52,first);struct.pack_into('<I',im,12,len(ii));struct.pack_into('<2I',im,28,2,0);struct.pack_into('<I',im,52,interiorfirst);mats+=im+gm
     info=bytearray(b[hp:l[0x134011][1]]);info[25]=3;info[26]=2;struct.pack_into('<I',info,20,len(ix)//3);struct.pack_into('<f',info,152,len(ix)/3)
     points=[struct.unpack_from('<3f',vs,i*36) for i in range(len(vs)//36)]
     for o,f in [(32,min),(48,max)]:struct.pack_into('<3f',info,o,*(f(p[k] for p in points) for k in range(3)))
     tex=b[slice(*l[0x134012])]+struct.pack('<2I',nh('WINDOW'),0)+it;sh=b[slice(*l[0x134013])]+struct.pack('<2I',nh('WINDSHIELD'),0)
     prefix=bytearray(chunk(0x134011,info)+chunk(0x134012,tex)+chunk(0x134013,sh))
     p,e=l[0x13401a];markers=b[align(p,16):e];pos=8+len(prefix)+8;prefix+=chunk(0x13401a,b'\x11'*(align(pos,16)-pos)+markers)
     mh=bytearray(b[slice(*l[0x134900])]);struct.pack_into('<I',mh,12,0xc180);struct.pack_into('<I',mh,16,3);struct.pack_into('<I',mh,36,len(ix)//3);struct.pack_into('<I',mh,52,len(vs)//36)
     mesh=bytearray(chunk(0x134900,mh));ms=8+len(prefix)+8
     for tag,payload,alignment in [(0x134b01,vs,128),(0x134b02,mats,16),(0x134b03,struct.pack('<'+'H'*len(ix),*ix),16)]:
      pos=ms+len(mesh)+8;mesh+=chunk(tag,b'\x11'*(align(pos,alignment)-pos)+payload)
     replacement=chunk(0x80134010,prefix+chunk(0x80134100,mesh))
    out=bytearray(data[:8]);records=[];index_at=None;target=nh('MX5NA_BASE_A')
    for tag,p,e in chunks(edited,8,len(edited)):
     if tag==0x80134010:
      if len(out)%128:out+=chunk(0,bytes((-(len(out)+8))%128))
      key=struct.unpack_from('<I',edited,p+24)[0];solid=replacement if key==target else edited[p-8:e];records.append((key,len(out),len(solid)));out+=solid
     elif tag!=0 or not records:
      off=len(out);out+=edited[p-8:e]
      if tag==0x80134001:
       for t,a,z in chunks(edited,p,e):
        if t==0x134004:index_at=off+a-(p-8)
    bykey={k:(o,s) for k,o,s in records}
    for i in range(len(records)):
     q=index_at+i*24;k=struct.unpack_from('<I',out,q)[0];o,s=bykey[k];struct.pack_into('<3I',out,q+4,o,s,s)
    struct.pack_into('<I',out,4,len(out)-8);destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(out)
    print('Moved',len(gi)//3,'glass triangles into BASE; original positions, UVs, normals retained')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    patch(args.source, args.destination)
