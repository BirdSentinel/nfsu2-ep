"""GOLF SNYPER: stock bumper with closed, UV-mapped fangs and tongue."""
import math,struct,argparse
from pathlib import Path
from fix_mx5na_doors import CH,NH,A,chunk,groups,build
from build_mx5na_luggage_rack import cross,sub,unit

def rebuild(data,solids):
 keys=sorted(solids);offsets={k:0 for k in keys};hp,he=next((p,e) for t,p,e in CH(data,8) if t==0x80134001)
 for _ in range(2):
  header=bytearray()
  for t,p,e in CH(data,hp,he):
   b=data[p:e]
   if t==0x134002:b=bytearray(b);struct.pack_into('<I',b,12,len(keys))
   elif t==0x134003:b=b''.join(struct.pack('<2I',k,0) for k in keys)
   elif t==0x134004:b=b''.join(struct.pack('<6I',k,offsets[k],len(solids[k]),len(solids[k]),0,0) for k in keys)
   header+=chunk(t,b)
  out=bytearray(data[:hp-8])+chunk(0x80134001,header)
  for k in keys:
   if len(out)%128:out+=chunk(0,bytes((-(len(out)+8))%128))
   offsets[k]=len(out);out+=solids[k]
  struct.pack_into('<I',out,4,len(out)-8)
 return out

