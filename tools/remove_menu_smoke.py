"""Disable only the showroom's named smoke instance, leaving shared effects intact."""
import argparse
import struct
from pathlib import Path
from texpacks import chunks


def remove_menu_smoke(data):
    result = bytearray(data)
    changed = 0
    for tag, start, end in chunks(data, 0, len(data)):
        # This 224-byte aligned instance contains one named effect and its
        # placement matrix. Do not remove its shared emitter definition/texture.
        aligned = (start + 15) // 16 * 16
        if tag == 0x35020 and end - aligned == 224:
            name = data[aligned + 160:aligned + 224].split(b'\0')[0]
            if name == b'XEFE_Showroom_SmokeA_01':
                struct.pack_into('<I', result, start - 8, 0)  # ignored padding chunk
                changed += 1
    return bytes(result), changed


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('output')
    args = parser.parse_args()
    original = Path(args.source).read_bytes()
    result, count = remove_menu_smoke(original)
    if count != 1:
        raise SystemExit(f'Expected exactly one showroom smoke instance, found {count}')
    assert len(result) == len(original)
    Path(args.output).write_bytes(result)
    print('Disabled only XEFE_Showroom_SmokeA_01; all other bytes preserved')
