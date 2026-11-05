"""Validate independent 240SX lamps, intact stock NA and texture arena safety."""
import math,runpy,struct,sys
from pathlib import Path
sys.path.insert(0,'tools')
from texpacks import jdlz
h=runpy.run_path('tools/vinyl-models.py');a=h['align'];nh=h['namehash'];ch=h['chunks']
source,output=map(Path,sys.argv[1:3])
def solids(path):
 d=path.read_bytes();return {struct.unpack_from('<I',d,s+24)[0]:d[s-8:e] for t,s,e in ch(d,8) if t==0x80134010}
o=solids(source/'GEOMETRY.BIN');n=solids(output/'GEOMETRY.BIN')
expected={nh(f'MX5NA_STYLE{i:02}_HEADLIGHT_{side}_{lod}') for i in range(1,15) for side in ['LEFT','RIGHT'] for lod in 'ABC'}
assert set(n)==set(o)|expected
for k in expected|{nh('MX5NA_KIT00_HEADLIGHT_'+side+'_A') for side in ['LEFT','RIGHT']}:
 b=n[k];l={t:(s,e) for t,s,e in h['walk'](b,8) if t>>28!=8}
 mh=a(l[0x134900][0],16)
 assert struct.unpack_from('<I',b,mh+52)[0]==(l[0x134b01][1]-a(l[0x134b01][0],128))//36
 assert struct.unpack_from('<I',b,mh+16)[0]==(l[0x134b02][1]-a(l[0x134b02][0],16))//60
for k,v in o.items():
 if k in expected:continue
 if k==nh('MX5NA_KIT00_BODY_A'):
  l={t:(s,e) for t,s,e in h['walk'](v,8) if t>>28!=8}
  edited=bytearray(v);struct.pack_into('<I',edited,a(l[0x134b02][0],16)+13*60+12,0)
  assert n[k]==edited # Only the baked front glass draw moves out of BODY.
 elif k in [nh('MX5NA_KIT00_HEADLIGHT_'+side+'_A') for side in ['LEFT','RIGHT']]:
  ll={t:(s,e) for t,s,e in h['walk'](v,8) if t>>28!=8};rr={t:(s,e) for t,s,e in h['walk'](n[k],8) if t>>28!=8}
  for tag,alignment in [(0x134b01,128),(0x134b02,16),(0x134b03,16)]:
   old=v[a(ll[tag][0],alignment):ll[tag][1]]
   assert n[k][a(rr[tag][0],alignment):a(rr[tag][0],alignment)+len(old)]==old
  body=o[nh('MX5NA_KIT00_BODY_A')];bl={t:(s,e) for t,s,e in h['walk'](body,8) if t>>28!=8}
  first=struct.unpack_from('<I',body,a(bl[0x134b02][0],16)+13*60+52)[0]
  oldids=struct.unpack_from('<576H',body,a(bl[0x134b03][0],16)+2*first)
  lens_vertices={body[a(bl[0x134b01][0],128)+36*i:a(bl[0x134b01][0],128)+36*(i+1)] for i in oldids}
  oldsize=ll[0x134b01][1]-a(ll[0x134b01][0],128)
  for q in range(a(rr[0x134b01][0],128)+oldsize,rr[0x134b01][1],36):assert n[k][q:q+36] in lens_vertices
 else:assert n[k]==v,hex(k)
for k in expected:
 b=n[k];l={t:(s,e) for t,s,e in h['walk'](b,8) if t>>28!=8}
 vp=a(l[0x134b01][0],128);ve=l[0x134b01][1];nv=(ve-vp)//36
 for q in range(vp,ve,36):
  x,y,z,nx,ny,nz=struct.unpack_from('<6f',b,q)
  assert all(math.isfinite(v) for v in [x,y,z,nx,ny,nz])
  assert 1.40<x<1.76 and .34<abs(y)<.68 and .30<z<.70,(hex(k),x,y,z)
  assert abs(nx*nx+ny*ny+nz*nz-1)<1e-4
 for q in range(a(l[0x134b02][0],16),l[0x134b02][1],60):
  ct=struct.unpack_from('<I',b,q+12)[0];fi=struct.unpack_from('<I',b,q+52)[0];ip=a(l[0x134b03][0],16)
  assert max(struct.unpack_from('<'+'H'*ct,b,ip+2*fi))<nv

def textures(path):
 d=path.read_bytes();head=next((s,e) for t,s,e in ch(d,8) if t==0xb3310000)
 p,e=next((s,e) for t,s,e in ch(d,*head) if t==0x33310003)
 return {k:jdlz(d[off:off+size]) for k,off,size,_,_,_ in (struct.unpack_from('<6I',d,q) for q in range(p,e,24))}
o=textures(source/'TEXTURES.BIN');n=textures(output/'TEXTURES.BIN')
assert len(n)==len(o)+26
for k,v in o.items():assert n[k][:-156]==v[:-156],hex(k)
spans=[]
for k,v in n.items():
 off,pal,size,ps=struct.unpack_from('<4I',v,len(v)-156+0x30)
 assert pal==off+size;assert size+ps<=len(v)-156
 spans.append((off,off+size+ps))
spans.sort();assert all(b[0]>=aa[1] for aa,b in zip(spans,spans[1:]))
print('PASS: 84 valid meshes; stock geometry/UVs preserved with lenses moved into stock parts; outer body and rear lamps preserved; 26 optical textures added without memory overlaps')
