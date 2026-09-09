"""Verify exported construction buffers and record source identity, without Blender or Unity writes."""
from pathlib import Path
import hashlib
import json
import math
import re
import numpy as np

root = Path(__file__).resolve().parent
parts = json.loads((root / 'bench-meshes.json').read_text())
zero_area = opposed = nonfinite = bad_indices = buffer_mismatch = 0
normal_error = 0.0
asset_names = []
for part in parts:
    p = np.asarray(part['positions'], dtype=float)
    n = np.asarray(part['normals'], dtype=float)
    uv = np.asarray(part['uv'], dtype=float)
    indices = np.asarray(part['indices'], dtype=int)
    buffer_mismatch += int(len(p) != len(n) or len(p) != len(uv))
    nonfinite += int((~np.isfinite(p)).sum() + (~np.isfinite(n)).sum() + (~np.isfinite(uv)).sum())
    bad_indices += int((indices < 0).sum() + (indices >= len(p)).sum() + (len(indices) % 3 != 0))
    triangles = indices.reshape(-1, 3)
    cross = np.cross(p[triangles[:, 1]] - p[triangles[:, 0]], p[triangles[:, 2]] - p[triangles[:, 0]])
    zero_area += int((np.linalg.norm(cross, axis=1) < 1e-10).sum())
    opposed += int((np.einsum('ij,ij->i', cross, n[triangles].mean(axis=1)) < -1e-10).sum())
    normal_error = max(normal_error, float(np.abs(np.linalg.norm(n, axis=1) - 1).max()))
    asset_names.append(re.sub(r'[^\w-]', '_', part['name']))

report = dict(parts=len(parts), triangles=sum(len(p['indices']) // 3 for p in parts),
              vertices=sum(len(p['positions']) for p in parts), zeroAreaTriangles=zero_area,
              opposedNormalTriangles=opposed, nonfiniteValues=nonfinite, invalidIndices=bad_indices,
              mismatchedBuffers=buffer_mismatch, duplicateAssetNames=len(asset_names) - len(set(asset_names)),
              maximumUnitNormalError=normal_error)
assert not any([zero_area, opposed, nonfinite, bad_indices, buffer_mismatch, report['duplicateAssetNames']]), report
assert normal_error < 0.00001, report
(root / 'buffer-validation.json').write_text(json.dumps(report, indent=2) + '\n')

paths = ['bench-family.blend', 'bench-meshes.json', 'author_bench.py', 'prepare_maps.py',
         'geometry-report.json', 'buffer-validation.json', 'uv-board-selection.json', 'textures/manifest.json',
         'studio-front.png', 'studio-rear.png', 'studio-joint.png']
manifest = dict(revision=3, source='Original Ward reclaimed timber bench construction',
                license='Original geometry and metal/endgrain maps; CC0 Poly Haven Wooden Planks photographic maps',
                nativeAcceptance='Pending root integration and independent native review',
                files=[dict(path=p, bytes=(root/p).stat().st_size,
                            sha256=hashlib.sha256((root/p).read_bytes()).hexdigest()) for p in paths])
(root / 'source-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(report, indent=2))
