"""Build the offline vinyl editor's model catalogue from locally owned game data.
Format references: OpenUG2 docs/FORMATS.md, NFS-ModTools Underground2SolidReader.
No game assets are embedded in this source file.
"""
import argparse, json, math, re, struct
from pathlib import Path

def chunks(b, start=0, end=None):
    end = len(b) if end is None else end
    while start + 8 <= end:
        tag, size = struct.unpack_from('<II', b, start)
        nxt = start + 8 + size
        if nxt > end: raise ValueError('Chunk outside parent')
        yield tag, start+8, nxt
        start = nxt

def walk(b, start=0, end=None, depth=0):
    if depth > 12: raise ValueError('Excessive nesting')
    for tag, p, e in chunks(b, start, end):
        yield tag, p, e
        if tag >> 28 == 8: yield from walk(b, p, e, depth+1)

def align(p, n): return (p+n-1)//n*n
def namehash(s):
    h=0xffffffff
    for c in s.encode('ascii'): h=(h*33+c)&0xffffffff
    return h

def vinyl_surface(texture_hash):
    # Both are game car-skin targets. Preserve their material IDs while
    # allowing the same vinyl projection/UV baking and preview body color.
    return {namehash('CARSKIN'): 1,
            namehash('CARSKIN_CARBONFIBRE'): 2}.get(texture_hash, 0)

def objects(path):
    b = path.read_bytes()
    for tag, p, e in walk(b):
        if tag != 0x80134010: continue
        leaves = {t:(s,z) for t,s,z in walk(b,p,e) if t >> 28 != 8}
        if not all(t in leaves for t in [0x134011,0x134b01,0x134b02,0x134b03,0x134013]): continue
        hp,he = leaves[0x134011]; hp = align(hp,16)
        name = b[hp+164:he].split(b'\0')[0].decode('ascii',errors='replace')
        if not name: continue
        yield name, b, leaves, hp

def extract(path, names_only=False):
    out=[]; selected=[]
    car=path.parent.name
    wanted={namehash(car+'_'+part+'_A'):car+'_'+part+'_A' for part in ['BASE']+['KIT00_'+s for s in ['BODY','DOOR_LEFT','DOOR_RIGHT','FRONT_BUMPER','REAR_BUMPER','SKIRT','HOOD','TRUNK','ROOF']]}
    for name,b,l,hp in objects(path):
        if names_only: print(name); continue
        # Stock, highest detail body panels. Exclude duplicate kits, damage,
        # interior accessories and LOD B/C/D. Roof/base includes glass context.
        key=struct.unpack_from('<I',b,hp+16)[0]
        if key not in wanted: continue
        name=wanted[key]
        vp,ve=l[0x134b01]; vp=align(vp,128)
        ip,ie=l[0x134b03]; ip=align(ip,16)
        mp,me=l[0x134b02]; mp=align(mp,16)
        sp,se=l[0x134013]
        mats=[struct.unpack_from('<I',b,q)[0] for q in range(sp,se-7,8)]
        if (ve-vp)%36 or (me-mp)%60: raise ValueError('Unexpected vertex/material stride: '+name)
        nv=(ve-vp)//36
        # Car panels already share car-space coordinates, as confirmed against
        # their header bounds. The authoring pivot is NOT a world placement:
        # applying ESCALADE_BASE_A's pivot rotates its cabin below the chassis.
        verts=[]
        for q in range(vp,ve,36):
            x,y,z=struct.unpack_from('<3f',b,q); u,v=struct.unpack_from('<2f',b,q+28)
            xyz=[x,y,z]
            verts.append([round(t,6) for t in xyz+[u,v]] if all(math.isfinite(t) and abs(t)<100 for t in xyz+[u,v]) else None)
        for q in range(mp,me,60):
            count=struct.unpack_from('<I',b,q+12)[0]; material=struct.unpack_from('<I',b,q+32)[0]; first=struct.unpack_from('<I',b,q+52)[0]
            if ip+(first+count)*2>ie or count%3 or material>=len(mats): raise ValueError('Invalid material range: '+name)
            skin=vinyl_surface(mats[material])
            indices=struct.unpack_from('<'+'H'*count,b,ip+first*2)
            if any(i>=nv for i in indices): raise ValueError('Invalid index')
            for j in range(0,count,3):
                if all(verts[ix] is not None for ix in indices[j:j+3]): out.append([int(skin)]+[t for ix in indices[j:j+3] for t in verts[ix]])
        selected.append(name)
    if names_only: return
    skin=[v[i:i+3] for v in out if v[0] for i in [1,6,11]]
    if not skin: raise ValueError('No CARSKIN triangles')
    return dict(triangles=out,bounds=[[min(v[k] for v in skin) for k in range(3)],[max(v[k] for v in skin) for k in range(3)]],parts=selected)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('game');ap.add_argument('output');ap.add_argument('--names');args=ap.parse_args()
    if args.names: extract(Path(args.game)/'CARS'/args.names/'GEOMETRY.BIN',True)
    else:
        models={}; failures={}
        for car in sorted((Path(args.game)/'CARS').iterdir()):
            if not (car/'VINYLS.BIN').exists(): continue
            try: models[car.name]=extract(car/'GEOMETRY.BIN')
            except Exception as err: failures[car.name]=str(err)
        dest=Path(args.output);dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text('window.VINYL_MODELS='+json.dumps(models,separators=(',',':'))+';\n',encoding='utf8')
        print(json.dumps({'cars':len(models),'triangles':{k:len(v['triangles']) for k,v in models.items()},'failures':failures},indent=2))
