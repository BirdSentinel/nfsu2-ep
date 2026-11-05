"""Validate NB tail replacement isolation, fitted bounds and lossless textures."""
import runpy,struct,sys
from pathlib import Path
h=runpy.run_path('tools/vinyl-models.py');a=h['align'];nh=h['namehash'];ch=h['chunks']
def solids(p):
 d=Path(p).read_bytes()
 return {struct.unpack_from('<I',d,s+24)[0]:d[s-8:e] for t,s,e in ch(d,8) if t==0x80134010}
old=solids(sys.argv[1]+'/GEOMETRY.BIN');new=solids(sys.argv[2]+'/GEOMETRY.BIN')
prefixes=[('KIT00','KIT00')]+[(f'STYLE{i:02}',f'STYLE{15 if i==1 else i:02}') for i in range(1,15)]
expected_keys={nh(f'MX5NA_{n}_BRAKELIGHT_{lod}') for _,n in prefixes for lod in 'ABC'}
assert new.keys()==old.keys()|expected_keys
for k,b in old.items():
 if k in expected_keys:continue
 expected=bytearray(b);groups=([14] if k==nh('MX5NA_KIT00_BODY_A') else list(range(5,12)) if k==nh('MX5NA_KIT00_HEADLIGHT_LEFT_A') else [])
 if groups:
  l={t:(s,e) for t,s,e in h['walk'](b,8) if t>>28!=8}
  for m in groups:struct.pack_into('<I',expected,a(l[0x134b02][0],16)+60*m+12,0)
 assert new[k]==expected,hex(k)
for lod in 'ABC':
 b=new[nh('MX5NA_KIT00_BRAKELIGHT_'+lod)];l={t:(s,e) for t,s,e in h['walk'](b,8) if t>>28!=8};p,e=l[0x134b01]
 pts=[struct.unpack_from('<3f',b,q) for q in range(a(p,128),e,36)]
 assert all(-1.91<x<-1.62 and .33<abs(y)<.69 and .38<z<.56 for x,y,z in pts)

# Every design/LOD must remain inside the actual NA lens silhouette, not
# merely its rectangular bounds. The entire outer body/trunk is checked above.
fit=runpy.run_path('tools/fix_mx5na_nb_taillights.py')
b=new[nh('MX5NA_KIT00_BODY_A')]
l={t:(s,e) for t,s,e in h['walk'](b,8) if t>>28!=8}
vp=a(l[0x134b01][0],128);ip=a(l[0x134b03][0],16)
first=struct.unpack_from('<I',b,a(l[0x134b02][0],16)+14*60+52)[0]
ids=struct.unpack_from('<756H',b,ip+2*first)
points=[struct.unpack_from('<3f',b,vp+36*i) for i in ids]
center,radius,hull=fit['contour']([(p[1],p[2]) for p in points if p[1]>0])
import math
for key in expected_keys:
 b=new[key];l={t:(s,e) for t,s,e in h['walk'](b,8) if t>>28!=8}
 for q in range(a(l[0x134b01][0],128),l[0x134b01][1],36):
  x,y,z,nx,ny,nz=struct.unpack_from('<6f',b,q)
  assert all(math.isfinite(v) for v in [x,y,z,nx,ny,nz])
  assert abs(nx*nx+ny*ny+nz*nz-1)<1e-4
  u,v=(abs(y)-center[0])/radius[0],(z-center[1])/radius[1]
  for start,end in zip(hull,hull[1:]+hull[:1]):
   assert (end[0]-start[0])*(v-start[1])-(end[1]-start[1])*(u-start[0])>=-2e-5,hex(key)
def textures(p):
 d=Path(p).read_bytes();head=next((s,e) for t,s,e in ch(d,8) if t==0xb3310000);p,e=next((s,e) for t,s,e in ch(d,*head) if t==0x33310003)
 return {k:d[o:o+c] for k,o,c,_,_,_ in (struct.unpack_from('<6I',d,q) for q in range(p,e,24))}
d=Path(sys.argv[2]+'/TEXTURES.BIN').read_bytes();head=next((s,e) for t,s,e in ch(d,8) if t==0xb3310000)
for t,p,e in ch(d,*head):
 if t==0x33310003:
  for q in range(p,e,24):
   k,_,_,_,flags,_=struct.unpack_from('<6I',d,q)
   if k in [nh('MX5NA_KIT00_BRAKELIGHT_OFF'),nh('MX5NA_KIT00_BRAKELIGHT_GLASS_OFF')]:assert flags==0x100
o=textures(sys.argv[1]+'/TEXTURES.BIN');n=textures(sys.argv[2]+'/TEXTURES.BIN')
expected_textures={nh(f'MX5NA_{p}_BRAKELIGHT_{s}') for _,p in prefixes for s in ['OFF','GLASS_OFF']}
assert n.keys()==o.keys()|expected_textures
sys.path.insert(0,'tools');from texpacks import jdlz
shadow_keys={nh('MX5NA_SHADOW'+s) for s in ['FE','IG']}
for k,v in o.items():
 if k not in shadow_keys:assert jdlz(n[k])[:-156]==jdlz(v)[:-156],hex(k)
intervals=[]
for k,blob in n.items():
 raw=jdlz(blob);ti=raw[-156:]
 offset,palette,size,palsize=struct.unpack_from('<4I',ti,0x30)
 assert palette==offset+size
 assert size+palsize<=len(raw)-156
 intervals.append((offset,offset+size+palsize,k))
intervals.sort()
for previous,current in zip(intervals,intervals[1:]):
 assert previous[1]<=current[0],(previous,current)
for suffix in ['FE','IG']:
 raw=jdlz(n[nh('MX5NA_SHADOW'+suffix)])
 original=(Path(sys.argv[3])/f'{nh("MIATA_SHADOW"+suffix):08x}.raw').read_bytes()
 assert raw[:-156]==original[:-156]
for suffix in ['OFF','GLASS_OFF']:
 raw=jdlz(n[nh('MX5NA_KIT00_BRAKELIGHT_'+suffix)])
 original=(Path(sys.argv[3])/f'{nh("MIATA_KIT00_BRAKELIGHT_"+suffix):08x}.raw').read_bytes()
 assert raw[:-156]==original[:-156]
print('PASS: all NB tail variants, unrelated NA parts preserved, optical/shadow pixels exact, decompressed image ranges disjoint')


