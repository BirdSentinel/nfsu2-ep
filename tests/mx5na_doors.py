"""Validate a staged MX5NA door conversion against its pre-door source."""
import sys,struct,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from fix_mx5na_doors import CH,NH,groups,leaves,A
from collections import Counter
old,new=map(lambda p:Path(p).read_bytes(),sys.argv[1:3])
def solids(b):return {struct.unpack_from('<I',b,p+24)[0]:b[p-8:e] for t,p,e in CH(b,8) if t==0x80134010}
a,b=solids(old),solids(new)
changed={NH('MX5NA_KIT00_BODY_A'),NH('MX5NA_BASE_A')}
assert len(b)==len(a)+10
for k in a:
 if k not in changed:assert a[k]==b[k],hex(k)
# Every exterior triangle appears exactly once, either on the fixed body or a door.
def surfaces(gs):return Counter(tuple(v for v in tri) for g in gs for tri in g[3])
before=surfaces(groups(a[NH('MX5NA_KIT00_BODY_A')]))
after=surfaces(groups(b[NH('MX5NA_KIT00_BODY_A')]))
for side in ('LEFT','RIGHT'):
 gs=groups(b[NH(f'MX5NA_KIT00_DOOR_{side}_A')])
 after.update(surfaces(gs[:5]))
assert before==after,'Door extraction lost/duplicated body triangles'
def area(tris):
 total=0
 for tri in tris:
  a,c,d=[struct.unpack_from('<3f',v) for v in tri]
  u=[c[i]-a[i] for i in range(3)];v=[d[i]-a[i] for i in range(3)]
  cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
  # The upholstery is flattened onto the backing in Y. Its XZ coverage
  # must still partition the source without missing/duplicated triangles.
  total+=abs(cross[1])/2
 return total
base=NH('MX5NA_BASE_A')
old_area=area(groups(a[base])[1][3]);new_area=area(groups(b[base])[1][3])
for side in ('LEFT','RIGHT'):new_area+=area(groups(b[NH(f'MX5NA_KIT00_DOOR_{side}_A')])[-2][3])
assert abs(old_area-new_area)<1e-5,'Cabin clipping lost or duplicated surface area'
# Attachment markers and all non-door animations must survive.
for k in changed:
 la,lb=leaves(a[k]),leaves(b[k])
 if 0x13401a in la:
  pa,ea=la[0x13401a];pb,eb=lb[0x13401a]
  assert a[k][A(pa,16):ea]==b[k][A(pb,16):eb]
for k in b.keys()-a.keys()|changed:
 for g in groups(b[k]):
  for tri in g[3]:
   for v in tri:assert all(math.isfinite(x) for x in struct.unpack_from('<6f',v))
# Door UVs and glass are retained, and each lower LOD has the same closed shape.
for side in ('LEFT','RIGHT'):
 door_groups=groups(b[NH(f'MX5NA_KIT00_DOOR_{side}_A')])
 expected=surfaces(door_groups)
 # Full-depth backing reaches the upholstery, rather than closing only a
 # thin skin while leaving the gap to the inner door panel untouched.
 backing=door_groups[-1][3][:len(door_groups[0][3])]
 assert all(abs(abs(struct.unpack_from('<f',v,4)[0])-.665)<1e-6 for t in backing for v in t)
 assert all(abs(abs(struct.unpack_from('<f',v,4)[0])-.6645)<1e-6 for t in door_groups[-2][3] for v in t),'Upholstery floats away from the backing'
 # The original skin plus recessed backing and rim walls is a closed shell:
 # every welded edge has exactly two adjacent faces, including UV seams.
 edges=Counter()
 for tri in door_groups[0][3]+door_groups[-1][3]:
  points=[tuple(round(x,5) for x in struct.unpack_from('<3f',v)) for v in tri]
  for p,q in zip(points,points[1:]+points[:1]):
   if p!=q:edges[tuple(sorted((p,q)))]+=1
 assert set(edges.values())=={2},'Door shell has an open or non-manifold edge'
 for lod in 'BC':assert expected==surfaces(groups(b[NH(f'MX5NA_KIT00_DOOR_{side}_{lod}')]))
 for kind in ('PANEL','SILL'):
  for g in groups(b[NH(f'MX5NA_KIT00_DOOR_{kind}_{side}_A')]):
   for tri in g[3]:
    assert all(abs(struct.unpack_from('<f',v,4)[0])<.68 for v in tri),'NB shell protrudes through NA skin'
for tri in groups(b[NH('MX5NA_KIT00_BODY_A')])[7][3]:
 ps=[struct.unpack_from('<3f',v) for v in tri]
 side=min(p[1] for p in ps)>.68 or max(p[1] for p in ps)<-.68
 assert not(side and all(-.55<p[0]<.42 and .56<p[2]<.617 for p in ps)),'Door beltline remains on body'
print('PASS: unchanged unrelated solids, exact exterior partition, markers, finite vertices, all door LODs')


