"""Berms landmarks: URP Lit masks (2 Oct 2026). Run after prepare.py:
    uv run --with pillow --with numpy python textures.py

Per landmark part, from the Meshy glTF metal-rough map (G roughness, B metallic, kept at its delivered size):
<stem>_Mask.png = R metallic, G occlusion 1, B 0, A smoothness (1 - roughness), next to the part's models, plus
mask statistics in berms-landmarks.json. The channel renders (meshy/.../review/chan_*.jpg) showed metal only on bare
steel edges (hauler), the alloy cradle (pylon) and the tube casing; concrete, canvas, sand and rust stay dielectric,
so the maps are used unscaled."""
import json
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / 'unity/AthenHill/Assets/AthenHill/Art/BermsExpanse/Landmarks'
man = json.loads((OUT / 'berms-landmarks.json').read_text())
for lid, e in man.items():
    for p in e['parts']:
        src = ROOT / p['maps']['MetalRoughSource']
        x = np.asarray(Image.open(src).convert('RGB')).astype(np.float32) / 255
        rough, metal = x[..., 1], x[..., 2]
        m = np.stack([metal, np.ones_like(metal), np.zeros_like(metal), 1 - rough], -1)
        Image.fromarray((m * 255 + 0.5).astype(np.uint8), 'RGBA').save(OUT / lid / p['maps']['Mask'])
        p['mask_stats'] = {'metallic_mean': round(float(metal.mean()), 4), 'metallic_over_half': round(float((metal > 0.5).mean()), 4),
                           'smoothness_mean': round(float(1 - rough.mean()), 4), 'size': list(rough.shape[::-1])}
        print(lid, p['name'], p['mask_stats'], flush=True)
(OUT / 'berms-landmarks.json').write_text(json.dumps(man, indent=1))
