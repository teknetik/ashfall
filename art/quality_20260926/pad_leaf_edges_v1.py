"""Run through live Blender MCP. Derive leaf fringe colors; preserve source and scene.

This uses Blender's image decoder with raw channel handling, then deterministic
eight-neighbor color dilation in NumPy. PNG export preserves exact bytes without
view transforms, resampling, alpha multiplication or a color grade.
"""
from pathlib import Path
import hashlib
import json
import struct
import zlib
import bpy
import numpy as np

ROOT = Path('/home/teknetik/code/ao2')
SOURCE = ROOT / 'unity/AthenHill/Assets/AthenHill/Art/HeroTree/leaves-albedo.png'
OUT = ROOT / 'art/quality_20260926/tree-edge-padding-v1'
EXPECTED_DECODED = 'dcde7d903d4976f8a8c3666aeb271f867409a7c8fa1c34838be15c72ea79ff7c'
SOLID_ALPHA = 250
RADIUS = 8


def digest(data):
    return hashlib.sha256(data).hexdigest()


def png_chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)


def export_png(path, pixels):
    height, width, channels = pixels.shape
    assert channels == 4 and pixels.dtype == np.uint8
    scanlines = np.zeros((height, width * channels + 1), dtype=np.uint8)
    scanlines[:, 1:] = pixels.reshape(height, width * channels)
    payload = b'\x89PNG\r\n\x1a\n'
    payload += png_chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
    payload += png_chunk(b'IDAT', zlib.compress(scanlines.tobytes(), 6))
    payload += png_chunk(b'IEND', b'')
    path.write_bytes(payload)


def author():
    before = [(obj.name, tuple(obj.matrix_world)) for obj in bpy.data.objects]
    image = bpy.data.images.load(str(SOURCE), check_existing=False)
    try:
        spaces = {item.identifier for item in image.colorspace_settings.bl_rna.properties['name'].enum_items}
        alpha_modes = {item.identifier for item in image.bl_rna.properties['alpha_mode'].enum_items}
        assert 'Non-Color' in spaces and 'CHANNEL_PACKED' in alpha_modes
        image.colorspace_settings.name = 'Non-Color'
        image.alpha_mode = 'CHANNEL_PACKED'
        width, height = image.size
        assert (width, height) == (4096, 4096)
        raw = np.empty(len(image.pixels), dtype=np.float32)
        image.pixels.foreach_get(raw)
        original = np.rint(np.clip(raw.reshape(height, width, 4)[::-1], 0, 1) * 255).astype(np.uint8)
        del raw
        assert digest(original.tobytes()) == EXPECTED_DECODED, 'Blender decoding must preserve the exact source bytes.'
        result = original.copy()
        solid = original[:, :, 3] >= SOLID_ALPHA
        known = solid.copy()
        iterations = []
        # Ties prefer cardinal neighbors before diagonals; no wrapped atlas edges.
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)]
        for radius in range(1, RADIUS + 1):
            next_known = known.copy()
            added = 0
            for dy, dx in directions:
                dst_y = slice(max(0, dy), min(height, height + dy))
                dst_x = slice(max(0, dx), min(width, width + dx))
                src_y = slice(max(0, -dy), min(height, height - dy))
                src_x = slice(max(0, -dx), min(width, width - dx))
                select = ~next_known[dst_y, dst_x] & known[src_y, src_x]
                added += int(np.count_nonzero(select))
                dst_rgb = result[dst_y, dst_x, :3]
                dst_rgb[select] = result[src_y, src_x, :3][select]
                next_known[dst_y, dst_x] |= select
            known = next_known
            iterations.append({'radiusPixels': radius, 'newPaddedPixels': added})
            if not added:
                break
        assert np.array_equal(result[:, :, 3], original[:, :, 3])
        assert np.array_equal(result[solid, :3], original[solid, :3])
        changed = np.any(result[:, :, :3] != original[:, :, :3], axis=2)
        partial = (original[:, :, 3] > 0) & ~solid
        OUT.mkdir(parents=True, exist_ok=True)
        destination = OUT / 'leaves-albedo-edge-padded-v1.png'
        export_png(destination, result)
        report = {
            'status': 'Derived diagnostic candidate; not installed or visually accepted',
            'authoring': 'Live Blender MCP, Blender ' + bpy.app.version_string + ', NumPy ' + np.__version__,
            'source': str(SOURCE.relative_to(ROOT)),
            'sourceSha256': digest(SOURCE.read_bytes()),
            'sourceDecodedRgbaSha256': digest(original.tobytes()),
            'sourceProvenance': 'Poly Haven Jacaranda CC0; original maps and import recipe remain in refs/quality_20260908/tree and art/quality_20260908/prepare_tree_runtime.py',
            'candidate': str(destination.relative_to(ROOT)),
            'candidateSha256': digest(destination.read_bytes()),
            'candidateDecodedRgbaSha256': digest(result.tobytes()),
            'dimensions': [width, height],
            'rgbaBitsPerChannel': 8,
            'algorithm': 'Eight-neighbor wavefront copies nearest propagated solid RGB into lower-alpha pixels; ties prefer cardinal directions; bounded radius; no averaging or tint.',
            'solidAlphaMinimum': SOLID_ALPHA,
            'radiusPixels': RADIUS,
            'iterations': iterations,
            'rgbChangedPixels': int(np.count_nonzero(changed)),
            'changedNonzeroAlphaPixels': int(np.count_nonzero(changed & (original[:, :, 3] > 0))),
            'changedFullyTransparentPixels': int(np.count_nonzero(changed & (original[:, :, 3] == 0))),
            'partialAlphaPixelsNotReached': int(np.count_nonzero(partial & ~known)),
            'alphaBytesIdentical': True,
            'alphaSha256': digest(result[:, :, 3].tobytes()),
            'solidLeafRgbBytesIdentical': True,
            'sourceUnchanged': True,
            'unityImportRecipe': 'Import as sRGB color, same alpha clipping/coverage, filter, anisotropy, compression, mip streaming and resolution settings as original; change only temporary diagnostic leaf material BaseMap assignment.',
            'acceptance': 'Compare same close canopy and hero cameras, time, shadow range and exposure; actual Unity imported mips may mitigate or preserve the source fringe. Retain original assignment until verified.'
        }
        assert before == [(obj.name, tuple(obj.matrix_world)) for obj in bpy.data.objects]
        (OUT / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))
    finally:
        bpy.data.images.remove(image)


author()
