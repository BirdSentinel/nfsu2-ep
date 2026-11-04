"""Export the menu showroom background (without turntable) as OBJ/MTL + PNG."""
import argparse, importlib.util, io, json, math, re, struct
from pathlib import Path
from PIL import Image
import texpacks as t
spec=importlib.util.spec_from_file_location('vinyl_models',Path(__file__).with_name('vinyl-models.py'))
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('game');ap.add_argument('output');args=ap.parse_args()
 source=Path(args.game)/'FRONTEND/PLATFORMS/Showroom.BIN';b=source.read_bytes();out=Path(args.output);(out/'textures').mkdir(parents=True,exist_ok=True)
 names={};original=t.texture
 def named(ti,pf,buf,base):
  result=original(ti,pf,buf,base);names[result[0]]=ti[12:36].split(b'\0')[0].decode('ascii','replace');return result
 t.texture=named
 textures={x[0]:x for x in t.textures(b)}
 for shared in list((Path(args.game)/'GLOBAL').glob('*'))+list((Path(args.game)/'FRONTEND').glob('*'))+list((Path(args.game)/'TRACKS').glob('*.BUN')):
  if shared.is_file():
   data=shared.read_bytes()
   if data[:4]==b'JDLZ':data=t.jdlz(data)
   for x in t.textures(data):textures.setdefault(x[0],x)
 lines=['# Showroom background; Z up; game coordinates. Turntable excluded.','mtllib background.mtl'];used=set();offset=0;parts=[]
 for tag,p,e in v.walk(b):
  if tag!=0x80134010:continue
  l={tag:(a,z) for tag,a,z in v.walk(b,p,e) if tag>>28!=8};hp=v.align(l[0x134011][0],16);name=b[hp+164:l[0x134011][1]].split(b'\0')[0].decode()
  if name not in ('BACKDROP','BACKDROP_FLOOR'):continue
  vp,ve=l[0x134b01];vp=v.align(vp,128);mp,me=l[0x134b02];mp=v.align(mp,16);ip,ie=l[0x134b03];ip=v.align(ip,16);sp,se=l[0x134012]
  hashes=[struct.unpack_from('<I',b,q)[0] for q in range(sp,se,8)]
  assert (ve-vp)%24==0 and (me-mp)%60==0
  count=(ve-vp)//24;lines+=['o '+name,'s off']
  for q in range(vp,ve,24):
   x,y,z=struct.unpack_from('<3f',b,q);assert all(math.isfinite(n) for n in (x,y,z));lines.append(f'v {x:.7g} {y:.7g} {z:.7g}')
  for q in range(vp,ve,24):
   u,w=struct.unpack_from('<2f',b,q+16);lines.append(f'vt {u:.7g} {1-w:.7g}')
  faces=0
  for q in range(mp,me,60):
   n=struct.unpack_from('<I',b,q+12)[0];material=struct.unpack_from('<I',b,q+28)[0];first=struct.unpack_from('<I',b,q+52)[0]
   assert n%3==0 and ip+(first+n)*2<=ie and material<len(hashes)
   h=hashes[material];assert h in textures,f'Missing texture {h:08x}';used.add(h);lines.append(f'usemtl tex_{h:08x}')
   indices=struct.unpack_from('<'+'H'*n,b,ip+first*2);assert max(indices)<count
   for i in range(0,n,3):lines.append('f '+' '.join(f'{offset+j+1}/{offset+j+1}' for j in indices[i:i+3]))
   faces+=n//3
  offset+=count;parts.append(dict(name=name,vertices=count,triangles=faces))
 mtl=[]
 for h in sorted(used):
  _,w,height,fmt,pix=textures[h];name=re.sub('[^A-Za-z0-9_-]','_',names[h]);file=f'textures/{name}_{h:08x}.png'
  if fmt==21:im=Image.frombytes('RGBA',(w,height),pix,'raw','BGRA')
  else:
   assert fmt in t.BLOCK_BYTES
   hdr=b'DDS '+struct.pack('<7I',124,0x81007,height,w,len(pix),0,1)+bytes(44)+struct.pack('<II4s5I',32,4,struct.pack('<I',fmt),0,0,0,0,0)+struct.pack('<5I',0x1000,0,0,0,0)
   im=Image.open(io.BytesIO(hdr+pix)).convert('RGBA')
  im.save(out/file);mtl.extend([f'newmtl tex_{h:08x}','Ka 1 1 1','Kd 1 1 1','Ks 0 0 0','illum 1',f'map_Kd {file}',''])
 (out/'background.obj').write_text('\n'.join(lines)+'\n');(out/'background.mtl').write_text('\n'.join(mtl))
 report=dict(source=str(source),parts=parts,textures=len(used),excluded=['DISC01','DISC02','DISC03','PLATFORMBASE']);(out/'export.json').write_text(json.dumps(report,indent=2))
 (out/'README.txt').write_text('Open background.obj in Blender or another OBJ importer. Keep background.mtl and textures next to it.\nZ is up; original game coordinates and UVs are preserved.\nContains BACKDROP and BACKDROP_FLOOR only. DISC01/02/03 and PLATFORMBASE are excluded.\nPNG textures preserve alpha. Original game lighting, vertex-color shading, animated effects and particles are not reproduced by this OBJ export.\nThis is an editable export, not an automatic game replacement.\n')
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
