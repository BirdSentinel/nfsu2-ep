"""Generate the blue UI border header from original game textures. Usage: build_blue_ui.py GAME_DIR"""
from pathlib import Path
import sys,struct,io,zlib
sys.path.insert(0,'tools')
import texpacks as t
from PIL import Image
wanted={0x0444e6d0,0x8a1c32b8,0xece956c5,0xece97828,0x906f5435,0x906f7598,0x9e61de28}
lines=['/* Generated blue menu border replacements; source keys match original UI only. */'];entries=[]
for rel in ['FRONTEND/FrontB.lzc','GLOBAL/GlobalB.lzc']:
 d=t.jdlz((Path(sys.argv[1])/rel).read_bytes())
 for nh,w,h,f,b in t.textures(d):
  if nh not in wanted:continue
  header=b'DDS '+struct.pack('<7I',124,0x81007,h,w,len(b),0,1)+bytes(44)+struct.pack('<II4s5I',32,4,struct.pack('<I',f),0,0,0,0,0)+struct.pack('<5I',0x1000,0,0,0,0)
  im=Image.open(io.BytesIO(header+b)).convert('RGBA');pixels=[]
  for r,g,bb,a in im.getdata():
   if g>40 and g*.55<=r<=g and bb<g*.8 and g-bb>25:r,bb,g=round(g*24/255),round(g*202/255),round(g*148/255)
   pixels.append((r,g,bb,a))
  im.putdata(pixels);raw=im.tobytes('raw','BGRA');name=f'blue_{nh:08x}'
  lines.append(f'static const uint8_t {name}[] = {{')
  lines.extend(','.join(str(x) for x in raw[i:i+32])+',' for i in range(0,len(raw),32));lines.append('};')
  entries.append(f'{{ {w}, {h}, 0x{f:08x}u, 0x{zlib.crc32(b):08x}u, 0x{zlib.adler32(b):08x}u, {len(b)}, {name} }}')
assert len(entries)==len(wanted)
lines.append('static const struct { unsigned w,h,fmt,crc,adler,bytes; const uint8_t *pixels; } blue_ui[] = {')
lines.append(',\n'.join(entries));lines.append('};')
Path('runtime/web/blue_ui.h').write_text('\n'.join(lines)+'\n')

