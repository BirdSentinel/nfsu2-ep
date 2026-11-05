"""Fit retail NB engine/neon assemblies and hood hinges to the MX5NA."""
import argparse,struct,math
from pathlib import Path
from fix_mx5na_doors import CH,NH,A,chunk,groups,build,leaves
from fix_mx5na_nb_taillights import textures
SX=(1.760-.525876)/ (1.707727-.370098)
SY=.98
DZ=.603568-.6641835
SHEAR=.028
NAMES=['KIT00_ENGINE_A','KIT00_ENGINE_B','STYLE01_ENGINE_A','STYLE01_ENGINE_UNLIT_A','STYLE02_ENGINE_A','STYLE02_ENGINE_UNLIT_A']
TEXTURES=[('MIATA_ENGINE','MX5NA_ENGINE'),('MIATA_STYLE01_ENGINE','MX5NA_STYLE01_ENGINE'),('MIATA_STYLE02_ENGINE','MX5NA_STYLE02_ENGINE')]
def point(p):
 x,y,z=p
 return (.525876+(x-.370098)*SX,y*SY,z+DZ+(x-.370098)*SHEAR)

def blanking_face(tri):
 return all(.5<x<1.8 and abs(y)<.68 and z>.3 for x,y,z in (struct.unpack_from('<3f',v) for v in tri))

def geometry(source,donor,destination):
 data=source.read_bytes();nb=donor.read_bytes()
 def solids(d):return {struct.unpack_from('<I',d,p+24)[0]:d[p-8:e] for t,p,e in CH(d,8) if t==0x80134010}
 ss=solids(data);dd=solids(nb);texmap={NH(o):NH(n) for o,n in TEXTURES}
 # The addon's closed engine-bay insert otherwise masks the imported engine.
 # Only its upper black molding faces are removed; painted exterior is retained.
 key=NH('MX5NA_KIT00_BODY_A');template=ss[key];gs=groups(template)
 mat,t,s,tris=gs[5]
 assert struct.unpack_from('<I',t)[0]==NH('MX5NA_SKIN4') and struct.unpack_from('<I',s)[0]==NH('MOLDINGS')
 removed=sum(blanking_face(tri) for tri in tris)
 assert removed==156,removed
 gs[5]=(mat,t,s,[tri for tri in tris if not blanking_face(tri)])
 ss[key]=build(template,'MX5NA_KIT00_BODY_A',gs)
 for suffix in NAMES:
  template=dd[NH('MIATA_'+suffix)];gs=[]
  for mat,t,s,tris in groups(template):
   t=bytearray(t);key=struct.unpack_from('<I',t)[0]
   if key in texmap:struct.pack_into('<I',t,0,texmap[key])
   fitted=[]
   for tri in tris:
    row=[]
    for raw in tri:
     v=bytearray(raw);struct.pack_into('<3f',v,0,*point(struct.unpack_from('<3f',v)))
     nx,ny,nz=struct.unpack_from('<3f',v,12);normal=((nx-SHEAR*nz)/SX,ny/SY,nz);length=math.sqrt(sum(x*x for x in normal))
     if length:struct.pack_into('<3f',v,12,*(x/length for x in normal))
     row.append(bytes(v))
    fitted.append(row)
   gs.append((mat,bytes(t),s,fitted))
  name='MX5NA_'+suffix;solid=bytearray(build(template,name,gs))
  # Keep the lighting anchors available for every engine geometry/LOD.
  # The frontend may retain the stock mesh when performance parts change.
  marker_template=dd[NH('MIATA_STYLE02_ENGINE_A')] if '_UNLIT_' not in suffix else template
  ll=leaves(marker_template)
  if 0x13401a in ll:
   p,e=ll[0x13401a];markers=bytearray(marker_template[A(p,16):e])
   for q in range(0,len(markers),80):
    struct.pack_into('<3f',markers,q+64,*point(struct.unpack_from('<3f',markers,q+64)))
   pos=len(solid)+8
   solid+=chunk(0x13401a,b'\x11'*(A(pos,16)-pos)+markers)
   struct.pack_into('<I',solid,4,len(solid)-8)
  ss[NH(name)]=solid
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
 destination.write_bytes(result)
def animations(source,destination):
 data=bytearray(source.read_bytes());hp,he=next((p,e) for t,p,e in CH(data,0) if t==0x37100);start=A(hp,16)+16
 assert he-start==21*64
 for i in range(6):
  pos=start+i*64+48;old=struct.unpack_from('<3f',data,pos)
  new=point(old)
  if i in (0,5):new=(.525876,0.,.603568)
  struct.pack_into('<3f',data,pos,*new)
 destination.write_bytes(data)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('car',type=Path);p.add_argument('donor',type=Path);p.add_argument('raw',type=Path);p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 geometry(a.car/'GEOMETRY.BIN',a.donor/'GEOMETRY.BIN',a.output/'GEOMETRY.BIN')
 textures(a.car/'TEXTURES.BIN',a.raw,a.output/'TEXTURES.BIN',TEXTURES)
 animations(a.car/'PARTS_ANIMATIONS.bin',a.output/'PARTS_ANIMATIONS.bin')

