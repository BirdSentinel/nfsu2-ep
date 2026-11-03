#!/usr/bin/env python3
"""Set the replaced song's three plaque lines in the PC game's EA Trax table.
Usage: rename_riders.py input-SPEED2.EXE output-SPEED2.EXE
"""
import pathlib
import struct
import sys

source, target = map(pathlib.Path, sys.argv[1:])
assert source.resolve() != target.resolve()
data = bytearray(source.read_bytes())
pe = struct.unpack_from('<I', data, 60)[0]
base = struct.unpack_from('<I', data, pe + 24 + 28)[0]
headers = pe + 24 + struct.unpack_from('<H', data, pe + 20)[0]
sections = []
for i in range(struct.unpack_from('<H', data, pe + 6)[0]):
    h = headers + i * 40
    size, rva, rawsize, raw = struct.unpack_from('<IIII', data, h + 8)
    sections.append((h, size, rva, rawsize, raw))

def offset(address):
    for h, size, rva, rawsize, raw in sections:
        if base + rva <= address < base + rva + rawsize:
            return raw + address - base - rva
    raise ValueError(hex(address))

# The game draws the artist first, title second, album third. Preserve the
# user's requested display order, including accents in the game's ANSI text.
lines = ['DJ Clanker (Check Engine Mix)', 'EgyüttParkolás Theme',
         'EgyüttParkolás Game Exclusive']
payload = b''.join(line.encode('cp1252') + b'\0' for line in lines)
h, size, rva, rawsize, raw = next(s for s in sections if data[s[0]:s[0]+8].rstrip(b'\0') == b'.rdata')
assert rawsize - size >= len(payload) and not any(data[raw+size:raw+size+len(payload)])
table = offset(0x7ecd80)
old_title = offset(struct.unpack_from('<I', data, table)[0])
assert b'Riders on the Storm' in data[old_title:data.index(0, old_title)]
data[raw+size:raw+size+len(payload)] = payload
struct.pack_into('<I', data, h+8, size+len(payload))
pos = 0
addresses = []
for i, line in enumerate(lines):
    addresses.append(base+rva+size+pos)
    struct.pack_into('<I', data, table+i*4, addresses[-1])
    pos += len(line.encode('cp1252'))+1
# sub_00468f30 / 00459d90 selects region-specific artist/album pointers
# during startup. Changing only the visible table is overwritten there.
for artist, album in [(0x7ecf30, 0x7ecf34), (0x7ecf38, 0x7ecf3c)]:
    struct.pack_into('<I', data, offset(artist), addresses[1])
    struct.pack_into('<I', data, offset(album), addresses[2])
    # Check the values after simulating either regional startup branch.
    simulated = [addresses[0], struct.unpack_from('<I', data, offset(artist))[0],
                 struct.unpack_from('<I', data, offset(album))[0]]
    assert simulated == addresses
for i, line in enumerate(lines):
    at = offset(struct.unpack_from('<I', data, table+i*4)[0])
    assert data[at:data.index(0, at)].decode('cp1252') == line
target.write_bytes(data)
print('Verified plaque order: ' + ' / '.join([lines[1], lines[0], lines[2]]))
