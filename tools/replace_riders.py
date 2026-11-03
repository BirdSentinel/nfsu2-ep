#!/usr/bin/env python3
"""Replace Riders on the Storm in SDATA/sdat.viv. Requires ffmpeg and lame.

Usage: replace_riders.py original-sdat.viv replacement.mp3 output-sdat.viv
The input archive is never overwritten. All other archive entries and music
streams are preserved byte for byte; only stream offsets and duration change.
"""
import array
import argparse
import pathlib
import struct
import subprocess
import sys

import musicpack as music


def entries(data):
    assert data[:4] in (b'BIG4', b'BIGF'), 'Not an EA BIG archive'
    result, pos = [], 16
    for _ in range(struct.unpack_from('>I', data, 8)[0]):
        offset, size = struct.unpack_from('>II', data, pos)
        end = data.index(0, pos + 8)
        result.append((data[pos + 8:end], data[offset:offset + size]))
        pos = end + 1
    return result


def replace(source, mp3, target, gain_db=0.0, limit_peaks=False, peak_db=-1.0):
    assert source.resolve() != target.resolve(), 'Use a separate output file'
    original = source.read_bytes()
    files = dict(entries(original))
    mus_key, map_key = b'pfdata/MusicSFx.mus', b'pfdata/MusicSFx.mpf'
    data, mapping = files[mus_key], bytearray(files[map_key])
    table, count = music.samples_table(mapping)
    samples = [struct.unpack_from('<II', mapping, table + i * 8) for i in range(count)]
    # PC NFSU2: EA Trax index 0 -> event 0 -> node 0 -> node 2,
    # whose one-based sample ID is 39 (sample table index 38).
    node2 = struct.unpack_from('<h', mapping, 0x20 + 2 * 2)[0] * 4
    assert struct.unpack_from('<H', mapping, node2)[0] == 39
    assert count == 43, 'Unexpected music map'
    index = 38
    start = samples[index][0] * music.ALIGN
    chunks = music.chunks(data, start)
    end = chunks[-1][1] + chunks[-1][2]
    tags = music.header_tags(data[start + 8:start + chunks[0][2]])
    audio_filter = f'volume={gain_db}dB'
    if limit_peaks:
        audio_filter += f',alimiter=limit={10 ** (peak_db / 20):.8f}:level=false:latency=true'
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(mp3), '-af', audio_filter, '-ar', '44100',
                          '-ac', '2', '-f', 's16le', '-'], capture_output=True, check=True).stdout
    pcm = array.array('h', raw)
    assert pcm and min(pcm) > -32768 and max(pcm) < 32767, 'Audio reaches clipping: reduce gain'
    assert sys.byteorder == 'little'
    frames = len(pcm) // 2
    updates = {0x84: (44100).to_bytes(2, 'big'), 0x85: frames.to_bytes(4, 'big')}
    tags = [(t, updates.get(t, v)) for t, v in tags]
    encoded = music.ealayer3_stream(tags, pcm)
    # Replace the complete aligned stream without touching any other stream.
    aligned_end = (end + music.ALIGN - 1) // music.ALIGN * music.ALIGN
    replacement = encoded + bytes(-len(encoded) % music.ALIGN)
    delta = len(replacement) - (aligned_end - start)
    rebuilt = data[:start] + replacement + data[aligned_end:]
    for i, (offset, ms) in enumerate(samples):
        new_offset = offset + (delta // music.ALIGN if offset * music.ALIGN >= aligned_end else 0)
        struct.pack_into('<II', mapping, table + i * 8, new_offset,
                         round(frames * 1000 / 44100) if i == index else ms)
        ch = music.chunks(rebuilt, new_offset * music.ALIGN)
        stream = rebuilt[ch[0][1]:ch[-1][1] + ch[-1][2]]
        old = music.chunks(data, offset * music.ALIGN)
        assert stream == (encoded if i == index else data[old[0][1]:old[-1][1] + old[-1][2]])
    old_gap = samples[-1][0] - samples[-2][0]
    assert struct.unpack_from('<I', mapping, table + (count - 1)*8)[0] - struct.unpack_from('<I', mapping, table + (count - 2)*8)[0] == old_gap
    files[mus_key], files[map_key] = rebuilt, bytes(mapping)
    header_size = 16 + sum(8 + len(name) + 1 for name in files)
    pos = (header_size + 63) // 64 * 64
    directory, body = bytearray(), bytearray(pos - header_size)
    for name, content in files.items():
        directory += struct.pack('>II', pos, len(content)) + name + b'\0'
        body += content
        pad = bytes(-len(content) % 64)
        body += pad
        pos += len(content) + len(pad)
    result = original[:4] + struct.pack('>III', pos, len(files), header_size) + directory + body
    assert len(result) == pos
    assert dict(entries(result)) == files
    target.write_bytes(result)
    print(f'Replaced Riders on the Storm: {frames / 44100:.3f}s, gain {gain_db:+.1f} dB; verified all other streams and archive entries.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=pathlib.Path)
    parser.add_argument('mp3', type=pathlib.Path)
    parser.add_argument('target', type=pathlib.Path)
    parser.add_argument('--gain-db', type=float, default=0.0)
    parser.add_argument('--limit-peaks', action='store_true', help='Limit peaks to -1 dBFS before encoding')
    parser.add_argument('--peak-db', type=float, default=-1.0, help='Limiter ceiling in dBFS')
    args = parser.parse_args()
    replace(args.source, args.mp3, args.target, args.gain_db, args.limit_peaks, args.peak_db)
