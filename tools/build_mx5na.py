"""Build the user's replacement Miata as a separate MX5NA pack in a staging dir.

Requires pauliquib/nfsu2-addcars (tools + built u2tool/Binarius) and Pillow.
Never writes to the supplied game or mod directory. The runtime extension in
regional.c is deliberately limited to this one extra, index 46 car.
"""
import argparse
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys


def chunks(data):
    off = 0
    while off + 8 <= len(data):
        kind, size = struct.unpack_from('<II', data, off)
        body = data[off + 8:off + 8 + size]
        if len(body) != size:
            raise ValueError('Truncated game chunk')
        yield kind, body
        if kind & 0x80000000:
            yield from chunks(body)
        off += size + 8


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('game', 'mod', 'converter', 'dotnet', 'output'):
        p.add_argument('--' + name, required=True, type=Path)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    if any(a.output.resolve() == x.resolve() for x in (a.game, a.mod)):
        raise ValueError('Output must be an isolated staging directory')
    sys.path.insert(0, str(a.converter / 'tools'))
    import u2geo, u2tpk, u2car, batch
    import texpacks
    from PIL import Image, ImageDraw, ImageFont
    out = a.output / 'MX5NA'
    out.mkdir(exist_ok=True)
    keys = u2geo.load_keys(str(a.converter / 'bin/mainkeys/underground2.txt'))
    texmap = u2tpk.auto_rename(str(a.mod / 'MIATA/TEXTURES.BIN'),
                             str(out / 'TEXTURES.BIN'), 'MIATA', 'MX5NA', keys)
    objects = u2geo.rename(str(a.mod / 'MIATA/GEOMETRY.BIN'), str(out / 'GEOMETRY.BIN'),
                           'MIATA', 'MX5NA', None, keys=keys, texmap=texmap)
    from fix_mx5na_lamp_housings import patch as fix_lamp_housings
    fix_lamp_housings(out / 'GEOMETRY.BIN', out / 'GEOMETRY.BIN')
    from build_mx5na_luggage_rack import build as build_luggage_rack, build_rack_texture
    build_luggage_rack(out / 'GEOMETRY.BIN', out / 'GEOMETRY.BIN')
    build_rack_texture(out / 'TEXTURES.BIN', out / 'TEXTURES.BIN')
    from remove_mx5na_stock_spoiler import patch as remove_stock_spoiler
    remove_stock_spoiler(out / 'GEOMETRY.BIN', out / 'GEOMETRY.BIN')
    from fix_mx5na_roof_scoop import patch as fix_roof_scoop
    fix_roof_scoop(out / 'GEOMETRY.BIN', a.game / 'CARS/MIATA/GEOMETRY.BIN', out / 'GEOMETRY.BIN')
    from fix_mx5na_window_tint import patch as fix_window_tint
    fix_window_tint(out / 'GEOMETRY.BIN', out / 'GEOMETRY.BIN')
    from move_mx5na_rack_to_spoiler import patch as move_rack
    move_rack(out / 'GEOMETRY.BIN', out / 'GEOMETRY.BIN')
    from fix_mx5na_trunk_audio import patch as fix_trunk_audio
    fix_trunk_audio(out / 'GEOMETRY.BIN', a.game / 'CARS/MIATA/GEOMETRY.BIN', out / 'GEOMETRY.BIN')
    from fix_mx5na_audio_clearance import patch as fit_audio_clearance
    fit_audio_clearance(out / 'GEOMETRY.BIN', out / 'GEOMETRY.BIN')
    # Decode the original NB's HUFF/JDLZ optical textures with Binarius' codec.
    helper = a.output / 'texture-helper'
    helper_project = Path(__file__).with_name('car-textures') / 'car-textures.csproj'
    subprocess.run([str(a.dotnet), 'build', str(helper_project), '--configfile',
                    str(helper_project.with_name('NuGet.Config')), '-o', str(helper),
                    '--nologo', '-v:q'], check=True)
    raw_textures = a.output / 'nb-light-textures'
    subprocess.run([str(a.dotnet), str(helper / 'car-textures.dll'),
                    str(a.game / 'CARS/MIATA/TEXTURES.BIN'), str(raw_textures),
                    str(a.converter / 'bin')], check=True)
    from fix_mx5na_nb_taillights import geometry as fit_nb_tails, textures as nb_tail_textures
    fit_nb_tails(out / 'GEOMETRY.BIN', a.game / 'CARS/MIATA/GEOMETRY.BIN', out / 'GEOMETRY.BIN')
    nb_tail_textures(out / 'TEXTURES.BIN', raw_textures, out / 'TEXTURES.BIN')
    raw_popups = a.output / '240sx-light-textures'
    subprocess.run([str(a.dotnet), str(helper / 'car-textures.dll'),
                    str(a.game / 'CARS/240SX/TEXTURES.BIN'), str(raw_popups),
                    str(a.converter / 'bin')], check=True)
    from fit_mx5na_240sx_headlights import geometry as fit_popups, optics as popup_textures
    fit_popups(out / 'GEOMETRY.BIN', a.game / 'CARS/240SX/GEOMETRY.BIN', out / 'GEOMETRY.BIN')
    popup_textures(out / 'TEXTURES.BIN', raw_popups, out / 'TEXTURES.BIN')
    from fix_mx5na_doors import patch as split_doors, animations as fit_door_animations
    split_doors(out / 'GEOMETRY.BIN', a.game / 'CARS/MIATA/GEOMETRY.BIN', out / 'GEOMETRY.BIN')
    from fix_mx5na_engine import geometry as fit_engine, animations as fit_hood_hinges, NAMES as engine_models, TEXTURES as engine_textures
    fit_engine(out / 'GEOMETRY.BIN', a.game / 'CARS/MIATA/GEOMETRY.BIN', out / 'GEOMETRY.BIN')
    from fix_mx5na_license_plate import geometry as fit_license_plate
    fit_license_plate(out / 'GEOMETRY.BIN', a.game / 'CARS/PLATES/GEOMETRY.BIN', out / 'GEOMETRY.BIN')
    from fix_mx5na_decals import patch as fit_decals, NAMES as decal_models
    fit_decals(out / 'GEOMETRY.BIN', a.game / 'CARS/MIATA/GEOMETRY.BIN', out / 'GEOMETRY.BIN')
    objects += ['MX5NA_DECAL_' + name + '_A' for name in decal_models]
    nb_tail_textures(out / 'TEXTURES.BIN', raw_textures, out / 'TEXTURES.BIN', engine_textures)
    objects += ['MX5NA_' + name for name in engine_models]
    objects += [f'MX5NA_KIT00_DOOR_{side}_{lod}' for side in ('LEFT', 'RIGHT') for lod in 'ABC']
    objects += [f'MX5NA_KIT00_DOOR_{kind}_{side}_A' for side in ('LEFT', 'RIGHT') for kind in ('PANEL', 'SILL')]
    objects += [f'MX5NA_STYLE{i:02}_BRAKELIGHT_A' for i in range(2,16)]
    (out / 'objects.txt').write_text('\n'.join(objects), encoding='utf-8')
    (out / 'cti.bin').write_bytes(u2car.decode(str(next(a.mod.glob('*.u2car')))))
    batch.rename_anim(str(a.game / 'CARS/MIATA/PARTS_ANIMATIONS.bin'),
                      str(out / 'PARTS_ANIMATIONS.bin'), 'MIATA', 'MX5NA')
    fit_door_animations(out / 'PARTS_ANIMATIONS.bin', out / 'PARTS_ANIMATIONS.bin')
    fit_hood_hinges(out / 'PARTS_ANIMATIONS.bin', out / 'PARTS_ANIMATIONS.bin')
    logo = Image.new('RGBA', (256, 64))
    ImageDraw.Draw(logo).text((128, 32), 'MX-5 NA', fill='white', anchor='mm',
                             font=ImageFont.truetype('C:/Windows/Fonts/arialbi.ttf', 44))
    logo.save(out / 'SECONDARY_LOGO_MX5NA.dds')
    files = ['GLOBAL\\GLOBALB.LZC', 'FRONTEND\\FRONTB.LZC', 'LANGUAGES\\ENGLISH.BIN']
    for rel in files:
        dst = a.output / 'game' / Path(rel.replace('\\', '/'))
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            dst.chmod(0o666)
        shutil.copy2(a.game / Path(rel.replace('\\', '/')), dst)
        dst.chmod(0o666)
    launcher = a.output / 'import.endlauncher'
    # Endscript's launcher parser expects literal Windows separators rather
    # than JSON-escaped backslashes (matching its own query.endlauncher).
    launcher.write_text(json.dumps(dict(Usage='Modder', Game='Underground2', Directory='',
                                        Endscript='', Files=files, Links=[])).replace('\\\\', '\\'), encoding='utf-8')
    script = a.output / 'install.u2s'
    script.write_text('''copy_collection GLOBAL\\GLOBALB.LZC CarTypeInfos MIATA MX5NA
cti_import GLOBAL\\GLOBALB.LZC MX5NA MX5NA/cti.bin
update_collection GLOBAL\\GLOBALB.LZC CarTypeInfos MX5NA ManufacturerName MAZDA
copy_collection GLOBAL\\GLOBALB.LZC DBModelParts MIATA MX5NA
parts_replace GLOBAL\\GLOBALB.LZC MX5NA ^MIATA(?=_|$) MX5NA
parts_prune GLOBAL\\GLOBALB.LZC MX5NA MX5NA/objects.txt
add_or_replace_texture FRONTEND\\FRONTB.LZC TPKBlocks FRONTENDTEXTURES SECONDARY_LOGO_MX5NA SECONDARY_LOGO_MX5NA "MX5NA/SECONDARY_LOGO_MX5NA.dds"
add_string LANGUAGES\\ENGLISH.BIN STRBlocks GLOBAL AUTO CAR_NAME_MX5NA "Mazda MX-5 NA (1994)"
''', encoding='utf-8')
    subprocess.run([str(a.dotnet), str(a.converter / 'bin/u2tool.dll'), 'apply',
                    str(launcher), str(a.output / 'game'), str(script)], check=True)
    source = (a.game / 'GLOBAL/GLOBALB.LZC').read_bytes()
    if source[:4] == b'JDLZ':
        source = texpacks.jdlz(source)
    target = a.output / 'game/GLOBAL/GLOBALB.LZC'
    data = target.read_bytes()
    before, after = dict(chunks(source)), dict(chunks(data))
    old, new = before[0x34600], after[0x34600]
    assert len(old) == 46 * 0x890 + 8 and len(new) == 47 * 0x890 + 8
    assert new[len(old):len(old) + 6] == b'MX5NA\0'
    # Binarius rounds floats on reassembly: retain every original CarTypeInfo.
    assert data.count(new) == 1
    replacements = {0x34600: old + new[len(old):], 0x34601: after[0x34601],
                    0x80034602: after[0x80034602]}
    # Binarius also rewrites unrelated career/unlock chunks. Keep those exact:
    # only transplant the three car chunks into the original top-level stream.
    merged = bytearray()
    pos = 0
    while pos + 8 <= len(source):
        kind, size = struct.unpack_from('<II', source, pos)
        body = replacements.get(kind, source[pos + 8:pos + 8 + size])
        assert (len(body) - size) % 16 == 0, 'Would disturb aligned following chunks'
        merged += struct.pack('<II', kind, len(body)) + body
        pos += size + 8
    assert pos == len(source)
    target.write_bytes(merged)
    # Saved cars refer to part indices. Names/type/group at each existing index
    # must survive unchanged, even when the rebuilt attribute offsets differ.
    oldparts, newparts = before[0x34604], after[0x34604]
    for i in range(0, len(oldparts) - 13, 14):
        assert oldparts[i:i + 8] == newparts[i:i + 8], f'Part index changed: {i // 14}'
    from restore_mx5na_tail_parts import patch as restore_tail_parts
    restore_tail_parts(target, target, a.converter, a.dotnet, a.output / 'tail-parts')
    print('Verified: 46 original car records and existing part indices preserved.')


if __name__ == '__main__':
    main()
