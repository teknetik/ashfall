"""Shared functions for staged live-Blender generator review. No execution on import.
Run only through the live Blender MCP after the main task hands over the app.
"""
import bpy
import json
import hashlib
import math
from pathlib import Path
import numpy as np
from mathutils import Vector

REPO = Path('/home/teknetik/code/ao2')
SOURCE = REPO / 'meshy/ground-detail-20260910/generator-v2'
SCENE = 'Generator v2 source inspection'
HIGH = 'GENERATOR_V2_SOURCE'
FBX_TRIANGLES = 1927842  # Verified raw FBX polygon index count; retained GLB contains1945352.
CHANNELS = ('base_color', 'metallic', 'roughness', 'normal')

def sha(path):
    with Path(path).open('rb') as stream:
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def write_new(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')

def source_contract():
    record = json.loads((SOURCE / 'task.json').read_text())
    assert record['task_id'] == '01a08ad7-d563-7043-89bc-bf138e742318'
    assert record['request']['should_remesh'] is False
    assert record['sourceTriangles'] == 1945352
    for relative, expected in record['retainedFiles'].items():
        path = SOURCE.parent / relative
        assert sha(path) == expected['sha256'], 'Retained source changed: ' + str(path)
    for relative, expected in record['referenceFiles'].items():
        assert sha(REPO / relative) == expected['sha256'], 'Retained reference changed'
    return record

def pbr_material(label, folder, prefix='SOURCE_'):
    material = bpy.data.materials.new(label)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    shader = nodes.get('Principled BSDF')
    dimensions = {}
    for name, socket in [('base_color', 'Base Color'), ('metallic', 'Metallic'), ('roughness', 'Roughness'), ('normal', 'Normal')]:
        texture = nodes.new('ShaderNodeTexImage')
        texture.name = prefix + name
        texture.image = bpy.data.images.load(str(Path(folder) / (name + '.png')), check_existing=True)
        texture.image.colorspace_settings.name = 'sRGB' if name == 'base_color' else 'Non-Color'
        dimensions[name] = list(texture.image.size)
        if name == 'normal':
            normal = nodes.new('ShaderNodeNormalMap')
            normal.name = prefix + 'GL_NORMAL'
            normal.space = 'TANGENT'
            links.new(texture.outputs['Color'], normal.inputs['Color'])
            links.new(normal.outputs['Normal'], shader.inputs['Normal'])
        else:
            links.new(texture.outputs['Color'], shader.inputs[socket])
    return material, dimensions

def world_vertices(obj):
    vertices = np.empty(len(obj.data.vertices) * 3, dtype=np.float64)
    obj.data.vertices.foreach_get('co', vertices)
    vertices = vertices.reshape((-1, 3))
    matrix = np.array(obj.matrix_world, dtype=np.float64)
    return vertices @ matrix[:3, :3].T + matrix[:3, 3]

def topology(obj):
    """Numeric audit without modifying geometry. Coincident seams are analysed separately.
    Quantized 10-micrometre vertex equivalence is only a diagnostic proxy, never a
    weld/repair or a guarantee that an intentional opening is a watertight solid.
    """
    mesh = obj.data
    mesh.calc_loop_triangles()
    vertex = world_vertices(obj)
    if not np.isfinite(vertex).all():
        raise ValueError('Nonfinite metric vertex positions; do not continue topology/fit analysis')
    tri = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int32)
    mesh.loop_triangles.foreach_get('vertices', tri)
    tri = tri.reshape((-1, 3))
    area = volume = 0.0
    degenerate = 0
    for start in range(0, len(tri), 131072):
        points = vertex[tri[start:start + 131072]]
        cross = np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0])
        areas = np.linalg.norm(cross, axis=1) * .5
        area += float(areas.sum())
        degenerate += int((areas <= 1e-12).sum())
        volume += float(np.einsum('ij,ij->i', points[:, 0], np.cross(points[:, 1], points[:, 2])).sum() / 6)
    def edge_audit(indices, count):
        edges = np.concatenate((indices[:, [0, 1]], indices[:, [1, 2]], indices[:, [2, 0]]))
        lo = edges.min(axis=1).astype(np.int64)
        hi = edges.max(axis=1).astype(np.int64)
        codes, counts = np.unique(lo * count + hi, return_counts=True)
        return {'uniqueEdges': int(len(codes)), 'boundaryEdges': int((counts == 1).sum()),
                'edgesWithMoreThanTwoFaces': int((counts > 2).sum()),
                'collapsedEdges': int((codes // count == codes % count).sum())}, codes
    raw, _ = edge_audit(tri, len(vertex))
    _, equivalence = np.unique(np.rint(vertex / 1e-5).astype(np.int64), axis=0, return_inverse=True)
    equivalent_count = int(equivalence.max()) + 1
    welded, codes = edge_audit(equivalence[tri], equivalent_count)
    a, b = codes // equivalent_count, codes % equivalent_count
    parent = np.arange(equivalent_count, dtype=np.int64)
    converged = False
    for iteration in range(128):
        previous = parent.copy()
        left, right = parent[a], parent[b]
        np.minimum.at(parent, np.maximum(left, right), np.minimum(left, right))
        while True:
            compressed = parent[parent]
            if np.array_equal(parent, compressed):
                break
            parent = compressed
        if np.array_equal(previous, parent):
            converged = True
            break
    _, components = np.unique(parent[equivalence], return_inverse=True)
    counts = np.bincount(components)
    largest = []
    for component in np.argsort(counts)[-12:][::-1]:
        points = vertex[components == component]
        largest.append({'verticesIncludingUvSplits': int(counts[component]), 'boundsMetres': [points.min(axis=0).tolist(), points.max(axis=0).tolist()]})
    uv = mesh.uv_layers.active
    return {'objects': 1, 'vertices': len(vertex), 'triangles': len(tri), 'allVertexPositionsFinite': bool(np.isfinite(vertex).all()),
            'boundsMetres': [vertex.min(axis=0).tolist(), vertex.max(axis=0).tolist()],
            'surfaceAreaSquareMetres': area, 'signedVolumeCubicMetres': volume,
            'volumeCaveat': 'Signed surface integral, meaningful as enclosed volume only for closed consistently oriented components.',
            'degenerateTrianglesAt1eMinus12SquareMetres': degenerate, 'rawIndexedTopology': raw,
            'coincidentSeamProxy10Micrometres': {**welded, 'vertices': equivalent_count, 'componentsConverged': converged,
                'componentIterations': iteration + 1, 'components': len(counts) if converged else None, 'largestComponents': largest},
            'uvLayers': [layer.name for layer in mesh.uv_layers], 'activeUvLoops': len(uv.data) if uv else 0,
            'hasCustomNormals': mesh.has_custom_normals,
            'acceptance': 'Diagnostic only. Inspect openings, disconnected parts and normals in the actual mesh and renders before accepting.'}

def cycles_settings(scene, samples=24):
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    devices = []
    error = None
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'CUDA'
        prefs.get_devices()
        for device in prefs.devices:
            device.use = device.type == 'CUDA'
            devices.append({'name': device.name, 'type': device.type, 'enabled': device.use})
        scene.cycles.device = 'GPU' if any(d['enabled'] for d in devices) else 'CPU'
    except Exception as exc:
        scene.cycles.device = 'CPU'
        error = str(exc)
    return {'engine': scene.render.engine, 'samples': samples, 'device': scene.cycles.device, 'devices': devices,
            'deviceSetupError': error, 'resolution': [1400, 1100], 'resolutionPercentage': 100,
            'viewTransform': 'AgX', 'exposure': 0, 'sourcePreviewOnly': True}

def memory_record():
    path = Path('/proc/self/status')
    return {line.split(':')[0]: line.split(':', 1)[1].strip() for line in path.read_text().splitlines()
            if line.startswith(('VmRSS:', 'VmHWM:', 'VmSwap:'))} if path.exists() else {'unavailable': True}
