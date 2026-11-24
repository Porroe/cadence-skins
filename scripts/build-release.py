#!/usr/bin/env python3
"""Validate and package all Cadence 1.0 skins using only Python's standard library."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.0'


def validate(skin_dir):
    manifest = skin_dir / 'skin.json'
    if manifest.stat().st_size > 256 * 1024:
        raise ValueError(f'{manifest}: exceeds 256 KB')
    skin = json.loads(manifest.read_text())
    if skin.get('format') != 1 or skin.get('version') != VERSION:
        raise ValueError(f'{manifest}: expected format 1 and version {VERSION}')
    if not skin.get('name', '').startswith('Cadence '):
        raise ValueError(f'{manifest}: invalid skin name')
    fonts = skin.get('fonts', {})
    if len(fonts) > 8:
        raise ValueError(f'{manifest}: exceeds 8 custom fonts')
    for font in fonts.values():
        relative = PurePosixPath(font['file'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError(f'{manifest}: unsafe asset path')
        asset = skin_dir / relative
        if not asset.is_file() or asset.stat().st_size > 8 * 1024 * 1024:
            raise ValueError(f'{asset}: missing or oversized font')
        if not 8 <= font['size'] <= 72:
            raise ValueError(f'{asset}: invalid font size')
    if not (skin_dir / 'LICENSE.txt').is_file():
        raise ValueError(f'{skin_dir}: missing license')
    return skin


def main():
    folders = sorted((ROOT / 'skins').glob('Cadence*'))
    if len(folders) != 14:
        raise ValueError(f'Expected 14 skins, found {len(folders)}')
    names = set()
    font_reference = None
    for folder in folders:
        skin = validate(folder)
        if skin['name'] in names:
            raise ValueError(f'Duplicate name: {skin["name"]}')
        names.add(skin['name'])
        fingerprint = {
            'definitions': skin['fonts'],
            'files': {spec['file']: hashlib.sha256((folder / spec['file']).read_bytes()).hexdigest()
                      for spec in skin['fonts'].values()},
        }
        if font_reference is not None and fingerprint != font_reference:
            raise ValueError(f'{folder}: font definitions or files differ from the collection')
        font_reference = fingerprint
    output = ROOT / 'releases'
    output.mkdir(exist_ok=True)
    archive = output / f'Cadence-{VERSION}.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for folder in folders:
            for source in sorted(folder.rglob('*')):
                if source.is_file():
                    bundle.write(source, source.relative_to(ROOT / 'skins'))
        bundle.write(ROOT / 'LICENSE', 'LICENSE')
        bundle.writestr('INSTALL.txt',
            'Cadence 1.0 for the Innioasis Y2 running Y2Linux and Y2Reborn.\n\n'
            'Copy your chosen Cadence folders into Skins on Internal Storage or the SD card.\n'
            'Each skin.json must be directly inside its Cadence folder, with fonts beside it.\n'
            'Safely eject, then select Settings > Skin > your installed Cadence skin.\n\n'
            'Source and credits: https://github.com/Porroe/cadence-skins\n')
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / f'Cadence-{VERSION}.zip.sha256').write_text(f'{checksum}  {archive.name}\n')
    print(f'Validated {len(folders)} skins; created {archive}')
    print(f'SHA-256: {checksum}')


if __name__ == '__main__':
    main()
