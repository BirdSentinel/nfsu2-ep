"""The audio clearance fit must never remove outer panels or audio triangles."""
import runpy,struct,sys,tempfile
from pathlib import Path
h=runpy.run_path('tools/vinyl-models.py');a=h['align'];nh=h['namehash']
def solids(path):
 b=Path(path).read_bytes()
 return {struct.unpack_from('<I',b,p+24)[0]:b[p-8:e] for t,p,e in h['chunks'](b,8) if t==0x80134010}
old,new=map(solids,sys.argv[1:3]);assert old.keys()==new.keys()
expected={nh(f'MX5NA_KIT{i:02}_TRUNK_AUDIO{s}_A') for i in range(4) for s in ['', '_UNLIT']}
for key,b in old.items():
 if key not in expected:
  assert b==new[key],f'Unrelated solid changed: {key:08x}'
  continue
 assert len(b)==len(new[key])
 leaves={t:(p,e) for t,p,e in h['walk'](b,8) if t>>28!=8}
 p,e=leaves[0x134b03];assert b[p:e]==new[key][p:e], 'Audio indices changed'
 for q in range(a(leaves[0x134b02][0],16),leaves[0x134b02][1],60):
  assert b[q+12:q+16]==new[key][q+12:q+16], 'Audio triangles removed'
  assert b[q+28:q+60]==new[key][q+28:q+60], 'Audio material changed'
 for q in range(a(leaves[0x134b01][0],128),leaves[0x134b01][1],36):
  x,y,z=struct.unpack_from('<3f',b,q);xx,yy,zz=struct.unpack_from('<3f',new[key],q)
  assert yy==y and zz==z and b[q+24:q+36]==new[key][q+24:q+36]
  assert abs(xx-(-1.70+(x+1.70)*.40 if x < -1.70 else x))<1e-6
  assert xx > -1.78
print('PASS: complete BODY/TRUNK and other solids unchanged; all audio triangles, materials and UVs preserved')

with tempfile.TemporaryDirectory() as directory:
 path=Path(directory)/'again.bin'
 runpy.run_path('tools/fix_mx5na_audio_clearance.py')['patch'](Path(sys.argv[2]),path)
 assert path.read_bytes()==Path(sys.argv[2]).read_bytes()
print('PASS: repeated clearance fit makes no further changes')
