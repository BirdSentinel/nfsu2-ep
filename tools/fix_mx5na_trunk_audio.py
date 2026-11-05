"""Add the Miata NB's four trunk-audio layouts and mounts to the separate NA.
Uses shared audio materials; removes only the original shallow boot liner.
"""
import argparse,runpy,struct
from pathlib import Path

def patch(source, donor, destination):
    h=runpy.run_path(str(Path(__file__).with_name('vinyl-models.py')));a=h['align'];nh=h['namehash'];chunks=h['chunks']
    data=source.read_bytes();nb=donor.read_bytes();chunk=lambda t,b:struct.pack('<II',t,len(b))+b
    # Match the two cars' trunk deck centres; preserve the speaker mount shapes.
    shift=(.17,0.,-.048)
    wanted={nh(f'MIATA_KIT{i:02}_TRUNK_AUDIO{suffix}_A'):f'MX5NA_KIT{i:02}_TRUNK_AUDIO{suffix}_A' for i in range(4) for suffix in ['', '_UNLIT']}
    additions={}
    for tag,p,e in chunks(nb,8):
        if tag!=0x80134010:continue
        info=p+8;key=struct.unpack_from('<I',nb,info+16)[0]
        if key not in wanted:continue
        solid=bytearray(nb[p-8:e]);leaves={t:(s,z) for t,s,z in h['walk'](solid,8) if t>>28!=8}
        hp,he=leaves[0x134011];hp=a(hp,16);name=wanted[key];newkey=nh(name)
        struct.pack_into('<I',solid,hp+16,newkey);size=he-hp-164;solid[hp+164:he]=name.encode()[:size-1].ljust(size,b'\0')
        def move(at):
            v=struct.unpack_from('<3f',solid,at);struct.pack_into('<3f',solid,at,*(x+s for x,s in zip(v,shift)))
        vp,ve=leaves[0x134b01]
        for q in range(a(vp,128),ve,36):move(q)
        for q in [hp+32,hp+48]:move(q)
        mp,me=leaves[0x134b02]
        for q in range(a(mp,16),me,60):move(q);move(q+16)
        if 0x13401a in leaves:
            mp,me=leaves[0x13401a]
            for q in range(a(mp,16),me,80):move(q+64)
        additions[newkey]=bytes(solid)
    assert len(additions)==8,'Expected four NB audio layouts and four unlit models'
    solids={};header=None
    for t,p,e in chunks(data,8):
        if t==0x80134001:header=(p,e)
        if t==0x80134010:solids[struct.unpack_from('<I',data,p+24)[0]]=data[p-8:e]
    original=dict(solids)
    # The mod has a shallow, permanently visible boot liner baked into BODY.
    # Remove only its upper bowl; the imported stock/audio layouts supply it.
    bodykey=nh('MX5NA_KIT00_BODY_A');solid=bytearray(solids[bodykey])
    leaves={t:(s,z) for t,s,z in h['walk'](solid,8) if t>>28!=8}
    vp=a(leaves[0x134b01][0],128);ip=a(leaves[0x134b03][0],16)
    mp=a(leaves[0x134b02][0],16)+5*60
    count=struct.unpack_from('<I',solid,mp+12)[0];first=struct.unpack_from('<I',solid,mp+52)[0]
    kept=[];removed=0
    for j in range(0,count,3):
        ids=struct.unpack_from('<3H',solid,ip+(first+j)*2)
        points=[struct.unpack_from('<3f',solid,vp+i*36) for i in ids]
        if all(x < -1.2 and abs(y)<.56 and z>.515 for x,y,z in points):removed+=1
        else:kept.extend(ids)
    struct.pack_into('<I',solid,mp+12,len(kept))
    struct.pack_into('<'+'H'*len(kept),solid,ip+first*2,*kept)
    solids[bodykey]=bytes(solid)
    solids.update(additions);keys=sorted(solids);offsets={k:0 for k in keys}
    for _ in range(2):
        body=bytearray()
        for t,p,e in chunks(data,*header):
            payload=data[p:e]
            if t==0x134002:
                payload=bytearray(payload);struct.pack_into('<I',payload,12,len(keys))
            elif t==0x134003:payload=b''.join(struct.pack('<2I',k,0) for k in keys)
            elif t==0x134004:payload=b''.join(struct.pack('<6I',k,offsets[k],len(solids[k]),len(solids[k]),0,0) for k in keys)
            body+=chunk(t,payload)
        out=bytearray(data[:header[0]-8])+chunk(0x80134001,body)
        for k in keys:
            if len(out)%128:out+=chunk(0,bytes((-(len(out)+8))%128))
            offsets[k]=len(out);out+=solids[k]
        struct.pack_into('<I',out,4,len(out)-8)
    for k,v in original.items():
        if k!=bodykey:assert solids[k]==v
    destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(out)
    assert len(list(h['objects'](destination)))==len(keys)
    print('Added 8 trunk audio solids with NB equipment mounts; removed',removed,'obscuring liner triangles')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['source','donor','destination']:p.add_argument(key,type=Path)
    args=p.parse_args();patch(args.source,args.donor,args.destination)
