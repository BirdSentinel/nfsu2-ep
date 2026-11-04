"""Replace the hilltop sign in place without shifting streaming bundle offsets."""
import argparse
import io
import shutil
import struct
from pathlib import Path

from PIL import Image
import texpacks as t


def replace(data, image):
    result = bytearray(data)
    count = 0
    for b, e in t.tpks(data, 0, len(data)):
        children = {cid: (cb, ce) for cid, cb, ce in t.chunks(data, b, e)}
        if 0xB3310000 not in children or 0xB3320000 not in children:
            continue
        info = {cid: (cb, ce) for cid, cb, ce in t.chunks(data, *children[0xB3310000])}
        if 0x33310004 not in info:
            continue
        tb, te = info[0x33310004]
        for index, q in enumerate(range(tb, te, 124)):
            if data[q+12:q+36].split(b'\0')[0] != b'SGN_BLACKBOXA_DM':
                continue
            pf = info[0x33310005][0] + index * 32
            assert data[pf+20:pf+24] == b'DXT1'
            pixel = next(cb for cid, cb, ce in t.chunks(data, *children[0xB3320000]) if cid == 0x33320002)
            base = (pixel + 127) & ~127
            offset, = struct.unpack_from('<I', data, q+48)
            size, = struct.unpack_from('<I', data, q+56)
            w, h = struct.unpack_from('<HH', data, q+68)
            levels = data[q+78]
            assert 0 < levels <= 12
            chain = bytearray()
            for level in range(levels):
                mip = image.resize((max(1,w >> level), max(1,h >> level)), Image.Resampling.LANCZOS)
                stream = io.BytesIO()
                mip.save(stream, format='DDS', pixel_format='DXT1')
                chain.extend(stream.getvalue()[128:])
            assert len(chain) <= size and base+offset+size <= len(data)
            result[base+offset:base+offset+len(chain)] = chain
            count += 1
    assert len(result) == len(data)
    return bytes(result), count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('game')
    parser.add_argument('png')
    parser.add_argument('--backup')
    args = parser.parse_args()
    image = Image.open(args.png).convert('RGBA')
    total = 0
    for name in ['STREAML4RA.BUN', 'STREAML4RB.BUN', 'STREAML4RD.BUN', 'STREAML4RG.BUN']:
        path = Path(args.game)/'TRACKS'/name
        original = path.read_bytes()
        patched, count = replace(original, image)
        if count != 1:
            raise ValueError(f'{name}: expected one sign, found {count}')
        if args.backup:
            backup = Path(args.backup)/name
            backup.parent.mkdir(parents=True, exist_ok=True)
            if not backup.exists():
                shutil.copy2(path, backup)
        if original != patched:
            path.write_bytes(patched)
        print(f'{name}: {count} sign replaced, file size preserved')
        total += count
    print(f'Updated {total} sign textures including mipmaps.')


if __name__ == '__main__':
    main()
