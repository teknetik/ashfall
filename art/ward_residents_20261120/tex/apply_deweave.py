"""Applies the skin de-weave to a resident's runtime GLB (20 Nov 2026).
  base colour: deweave.py (FFT notch of periodic peaks, skin mask only)
  normal map:  inside the same skin mask, blended toward flat (128,128,255) by `flat` (the re-baked normal carried the weave)
The original is kept once as rigged_fixed_weave.glb; rigged_fixed.glb is rewritten with the two images replaced (PNG).
Usage: python3 apply_deweave.py <meshy resident folder> [k] [flat]"""
import json, struct, subprocess, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
D = Path(sys.argv[1]); k = sys.argv[2] if len(sys.argv) > 2 else '1.5'; flat = float(sys.argv[3]) if len(sys.argv) > 3 else .75
orig = D / 'rigged_fixed_weave.glb'
if not orig.exists(): orig.write_bytes((D / 'rigged_fixed.glb').read_bytes())
name = D.name
base_png = HERE / f'{name}_base.png'
print(subprocess.check_output(['python3', str(HERE / 'deweave.py'), str(orig), str(base_png), k]).decode().strip())
b = orig.read_bytes(); jl = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20 + jl]); o = 20 + jl
bl = struct.unpack('<I', b[o:o + 4])[0]; binary = bytearray(b[o + 8:o + 8 + bl])
mat = j['materials'][j['meshes'][0]['primitives'][0].get('material', 0)]
ni = j['textures'][mat['normalTexture']['index']]['source']; bi = j['textures'][mat['pbrMetallicRoughness']['baseColorTexture']['index']]['source']
def img(i):
    v = j['bufferViews'][j['images'][i]['bufferView']]; return bytes(binary[v.get('byteOffset', 0):v.get('byteOffset', 0) + v['byteLength']])
# normal: flatten inside the skin mask
nsrc = HERE / f'{name}_normal_src.img'; nsrc.write_bytes(img(ni))
w, h = map(int, subprocess.check_output(['magick', 'identify', '-format', '%w %h', str(nsrc)]).split())
N = np.frombuffer(subprocess.check_output(['magick', str(nsrc), '-depth', '8', 'rgb:-']), np.uint8).reshape(h, w, 3).astype(np.float32)
M = np.frombuffer(subprocess.check_output(['magick', str(HERE / f'{name}_base_mask.png'), '-resize', f'{w}x{h}!', '-depth', '8', 'gray:-']), np.uint8).reshape(h, w).astype(np.float32) / 255
F = np.array([128, 128, 255], np.float32)
N2 = N * (1 - flat * M[..., None]) + F * (flat * M[..., None])
v = N2[..., :2] / 127.5 - 1; z = np.sqrt(np.clip(1 - (v ** 2).sum(-1), 0, 1)); N2[..., 2] = z * 127.5 + 127.5
raw = HERE / f'{name}_normal.rgb'; raw.write_bytes(np.clip(np.round(N2), 0, 255).astype(np.uint8).tobytes())
npng = HERE / f'{name}_normal.png'
subprocess.run(['magick', '-size', f'{w}x{h}', '-depth', '8', f'rgb:{raw}', str(npng)], check=True); raw.unlink(); nsrc.unlink()
def put(i, data):
    while len(binary) % 4: binary.append(0)
    start = len(binary); binary.extend(data)
    j['bufferViews'].append({'buffer': 0, 'byteOffset': start, 'byteLength': len(data)})
    j['images'][i] = {'name': j['images'][i].get('name', 'img'), 'mimeType': 'image/png', 'bufferView': len(j['bufferViews']) - 1}
put(bi, base_png.read_bytes()); put(ni, npng.read_bytes())
while len(binary) % 4: binary.append(0)
j['buffers'][0]['byteLength'] = len(binary)
js = json.dumps(j, separators=(',', ':')).encode()
while len(js) % 4: js += b' '
out = b'glTF' + struct.pack('<II', 2, 12 + 8 + len(js) + 8 + len(binary)) + struct.pack('<I', len(js)) + b'JSON' + js + struct.pack('<I', len(binary)) + b'BIN\x00' + bytes(binary)
(D / 'rigged_fixed.glb').write_bytes(out)
print(json.dumps({'resident': name, 'normalFlat': flat, 'glb': str(D / 'rigged_fixed.glb'), 'bytes': len(out)}))
