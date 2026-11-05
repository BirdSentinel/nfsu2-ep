import sys,struct,collections,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from build_golf_fangs import *
from texpacks import jdlz
source,rawdir,stage=map(Path,sys.argv[1:4])
def solids(path):
 d=path.read_bytes();return {struct.unpack_from('<I',d,p+24)[0]:d[p-8:e] for t,p,e in CH(d,8) if t==0x80134010}
a,b=solids(source/'GEOMETRY.BIN'),solids(stage/'GEOMETRY.BIN');targets={NH('GOLF_KIT01_FRONT_BUMPER_'+l) for l in 'ABC'}
assert a.keys()==b.keys()
# The retail global header caches these absolute offsets and lengths.
def slots(path):
 d=path.read_bytes();return {struct.unpack_from('<I',d,p+24)[0]:(p-8,e-p+8) for t,p,e in CH(d,8) if t==0x80134010}
assert slots(source/'GEOMETRY.BIN')==slots(stage/'GEOMETRY.BIN'),'Retail cached solid locations invalidated'
assert (source/'GEOMETRY.BIN').stat().st_size==(stage/'GEOMETRY.BIN').stat().st_size
for k in a:
 if k not in targets:assert a[k]==b[k]
for lod in 'ABC':
 old=groups(a[NH('GOLF_KIT00_FRONT_BUMPER_'+lod)]);new=groups(b[NH('GOLF_KIT01_FRONT_BUMPER_'+lod)])
 assert len(new)==len(old)+1
 for g,h in zip(old,new):assert g[1:]==h[1:],'Stock surface/UV/material modified'
 tris=new[-1][3];edges=collections.Counter()
 for tri in tris:
  ps=[tuple(round(v,6) for v in struct.unpack_from('<3f',p)) for p in tri]
  for i in range(3):edges[tuple(sorted((ps[i],ps[(i+1)%3])))]+=1
  for p in tri:
   x,y,z,nx,ny,nz,color,u,v=struct.unpack('<6fI2f',p)
   assert all(math.isfinite(f) for f in (x,y,z,nx,ny,nz,u,v)) and abs(nx*nx+ny*ny+nz*nz-1)<1e-5
   assert 1.97<x<2.24 and abs(y)<.31 and -.07<z<.24 and 0<=u<=1 and 0<=v<=1
 assert set(edges.values())=={2},'Open accessory mesh'
d=(stage/'TEXTURES.BIN').read_bytes();hp,he=next((p,e) for t,p,e in CH(d,8) if t==0xb3310000);p,e=next((p,e) for t,p,e in CH(d,hp,he) if t==0x33310003)
count=0;ranges=[]
original=(source/'TEXTURES.BIN').read_bytes()
oh,oe=next((p,e) for t,p,e in CH(original,8) if t==0xb3310000)
op,oe=next((p,e) for t,p,e in CH(original,oh,oe) if t==0x33310003)
oldslots={s[0]:s for q in range(op,oe,24) for s in [struct.unpack_from('<6I',original,q)]}
# Chunk traversal must never interpret compressed image bytes as chunk headers.
def validate_chunks(data,start,end):
 while start<end:
  assert start+8<=end
  tag,size=struct.unpack_from('<2I',data,start);stop=start+8+size
  assert stop<=end
  if tag&0x80000000:validate_chunks(data,start+8,stop)
  start=stop
validate_chunks(d,0,len(d))
for q in range(p,e,24):
 k,off,size,*_=struct.unpack_from('<6I',d,q)
 f=rawdir/f'{k:08x}.raw'
 if f.exists():
  s=oldslots[k];assert (off,size)==s[1:3] and d[off:off+size]==original[off:off+size]
  r=f.read_bytes();count+=1
 else:
  assert k==NH('GOLF_DOOR_HANDLE');r=jdlz(d[off:off+size])
 ti=len(r)-156;im,pal=struct.unpack_from('<2I',r,ti+0x38);start=struct.unpack_from('<I',r,ti+0x30)[0];ranges.append((start,start+im+pal))
assert count==len(list(rawdir.glob('*.raw')))
ranges.sort();assert all(x[1]<=y[0] for x,y in zip(ranges,ranges[1:]))
print('PASS: only SNYPER A/B/C changed; stock bumper surfaces preserved; closed accessories; original texture pixels retained; no overlapping image ranges.')

