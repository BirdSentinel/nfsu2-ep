"""Separate the NA's baked doors and supply NB-style inner panels and sills."""
import argparse,struct,math
from pathlib import Path
from collections import defaultdict
from fit_mx5na_240sx_headlights import H,A,NH,CH,chunk

def leaves(b):return {t:(p,e) for t,p,e in H['walk'](b,8) if t>>28!=8}
def groups(b):
 l=leaves(b);vp=A(l[0x134b01][0],128);ip=A(l[0x134b03][0],16)
 vs=[b[q:q+36] for q in range(vp,l[0x134b01][1],36)]
 result=[]
 for q in range(A(l[0x134b02][0],16),l[0x134b02][1],60):
  mat=b[q:q+60];ct=struct.unpack_from('<I',mat,12)[0];fi=struct.unpack_from('<I',mat,52)[0];ti,si=struct.unpack_from('<2I',mat,28)
  ids=struct.unpack_from('<'+'H'*ct,b,ip+fi*2)
  result.append((mat,b[l[0x134012][0]+8*ti:l[0x134012][0]+8*ti+8],b[l[0x134013][0]+8*si:l[0x134013][0]+8*si+8],[[vs[i] for i in ids[j:j+3]] for j in range(0,ct,3)]))
 return result

def build(template,name,gs,name_alignment=1):
 l=leaves(template);hp=A(l[0x134011][0],16)
 info=bytearray(template[hp:l[0x134011][1]]);struct.pack_into('<I',info,16,NH(name));info[164:]=(name.encode()+b'\0').ljust(A(len(name)+1,name_alignment),b'\0')
 tex=bytearray();sh=bytearray();mats=bytearray();verts=bytearray();ids=[]
 def entry(table,v):
  for i in range(0,len(table),8):
   if table[i:i+8]==v:return i//8
  table.extend(v);return len(table)//8-1
 for mat,t,s,tris in gs:
  if not tris:continue
  m=bytearray(mat);start=len(ids);lookup={};points=[]
  for tri in tris:
   for v in tri:
    if v not in lookup:lookup[v]=len(verts)//36;verts+=v
    ids.append(lookup[v]);points.append(struct.unpack_from('<3f',v))
  struct.pack_into('<I',m,12,len(ids)-start);struct.pack_into('<I',m,52,start);struct.pack_into('<2I',m,28,entry(tex,t),entry(sh,s))
  for off,fn in [(0,min),(16,max)]:struct.pack_into('<3f',m,off,*(fn(p[i] for p in points) for i in range(3)))
  mats+=m
 points=[struct.unpack_from('<3f',verts,q) for q in range(0,len(verts),36)]
 for off,fn in [(32,min),(48,max)]:struct.pack_into('<3f',info,off,*(fn(p[i] for p in points) for i in range(3)))
 info[25]=len(tex)//8;info[26]=len(sh)//8;struct.pack_into('<I',info,20,len(ids)//3);struct.pack_into('<f',info,152,len(ids)/3)
 prefix=chunk(0x134011,info)+chunk(0x134012,tex)+chunk(0x134013,sh)
 mh=bytearray(template[A(l[0x134900][0],16):l[0x134900][1]]);struct.pack_into('<I',mh,16,len(mats)//60);struct.pack_into('<I',mh,36,len(ids)//3);struct.pack_into('<I',mh,52,len(verts)//36)
 ms=8+len(prefix)+8;mesh=bytearray(chunk(0x134900,b'\x11'*(A(ms+8,16)-ms-8)+mh))
 for tag,payload,alignment in [(0x134b01,verts,128),(0x134b02,mats,16),(0x134b03,struct.pack('<'+'H'*len(ids),*ids),16)]:
  pos=ms+len(mesh)+8;mesh+=chunk(tag,b'\x11'*(A(pos,alignment)-pos)+payload)
 return chunk(0x80134010,prefix+chunk(0x80134100,mesh))

def components(tris):
 parent=list(range(len(tris)));at={}
 def root(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 for i,t in enumerate(tris):
  for v in t:
   k=tuple(round(x,4) for x in struct.unpack_from('<3f',v))
   if k in at:parent[root(i)]=root(at[k])
   at[k]=i
 result=defaultdict(list)
 for i,t in enumerate(tris):result[root(i)].append(i)
 return result.values()

def door_outline(tris):
 points=sorted(set((struct.unpack_from('<3f',v)[0],struct.unpack_from('<3f',v)[2]) for t in tris for v in t))
 def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
 def half(ps):
  h=[]
  for p in ps:
   while len(h)>1 and cross(h[-2],h[-1],p)<=0:h.pop()
   h.append(p)
  return h[:-1]
 return half(points)+half(points[::-1])

def split_liner(tris,outline):
 """Cut only the cabin sidewall at the door aperture, retaining its lower floor."""
 inside=[];outside=[]
 def mix(a,b,t):
  v=bytearray(a)
  for off in (0,4,8,12,16,20,28,32):
   x=struct.unpack_from('<f',a,off)[0];y=struct.unpack_from('<f',b,off)[0]
   struct.pack_into('<f',v,off,x+(y-x)*t)
  for off in range(24,28):v[off]=round(a[off]+(b[off]-a[off])*t)
  return bytes(v)
 def fan(poly):return [[poly[0],poly[i],poly[i+1]] for i in range(1,len(poly)-1)]
 for tri in tris:
  poly=tri
  for a,b in zip(outline,outline[1:]+outline[:1]):
   def dist(v):
    x,_,z=struct.unpack_from('<3f',v);return (b[0]-a[0])*(z-a[1])-(b[1]-a[1])*(x-a[0])
   yes=[];no=[]
   for v,w in zip(poly,poly[1:]+poly[:1]):
    d,e=dist(v),dist(w)
    (yes if d>=0 else no).append(v)
    if (d>=0)!=(e>=0):
     p=mix(v,w,d/(d-e));yes.append(p);no.append(p)
   outside.extend(fan(no));poly=yes
   if not poly:break
  inside.extend(fan(poly))
 return inside,outside

def close_door_shell(tris,side):
 """Back and edge walls follow the actual NA skin, never a donor bounding box.

 The original upholstery sits in front of this full-depth backing. Weld the
 exterior by position (UV/normal seams are not holes) before finding its rim.
 """
 sign=1 if side=='LEFT' else -1
 def key(v):return tuple(round(x,5) for x in struct.unpack_from('<3f',v))
 edges=defaultdict(list)
 for tri in tris:
  for a,b in zip(tri,tri[1:]+tri[:1]):edges[tuple(sorted((key(a),key(b))))].append((a,b))
 def inner(v):
  # Span the FULL door depth to the inner panel, rather than adding only a
  # thin second skin that leaves a cavity between the skin and upholstery.
  p=list(struct.unpack_from('<3f',v));p[1]=sign*.665;return p
 def face(points):
  a,b,c=points;u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
  n=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]);length=math.sqrt(sum(x*x for x in n))
  if length<1e-10:return []
  return [[struct.pack('<6fI2f',*p,*(x/length for x in n),0xffffffff,130.5/512,230.5/512) for p in points]]
 result=[]
 for tri in tris:result.extend(face([inner(v) for v in reversed(tri)]))
 for es in edges.values():
  if len(es)!=1:continue
  a,b=es[0];pa=struct.unpack_from('<3f',a);pb=struct.unpack_from('<3f',b)
  result.extend(face([pb,pa,inner(a)]));result.extend(face([pb,inner(a),inner(b)]))
 return result

