"""Threshold v2: explicit metric UVs and narrowly scoped corner-normal correction.

Execute this script through the live Blender session, after other authoring ends.
No modifiers, remesh, displacement, silhouette changes or collider edits occur.
--audit-only runs the pure buffer calculations offline without importing bpy.
"""
from pathlib import Path
import hashlib
import json
import math
import sys

ROOT = Path('/home/teknetik/code/ao2')
OUT = ROOT / 'art/reference_street_20260910'
SOURCE = OUT / 'stone-threshold-meshes-v1.json'
SOURCE_SHA256 = 'ebf440df01c8284f97b54e0fc07403303f5f929dbb1a5d32a9f44406960e620b'
METRES_PER_TILE = 2.0


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def unit(v):
    length = math.sqrt(dot(v, v))
    assert length > 1e-15, 'Degenerate face or normal requires a separate geometry repair.'
    return tuple(x/length for x in v)


def components(part):
    """Find whole stones from exact shared exported positions, without welding them."""
    lookup, parents, vertex_ids = {}, [], []
    for point in part['positions']:
        key = tuple(point)
        if key not in lookup:
            lookup[key] = len(parents)
            parents.append(len(parents))
        vertex_ids.append(lookup[key])

    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    indices = part['indices']
    for t in range(0, len(indices), 3):
        a, b, c = (find(vertex_ids[i]) for i in indices[t:t+3])
        parents[b] = a
        parents[c] = a
    groups = {}
    for i, key in enumerate(vertex_ids):
        groups.setdefault(find(key), []).append(i)
    groups = sorted(groups.values(), key=lambda ids: min(tuple(part['positions'][i]) for i in ids))
    membership, records = {}, []
    for index, ids in enumerate(groups):
        points = [part['positions'][i] for i in ids]
        lo = [min(p[k] for p in points) for k in range(3)]
        hi = [max(p[k] for p in points) for k in range(3)]
        center = [(a+b)*.5 for a, b in zip(lo, hi)]
        key = part['name'] + ':' + ','.join(format(v, '.6f') for v in center)
        seed = hashlib.sha256(key.encode()).digest()
        # The scale is always 2 metres. Translation and a small rotation break
        # repeated photographic features without randomly resizing the mineral.
        angle = math.radians((int.from_bytes(seed[:2], 'big')/65535*2-1)*8)
        offset = [int.from_bytes(seed[n:n+2], 'big')/65535*.43 for n in (2, 4)]
        records.append({'component': index, 'bounds': [lo, hi], 'center': center,
                        'rotationDegrees': math.degrees(angle), 'offsetUv': offset,
                        'cos': math.cos(angle), 'sin': math.sin(angle)})
        membership.update((i, index) for i in ids)
    return membership, records


