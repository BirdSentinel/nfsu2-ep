"""Fit stock and aftermarket NB taillights to the NA's existing apertures, with original optics."""
import argparse, math, runpy, struct
from pathlib import Path

H=runpy.run_path(str(Path(__file__).with_name('vinyl-models.py')))
A=H['align']; NH=H['namehash']; CH=H['chunks']
def chunk(t,b):return struct.pack('<II',t,len(b))+b

def contour(points):
    """Convex lens outline in normalized lateral/vertical coordinates."""
    lo=[min(p[i] for p in points) for i in range(2)]
    hi=[max(p[i] for p in points) for i in range(2)]
    center=[(a+b)/2 for a,b in zip(lo,hi)]
    radius=[(b-a)/2 for a,b in zip(lo,hi)]
    ps=sorted(set(tuple((p[i]-center[i])/radius[i] for i in range(2)) for p in points))
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    halves=[]
    for seq in (ps,ps[::-1]):
        half=[]
        for p in seq:
            while len(half)>1 and cross(half[-2],half[-1],p)<=1e-10:half.pop()
            half.append(p)
        halves+=half[:-1]
    return center,radius,halves

def ray_radius(hull,d):
    # CCW convex polygon: intersect a ray from its interior with each edge.
    result=float('inf')
    for a,b in zip(hull,hull[1:]+hull[:1]):
        ex,ey=b[0]-a[0],b[1]-a[1]
        denominator=ex*d[1]-ey*d[0]
        if denominator < -1e-12:
            result=min(result,(ex*a[1]-ey*a[0])/denominator)
    return result