def animations(source,destination):
 """Retarget NB hinges to the NA door envelope without changing rotations."""
 data=bytearray(source.read_bytes());original=bytes(data)
 hp,he=next((p,e) for t,p,e in CH(data,0) if t==0x37100)
 start=A(hp,16)+16
 assert he-start==21*64
 for index in range(6,12):
  pos=start+index*64+48
  old=struct.unpack_from('<3f',data,pos);x,y,z=old
  new=(-.574+(x+.7619123459)*(1.142/1.1849990785),y,.067+(z-.1090206057)*(.539/.568641469))
  struct.pack_into('<3f',data,pos,*new)
  if index in (7,10):
   side='LEFT' if index==7 else 'RIGHT'
   p,e=next((p,e) for t,p,e in CH(data,0) if t==0xe34010 and f'MX5NA_ZAM_{side}_DOOR_SCISSOR_t'.encode() in data[p:e])
   key=original.find(struct.pack('<3f',*old),p,e)
   assert key>=p and struct.unpack_from('<3I',original,key-12)==(2,1,2)
   count=struct.unpack_from('<I',original,key-20)[0]
   assert count==28
   for q in range(key,key+count*12,12):
    v=struct.unpack_from('<3f',original,q)
    struct.pack_into('<3f',data,q,*(v[j]+new[j]-old[j] for j in range(3)))
 destination.write_bytes(data)

