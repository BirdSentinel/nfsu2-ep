"""Verify rigid donor import: no warped lenses, covers or normals."""
import sys,struct,random
from pathlib import Path
import numpy as np
sys.path.insert(0,'tools')
from fit_mx5na_240sx_headlights import H,A,NH,CH

def objects(path):
 return {struct.unpack_from('<I',b,hp+16)[0]:(b,l,hp) for _,b,l,hp in H['objects'](Path(path)/'GEOMETRY.BIN')}
old,new,donor=map(objects,sys.argv[1:4])
expected={NH(f'MX5NA_STYLE{i:02}_HEADLIGHT_{side}_{lod}') for i in range(1,15) for side in ['LEFT','RIGHT'] for lod in 'ABC'}
assert old.keys()==new.keys()
for key in old.keys()-expected:
 for tag,(p,e) in old[key][1].items():
  np_,ne=new[key][1][tag]
  assert old[key][0][p:e]==new[key][0][np_:ne],hex(key)
for style in range(1,15):
 for side in ['LEFT','RIGHT']:
  for lod in 'ABC':
   name=f'240SX_STYLE{style:02}_HEADLIGHT_{side}_{lod}'
   key=NH(name)
   if key not in donor:key=next(NH(name[:-1]+fallback) for fallback in 'CBA' if NH(name[:-1]+fallback) in donor)
   b,l,hp=donor[key];nb,nl,nhp=new[NH(name.replace('240SX','MX5NA'))]
   vp=A(l[0x134b01][0],128);nvp=A(nl[0x134b01][0],128)
   count=(l[0x134b01][1]-vp)//36
   v=np.array([struct.unpack_from('<6fI2f',b,vp+i*36) for i in range(count)])
   nv=np.array([struct.unpack_from('<6fI2f',nb,nvp+i*36) for i in range(count)])
   # A single scaled orthogonal transform must explain EVERY original vertex.
   x=v[:,:3]-v[:,:3].mean(0);y=nv[:,:3]-nv[:,:3].mean(0)
   matrix=np.linalg.lstsq(x,y,rcond=None)[0]
   assert np.max(np.abs(x@matrix-y))<2e-7,(name,'deformation')
   assert np.max(np.abs(matrix.T@matrix-np.eye(3)*.81))<2e-5,(name,'nonuniform scale')
   assert np.max(np.abs(v[:,3:6]@(matrix/.9)-nv[:,3:6]))<3e-5,(name,'normals')
   assert np.array_equal(v[:,6],nv[:,6])
   for m,nm in zip(range(A(l[0x134b02][0],16),l[0x134b02][1],60),range(A(nl[0x134b02][0],16),nl[0x134b02][1],60)):
    ct=struct.unpack_from('<I',b,m+12)[0];fi=struct.unpack_from('<I',b,m+52)[0]
    assert struct.unpack_from('<I',nb,nm+12)[0]==ct
    indices=struct.unpack_from('<'+'H'*ct,b,A(l[0x134b03][0],16)+2*fi)
    assert indices==struct.unpack_from('<'+'H'*ct,nb,A(nl[0x134b03][0],16)+2*fi)
    ti=struct.unpack_from('<I',b,m+28)[0]
    if struct.unpack_from('<I',b,l[0x134012][0]+8*ti)[0]!=NH('240SX_SKIN1'):
     assert np.array_equal(v[list(indices),7:],nv[list(indices),7:]),(name,'optical UV')
   # Adapter is a separate material; no donor triangles were removed or split.
   assert nl[0x134b02][1]-A(nl[0x134b02][0],16)==l[0x134b02][1]-A(l[0x134b02][0],16)+60
   trim=nl[0x134b02][1]-60
   ti,si=struct.unpack_from('<2I',nb,trim+28)
   assert struct.unpack_from('<I',nb,nl[0x134012][0]+8*ti)[0]==NH('MX5NA_SKIN4')
   assert struct.unpack_from('<I',nb,nl[0x134013][0]+8*si)[0]==NH('MOLDINGS')
   ct=struct.unpack_from('<I',nb,trim+12)[0];fi=struct.unpack_from('<I',nb,trim+52)[0]
   for i in set(struct.unpack_from('<'+'H'*ct,nb,A(nl[0x134b03][0],16)+2*fi)):
    assert struct.unpack_from('<2f',nb,nvp+i*36+28)==(130.5/512,230.5/512)
print('PASS: all 84 donor meshes retain proportions, topology, optical UVs and rotated normals; only uniform 0.90 scale, rotation and translation; unrelated NA parts unchanged')