def geometry(source, donor, destination):
    data=source.read_bytes(); edited=bytearray(data)
    # The mod bakes rear lenses into BODY and their optics into HEADLIGHT_LEFT.
    for name,b,l,hp in H['objects'](source):
        key=struct.unpack_from('<I',b,hp+16)[0]
        groups=([14] if key==NH('MX5NA_KIT00_BODY_A') else
                list(range(5,12)) if key==NH('MX5NA_KIT00_HEADLIGHT_LEFT_A') else [])
        for group in groups:
            q=A(l[0x134b02][0],16)+group*60
            struct.pack_into('<I',edited,q+12,0)
    # Match the original NA lens bounds, independently mirrored on each side.
    source_min=(-2.020, .393, .428);source_max=(-1.792,.731,.600)
    target_min=(-1.860,.3414,.3896);target_max=(-1.662,.6747,.5362)
    scales=tuple((v-u)/(b-a) for a,b,u,v in zip(source_min,source_max,target_min,target_max))
    # Preserve the NA aperture's curved surface, rather than fitting only its
    # box. The NB curves differently: a box fit leaves the NA lip in front.
    def surface(path, name, group, fallback_count=None):
        for n,b,l,hp in H['objects'](path):
            if struct.unpack_from('<I',b,hp+16)[0]!=NH(name):continue
            vp=A(l[0x134b01][0],128);ip=A(l[0x134b03][0],16)
            q=A(l[0x134b02][0],16)+group*60
            count=struct.unpack_from('<I',b,q+12)[0] or fallback_count
            first=struct.unpack_from('<I',b,q+52)[0]
            triangles=[]
            for j in range(0,count,3):
                ids=struct.unpack_from('<3H',b,ip+2*(first+j))
                ps=[struct.unpack_from('<3f',b,vp+36*i) for i in ids]
                if all(v[1]>0 for v in ps):triangles.append(ps)
            return triangles
        raise ValueError(name)
    na_surface=surface(source,'MX5NA_KIT00_BODY_A',14,756)
    nb_surface=surface(donor,'MIATA_KIT00_BRAKELIGHT_A',0)
    def surface_x(triangles,y,z):
        best=(float('inf'),0.)
        for ps in triangles:
            a,b,c=ps
            det=(b[1]-a[1])*(c[2]-a[2])-(c[1]-a[1])*(b[2]-a[2])
            if abs(det)>1e-12:
                u=((y-a[1])*(c[2]-a[2])-(z-a[2])*(c[1]-a[1]))/det
                v=((b[1]-a[1])*(z-a[2])-(b[2]-a[2])*(y-a[1]))/det
                if u>=-1e-6 and v>=-1e-6 and u+v<=1.000001:
                    return a[0]+u*(b[0]-a[0])+v*(c[0]-a[0])
            for a,b in [(a,b),(b,c),(c,a)]:
                dy=b[1]-a[1];dz=b[2]-a[2];length=dy*dy+dz*dz
                t=max(0.,min(1.,((y-a[1])*dy+(z-a[2])*dz)/length)) if length else 0.
                dist=(y-a[1]-t*dy)**2+(z-a[2]-t*dz)**2
                if dist<best[0]:best=(dist,a[0]+t*(b[0]-a[0]))
        return best[1]
    target_center,target_radius,target_hull=contour([(v[1],v[2]) for tri in na_surface for v in tri])
    replacements={}
    nb=donor.read_bytes()
    prefixes=[('KIT00','KIT00')]+[(f'STYLE{i:02}',f'STYLE{15 if i==1 else i:02}') for i in range(1,15)]
    for old_prefix,new_prefix,lod in [(o,n,lod) for o,n in prefixes for lod in 'ABC']:
        key=NH(f'MIATA_{old_prefix}_BRAKELIGHT_{lod}')
        found=next(((p,e) for t,p,e in CH(nb,8) if t==0x80134010 and struct.unpack_from('<I',nb,p+24)[0]==key),None)
        if found is None:
            assert lod!='A', old_prefix
            continue
        p,e=found
        solid=bytearray(nb[p-8:e]);l={t:(p,e) for t,p,e in H['walk'](solid,8) if t>>28!=8}
        hp=A(l[0x134011][0],16);name=f'MX5NA_{new_prefix}_BRAKELIGHT_{lod}';key=NH(name)
        struct.pack_into('<I',solid,hp+16,key)
        end=l[0x134011][1];solid[hp+164:end]=name.encode()[:end-hp-165].ljust(end-hp-164,b'\0')
        vp,ve=l[0x134b01];vp=A(vp,128)
        original=[struct.unpack_from('<3f',solid,q) for q in range(vp,ve,36)]
        center,radius,hull=contour([(abs(v[1]),v[2]) for v in original])
        def point(p):
            d=[(abs(p[1])-center[0])/radius[0],(p[2]-center[1])/radius[1]]
            factor=ray_radius(target_hull,d)/ray_radius(hull,d) if max(map(abs,d))>1e-10 else 1.
            y,z=[target_center[i]+d[i]*factor*target_radius[i] for i in range(2)]
            # Keep the donor's recessed optics, but seat its outline on the NA
            # lens surface. The small outward offset prevents coplanar flicker.
            x=surface_x(na_surface,y,z)+(p[0]-surface_x(nb_surface,abs(p[1]),p[2]))*scales[0]-.002
            return [x,y if p[1]>=0 else -y,z]
        def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
        for q in range(vp,ve,36):
            p0=struct.unpack_from('<3f',solid,q);struct.pack_into('<3f',solid,q,*point(p0))
            jac=[]
            for axis in range(3):
                before=list(p0);after=list(p0);before[axis]-=1e-5;after[axis]+=1e-5
                jac.append([(b-a)/2e-5 for a,b in zip(point(before),point(after))])
            cofactors=[cross(jac[1],jac[2]),cross(jac[2],jac[0]),cross(jac[0],jac[1])]
            old_n=struct.unpack_from('<3f',solid,q+12)
            n=[sum(old_n[j]*cofactors[j][i] for j in range(3)) for i in range(3)];length=math.sqrt(sum(v*v for v in n))
            if length:struct.pack_into('<3f',solid,q+12,*(v/length for v in n))
        points=[struct.unpack_from('<3f',solid,q) for q in range(vp,ve,36)]
        for o,f in [(32,min),(48,max)]:struct.pack_into('<3f',solid,hp+o,*(f(v[i] for v in points) for i in range(3)))
        mp,me=l[0x134b02];ip=A(l[0x134b03][0],16)
        for q in range(A(mp,16),me,60):
            ct=struct.unpack_from('<I',solid,q+12)[0];fi=struct.unpack_from('<I',solid,q+52)[0]
            ids=struct.unpack_from('<'+'H'*ct,solid,ip+fi*2);ps=[points[i] for i in ids]
            for o,f in [(0,min),(16,max)]:struct.pack_into('<3f',solid,q+o,*(f(v[i] for v in ps) for i in range(3)))
        replacements[key]=bytes(solid)
    solids={struct.unpack_from('<I',edited,p+24)[0]:bytes(edited[p-8:e]) for t,p,e in CH(edited,8) if t==0x80134010}
    solids.update(replacements);keys=sorted(solids);offsets={k:0 for k in keys}
    hp,he=next((p,e) for t,p,e in CH(data,8) if t==0x80134001)
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
    destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(out)
    print('Fitted all 15 NB taillight designs at three LODs; removed old NA optics only')

