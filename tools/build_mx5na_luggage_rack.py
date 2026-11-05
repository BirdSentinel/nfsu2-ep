"""Replace only the MX5NA CRIMSON roll-bar mesh with a silver trunk rack.

Preserves the slot's stock interior, all other solids and existing part hashes.
No shared textures or database entries are changed. Dimensions are in metres.
"""
import argparse
import json
import math
from pathlib import Path
import runpy
import struct


def add(a, b): return tuple(x + y for x, y in zip(a, b))
def sub(a, b): return tuple(x - y for x, y in zip(a, b))
def mul(a, s): return tuple(x * s for x in a)
def cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def unit(a): return mul(a, 1 / math.sqrt(sum(x*x for x in a)))
def deck(x): return .720 + .08 * (x + 1.34)


class Mesh:
    def __init__(self): self.vertices, self.indices = [], []

    def vertex(self, p, n):
        self.vertices.append((*p, *n, 0xffffffff, .5, .5))
        return len(self.vertices) - 1

    def tube(self, path, radius=.009, closed=False, sides=10):
        start = len(self.vertices)
        for j, p in enumerate(path):
            before = path[(j-1) % len(path)] if closed or j else p
            after = path[(j+1) % len(path)] if closed or j+1 < len(path) else p
            tangent = unit(sub(after, before))
            axis = (0, 0, 1) if abs(tangent[2]) < .9 else (1, 0, 0)
            u = unit(cross(tangent, axis)); v = cross(tangent, u)
            for k in range(sides):
                a = 2 * math.pi * k / sides
                n = add(mul(u, math.cos(a)), mul(v, math.sin(a)))
                self.vertex(add(p, mul(n, radius)), n)
        for j in range(len(path) if closed else len(path)-1):
            for k in range(sides):
                a = start+j*sides+k; b = start+j*sides+(k+1)%sides
                c = start+((j+1)%len(path))*sides+(k+1)%sides
                d = start+((j+1)%len(path))*sides+k
                self.indices.extend((a,b,c,a,c,d))
        if not closed:
            for j, other in ((0,1),(len(path)-1,len(path)-2)):
                n = unit(sub(path[j], path[other])); center = self.vertex(path[j], n)
                ring = []
                for k in range(sides):
                    ring.append(self.vertex(self.vertices[start+j*sides+k][:3], n))
                for k in range(sides):
                    a,b = ring[k],ring[(k+1)%sides]
                    direction = cross(sub(self.vertices[a][:3], path[j]), sub(self.vertices[b][:3], path[j]))
                    if sum(x*y for x,y in zip(direction,n)) < 0: a,b=b,a
                    self.indices.extend((center,a,b))

    def box(self, low, high):
        p=[(x,y,z) for x in (low[0],high[0]) for y in (low[1],high[1]) for z in (low[2],high[2])]
        for face in ((0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)):
            n=unit(cross(sub(p[face[1]],p[face[0]]),sub(p[face[2]],p[face[0]])))
            a,b,c,d=[self.vertex(p[i],n) for i in face]
            self.indices.extend((a,b,c,a,c,d))


def rack_mesh():
    mesh=Mesh(); xmin,xmax,ymin,ymax,r=-1.78,-1.34,-.43,.43,.045
    path=[]
    for x,y,angle in ((xmax-r,ymax-r,0),(xmin+r,ymax-r,90),(xmin+r,ymin+r,180),(xmax-r,ymin+r,270)):
        for step in range(7):
            a=math.radians(angle+step*15); px=x+r*math.cos(a); py=y+r*math.sin(a)
            path.append((px,py,deck(px)))
    mesh.tube(path,closed=True,sides=12)
    # Five narrow polished load-bearing slats, following the trunk's slope.
    for y in (-.30,-.15,0,.15,.30):
        mesh.tube([(xmin+.012,y,deck(xmin)+.002),(xmax-.012,y,deck(xmax)+.002)],radius=.006,sides=8)
    for x in (-1.65,-1.47):
        mesh.tube([(x,ymin+.01,deck(x)-.008),(x,ymax-.01,deck(x)-.008)],radius=.007,sides=10)
    # Four short mounting feet, resting on the curved deck near the side edges.
    for x,foot_z in ((-1.73,.622),(-1.39,.655)):
        for y in (-.38,.38):
            mesh.box((x-.024,y-.022,foot_z),(x+.024,y+.022,foot_z+.006))
            mesh.tube([(x,y,foot_z+.006),(x,y,deck(x)-.006)],radius=.009,sides=10)
    # Raised stop at the rear of the car (negative X), away from the cabin.
    x=xmin-.001
    mesh.tube([(x,-.37,deck(x)),(x,-.37,deck(x)+.027),(x,-.35,deck(x)+.045),
               (x,.35,deck(x)+.045),(x,.37,deck(x)+.027),(x,.37,deck(x))],radius=.007,sides=10)
    return mesh