def patch(source,donor,destination):
 data=source.read_bytes();nb=donor.read_bytes()
 def solids(d):return {struct.unpack_from('<I',d,p+24)[0]:d[p-8:e] for t,p,e in CH(d,8) if t==0x80134010}
 ss=solids(data);dd=solids(nb);doors={s:[] for s in ['LEFT','RIGHT']}
 assert NH('MX5NA_KIT00_DOOR_LEFT_A') not in ss,'Doors already separated; build from pre-door backup'
 outlines={}
 for name in ['MX5NA_KIT00_BODY_A','MX5NA_BASE_A']:
  b=ss[NH(name)];l=leaves(b);edited=bytearray(b);ip=A(l[0x134b03][0],16)
  for mi,(mat,t,s,tris) in enumerate(groups(b)):
   selected={side:[] for side in doors};take=set()
   # The beltline seal is connected to the hardtop seals, so component
   # extraction cannot separate it. Its low, horizontal faces belong to the door.
   if name.endswith('BODY_A') and mi==7:
    for i,tri in enumerate(tris):
     ps=[struct.unpack_from('<3f',v) for v in tri]
     side='LEFT' if min(p[1] for p in ps)>.68 else 'RIGHT' if max(p[1] for p in ps)<-.68 else None
     if side and all(-.55<p[0]<.42 and .56<p[2]<.617 for p in ps):
      selected[side].append(tri);take.add(i)
   for comp in components(tris):
    pts=[struct.unpack_from('<3f',v) for i in comp for v in tris[i]]
    lo=[min(p[j] for p in pts) for j in range(3)];hi=[max(p[j] for p in pts) for j in range(3)]
    side='LEFT' if lo[1]>.55 else 'RIGHT' if hi[1]<-.55 else None
    if side and lo[0]>-.60 and hi[0]<.58 and lo[2]>.04 and hi[2]<.925:
     if (name.endswith('BODY_A') and mi in [0,3,4,8,9]) or (name.endswith('BASE_A') and mi==2):
      selected[side].extend(tris[i] for i in comp);take.update(comp)
   for side,ts in selected.items():
    if ts:
     doors[side].append((mat,t,s,ts));print(name,mi,side,len(ts))
     if name.endswith('BODY_A') and mi==0:outlines[side]=door_outline(ts)
   if take:
    # Preserve vertex bytes and all surviving triangles exactly.
    q=A(l[0x134b02][0],16)+mi*60;ct=struct.unpack_from('<I',mat,12)[0];fi=struct.unpack_from('<I',mat,52)[0]
    ids=struct.unpack_from('<'+'H'*ct,b,ip+fi*2);kept=[v for i in range(len(tris)) if i not in take for v in ids[3*i:3*i+3]]
    struct.pack_into('<I',edited,q+12,len(kept));struct.pack_into('<'+'H'*len(kept),edited,ip+fi*2,*kept)
  ss[NH(name)]=bytes(edited)
 # The cabin was modeled as a closed shell. Open its sidewalls only inside
 # the actual door silhouette, and carry that original upholstery with the door.
 name='MX5NA_BASE_A';gs=groups(ss[NH(name)]);mat,t,s,tris=gs[1];kept=[];liners={side:[] for side in doors}
 for tri in tris:
  ys=[struct.unpack_from('<f',v,4)[0] for v in tri]
  side='LEFT' if min(ys)>.60 else 'RIGHT' if max(ys)<-.60 else None
  if side:
   cut,rest=split_liner([tri],outlines[side]);kept.extend(rest)
   liners[side].extend(cut)
  else:kept.append(tri)
 gs[1]=(mat,t,s,kept)
 for side,cut in liners.items():
  if cut:
   # Apply the original upholstery directly to the backing plane, with only
   # 0.5 mm raster clearance. A translated 3D liner floats away from this plane.
   sign=1 if side=='LEFT' else -1
   moved=[]
   for tri in cut:
    row=[]
    for raw in tri:
     v=bytearray(raw)
     struct.pack_into('<f',v,4,sign*.6645)
     struct.pack_into('<3f',v,12,0,-sign,0)
     row.append(bytes(v))
    moved.append(row)
   doors[side].append((mat,t,s,moved))
 # BASE owns attachment markers; retain those after rebuilding its mesh.
 old=ss[NH(name)];new=build(old,name,gs);ll=leaves(old)
 if 0x13401a in ll:
  p,e=ll[0x13401a];pos=len(new)+8
  new+=chunk(0x13401a,b'\x11'*(A(pos,16)-pos)+old[A(p,16):e])
  new=bytearray(new);struct.pack_into('<I',new,4,len(new)-8);new=bytes(new)
 ss[NH(name)]=new
 # Keep the exact NA surfaces/UVs. NB supplies naming, mesh flags and inner shell.
 for side in doors:
  assert sum(len(g[3]) for g in doors[side])>600
  stock=ss[NH(f'MX5NA_KIT00_HEADLIGHT_{side}_A')]
  dark=next(g for g in groups(stock) if struct.unpack_from('<I',g[1])[0]==NH('MX5NA_SKIN4') and struct.unpack_from('<I',g[2])[0]==NH('MOLDINGS'))
  shell=close_door_shell(doors[side][0][3],side)
  doors[side].append((dark[0],dark[1],dark[2],shell))
  for lod in 'ABC':
   name=f'MX5NA_KIT00_DOOR_{side}_{lod}'
   ss[NH(name)]=build(dd[NH(f'MIATA_KIT00_DOOR_{side}_{lod}')],name,doors[side])
  for kind in ['PANEL','SILL']:
   template=dd[NH(f'MIATA_KIT00_DOOR_{kind}_{side}_A')]
   tris=[]
   for tri in groups(template)[0][3]:
    out=[]
    for raw in tri:
     v=bytearray(raw);x,y,z=struct.unpack_from('<3f',v)
     x=-.574+(x+.7619123459)*(1.142/1.1849990785)
     z=.067+(z-.1090206057)*(.539/.568641469)
     # NB shells are wider at their edges than the NA door skin. Keep the
     # complete support shell inward of the original NA upholstery, preventing
     # the black panel/sill edges from piercing the painted door when closed.
     yscale=.01 if kind=='PANEL' else .10
     ybase=.666 if kind=='PANEL' else .66
     y=math.copysign(ybase+(abs(y)-.655)*yscale,y)
     nx,ny,nz=struct.unpack_from('<3f',v,12)
     normal=(nx/(1.142/1.1849990785),ny/yscale,nz/(.539/.568641469))
     length=math.sqrt(sum(n*n for n in normal))
     if length:struct.pack_into('<3f',v,12,*(n/length for n in normal))
     struct.pack_into('<3f',v,0,x,y,z);struct.pack_into('<2f',v,28,130.5/512,230.5/512);out.append(bytes(v))
    tris.append(out)
   name=f'MX5NA_KIT00_DOOR_{kind}_{side}_A';ss[NH(name)]=build(template,name,[(dark[0],dark[1],dark[2],tris)])
 # Rebuild the solid index, preserving every unrelated solid.
 keys=sorted(ss);offsets={k:0 for k in keys};hp,he=next((p,e) for t,p,e in CH(data,8) if t==0x80134001)
 for _ in range(2):
  header=bytearray()
  for t,p,e in CH(data,hp,he):
   payload=data[p:e]
   if t==0x134002:payload=bytearray(payload);struct.pack_into('<I',payload,12,len(keys))
   elif t==0x134003:payload=b''.join(struct.pack('<2I',k,0) for k in keys)
   elif t==0x134004:payload=b''.join(struct.pack('<6I',k,offsets[k],len(ss[k]),len(ss[k]),0,0) for k in keys)
   header+=chunk(t,payload)
  result=bytearray(data[:hp-8])+chunk(0x80134001,header)
  for k in keys:
   if len(result)%128:result+=chunk(0,bytes((-(len(result)+8))%128))
   offsets[k]=len(result);result+=ss[k]
  struct.pack_into('<I',result,4,len(result)-8)
 destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(result)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('donor',type=Path);p.add_argument('destination',type=Path);a=p.parse_args();patch(a.source,a.donor,a.destination)

