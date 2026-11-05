"""Add fitted 240SX aftermarket popups, keeping the NA stock pair intact."""
import argparse, math, struct
import numpy as np
from pathlib import Path
from fix_mx5na_nb_taillights import H,A,NH,CH,chunk,contour,textures

def separate_stock_glass(data,objects):
    """Move the baked circular lenses from BODY into the stock popup pair."""
    b,l,hp=objects[NH('MX5NA_KIT00_BODY_A')]
    q=A(l[0x134b02][0],16)+13*60
    count=struct.unpack_from('<I',b,q+12)[0]
    if not count:return data,{} # Already separated: importing again is safe.
    assert count==576
    edited=bytearray(data);struct.pack_into('<I',edited,q+12,0)
    vp=A(l[0x134b01][0],128);ip=A(l[0x134b03][0],16)
    first=struct.unpack_from('<I',b,q+52)[0]
    ids=struct.unpack_from('<576H',b,ip+2*first)
    material=bytes(b[q:q+60]);ti,si=struct.unpack_from('<2I',material,28)
    texture=b[l[0x134012][0]+8*ti:l[0x134012][0]+8*ti+8]
    shader=b[l[0x134013][0]+8*si:l[0x134013][0]+8*si+8]
    replacements={}
    for side,sign in [('LEFT',1),('RIGHT',-1)]:
        chosen=[]
        for i in range(0,len(ids),3):
            tri=ids[i:i+3]
            if all(struct.unpack_from('<f',b,vp+36*j+4)[0]*sign>0 for j in tri):chosen.extend(tri)
        assert len(chosen)==288
        used=sorted(set(chosen));remap={v:i for i,v in enumerate(used)}
        addition=b''.join(b[vp+36*j:vp+36*(j+1)] for j in used)
        key=NH(f'MX5NA_KIT00_HEADLIGHT_{side}_A');d,dl,dh=objects[key]
        dv=A(dl[0x134b01][0],128);di=A(dl[0x134b03][0],16)
        vs=d[dv:dl[0x134b01][1]];nv=len(vs)//36
        indices=list(struct.unpack('<'+'H'*((dl[0x134b03][1]-di)//2),d[di:dl[0x134b03][1]]))
        mat=bytearray(material);struct.pack_into('<I',mat,12,len(chosen));struct.pack_into('<I',mat,52,len(indices))
        indices += [nv+remap[j] for j in chosen];vs+=addition
        tex=bytearray(d[slice(*dl[0x134012])]);sh=bytearray(d[slice(*dl[0x134013])])
        def entry(table,value):
            for i in range(0,len(table),8):
                if table[i:i+8]==value:return i//8
            table.extend(value);return len(table)//8-1
        struct.pack_into('<2I',mat,28,entry(tex,texture),entry(sh,shader))
        mats=d[A(dl[0x134b02][0],16):dl[0x134b02][1]]+mat
        info=bytearray(d[dh:dl[0x134011][1]]);info[25]=len(tex)//8;info[26]=len(sh)//8
        struct.pack_into('<I',info,20,len(indices)//3);struct.pack_into('<f',info,152,len(indices)/3)
        prefix=bytearray(chunk(0x134011,info)+chunk(0x134012,tex)+chunk(0x134013,sh))
        if 0x13401a in dl:
            p,e=dl[0x13401a];pos=8+len(prefix)+8
            prefix+=chunk(0x13401a,b'\x11'*(A(pos,16)-pos)+d[A(p,16):e])
        mh=bytearray(d[A(dl[0x134900][0],16):dl[0x134900][1]]);struct.pack_into('<I',mh,16,len(mats)//60)
        struct.pack_into('<I',mh,36,len(indices)//3);struct.pack_into('<I',mh,52,len(vs)//36)
        ms=8+len(prefix)+8
        mesh=bytearray(chunk(0x134900,b'\x11'*(A(ms+8,16)-(ms+8))+mh))
        for tag,payload,alignment in [(0x134b01,vs,128),(0x134b02,mats,16),(0x134b03,struct.pack('<'+'H'*len(indices),*indices),16)]:
            pos=ms+len(mesh)+8;mesh+=chunk(tag,b'\x11'*(A(pos,alignment)-pos)+payload)
        replacements[key]=chunk(0x80134010,prefix+chunk(0x80134100,mesh))
    return edited,replacements

def finish_lamp(solid,stock,paint_uv,frame):
    """Keep donor topology intact; add an independent dark adapter surround."""
    l={t:(p,e) for t,p,e in H['walk'](solid,8) if t>>28!=8}
    hp=A(l[0x134011][0],16);vp=A(l[0x134b01][0],128);ip=A(l[0x134b03][0],16)
    verts=[list(struct.unpack_from('<6fI2f',solid,q)) for q in range(vp,l[0x134b01][1],36)]
    mats=bytearray(solid[A(l[0x134b02][0],16):l[0x134b02][1]])
    ids=list(struct.unpack_from('<'+'H'*((l[0x134b03][1]-ip)//2),solid,ip))
    tex=bytearray(solid[slice(*l[0x134012])]);shaders=bytearray(solid[slice(*l[0x134013])])
    for q in range(0,len(mats),60):
        count=struct.unpack_from('<I',mats,q+12)[0];first=struct.unpack_from('<I',mats,q+52)[0]
        ti=struct.unpack_from('<I',mats,q+28)[0]
        if struct.unpack_from('<I',tex,8*ti)[0]==NH('MX5NA_SKIN1'):
            for i in set(ids[first:first+count]):verts[i][7:9]=paint_uv
    sb,sl,_=stock
    # Material ordering differs between left/right stock lamps. Select the
    # actual fixed black housing, never the chrome rim at a numeric slot.
    sm=next(q for q in range(A(sl[0x134b02][0],16),sl[0x134b02][1],60)
            if struct.unpack_from('<I',sb,sl[0x134012][0]+8*struct.unpack_from('<I',sb,q+28)[0])[0]==NH('MX5NA_SKIN4')
            and struct.unpack_from('<I',sb,sl[0x134013][0]+8*struct.unpack_from('<I',sb,q+32)[0])[0]==NH('MOLDINGS'))
    mat=bytearray(sb[sm:sm+60]);ti,si=struct.unpack_from('<2I',mat,28)
    def entry(table,value):
        for i in range(0,len(table),8):
            if table[i:i+8]==value:return i//8
        table.extend(value);return len(table)//8-1
    struct.pack_into('<2I',mat,28,entry(tex,sb[sl[0x134012][0]+8*ti:sl[0x134012][0]+8*ti+8]),entry(shaders,sb[sl[0x134013][0]+8*si:sl[0x134013][0]+8*si+8]))
    start=len(ids)
    for triangle in frame:
        a,b,c=map(np.array,triangle);normal=np.cross(b-a,c-a);normal/=np.linalg.norm(normal)
        if normal[2]<0:b,c=c,b;normal=-normal
        for point in [a,b,c]:
            ids.append(len(verts));verts.append([*point,*normal,0xff000000,130.5/512,230.5/512])
    struct.pack_into('<I',mat,12,len(ids)-start);struct.pack_into('<I',mat,52,start)
    for off,fn in [(0,min),(16,max)]:struct.pack_into('<3f',mat,off,*(fn(p[i] for tri in frame for p in tri) for i in range(3)))
    mats+=mat
    info=bytearray(solid[hp:l[0x134011][1]])
    info[25]=len(tex)//8;info[26]=len(shaders)//8
    for off,fn in [(32,min),(48,max)]:
        struct.pack_into('<3f',info,off,*(fn(v[i] for v in verts) for i in range(3)))
    struct.pack_into('<I',info,20,len(ids)//3);struct.pack_into('<f',info,152,len(ids)/3)
    prefix=bytearray(chunk(0x134011,info)+chunk(0x134012,tex)+chunk(0x134013,shaders))
    if 0x13401a in l:
        p,e=l[0x13401a];pos=8+len(prefix)+8
        prefix+=chunk(0x13401a,b'\x11'*(A(pos,16)-pos)+solid[A(p,16):e])
    mh=bytearray(solid[A(l[0x134900][0],16):l[0x134900][1]])
    struct.pack_into('<I',mh,16,len(mats)//60)
    struct.pack_into('<I',mh,36,len(ids)//3);struct.pack_into('<I',mh,52,len(verts))
    ms=8+len(prefix)+8;mesh=bytearray(chunk(0x134900,b'\x11'*(A(ms+8,16)-ms-8)+mh))
    payloads=[(0x134b01,b''.join(struct.pack('<6fI2f',*v) for v in verts),128),(0x134b02,mats,16),(0x134b03,struct.pack('<'+'H'*len(ids),*ids),16)]
    for tag,payload,alignment in payloads:
        pos=ms+len(mesh)+8;mesh+=chunk(tag,b'\x11'*(A(pos,alignment)-pos)+payload)
    return bytearray(chunk(0x80134010,prefix+chunk(0x80134100,mesh)))

def mounting_surface(points,outline=False):
    center,radius,hull=contour([(p[0],abs(p[1])) for p in points])
    if outline:
        hull=sorted([((p[0]-center[0])/radius[0],(p[1]-center[1])/radius[1]) for p in points],key=lambda p:math.atan2(p[1],p[0]))
    boundary=[]
    for u,v in hull:
        x,y=center[0]+u*radius[0],center[1]+v*radius[1]
        boundary.append(min(points,key=lambda p:(p[0]-x)**2+(abs(p[1])-y)**2))
    middle=tuple(sum(p[i] for p in boundary)/len(boundary) for i in range(3))
    def height(x,y):
        best=None
        for b,c in zip(boundary,boundary[1:]+boundary[:1]):
            ax,ay,az=middle;bx,by,bz=b;cx,cy,cz=c
            det=(bx-ax)*(cy-ay)-(cx-ax)*(by-ay)
            u=((x-ax)*(cy-ay)-(y-ay)*(cx-ax))/det
            v=((bx-ax)*(y-ay)-(by-ay)*(x-ax))/det
            penalty=max(0.,-u)+max(0.,-v)+max(0.,u+v-1.)
            z=az+u*(bz-az)+v*(cz-az)
            if best is None or penalty<best[0]:best=(penalty,z)
        return best[1]
    return center,radius,hull,height

def mounting_ray(hull,d):
    hits=[]
    for a,b in zip(hull,hull[1:]+hull[:1]):
        ex,ey=b[0]-a[0],b[1]-a[1]
        det=d[0]*ey-d[1]*ex
        if abs(det)<1e-12:continue
        t=(a[0]*ey-a[1]*ex)/det
        u=(a[0]*d[1]-a[1]*d[0])/det
        if t>0 and -1e-8<=u<=1.00000001:hits.append(t)
    return min(hits)

# Measured painted aperture edge on the NA BODY mesh, from rear to front.
# The old stock popup's bottom tray sits below this edge and is not a seat.
NA_APERTURE=[(1.4469,.6417,.5112),(1.4518,.5934,.5175),
 (1.4565,.5442,.5206),(1.4598,.4859,.5207),(1.4637,.4191,.5201),
 (1.4682,.4003,.5194),(1.476,.387,.5178),(1.4868,.3797,.5156),
 (1.5006,.3769,.5128),(1.5616,.3767,.4959),(1.6257,.3779,.4757),
 (1.6899,.3789,.4528),(1.7244,.5365,.426),(1.7042,.6138,.4234),
 (1.6532,.618,.4461),(1.5953,.6264,.4687),(1.5335,.6339,.4886)]

def geometry(source,donor,destination):
    data=source.read_bytes();nb=donor.read_bytes()
    originals={struct.unpack_from('<I',b,hp+16)[0]:(b,l,hp) for _,b,l,hp in H['objects'](source)}
    donors={struct.unpack_from('<I',b,hp+16)[0]:(b,l,hp) for _,b,l,hp in H['objects'](donor)}
    def vertices(obj,active=False,material_limit=None):
        b,l,hp=obj;vp=A(l[0x134b01][0],128)
        if active:
            ids=set();ip=A(l[0x134b03][0],16)
            start=A(l[0x134b02][0],16)
            end=min(l[0x134b02][1],start+60*material_limit) if material_limit else l[0x134b02][1]
            for q in range(start,end,60):
                ct=struct.unpack_from('<I',b,q+12)[0];fi=struct.unpack_from('<I',b,q+52)[0]
                ids.update(struct.unpack_from('<'+'H'*ct,b,ip+2*fi))
            return [struct.unpack_from('<3f',b,vp+36*i) for i in ids]
        return [struct.unpack_from('<3f',b,q) for q in range(vp,l[0x134b01][1],36)]
    edited,replacements=separate_stock_glass(data,originals)
    for side in ['LEFT','RIGHT']:
        # The flat donor lamp's first two materials outline its mounting
        # aperture. Fit that seat to the NA body edge, not whole-popup bounds.
        reference_obj=donors[NH(f'240SX_STYLE01_HEADLIGHT_{side}_A')]
        reference=vertices(reference_obj,True,2)
        reference=[(p[0],abs(p[1]),p[2]) for p in reference]
        # A similarity transform preserves every angle and length ratio.
        sc,sr,sh,_=mounting_surface(reference)
        boundary=[min(reference,key=lambda p:(p[0]-sc[0]-u*sr[0])**2+(p[1]-sc[1]-v*sr[1])**2) for u,v in sh]
        def plane(points):
            p=np.array(points);return np.linalg.lstsq(np.column_stack([p[:,:2],np.ones(len(p))]),p[:,2],rcond=None)[0]
        source_plane=plane(boundary);target_plane=plane(NA_APERTURE)
        def basis(plane):
            forward=np.array([1.,0.,plane[0]]);forward/=np.linalg.norm(forward)
            up=np.array([-plane[0],-plane[1],1.]);up/=np.linalg.norm(up)
            return np.column_stack([forward,np.cross(up,forward),up])
        rotation=basis(target_plane)@basis(source_plane).T
        tc,tr,th,target_height=mounting_surface(NA_APERTURE,outline=True)
        origin=np.array([*sc,np.dot(source_plane,[*sc,1.])])
        target=np.array([*tc,np.dot(target_plane,[*tc,1.])])
        scale=.90
        def point(p):
            v=target+scale*(rotation@(np.array([p[0],abs(p[1]),p[2]])-origin))
            if side=='RIGHT':v[1]=-v[1]
            return v.tolist()
        transformed=[point(p) for p in boundary]
        ic,ir,ih,inner_height=mounting_surface([(p[0],abs(p[1]),p[2]) for p in transformed])
        # Only the adapter follows the NA contour. The optical mesh is rigid.
        rings=[]
        for i in range(96):
            angle=2*math.pi*i/96;d=[math.cos(angle),math.sin(angle)]
            ot=mounting_ray(th,[d[j]/tr[j] for j in range(2)])
            it=mounting_ray(ih,[d[j]/ir[j] for j in range(2)])
            outer=[tc[j]+d[j]*ot for j in range(2)]
            inner=[ic[j]+d[j]*it*.985 for j in range(2)]
            # Meet the real donor perimeter, not its approximate mounting
            # plane; the latter leaves a visible step under curved rims.
            pair=[[outer[0],outer[1],target_height(*outer)-.0005],[inner[0],inner[1],inner_height(*inner)-.0005]]
            if side=='RIGHT':
                for p in pair:p[1]=-p[1]
            rings.append(pair)
        frame=[]
        for (a,b),(c,d) in zip(rings,rings[1:]+rings[:1]):frame.extend([(a,b,c),(b,d,c)])
        for style in range(1,15):
            for lod in 'ABC':
                old=f'240SX_STYLE{style:02}_HEADLIGHT_{side}_{lod}'
                key=NH(old)
                if key not in donors:key=next(NH(old[:-1]+fallback) for fallback in 'CBA' if NH(old[:-1]+fallback) in donors)
                b,l0,hp0=donors[key]
                start,end=next((p-8,e) for t,p,e in CH(nb,8) if t==0x80134010 and struct.unpack_from('<I',nb,p+24)[0]==key)
                solid=bytearray(nb[start:end]);l={t:(p,e) for t,p,e in H['walk'](solid,8) if t>>28!=8}
                hp=A(l[0x134011][0],16);name=old.replace('240SX','MX5NA');newkey=NH(name)
                struct.pack_into('<I',solid,hp+16,newkey)
                end=l[0x134011][1];solid[hp+164:end]=name.encode()[:end-hp-165].ljust(end-hp-164,b'\0')
                # The paintable cover uses the NA's generated car skin. Optical
                # texture aliases are shared by the engine and stay unchanged.
                for q in range(*l[0x134012],8):
                    if struct.unpack_from('<I',solid,q)[0]==NH('240SX_SKIN1'):struct.pack_into('<I',solid,q,NH('MX5NA_SKIN1'))
                # Sample the intact stock lid's paint area, not the donor
                # atlas region (which is transparent on the NA skin).
                stock,sl,sp=originals[NH(f'MX5NA_KIT00_HEADLIGHT_{side}_A')]
                sq=A(sl[0x134b02][0],16);sv=A(sl[0x134b01][0],128);si=A(sl[0x134b03][0],16)
                count=struct.unpack_from('<I',stock,sq+12)[0];first=struct.unpack_from('<I',stock,sq+52)[0]
                samples=[struct.unpack_from('<2f',stock,sv+36*j+28) for j in set(struct.unpack_from('<'+'H'*count,stock,si+2*first))]
                paint_uv=[sum(v[i] for v in samples)/len(samples) for i in range(2)]
                l={t:(p,e) for t,p,e in H['walk'](solid,8) if t>>28!=8};hp=A(l[0x134011][0],16)
                vp=A(l[0x134b01][0],128);ve=l[0x134b01][1]
                for q in range(vp,ve,36):
                    p=struct.unpack_from('<3f',solid,q);n=struct.unpack_from('<3f',solid,q+12)
                    struct.pack_into('<3f',solid,q,*point(p))
                    # Mirror into the reference side, rotate, then mirror back.
                    sign=1 if side=='LEFT' else -1
                    normal=rotation@np.array([n[0],sign*n[1],n[2]])
                    normal[1]*=sign
                    struct.pack_into('<3f',solid,q+12,*normal)
                ps=[struct.unpack_from('<3f',solid,q) for q in range(vp,ve,36)]
                for off,fn in [(32,min),(48,max)]:struct.pack_into('<3f',solid,hp+off,*(fn(p[i] for p in ps) for i in range(3)))
                ip=A(l[0x134b03][0],16)
                for q in range(A(l[0x134b02][0],16),l[0x134b02][1],60):
                    ct=struct.unpack_from('<I',solid,q+12)[0];fi=struct.unpack_from('<I',solid,q+52)[0]
                    pts=[ps[i] for i in struct.unpack_from('<'+'H'*ct,solid,ip+2*fi)]
                    for off,fn in [(0,min),(16,max)]:struct.pack_into('<3f',solid,q+off,*(fn(p[i] for p in pts) for i in range(3)))
                if 0x13401a in l:
                    for q in range(A(l[0x13401a][0],16),l[0x13401a][1],80):struct.pack_into('<3f',solid,q+64,*point(struct.unpack_from('<3f',solid,q+64)))
                replacements[newkey]=finish_lamp(solid,originals[NH(f'MX5NA_KIT00_HEADLIGHT_{side}_A')],paint_uv,frame)
    solids={struct.unpack_from('<I',edited,p+24)[0]:edited[p-8:e] for t,p,e in CH(edited,8) if t==0x80134010}
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
    print('Added 84 fitted 240SX lamp meshes; stock NA optics isolated; unrelated NA solids preserved')

def optics(source,raw,destination):
    names=[(f'240SX_STYLE{i:02}_HEADLIGHT_{s}',f'MX5NA_STYLE{i:02}_HEADLIGHT_{s}') for i in range(1,15) for s in ['OFF','GLASS_OFF']]
    names=[(old,new) for old,new in names if (raw/f'{NH(old):08x}.raw').exists()]
    assert len(names)==26, 'Expected all donor optics (styles 10/11 have no separate glass)'
    textures(source,raw,destination,names)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['source','donor','raw','output']:p.add_argument(n,type=Path)
    a=p.parse_args();geometry(a.source/'GEOMETRY.BIN',a.donor/'GEOMETRY.BIN',a.output/'GEOMETRY.BIN');optics(a.source/'TEXTURES.BIN',a.raw,a.output/'TEXTURES.BIN')
