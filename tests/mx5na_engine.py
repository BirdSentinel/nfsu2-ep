import sys,struct,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from fix_mx5na_engine import *
source,donor,stage=map(Path,sys.argv[1:4])
def solids(path):
 d=path.read_bytes();return {struct.unpack_from('<I',d,p+24)[0]:d[p-8:e] for t,p,e in CH(d,8) if t==0x80134010}
a=solids(source/'GEOMETRY.BIN');b=solids(stage/'GEOMETRY.BIN');nb=solids(donor/'GEOMETRY.BIN')
assert len(b)==len(a)+len(NAMES)
for k,v in a.items():
 if k==NH('MX5NA_KIT00_BODY_A'):
  old,new=groups(v),groups(b[k]);nonempty=[(i,g) for i,g in enumerate(old) if g[3]];assert len(nonempty)==len(new)
  for (i,g),h in zip(nonempty,new):
   expected=[t for t in g[3] if not blanking_face(t)] if i==5 else g[3]
   assert h[3]==expected,'Non-blanking body surface changed'
  assert sum(len(g[3]) for g in old)-sum(len(g[3]) for g in new)==156
 else:assert b[k]==v,'Unrelated solid modified'
for name in NAMES:
 oldsolid=nb[NH('MIATA_'+name)];newsolid=b[NH('MX5NA_'+name)]
 marker_source=nb[NH('MIATA_STYLE02_ENGINE_A')] if '_UNLIT_' not in name else oldsolid
 ll=leaves(marker_source)
 if 0x13401a in ll:
  p,e=ll[0x13401a];oldmarks=marker_source[A(p,16):e]
  p,e=leaves(newsolid)[0x13401a];newmarks=newsolid[A(p,16):e]
  assert len(newmarks)==len(oldmarks)
  for q in range(0,len(oldmarks),80):
   assert newmarks[q:q+64]==oldmarks[q:q+64]
   assert newmarks[q+76:q+80]==oldmarks[q+76:q+80]
   assert all(abs(a-b)<1e-6 for a,b in zip(point(struct.unpack_from('<3f',oldmarks,q+64)),struct.unpack_from('<3f',newmarks,q+64)))
 old=groups(nb[NH('MIATA_'+name)]);new=groups(b[NH('MX5NA_'+name)])
 old=[g for g in old if g[3]];assert len(old)==len(new)
 for g,h in zip(old,new):
  assert len(g[3])==len(h[3])
  for t,u in zip(g[3],h[3]):
   for v,w in zip(t,u):
    expected=point(struct.unpack_from('<3f',v));actual=struct.unpack_from('<3f',w)
    assert max(abs(x-y) for x,y in zip(expected,actual))<1e-6
    assert v[24:]==w[24:],'UV/color altered'
    assert all(math.isfinite(x) for x in struct.unpack_from('<6f',w))
x=(source/'PARTS_ANIMATIONS.bin').read_bytes();y=(stage/'PARTS_ANIMATIONS.bin').read_bytes()
allowed=set();hp,he=next((p,e) for t,p,e in CH(x,0) if t==0x37100);start=A(hp,16)+16
for i in range(6):allowed.update(range(start+i*64+48,start+i*64+60))
assert len(x)==len(y) and all(p in allowed for p,(u,v) in enumerate(zip(x,y)) if u!=v),'Non-hood animation modified'
pivot=struct.unpack_from('<3f',y,start+48)
assert max(abs(pivot[i]-(.525876,0,.603568)[i]) for i in range(3))<1e-6
print('PASS: six fitted engine/neon solids; donor UVs; only 156 blanking faces removed; exterior and non-hood animation bytes retained; rear hinge on NA hood edge')


