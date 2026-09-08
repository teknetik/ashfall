"""Pack the preserved salvage atlas and eight new building maps for Unity batching."""
import json
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1] / 'AthenHill/Assets/AthenHill'
OLD = ROOT / 'Art/Imported/Meshy/Salvage/Atlas'
NEW = ROOT / 'Art/Imported/Meshy/District'
OUT = NEW / 'Atlas'
NAMES = ['water', 'tools', 'salvage', 'finery', 'field', 'repairs', 'thread', 'gate']
OUT.mkdir(parents=True, exist_ok=True)
for channel in ['base_color', 'normal', 'metallic_smoothness']:
    atlas = Image.new('RGBA', (6144, 4096))
    original = Image.open(OLD / (channel + '.png')).convert('RGBA')
    assert original.size == (4096, 4096)
    atlas.paste(original, (0, 0))
    for i, name in enumerate(NAMES):
        tile = Image.open(NEW / name / (channel + '.png')).convert('RGBA')
        tile = tile.resize((1008, 1008), Image.Resampling.LANCZOS)
        padded = Image.new('RGBA', (1024, 1024))
        padded.paste(tile, (8, 8))
        padded.paste(tile.crop((0, 0, 1008, 1)).resize((1008, 8)), (8, 0))
        padded.paste(tile.crop((0, 1007, 1008, 1008)).resize((1008, 8)), (8, 1016))
        padded.paste(padded.crop((8, 0, 9, 1024)).resize((8, 1024)), (0, 0))
        padded.paste(padded.crop((1015, 0, 1016, 1024)).resize((8, 1024)), (1016, 0))
        atlas.paste(padded, (4096 + i % 2 * 1024, i // 2 * 1024))
    atlas.save(OUT / (channel + '.png'))
slots = [{'name': name, 'x': 4096 + i % 2 * 1024, 'y': (3 - i // 2) * 1024,
          'width': 1024, 'height': 1024} for i, name in enumerate(NAMES)]
(OUT / 'layout.json').write_text(json.dumps({'width': 6144, 'height': 4096, 'padding': 8,
    'preservedSalvageArea': [0, 0, 4096, 4096], 'slots': slots}, indent=2))
print('Packed 16 source asset types into one material atlas; old texels preserved.')