def textures(source, raw_dir, destination, names=None):
    from texpacks import jdlz
    data=source.read_bytes();hp,he=next((p,e) for t,p,e in CH(data,8) if t==0xb3310000)
    p,e=next((p,e) for t,p,e in CH(data,hp,he) if t==0x33310003)
    slots=[list(struct.unpack_from('<6I',data,q)) for q in range(p,e,24)]
    entries={s[0]:(data[s[1]:s[1]+s[2]],s) for s in slots}
    prefixes=[('KIT00','KIT00')]+[(f'STYLE{i:02}',f'STYLE{15 if i==1 else i:02}') for i in range(1,15)]
    default_names=[(f'MIATA_{o}_BRAKELIGHT_{s}',f'MX5NA_{n}_BRAKELIGHT_{s}') for o,n in prefixes for s in ['OFF','GLASS_OFF']]
    # The addon's shadows have inconsistent mip sizes. Use the complete retail
    # Miata shadow chains for both garage and driving, under the NA's own keys.
    if names is None:names=default_names+[(f'MIATA_SHADOW{s}',f'MX5NA_SHADOW{s}') for s in ['FE','IG']]
    for old,name in names:
        key=NH(name)
        raw=bytearray((raw_dir/f'{NH(old):08x}.raw').read_bytes());ti=len(raw)-156
        raw[ti+12:ti+36]=name.encode()[:23].ljust(24,b'\0');struct.pack_into('<I',raw,ti+36,key)
        blob=bytearray(b'JDLZ\x02\x10\0\0'+struct.pack('<II',len(raw),0)+b'\0')
        for i in range(0,len(raw),8):blob+=b'\0'+raw[i:i+8]
        struct.pack_into('<I',blob,12,len(blob));assert jdlz(blob)==raw
        entries[key]=(blob,[key,0,len(blob),len(raw),0x100,0])
    # Compressed records still carry offsets into the shared decompressed
    # image arena. Donor offsets collide with NA images unless rebased.
    image_offset=0
    for key in sorted(entries):
        blob,slot=entries[key];raw=bytearray(jdlz(blob));ti=len(raw)-156
        image_size,palette_size=struct.unpack_from('<2I',raw,ti+0x38)
        image_offset=A(image_offset,128)
        struct.pack_into('<2I',raw,ti+0x30,image_offset,image_offset+image_size)
        image_offset+=image_size+palette_size
        packed=bytearray(b'JDLZ\x02\x10\0\0'+struct.pack('<II',len(raw),0)+b'\0')
        for i in range(0,len(raw),8):packed+=b'\0'+raw[i:i+8]
        struct.pack_into('<I',packed,12,len(packed))
        slot=list(slot);slot[2]=len(packed);slot[3]=len(raw)
        entries[key]=(packed,slot)
    keys=sorted(entries);offsets={k:0 for k in keys}
    for _ in range(2):
        header=bytearray()
        for t,p,e in CH(data,hp,he):
            b=data[p:e]
            if t==0x33310002:b=b''.join(struct.pack('<2I',k,0) for k in keys)
            elif t==0x33310003:b=b''.join(struct.pack('<6I',k,offsets[k],len(entries[k][0]),*entries[k][1][3:]) for k in keys)
            header+=chunk(t,b)
        out=bytearray(data[:hp-8])+chunk(0xb3310000,header)
        if len(out)%128:out+=chunk(0,bytes((-(len(out)+8))%128))
        for k in keys:
            out+=bytes((-len(out))%128)
            offsets[k]=len(out);out+=entries[k][0]
        struct.pack_into('<I',out,4,len(out)-8)
    destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(out)
    print(f'Imported {len(names)} textures; rebased every image range without changing unrelated pixels')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['source','donor','raw_textures','output']:p.add_argument(name,type=Path)
    a=p.parse_args();geometry(a.source/'GEOMETRY.BIN',a.donor/'GEOMETRY.BIN',a.output/'GEOMETRY.BIN')
    textures(a.source/'TEXTURES.BIN',a.raw_textures,a.output/'TEXTURES.BIN')


