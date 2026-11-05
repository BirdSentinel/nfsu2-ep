"""Append NB rear and 240SX front lamp choices, preserving existing indices."""
import argparse, json, os, shutil, struct, subprocess
from pathlib import Path
from texpacks import jdlz

def chunks(data):
    pos=0
    while pos+8<=len(data):
        tag,size=struct.unpack_from('<II',data,pos)
        yield tag,data[pos:pos+8+size]
        pos+=8+size
    assert pos==len(data)

def records(data):
    for tag,blob in chunks(data):
        if tag==0x34604:return blob[8:]
        if tag&0x80000000:
            found=records(blob[8:])
            if found is not None:return found

def merge(original, rebuilt):
    old=jdlz(original) if original[:4]==b'JDLZ' else original
    new=jdlz(rebuilt) if rebuilt[:4]==b'JDLZ' else rebuilt
    before=records(old);after=records(new)
    assert len(after)>=len(before)
    for i in range(0,len(before)-13,14):
        assert before[i:i+8]==after[i:i+8],f'Existing part index changed: {i//14}'
    replacement=next(b for t,b in chunks(new) if t==0x80034602)
    previous=next(b for t,b in chunks(old) if t==0x80034602)
    assert (len(replacement)-len(previous))%16==0
    return b''.join(replacement if t==0x80034602 else b for t,b in chunks(old))

def patch(source, destination, converter, dotnet, staging):
    source=source.resolve();destination=destination.resolve();staging=staging.resolve()
    converter=converter.resolve();dotnet=dotnet.resolve()
    project=Path(__file__).with_name('car-parts').resolve()/'car-parts.csproj'
    helper=staging/'helper';game=staging/'game';target=game/'GLOBAL/GLOBALB.LZC'
    target.parent.mkdir(parents=True,exist_ok=True)
    original=source.read_bytes();target.write_bytes(original)
    launcher=staging/'parts.endlauncher'
    launcher.write_text(json.dumps(dict(Usage='Modder',Game='Underground2',Directory='',
        Endscript='',Files=['GLOBAL\\GLOBALB.LZC'],Links=[])).replace('\\\\','\\'))
    subprocess.run([str(dotnet),'build',str(project),'--configfile',str(project.with_name('NuGet.Config')),
        '-p:BinariusDirectory='+str(converter/'bin'),'-o',str(helper),'--nologo','-v:q'],check=True)
    subprocess.run([str(dotnet),str(helper/'car-parts.dll'),str(launcher),str(game),str(converter/'bin')],check=True)
    destination.write_bytes(merge(original,target.read_bytes()))
    print('Existing save indices and all non-part database chunks preserved')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['source','destination','converter','dotnet','staging']:p.add_argument(n,type=Path)
    a=p.parse_args();patch(a.source,a.destination,a.converter,a.dotnet,a.staging)
