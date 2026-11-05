"""Keep the NB trunk-audio shell inside the NA rear panel and lamp recesses."""
import argparse,runpy,struct,math
from pathlib import Path

def patch(source,destination):
    h=runpy.run_path(str(Path(__file__).with_name('vinyl-models.py')));a=h['align'];data=bytearray(source.read_bytes())
    wanted={h['namehash'](f'MX5NA_KIT{i:02}_TRUNK_AUDIO{s}_A') for i in range(4) for s in ['', '_UNLIT']}
    original_rear=False
    for name,b,l,hp in h['objects'](source):
        if struct.unpack_from('<I',b,hp+16)[0] in wanted:
            vp=a(l[0x134b01][0],128)
            original_rear |= any(struct.unpack_from('<f',b,q)[0]<-1.78 for q in range(vp,l[0x134b01][1],36))
    if not original_rear:
        destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(data)
        print('Trunk-audio rear shell already inside the NA envelope')
        return
    count=0
    # The imported NB shell's rear return reaches x=-1.834, inside the NA
    # lamp apertures. Compress its rear 14 cm into the boot's inner envelope.
    # Keep the outer BODY/TRUNK surfaces and all audio topology untouched.
    def x_inside(x):return -1.70+(x+1.70)*.40 if x < -1.70 else x
    for name,b,l,hp in h['objects'](source):
        if struct.unpack_from('<I',b,hp+16)[0] not in wanted:continue
        vp=a(l[0x134b01][0],128);ve=l[0x134b01][1];points=[]
        for q in range(vp,ve,36):
            x,y,z=struct.unpack_from('<3f',b,q);points.append((x_inside(x),y,z))
            if x < -1.70:
                struct.pack_into('<f',data,q,x_inside(x));count+=1
                nx,ny,nz=struct.unpack_from('<3f',b,q+12);nx/=.40
                length=math.sqrt(nx*nx+ny*ny+nz*nz)
                if length:struct.pack_into('<3f',data,q+12,nx/length,ny/length,nz/length)
        for offset,fn in [(32,min),(48,max)]:struct.pack_into('<3f',data,hp+offset,*(fn(p[i] for p in points) for i in range(3)))
        ip=a(l[0x134b03][0],16)
        for q in range(a(l[0x134b02][0],16),l[0x134b02][1],60):
            ct=struct.unpack_from('<I',b,q+12)[0];fi=struct.unpack_from('<I',b,q+52)[0]
            if not ct:continue
            ids=struct.unpack_from('<'+'H'*ct,b,ip+2*fi);ps=[points[i] for i in ids]
            for offset,fn in [(0,min),(16,max)]:struct.pack_into('<3f',data,q+offset,*(fn(p[i] for p in ps) for i in range(3)))
        if 0x13401a in l:
            p,e=l[0x13401a]
            for q in range(a(p,16),e,80):
                x=struct.unpack_from('<f',b,q+64)[0];struct.pack_into('<f',data,q+64,x_inside(x))
    destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(data)
    print('Fitted rear trunk-audio shell vertices:',count)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('destination',type=Path)
    args=p.parse_args();patch(args.source,args.destination)
