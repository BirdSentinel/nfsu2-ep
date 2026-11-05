"""Hide only the NA's stock ducktail, retaining the part slot and trunk mesh."""
import argparse
from pathlib import Path
import runpy
import struct


def patch(source, destination):
    h = runpy.run_path(str(Path(__file__).with_name('vinyl-models.py')))
    result = bytearray(source.read_bytes())
    found = 0
    for name, b, leaves, hp in h['objects'](source):
        if struct.unpack_from('<I', b, hp + 16)[0] != h['namehash']('MX5NA_KIT00_SPOILER_A'):
            continue
        # Keep the valid buffers, material bindings and part identity. Empty draw
        # ranges remove the default accessory without changing other spoilers.
        struct.pack_into('<I', result, hp + 20, 0)
        struct.pack_into('<f', result, hp + 152, 0)
        struct.pack_into('<I', result, leaves[0x134900][0] + 36, 0)
        mp, me = leaves[0x134b02]
        for q in range(h['align'](mp, 16), me, 60):
            struct.pack_into('<I', result, q + 12, 0)
            struct.pack_into('<I', result, q + 52, 0)
        found += 1
    assert found == 1, 'Expected exactly one stock NA spoiler'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(result)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('destination', type=Path)
    a = p.parse_args()
    patch(a.source, a.destination)