def build(source, destination, preview=None):
    h=runpy.run_path(str(Path(__file__).with_name('vinyl-models.py')))
    align, chunks, namehash=h['align'],h['chunks'],h['namehash']
    data=source.read_bytes(); target=namehash('MX5NA_STYLE01_BRAKELIGHT_A')
    rack=rack_mesh(); replacement=None
    def chunk(tag,body): return struct.pack('<II',tag,len(body))+body
    for name,b,l,hp in h['objects'](source):
        if struct.unpack_from('<I',b,hp+16)[0]!=target: continue
        vp,ve=l[0x134b01];vp=align(vp,128)
        ip,ie=l[0x134b03];ip=align(ip,16)
        mp,me=l[0x134b02];mp=align(mp,16)
        assert (me-mp)//60==2
        n,=struct.unpack_from('<I',b,mp+12);first,=struct.unpack_from('<I',b,mp+52)
        # After the tint fix, the shared seats live in BASE instead of here.
        assert n in (0,630) and first==0, 'Unexpected stock interior'
        indices=list(struct.unpack_from('<'+'H'*n,b,ip)); used=sorted(set(indices)); remap={v:i for i,v in enumerate(used)}
        vertices=b''.join(b[vp+i*36:vp+(i+1)*36] for i in used)
        original_indices=[remap[i] for i in indices]
        indices=original_indices+[len(used)+i for i in rack.indices]
        vertices+=b''.join(struct.pack('<6fI2f',*v) for v in rack.vertices)
        assert len(vertices)//36<65536
        triangle_count=len(indices)//3
        info=bytearray(b[hp:l[0x134011][1]])
        struct.pack_into('<I',info,20,triangle_count)
        points=[struct.unpack_from('<3f',vertices,i*36) for i in set(indices)]
        for offset,fn in ((32,min),(48,max)):
            struct.pack_into('<3f',info,offset,*(fn(p[k] for p in points) for k in range(3)))
        struct.pack_into('<f',info,152,float(triangle_count))
        tex=bytearray(b[slice(*l[0x134012])]);shader=bytearray(b[slice(*l[0x134013])])
        # Dedicated silver texture; fixed trim shading is independent of paint.
        # The car loader only preloads known suffixes. DOOR_HANDLE is unused
        # by this conversion, so it can safely carry this independent finish.
        struct.pack_into('<I',tex,8,namehash('MX5NA_DOOR_HANDLE'))
        struct.pack_into('<I',shader,8,namehash('CHROME'))
        mesh_header=bytearray(b[slice(*l[0x134900])]);struct.pack_into('<I',mesh_header,36,triangle_count)
        struct.pack_into('<I',mesh_header,52,len(vertices)//36)
        materials=bytearray(b[mp:me]);struct.pack_into('<I',materials,60+12,len(rack.indices))
        struct.pack_into('<I',materials,60+52,len(original_indices))
        prefix=chunk(0x134011,info)+chunk(0x134012,tex)+chunk(0x134013,shader)
        mesh_start=8+len(prefix)+8
        mesh=bytearray(chunk(0x134900,mesh_header))
        def append_aligned(tag,body,boundary):
            pos=mesh_start+len(mesh)+8
            padding=align(pos,boundary)-pos
            mesh.extend(chunk(tag,b'\x11'*padding+body))
        append_aligned(0x134b01,vertices,128)
        append_aligned(0x134b02,materials,16)
        append_aligned(0x134b03,struct.pack('<'+'H'*len(indices),*indices),16)
        replacement=chunk(0x80134010,prefix+chunk(0x80134100,mesh))
    assert replacement is not None, 'CRIMSON solid not found'
    # Keep solids in the original order and 128-byte aligned. Update only offsets
    # and size fields in the geometry index; all unrelated solid bytes survive.
    out=bytearray(data[:8]);records=[];index_at=None
    for tag,p,e in chunks(data,8,len(data)):
        if tag==0x80134010:
            if len(out)%128:
                out.extend(chunk(0,bytes((-(len(out)+8))%128)))
            key=struct.unpack_from('<I',data,p+8+16)[0]
            solid=replacement if key==target else data[p-8:e]
            records.append((key,len(out),len(solid)));out.extend(solid)
        elif tag!=0 or not records:
            offset=len(out);out.extend(data[p-8:e])
            if tag==0x80134001:
                for subtag,a,z in chunks(data,p,e):
                    if subtag==0x134004:index_at=offset+(a-(p-8))
    assert index_at is not None
    by_hash={key:(off,size) for key,off,size in records}
    for i in range(len(records)):
        at=index_at+i*24;key=struct.unpack_from('<I',out,at)[0];off,size=by_hash[key]
        struct.pack_into('<III',out,at+4,off,size,size)
    struct.pack_into('<I',out,4,len(out)-8)
    old_header=next(p for tag,p,e in chunks(data,8,len(data)) if tag==0x80134001)
    new_header=next(p for tag,p,e in chunks(out,8,len(out)) if tag==0x80134001)
    assert old_header==new_header, 'Header padding/alignment must be preserved'
    # Parse it again to catch padding, bounds and array errors before installation.
    destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(out)
    objects=list(h['objects'](destination));assert len(objects)==len(records)
    if preview:
        preview.write_text(json.dumps({'vertices':rack.vertices,'indices':rack.indices}),encoding='utf8')
    print(f'Rack: {len(rack.vertices)} vertices, {len(rack.indices)//3} triangles; {len(records)} solids preserved')


def build_rack_texture(source, destination):
    """Append a constant silver DXT1 texture, preserving every existing blob."""
    from texpacks import jdlz, bstring_hash
    h=runpy.run_path(str(Path(__file__).with_name('vinyl-models.py')))
    chunks=h['chunks'];data=source.read_bytes()
    # This TPK stores compressed texture blobs directly after its header.
    header=next((p,e) for tag,p,e in chunks(data,8,len(data)) if tag==0xb3310000)
    leaves={tag:(p,e) for tag,p,e in chunks(data,*header)}
    p,e=leaves[0x33310003]
    slots=[list(struct.unpack_from('<6I',data,q)) for q in range(p,e,24)]
    donor=next(s for s in slots if s[0]==bstring_hash('MX5NA_RIM'))
    raw=bytearray(jdlz(data[donor[1]:donor[1]+donor[2]]))
    ti=len(raw)-156;image_size=struct.unpack_from('<I',raw,ti+0x38)[0]
    assert raw[-12:-8]==b'DXT1' and image_size%8==0 and image_size<=ti
    # One uniform DXT1 block at every mip: approximately RGB(222,223,222).
    raw[:image_size]=struct.pack('<HHI',0xdefb,0xc618,0)*(image_size//8)
    name='MX5NA_DOOR_HANDLE';key=bstring_hash(name)
    raw[ti+12:ti+36]=name.encode().ljust(24,b'\0');struct.pack_into('<I',raw,ti+36,key)
    blob=bytearray(b'JDLZ\x02\x10\0\0'+struct.pack('<II',len(raw),0)+b'\0')
    for i in range(0,len(raw),8):blob.extend(b'\0'+raw[i:i+8])
    struct.pack_into('<I',blob,12,len(blob))
    assert jdlz(blob)==bytes(raw)
    entries=[(s[0],data[s[1]:s[1]+s[2]],s) for s in slots if s[0]!=key]
    new_slot=donor.copy();new_slot[0]=key;new_slot[2]=len(blob);new_slot[3]=len(raw)
    entries.append((key,bytes(blob),new_slot));entries.sort(key=lambda x:x[0])
    def chunk(tag,b):return struct.pack('<II',tag,len(b))+b
    prefix=data[8:header[0]-8];offsets=[0]*len(entries)
    for _ in range(2):
        body=bytearray()
        for tag,p,e in chunks(data,*header):
            if tag==0x33310002:b=b''.join(struct.pack('<II',key,0) for key,_,_ in entries)
            elif tag==0x33310003:
                b=b''.join(struct.pack('<6I',key,offsets[i],len(blob),s[3],s[4],s[5]) for i,(key,blob,s) in enumerate(entries))
            else:b=data[p:e]
            body.extend(chunk(tag,b))
        out=bytearray(data[:8]+prefix+chunk(0xb3310000,body))
        if len(out)%128:out.extend(chunk(0,bytes((-(len(out)+8))%128)))
        offsets=[]
        for _,blob,_ in entries:offsets.append(len(out));out.extend(blob)
    struct.pack_into('<I',out,4,len(out)-8)
    destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(out)
    print(f'Silver texture added; {len(slots)} existing compressed textures preserved')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path);p.add_argument('--preview',type=Path)
    p.add_argument('--textures-source',type=Path,required=True);p.add_argument('--textures-output',type=Path,required=True)
    a=p.parse_args()
    if a.source.resolve()==a.output.resolve():p.error('Use a staged output file')
    if a.textures_source.resolve()==a.textures_output.resolve():p.error('Use a staged textures output file')
    build(a.source,a.output,a.preview)
    build_rack_texture(a.textures_source,a.textures_output)