def surface(rings,sides,tongue=False):
 # ring: centre X/Y/Z, half-width, half-thickness; closed at both ends.
 vs=[];faces=[];tangents=[]
 for j in range(len(rings)):
  a=rings[max(0,j-1)];b=rings[min(len(rings)-1,j+1)]
  tangents.append(unit((b[0]-a[0],b[1]-a[1],b[2]-a[2])))
 for j,(x,y,z,w,d) in enumerate(rings):
  for k in range(sides):
   a=2*math.pi*k/sides;c=math.cos(a);s=math.sin(a)
   groove=.003*math.exp(-c*c/.02)*max(0,s) if tongue else 0
   radial=d*s-groove
   tx,_,tz=tangents[j] if tongue else (0,0,-1)
   p=(x-radial*tz,y+w*c,z+radial*tx)
   uv=(.75+.22*c,j/(len(rings)-1)) if tongue else (.25,.5)
   vs.append((p,uv))
 for j in range(len(rings)-1):
  for k in range(sides):
   a=j*sides+k;b=j*sides+(k+1)%sides;c=b+sides;d=a+sides
   faces.extend([(a,b,c),(a,c,d)])
 for j in [0,len(rings)-1]:
  x,y,z,w,d=rings[j];center=len(vs);vs.append(((x,y,z),(.75, float(j>0)) if tongue else (.25,.5)))
  for k in range(sides):faces.append((center,j*sides+k,j*sides+(k+1)%sides))
 # Orient the side surfaces away from their ring centre and caps outward.
 oriented=[];normals=[[0.,0.,0.] for _ in vs]
 for ids in faces:
  a,b,c=ids;n=cross(sub(vs[b][0],vs[a][0]),sub(vs[c][0],vs[a][0]))
  if a>=len(rings)*sides:
   desired=tuple(-v for v in tangents[0]) if a==len(rings)*sides else tangents[-1]
  else:
   cy=sum(vs[i][0][1] for i in ids)/3;cx=sum(vs[i][0][0] for i in ids)/3
   cz=sum(vs[i][0][2] for i in ids)/3
   desired=(cx-sum(rings[i//sides][0] for i in ids)/3,cy-sum(rings[i//sides][1] for i in ids)/3,cz-sum(rings[i//sides][2] for i in ids)/3)
  if sum(n[i]*desired[i] for i in range(3))<0:b,c=c,b;n=tuple(-x for x in n)
  oriented.append((a,b,c))
  for i in [a,b,c]:
   for q in range(3):normals[i][q]+=n[q]
 packed=[struct.pack('<6fI2f',*p,*unit(n),0xffffffff,*uv) for (p,uv),n in zip(vs,normals)]
 return [[packed[i] for i in t] for t in oriented]

def extras(lod):
 sides={'A':16,'B':10,'C':6}[lod];ts=[]
 for y in [-.27,.27]:
  ts+=surface([(1.995,y,.212,.037,.015),(2.013,y,.197,.037,.018),(2.022,y,.090,.021,.013),(2.025,y,.047,.003,.003)],sides)
 rings=[];steps={'A':20,'B':14,'C':10}[lod]
 for j in range(steps+1):
  t=j/steps;angle=min(t*2,1)*math.pi/2
  # Roll over the intake edge, then hang down with a soft outward belly.
  x=2.018+.095*math.sin(angle);z=.183-.095*(1-math.cos(angle))
  if t>.5:
   u=(t-.5)*2;x+=.012*math.sin(math.pi*u);z-=.15*u
  w=.082*(math.sqrt(max(.0001,1-((t-.78)/.22)**2)) if t>.78 else 1)
  rings.append((x,0,z,w,.018*max(.12,w/.082)))
 return ts+surface(rings,sides,True)

def geometry(source,dest):
 data=source.read_bytes();ss={struct.unpack_from('<I',data,p+24)[0]:data[p-8:e] for t,p,e in CH(data,8) if t==0x80134010}
 assert data.count(struct.pack('<I',NH('GOLF_DOOR_HANDLE')))==0,'Texture suffix already in use'
 for lod in 'ABC':
  stock=ss[NH('GOLF_KIT00_FRONT_BUMPER_'+lod)];gs=groups(stock);mat,tex,shader,_=gs[3]
  tex=struct.pack('<2I',NH('GOLF_DOOR_HANDLE'),0)
  gs.append((mat,tex,shader,extras(lod)))
  name='GOLF_KIT01_FRONT_BUMPER_'+lod;ss[NH(name)]=build(stock,name,gs,name_alignment=4)
 # Retail CarHeadersMemoryFile also caches solid offsets and byte lengths.
 # Preserve every original slot; rebuilding/sorting the pack invalidates that
 # external index even when the pack's own index has been updated correctly.
 out=bytearray(data)
 for t,p,e in CH(data,8):
  if t!=0x80134010:continue
  key=struct.unpack_from('<I',data,p+24)[0]
  if key not in {NH('GOLF_KIT01_FRONT_BUMPER_'+lod) for lod in 'ABC'}:continue
  replacement=bytearray(ss[key]);remaining=e-(p-8)-len(replacement)
  assert remaining>=8,(key,remaining)
  replacement+=chunk(0,bytes(remaining-8));struct.pack_into('<I',replacement,4,len(replacement)-8)
  out[p-8:e]=replacement
 dest.write_bytes(out)

def textures(source,rawdir,dest):
 from PIL import Image
 data=source.read_bytes();raws={int(p.stem,16):bytearray(p.read_bytes()) for p in rawdir.glob('*.raw')}
 atlas=Image.new('RGB',(64,64));pix=atlas.load()
 for y in range(64):
  for x in range(64):
   if x<32:rgb=(244,240,226)
   else:
    edge=abs((x-48)/16);groove=math.exp(-((x-48)/1.05)**2)*.40
    shade=1-.20*edge-groove-.08*(y/63)
    rgb=tuple(int(c*shade) for c in (234,76,145))
   pix[x,y]=rgb
 atlas.save(dest.parent/'fangs-tongue-atlas.png')
 def rgb565(rgb):r,g,b=rgb;return (r>>3)<<11|(g>>2)<<5|(b>>3)
 raw=bytearray(raws[NH('GOLF_MISC')]);size=struct.unpack_from('<I',raw,len(raw)-156+0x38)[0];payload=bytearray()
 for dim in [64,32,16,8]:
  im=atlas.resize((dim,dim),Image.Resampling.LANCZOS)
  for y in range(0,dim,4):
   for x in range(0,dim,4):
    colors=[im.getpixel((x+i,y+j)) for j in range(4) for i in range(4)];light=max(colors,key=sum);dark=min(colors,key=sum);a,b=rgb565(light),rgb565(dark)
    if a<b:a,b=b,a
    def rgb(c):return ((c>>11)*255//31,((c>>5)&63)*255//63,(c&31)*255//31)
    aa,bb=rgb(a),rgb(b);pal=[aa,bb,tuple((2*p+q)//3 for p,q in zip(aa,bb)),tuple((p+2*q)//3 for p,q in zip(aa,bb))];bits=0
    for i,c in enumerate(colors):bits|=min(range(4),key=lambda k:sum((c[j]-pal[k][j])**2 for j in range(3)))<<(i*2)
    payload+=struct.pack('<HHI',a,b,bits)
 assert len(payload)==size
 raw[:size]=payload;ti=len(raw)-156;name='GOLF_DOOR_HANDLE';key=NH(name);assert key not in raws
 raw[ti+12:ti+36]=name.encode().ljust(24,b'\0');struct.pack_into('<I',raw,ti+36,key);raws[key]=raw
 hp,he=next((p,e) for t,p,e in CH(data,8) if t==0xb3310000)
 p,e=next((p,e) for t,p,e in CH(data,hp,he) if t==0x33310003)
 slots=[struct.unpack_from('<6I',data,q) for q in range(p,e,24)]
 # Keep retail compression and arena positions. Expanding every retail record
 # to literal-only JDLZ makes the streaming working set unnecessarily large.
 entries={s[0]:(data[s[1]:s[1]+s[2]],s[3:]) for s in slots}
 arena=max(struct.unpack_from('<I',r,len(r)-156+0x30)[0]+sum(struct.unpack_from('<2I',r,len(r)-156+0x38)) for k,r in raws.items() if k!=key)
 ti=len(raw)-156;size,pal=struct.unpack_from('<2I',raw,ti+0x38);arena=A(arena,128)
 struct.pack_into('<2I',raw,ti+0x30,arena,arena+size)
 blob=bytearray(b'JDLZ\x02\x10\0\0'+struct.pack('<II',len(raw),0)+b'\0')
 for i in range(0,len(raw),8):blob+=b'\0'+raw[i:i+8]
 struct.pack_into('<I',blob,12,len(blob));entries[key]=(blob,(len(raw),0x100,0))
 entries=dict(sorted(entries.items()))
 # Retain the retail data container and every old record's absolute offset.
 # The additional directory entry fits in the existing header alignment pad.
 bp,be=next((p,e) for t,p,e in CH(data,8) if t==0xb3320000)
 ip,ie=next((p,e) for t,p,e in CH(data,bp,be) if t==0x33320002)
 assert ie==be==len(data)
 out=bytearray(data);out+=bytes((-len(out))%128);new_offset=len(out);out+=blob
 offsets={s[0]:s[1] for s in slots};offsets[key]=new_offset
 header=bytearray()
 for t,p,e in CH(data,hp,he):
  b=data[p:e]
  if t==0x33310002:b=b''.join(struct.pack('<2I',k,0) for k in entries)
  elif t==0x33310003:b=b''.join(struct.pack('<6I',k,offsets[k],len(v[0]),*v[1]) for k,v in entries.items())
  header+=chunk(t,b)
 header=chunk(0xb3310000,header);gap=bp-8-(hp-8+len(header));assert gap>=8
 out[hp-8:bp-8]=header+chunk(0,bytes(gap-8))
 for pos in [0,bp-8,ip-8]:struct.pack_into('<I',out,pos+4,len(out)-pos-8)
 dest.write_bytes(out)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('car',type=Path);p.add_argument('raw',type=Path);p.add_argument('out',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 geometry(a.car/'GEOMETRY.BIN',a.out/'GEOMETRY.BIN');textures(a.car/'TEXTURES.BIN',a.raw,a.out/'TEXTURES.BIN')
 print('Built SNYPER at three LODs, preserving STOCK and all other solids; added independent enamel/pink atlas.')