def prepare_parts():
    assert sha(SOURCE) == SOURCE_SHA256, 'The reviewed v1 geometry changed.'
    original = json.loads(SOURCE.read_text())
    assert len(original) == 36 and sum(len(p['indices'])//3 for p in original) == 235138
    output, audits = [], []
    for part in original:
        positions, indices = part['positions'], part['indices']
        # V1's explicit triangle-corner buffers allow a chart seam or targeted
        # normal correction without adding vertices or changing topology.
        assert indices == list(range(len(positions))) and len(indices) % 3 == 0
        membership, islands = components(part)
        uvs, normals = [None]*len(positions), list(part['normals'])
        changed, negative_faces, min_metric_ratio, max_metric_ratio = [], 0, float('inf'), 0
        for t in range(0, len(indices), 3):
            ids = indices[t:t+3]
            a, b, c = (positions[i] for i in ids)
            e1, e2 = [b[k]-a[k] for k in range(3)], [c[k]-a[k] for k in range(3)]
            face_cross = cross(e1, e2)
            normal = unit(face_cross)
            # Geometric normals avoid choosing a chart from a corrupt custom normal.
            axis = max(range(3), key=lambda k: abs(normal[k]))
            axes = ((2, 1), (0, 2), (0, 1))[axis]  # Unity X/Y/Z normal -> ZY/XZ/XY.
            island = islands[membership[ids[0]]]
            assert all(membership[i] == membership[ids[0]] for i in ids)
            cs, sn = island['cos'], island['sin']
            center_u, center_v = (island['center'][k]/METRES_PER_TILE for k in axes)
            average = [sum(part['normals'][i][k] for i in ids)/3 for k in range(3)]
            negative_faces += dot(normal, average) < 0
            for i in ids:
                pu, pv = (positions[i][k]/METRES_PER_TILE for k in axes)
                du, dv = pu-center_u, pv-center_v
                uvs[i] = [center_u + cs*du-sn*dv + island['offsetUv'][0],
                          center_v + sn*du+cs*dv + island['offsetUv'][1]]
                if dot(normal, part['normals'][i]) <= 0:
                    changed.append(i)
                    normals[i] = list(normal)
                assert dot(normal, normals[i]) > 0, 'A corrected corner still faces behind its triangle.'
            # Projected area has a known metric ratio. This catches wrong active
            # layers, stretching and accidental per-part UV normalization.
            area2 = math.sqrt(dot(face_cross, face_cross))
            if area2 > 2e-8:
                u, v, w = (uvs[i] for i in ids)
                uv_area2 = abs((v[0]-u[0])*(w[1]-u[1])-(v[1]-u[1])*(w[0]-u[0]))
                ratio = uv_area2/area2
                expected = abs(normal[axis])/(METRES_PER_TILE**2)
                assert abs(ratio-expected) < 1e-6, (part['name'], t//3, ratio, expected)
                min_metric_ratio, max_metric_ratio = min(min_metric_ratio, ratio), max(max_metric_ratio, ratio)
        updated = dict(part, uv=uvs, normals=normals)
        assert updated['positions'] == part['positions'] and updated['indices'] == part['indices']
        assert all(updated[k] == v for k, v in part.items() if k not in {'uv', 'normals'})
        output.append(updated)
        audits.append({'name': part['name'], 'sourcePath': part.get('sourcePath'),
            'triangles': len(indices)//3, 'connectedStoneComponents': len(islands),
            'metricAreaRatioRange': [min_metric_ratio, max_metric_ratio],
            'oldNegativeAverageNormalFaces': negative_faces, 'correctedCornerNormals': len(changed),
            'correctedCornerIndices': changed, 'positionsAndIndicesExactlyPreserved': True,
            'unmodifiedNormalCorners': len(normals)-len(changed),
            'islands': [{k:v for k,v in item.items() if k not in {'cos', 'sin'}} for item in islands]})
    return output, {'revision': 'stone-threshold-v2', 'sourceFile': str(SOURCE.relative_to(ROOT)),
        'sourceSha256': SOURCE_SHA256, 'sourceGeometryPreserved': True, 'positionsAndIndicesExactlyPreserved': True,
        'triangles': 235138, 'parts': 36, 'metresPerTextureTile': METRES_PER_TILE,
        'normalPolicy': 'Preserve every original corner normal except those with dot(geometricFaceNormal, cornerNormal) <= 0; replace only those with the face normal.',
        'geometryPolicy': 'No geometry modifiers, face filling, deletion, remesh, subdivision, displacement, transforms or collider changes.',
        'materialPolicy': 'Original 4K sandstone color/normal/roughness; installer must pack smoothness into a separate RGBA32 output. No arbitrary roughness reduction.',
        'sourceBlend': 'stone-thresholds-v2.blend', 'nativeAccepted': False, 'meshAudits': audits}


def author():
    import bpy
    paths = [OUT/'stone-thresholds-v2.blend', OUT/'stone-threshold-meshes-v2.json', OUT/'stone-threshold-manifest-v2.json']
    assert not any(path.exists() for path in paths), 'Preserve earlier v2 output; inspect before retrying.'
    parts, manifest = prepare_parts()
    scene = bpy.data.scenes.new('Threshold v2 metric UV and source roughness')
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1
    bpy.context.window.scene = scene
    photo = ROOT/'refs/quality_20260909/basic-general/materials/sandstone_cracks'
    images = {}
    for key, file in [('color', 'diff'), ('normal', 'nor_gl'), ('roughness', 'rough')]:
        image = bpy.data.images.load(str(photo/f'sandstone_cracks_{file}_4k.jpg'), check_existing=False)
        image.colorspace_settings.name = 'sRGB' if key == 'color' else 'Non-Color'
        images[key] = image
    materials = {}
    for key, tint in [('ThresholdStone', (.87,.87,.82)), ('ThresholdMortar', (.48,.44,.37)), ('ThresholdGrit', (.80,.78,.71))]:
        material = bpy.data.materials.new(key+' v2 source preview')
        material.use_nodes = True
        nodes, links = material.node_tree.nodes, material.node_tree.links
        bsdf = nodes.get('Principled BSDF')
        tex = {}
        for name, image in images.items():
            tex[name] = nodes.new('ShaderNodeTexImage'); tex[name].image = image
        multiply = nodes.new('ShaderNodeMixRGB'); multiply.blend_type = 'MULTIPLY'
        multiply.inputs[0].default_value = 1; multiply.inputs[2].default_value = (*tint, 1)
        links.new(tex['color'].outputs['Color'], multiply.inputs[1]); links.new(multiply.outputs[0], bsdf.inputs['Base Color'])
        normal = nodes.new('ShaderNodeNormalMap'); normal.inputs['Strength'].default_value = .65
        links.new(tex['normal'].outputs['Color'], normal.inputs['Color']); links.new(normal.outputs[0], bsdf.inputs['Normal'])
        links.new(tex['roughness'].outputs['Color'], bsdf.inputs['Roughness']); bsdf.inputs['Metallic'].default_value = 0
        materials[key] = material
    def blender(p): return (p[0], -p[2], p[1])
    for part in parts:
        mesh = bpy.data.meshes.new(part['name']+' v2 exact geometry')
        mesh.from_pydata([blender(p) for p in part['positions']], [], [part['indices'][i:i+3] for i in range(0,len(part['indices']),3)])
        mesh.update()
        for polygon in mesh.polygons: polygon.use_smooth = True
        mesh.normals_split_custom_set([blender(n) for n in part['normals']])
        uv = mesh.uv_layers.new(name='UV0_metric_two_metres')
        for loop in mesh.loops: uv.data[loop.index].uv = part['uv'][loop.vertex_index]
        mesh.uv_layers.active_index = 0
        uv.active_render = True
        assert mesh.uv_layers.active == uv
        obj = bpy.data.objects.new(part['name'], mesh); scene.collection.objects.link(obj)
        obj['sourcePath'] = part.get('sourcePath') or ''; obj['material_key'] = part['material']
        mesh.materials.append(materials[part['material']])
    paths[1].write_text(json.dumps(parts,separators=(',',':')))
    manifest['meshFileSha256'] = sha(paths[1])
    # Save this authored scene and dependencies without overwriting another
    # agent's active main .blend or carrying unrelated authoring scenes along.
    bpy.data.libraries.write(str(paths[0]), {scene}, fake_user=True, compress=True)
    manifest['sourceBlendSha256'] = sha(paths[0])
    paths[2].write_text(json.dumps(manifest,indent=2)+'\n')
    assert sha(SOURCE) == SOURCE_SHA256
    print(json.dumps({'parts':len(parts),'triangles':235138,'geometryPreserved':True,
                      'correctedCornerNormals':sum(p['correctedCornerNormals'] for p in manifest['meshAudits']),
                      'outputs':[str(path) for path in paths]}))


if '--audit-only' in sys.argv:
    _, result = prepare_parts()
    destination = OUT/'threshold-v2-offline-preview.json'
    assert not destination.exists(), 'Preserve prior offline preview.'
    destination.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'report':str(destination),'geometryPreserved':True,'triangles':result['triangles'],
                      'correctedCornerNormals':sum(p['correctedCornerNormals'] for p in result['meshAudits'])}))
else:
    author()
