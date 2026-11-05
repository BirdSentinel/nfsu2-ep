"""Build a separate NA vinyl pack from the NB donor, without touching the NB.

Uses the same built nfsu2-addcars/u2tool dependency as build_mx5na.py.
The output directory must be an isolated staging directory.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import os

from mx5na_vinyl_map import make_map


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('game', 'converter', 'dotnet', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    game, out = a.game.resolve(), a.output.resolve()
    if out == game or game in out.parents:
        raise ValueError('Use a staging directory outside the game directory')
    archive = out / 'CARS/MX5NA/VINYLS.BIN'
    archive.parent.mkdir(parents=True, exist_ok=True)
    if archive.exists():
        raise ValueError('Staged archive already exists; use a new output directory')
    shutil.copy2(game / 'CARS/MIATA/VINYLS.BIN', archive)
    archive.chmod(0o666)
    rel = r'CARS\MX5NA\VINYLS.BIN'
    launcher = out / 'vinyl.endlauncher'
    launcher.write_text(json.dumps(dict(Usage='Modder', Game='Underground2',
        Directory='', Endscript='', Files=[rel], Links=[])).replace('\\\\', '\\'), encoding='utf8')
    command = [str(a.dotnet.resolve()), str((a.converter / 'bin/u2tool.dll').resolve())]
    result = subprocess.run(command + ['textures', str(launcher), str(out), rel, '^MIATA_'],
                            check=True, capture_output=True, text=True)
    names = [line.split('\t')[1] for line in result.stdout.splitlines() if '\tMIATA_' in line]
    if not {'MIATA_CONTEST_01', 'MIATA_CONTEST_01_MASK'}.issubset(names):
        raise ValueError('Donor archive is missing the editor artwork/mask pair')
    script = out / 'vinyl.u2s'
    script.write_text('\n'.join(f'tex_rename {rel} {n} MX5NA_{n[6:]}' for n in names) + '\n', encoding='utf8')
    subprocess.run(command + ['apply', str(launcher), str(out), str(script)], check=True)
    # Renaming alone leaves NB artwork in the wrong UV islands on the NA.
    # Reproject the indexed artwork and masks, leaving NA custom PNGs intact.
    mapping = out / 'na-vinyl-map.bin'
    make_map(game / 'CARS/MX5NA/GEOMETRY.BIN', game / 'CARS/MIATA/GEOMETRY.BIN').astype('<f4').tofile(mapping)
    helper = out / 'atlas-helper'
    env = dict(os.environ, DOTNET_CLI_HOME=str(out / 'dotnet-home'), DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1')
    tools = Path(__file__).resolve().parent
    subprocess.run([str(a.dotnet.resolve()), 'build', str(tools / 'fit-vinyl-atlas/fit-vinyl-atlas.csproj'),
                    '--configfile', str(tools / 'car-textures/NuGet.Config'), '-o', str(helper),
                    '--nologo', '-v:q'], check=True, env=env)
    fitted = archive.with_suffix('.fitted.bin')
    subprocess.run([str(a.dotnet.resolve()), str(helper / 'fit-vinyl-atlas.dll'), str(archive),
                    str(fitted), str(mapping), str((a.converter / 'bin').resolve())], check=True, env=env)
    fitted.replace(archive)
    print(f'Created {archive} ({len(names)} renamed textures)')


if __name__ == '__main__':
    main()
