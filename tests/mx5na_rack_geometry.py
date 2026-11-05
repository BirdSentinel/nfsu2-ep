"""Check that moving the rack preserves its world placement and other solids."""
import runpy,struct,sys
from pathlib import Path
h=runpy.run_path('tools/vinyl-models.py');a=h['align']
old={o[0]:o for o in h['objects'](Path(sys.argv[1]))};new={o[0]:o for o in h['objects'](Path(sys.argv[2]))}
assert old.keys()==new.keys()
for n,(_,d,l,hp) in old.items():
 _,b,k,bp=new[n]
 for t in l:
  alignment={0x134b01:128,0x134b02:16,0x134b03:16,0x13401a:16}.get(t,1)
  before=d[a(l[t][0],alignment):l[t][1]];after=b[a(k[t][0],alignment):k[t][1]]
  if n=='MX5NA_STYLE01_BRAKELIGHT_A' and t in [0x134011,0x134b01,0x134b02]:continue
  assert before==after,(n,hex(t))
_,d,l,_=old['MX5NA_BASE_A'];p,e=l[0x13401a]
q=next(q for q in range(a(p,16),e,80) if struct.unpack_from('<I',d,q)[0]==h['namehash']('SPOILER'))
shift=struct.unpack_from('<3f',d,q+64)
_,d,l,_=old['MX5NA_STYLE01_BRAKELIGHT_A'];_,b,k,_=new['MX5NA_STYLE01_BRAKELIGHT_A']
p,e=l[0x134b01];p=a(p,128);np=a(k[0x134b01][0],128)
mp=a(l[0x134b02][0],16)+60;ip=a(l[0x134b03][0],16)
n=struct.unpack_from('<I',d,mp+12)[0];first=struct.unpack_from('<I',d,mp+52)[0]
used=set(struct.unpack_from('<'+'H'*n,d,ip+first*2))
for i in range((e-p)//36):
 v=struct.unpack_from('<3f',d,p+i*36);w=struct.unpack_from('<3f',b,np+i*36)
 assert all(abs(x-y-z)<1e-6 for x,y,z in zip(v,w,shift)) if i in used else v==w
 assert d[p+i*36+12:p+(i+1)*36]==b[np+i*36+12:np+(i+1)*36]
print('PASS rack world placement, finish, normals, UVs and all other model parts preserved')
