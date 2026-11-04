"""Build a two-plane menu backdrop from a photograph; preserve the turntable."""
import argparse,importlib.util,io,struct
from pathlib import Path
from PIL import Image
import texpacks as t
from remove_menu_smoke import remove_menu_smoke
spec=importlib.util.spec_from_file_location('models',Path(__file__).with_name('vinyl-models.py'));v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)

def high_resolution_background(b, image):
 # Append a larger mip chain inside the original TPK. Keep all existing slots
 # and 128-byte alignment intact, including the following environment-map TPK.
 for start,end in t.tpks(b,0,len(b)):
  info=data=None
  for tag,p,e in t.chunks(b,start,end):
   if tag==0xb3310000:info=(p,e)
   if tag==0xb3320000:data=(p,e)
  if not info or not data:continue
  for tag,p,e in t.chunks(b,*info):
   if tag!=0x33310004:continue
   for q in range(p,e,124):
    if struct.unpack_from('<I',b,q+36)[0]!=0x4d5565d8:continue
    pixel_start,pixel_end=next((a,z) for tag,a,z in t.chunks(b,*data) if tag==0x33320002)
    assert pixel_end==data[1]==end
    base=v.align(pixel_start,128);pixels=bytearray()
    for level in range(6):
     stream=io.BytesIO();image.resize((1024>>level,512>>level),Image.Resampling.LANCZOS).save(stream,format='DDS',pixel_format='DXT1')
     pixels+=stream.getvalue()[128:]
    size=len(pixels);pixels+=bytes((-size)%128)
    struct.pack_into('<I',b,q+0x30,pixel_end-base)
    struct.pack_into('<I',b,q+0x38,size)
    struct.pack_into('<I',b,q+0x40,1024*512//2)
    struct.pack_into('<HHBB',b,q+0x44,1024,512,10,9)
    for header in (start-4,data[0]-4,pixel_start-4):
     struct.pack_into('<I',b,header,struct.unpack_from('<I',b,header)[0]+len(pixels))
    b[pixel_end:pixel_end]=pixels
    return
 raise ValueError('Background texture slot not found')
def build(source,photo,output):
 original=Path(source).read_bytes();b=bytearray(original);im=Image.open(photo).convert('RGBA');out=Path(output);out.mkdir(parents=True,exist_ok=True)
 top=im.crop((0,0,im.width,im.height//2));floor=im.crop((0,im.height//2,im.width,im.height));top.save(out/'background.png');floor.save(out/'floor.png')
 # Reuse only background texture slots. Platform geometry/materials remain byte-identical.
 chosen={0x4d5565d8:top,0x957c075e:floor};tex=t.texture
 def replace(ti,pf,buf,base):
  r=tex(ti,pf,buf,base);h,w,height,fmt,_=r
  if h not in chosen:return r
  offset=base+struct.unpack_from('<I',ti,0x30)[0];size=struct.unpack_from('<I',ti,0x38)[0];pixels=bytearray();a,c=w,height
  while len(pixels)<size:
   image=chosen[h].resize((a,c),Image.Resampling.LANCZOS);stream=io.BytesIO();image.save(stream,format='DDS',pixel_format=struct.pack('<I',fmt).decode());pixels+=stream.getvalue()[128:];a=max(1,a//2);c=max(1,c//2)
  assert len(pixels)==size
  b[offset:offset+size]=pixels;return r
 t.texture=replace;list(t.textures(original));t.texture=tex
 for tag,p,e in v.walk(original):
  if tag!=0x80134010:continue
  l={tag:(a,z) for tag,a,z in v.walk(original,p,e) if tag>>28!=8};hp=v.align(l[0x134011][0],16);name=original[hp+164:l[0x134011][1]].split(b'\0')[0].decode()
  if name not in ('BACKDROP','BACKDROP_FLOOR'):continue
  isfloor=name=='BACKDROP_FLOOR';hash=0x957c075e if isfloor else 0x4d5565d8
  points=[(-26,-16,-.03),(26,-16,-.03),(26,35,-.03),(-26,35,-.03)] if isfloor else [(-22.5,35,0),(16.5,35,0),(16.5,35,13),(-22.5,35,13)]
  uv=[(0,1),(1,1),(1,0),(0,0)]
  vp,ve=l[0x134b01];vp=v.align(vp,128);mp,me=l[0x134b02];mp=v.align(mp,16);ip,ie=l[0x134b03];ip=v.align(ip,16);sp,se=l[0x134012]
  struct.pack_into('<I',b,sp,hash)
  if not isfloor:struct.pack_into('<I',b,sp+8,0x957c075e)
  for q in range(vp,ve,24):struct.pack_into('<3fI2f',b,q,*points[0],0xff909090,*uv[0])
  if not isfloor:
   points += [(-26,-16,-.03),(26,-16,-.03),(26,35,-.03),(-26,35,-.03)];uv+=uv
  for j in range(len(points)):struct.pack_into('<3fI2f',b,vp+j*24,*points[j],0xff909090,*uv[j])
  # Both windings allow the plane to remain visible during menu camera moves.
  b[ip:ie]=bytes(ie-ip)
  if not isfloor:struct.pack_into('<24H',b,ip,0,1,2,0,2,3,2,1,0,3,2,0,4,5,6,4,6,7,6,5,4,7,6,4)
  for q in range(mp,me,60):
   struct.pack_into('<I',b,q+12,12 if not isfloor and q in (mp,mp+60) else 0);struct.pack_into('<I',b,q+28,1 if q==mp+60 else 0);struct.pack_into('<I',b,q+52,12 if q==mp+60 else 0)
   struct.pack_into('<3f',b,q,*[min(x[k] for x in points) for k in range(3)]);struct.pack_into('<3f',b,q+16,*[max(x[k] for x in points) for k in range(3)])
  struct.pack_into('<3f',b,hp+32,*[min(x[k] for x in points) for k in range(3)]);struct.pack_into('<3f',b,hp+48,*[max(x[k] for x in points) for k in range(3)])
 assert len(b)==len(original)
 for tag,p,e in v.walk(original):
  if tag==0x80134010:
   leaves={tag:(a,z) for tag,a,z in v.walk(original,p,e) if tag>>28!=8};hp=v.align(leaves[0x134011][0],16);name=original[hp+164:leaves[0x134011][1]].split(b'\0')[0]
   if name.startswith(b'DISC') or name==b'PLATFORMBASE':assert b[p:e]==original[p:e]
 high_resolution_background(b,top)
 b,_=remove_menu_smoke(bytes(b))
 assert next(x for x in t.textures(bytes(b)) if x[0]==0x4d5565d8)[1:3]==(1024,512)
 (out/'Showroom.BIN').write_bytes(b);print('Created two-plane backdrop with 1024x512 background; all platform geometry preserved')
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('source');ap.add_argument('photo');ap.add_argument('output');a=ap.parse_args();build(a.source,a.photo,a.output)

