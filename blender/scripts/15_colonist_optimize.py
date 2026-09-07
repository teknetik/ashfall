"""Geometry-only export preparation for the fitted MPFB colonist.

Call ``result = optimize_colonist(body, rig)`` in Blender. ``result['objects']``
contains the meshes to select alongside the rig for export; ``result['report']``
is JSON-ready. Importing does nothing. Source meshes are retained and hidden
only after a complete successful replacement. No materials, body masks, rig,
animations, scene camera or files are changed.

The head/neck stays connected to the skin. Zero decimation weights lock the
head and its neighbouring vertex ring, rather than creating a neck seam.
Blender's collapse implementation rejects an edge with either endpoint zero:
https://github.com/blender/blender/blob/main/source/blender/bmesh/tools/bmesh_decimate_collapse.cc
"""
import collections
import json
import math
import bpy
import bmesh


OPTIMIZE_TAG = 'colonistOptimizeV1'
PROTECTION_GROUP = '__colonist_reducible_body'
HEAD_WORLD_Z = 1.44


class ColonistOptimizationError(RuntimeError):
    """Carries the full JSON-ready report while keeping MCP errors concise."""

    def __init__(self, stage, report):
        self.report = report
        offenders = []
        for scope, part in [('visual', report), ('shadow', report.get('shadowProxy', {}))]:
            for entry in part.get('objects', []):
                if entry.get('unweightedVertices') or entry.get('invalidUvValues'):
                    offenders.append({'scope': scope, 'mesh': entry['name'],
                        'unweightedVertices': entry.get('unweightedVertices', 0),
                        'invalidUvValues': entry.get('invalidUvValues', 0),
                        'badVertices': entry.get('unweightedExamples', [])[:3],
                        'badUvLoops': entry.get('invalidUvExamples', [])[:3]})
        super().__init__(stage + ': ' + json.dumps({'offenders': offenders,
                                                   'fullReport': 'exception.report'}))


def _triangles(mesh):
    mesh.calc_loop_triangles()
    return len(mesh.loop_triangles)


def _remove_object(obj):
    mesh = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)


def _belongs_to(obj, body, rig):
    if obj.type != 'MESH':
        return False
    if any(m.type == 'ARMATURE' and m.object == rig for m in obj.modifiers):
        return True
    parent = obj.parent
    while parent:
        if parent in (body, rig):
            return True
        parent = parent.parent
    return obj == body


def _activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def _clone(source, rig, created):
    obj = source.copy()
    obj.data = source.data.copy()
    obj.name = 'COLONIST_PREP_' + source.name
    bpy.context.scene.collection.objects.link(obj)
    world = source.matrix_world.copy()
    obj.parent = rig
    obj.matrix_world = world
    obj.hide_render = False
    obj.hide_set(False)
    obj[OPTIMIZE_TAG] = rig.name
    obj['colonistSource'] = source.get('colonistSource', source.name)
    # Only the original skinning modifier is retained. Any other enabled
    # geometry modifier is rejected in preflight, never implicitly baked.
    created.append(obj)
    return obj


def _vertex_signature(obj, indices, bone_names):
    """Protected rest coordinates, all UV seams, and named skin weights."""
    uv_at_vertex = [collections.defaultdict(set) for _ in obj.data.uv_layers]
    for layer_index, layer in enumerate(obj.data.uv_layers):
        for loop in obj.data.loops:
            uv_at_vertex[layer_index][loop.vertex_index].add(tuple(round(x, 7) for x in layer.data[loop.index].uv))
    group_names = {g.index: g.name for g in obj.vertex_groups}
    result = collections.Counter()
    for index in indices:
        vertex = obj.data.vertices[index]
        weights = tuple(sorted((group_names[g.group], round(g.weight, 7))
                               for g in vertex.groups if group_names.get(g.group) in bone_names))
        uv = tuple(tuple(sorted(layer[index])) for layer in uv_at_vertex)
        result[(tuple(round(x, 7) for x in vertex.co), weights, uv)] += 1
    return result


def _decimate(obj, ratio, vertex_group=None):
    before = _triangles(obj.data)
    if ratio >= .999 or before < 12:
        return {'before': before, 'after': before, 'requestedRatio': ratio}
    _activate(obj)
    modifier = obj.modifiers.new('Colonist_export_reduction', 'DECIMATE')
    modifier.decimate_type = 'COLLAPSE'
    modifier.ratio = ratio
    modifier.use_collapse_triangulate = False
    if vertex_group:
        modifier.vertex_group = vertex_group
        modifier.vertex_group_factor = 1.0
        modifier.invert_vertex_group = False
    # Decimate the rest geometry BEFORE the armature, even if idle is currently
    # posed. Applying a modifier after skinning would freeze the current pose.
    while obj.modifiers.find(modifier.name) > 0:
        bpy.ops.object.modifier_move_up(modifier=modifier.name)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    return {'before': before, 'after': _triangles(obj.data), 'requestedRatio': ratio}


def _material_piece(source, material_index, rig, created):
    obj = _clone(source, rig, created)
    mesh = obj.data
    material = mesh.materials[material_index]
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        remove = [f for f in bm.faces if f.material_index != material_index]
        if remove:
            bmesh.ops.delete(bm, geom=remove, context='FACES_ONLY')
        loose = [v for v in bm.verts if not v.link_faces]
        if loose:
            bmesh.ops.delete(bm, geom=loose, context='VERTS')
        for face in bm.faces:
            face.material_index = 0
        bm.to_mesh(mesh)
    finally:
        bm.free()
    mesh.materials.clear()
    mesh.materials.append(material)
    mesh.update()
    return obj


def _geometry_report(objects, rig):
    bone_names = set(rig.data.bones.keys())
    report = {'objects': [], 'triangles': 0, 'skinnedPrimitives': 0,
              'materials': [], 'unweightedVertices': 0, 'maxBoneInfluences': 0,
              'maxWeightSumError': 0.0, 'invalidUvValues': 0}
    materials = set()
    for obj in objects:
        mesh = obj.data
        count = _triangles(mesh)
        used = sorted({p.material_index for p in mesh.polygons})
        names = [mesh.materials[index].name for index in used]
        report['triangles'] += count
        report['skinnedPrimitives'] += len(used)
        materials.update(names)
        groups = {g.index: g.name for g in obj.vertex_groups}
        unweighted, invalid_uv, examples, uv_examples = 0, 0, [], []
        for vertex in mesh.vertices:
            weights = [g.weight for g in vertex.groups if groups.get(g.group) in bone_names and g.weight > 1e-7]
            report['maxBoneInfluences'] = max(report['maxBoneInfluences'], len(weights))
            if not weights:
                report['unweightedVertices'] += 1
                unweighted += 1
                if len(examples) < 6:
                    examples.append({'index': vertex.index, 'restPosition': list(vertex.co),
                                     'groups': [{'name': groups.get(g.group, 'MISSING_GROUP_' + str(g.group)),
                                                 'weight': g.weight} for g in vertex.groups]})
            else:
                report['maxWeightSumError'] = max(report['maxWeightSumError'], abs(sum(weights) - 1))
        for layer in mesh.uv_layers:
            for index, entry in enumerate(layer.data):
                if not all(math.isfinite(v) for v in entry.uv):
                    invalid_uv += 1
                    if len(uv_examples) < 6:
                        uv_examples.append({'layer': layer.name, 'loop': index, 'uv': list(entry.uv)})
        report['invalidUvValues'] += invalid_uv
        report['objects'].append({'name': obj.name, 'triangles': count,
                                  'vertices': len(mesh.vertices), 'materials': names,
                                  'uvLayers': [u.name for u in mesh.uv_layers],
                                  'source': obj.get('colonistSource', obj.name),
                                  'unweightedVertices': unweighted, 'invalidUvValues': invalid_uv,
                                  'unweightedExamples': examples, 'invalidUvExamples': uv_examples})
    report['materials'] = sorted(materials)
    return report


def _shadow_proxy(visuals, rig, created, triangle_limit=3000):
    """One opaque, genuinely decimated skinned mesh for shadow rendering."""
    pieces = [_clone(source, rig, created) for source in visuals]
    active = pieces[0]
    _activate(active)
    for piece in pieces:
        piece.select_set(True)
    if len(pieces) > 1:
        bpy.ops.object.join()
    active.name = 'COLONIST_shadow_proxy'
    material = bpy.data.materials.get('MAT_colonist_armour_graphite') or active.data.materials[0]
    active.data.materials.clear()
    active.data.materials.append(material)
    for poly in active.data.polygons:
        poly.material_index = 0
    before = _triangles(active.data)
    reduction = _decimate(active, min(1.0, 2600 / before))
    if reduction['after'] > triangle_limit:
        raise RuntimeError('Shadow proxy exceeds the 3,000 triangle cap')
    active['shadowProxy'] = True
    active['assetRole'] = 'skinned_shadow_proxy'
    active['shadowTriangleCount'] = reduction['after']
    active.hide_render = True
    active.display_type = 'WIRE'
    return active, reduction


def optimize_colonist(body, rig, body_ratio=.34, hair_ratio=.38, max_primitives=8):
    """Return optimized, same-material skin batches and measured counts.

    No source object is deleted. Re-running against the original ``body``
    replaces only outputs tagged for this rig; it never decimates an already
    reduced mesh. Head preservation and bone/UV integrity are verified before
    the replacement is made visible. Material consolidation stays the caller's
    responsibility when the source has more than ``max_primitives`` materials.
    """
    if body.type != 'MESH' or rig.type != 'ARMATURE':
        raise TypeError('Expected a source body mesh and its armature')
    if body.get(OPTIMIZE_TAG):
        raise ValueError('Pass the original source body, not an optimized output')
    if bpy.context.mode != 'OBJECT':
        raise ValueError('Return to Object mode before geometry optimization')
    if not .1 <= body_ratio <= 1 or not .1 <= hair_ratio <= 1:
        raise ValueError('Reduction ratios must be between .1 and 1')
    sources = [obj for obj in bpy.context.scene.objects if _belongs_to(obj, body, rig)
               and not obj.get(OPTIMIZE_TAG)]
    if body not in sources:
        raise ValueError('Source body is not in the current scene')
    # The source skin's brows are too faint in the actual portrait. Preserve
    # the separate authored brow cards; the caller owns their alpha/material.
    eyebrows = [obj for obj in sources if 'eyebrow001' in obj.name.lower()]
    omitted = []
    chosen = list(sources)
    for obj in chosen:
        if obj.data.shape_keys:
            raise ValueError('Freeze fitted shape keys first: ' + obj.name)
        if any(m.type != 'ARMATURE' and m.show_viewport for m in obj.modifiers):
            raise ValueError('Resolve non-skinning modifiers explicitly first: ' + obj.name)
        if not any(m.type == 'ARMATURE' and m.object == rig for m in obj.modifiers):
            raise ValueError('Actor mesh lacks an armature modifier: ' + obj.name)
        if not len(obj.data.materials) or any(not mat for mat in obj.data.materials):
            raise ValueError('Resolve empty material slots first: ' + obj.name)
    source_counts = {obj.name: _triangles(obj.data) for obj in sources}
    source_integrity = _geometry_report(chosen, rig)
    if source_integrity['unweightedVertices'] or source_integrity['invalidUvValues']:
        raise ColonistOptimizationError('Original source geometry is invalid before optimization', source_integrity)
    original_matrices = {obj.name: obj.matrix_world.copy() for obj in sources}
    created, reduced, batches = [], [], []
    shadow = None
    old_selection = list(bpy.context.selected_objects)
    old_active = bpy.context.view_layer.objects.active
    old_outputs = [obj for obj in bpy.context.scene.objects if obj.get(OPTIMIZE_TAG) == rig.name]
    reduction, protection = {}, {}
    try:
        for source in chosen:
            obj = _clone(source, rig, created)
            if source == body:
                high = {v.index for v in obj.data.vertices if (obj.matrix_world @ v.co).z >= HEAD_WORLD_Z}
                if not high:
                    raise ValueError('No head above world Z=1.44; verify character scale/origin')
                # Every face touching the head threshold is protected in full,
                # including one contiguous neck boundary ring below the cut.
                protected = set(high)
                for poly in obj.data.polygons:
                    if any(index in high for index in poly.vertices):
                        protected.update(poly.vertices)
                reducible = [v.index for v in obj.data.vertices if v.index not in protected]
                before_signature = _vertex_signature(obj, protected, set(rig.data.bones.keys()))
                protected_tris = sum(len(p.vertices) - 2 for p in obj.data.polygons
                                     if all(index in protected for index in p.vertices))
                total = _triangles(obj.data)
                target = protected_tris + (total - protected_tris) * body_ratio
                group = obj.vertex_groups.new(name=PROTECTION_GROUP)
                group.add(reducible, 1.0, 'REPLACE')
                reduction[source.name] = _decimate(obj, target / total, group.name)
                obj.vertex_groups.remove(obj.vertex_groups[group.name])
                after_signature = _vertex_signature(obj, range(len(obj.data.vertices)), set(rig.data.bones.keys()))
                missing = before_signature - after_signature
                protection = {'worldCutHeight': HEAD_WORLD_Z, 'protectedVertices': len(protected),
                              'protectedTriangles': protected_tris, 'requestedCoveredBodyRatio': body_ratio,
                              'missingProtectedSignatures': sum(missing.values()),
                              'coordinatesUvsWeightsUnchanged': not missing}
                if missing:
                    raise RuntimeError('Decimation changed protected head/neck geometry, UVs or weights')
            elif 'hair' in source.name.lower():
                reduction[source.name] = _decimate(obj, hair_ratio)
            reduced.append(obj)

        reduction_integrity = _geometry_report(reduced, rig)
        if reduction_integrity['unweightedVertices'] or reduction_integrity['invalidUvValues']:
            raise ColonistOptimizationError('Rest-mesh decimation introduced invalid geometry data', reduction_integrity)

        # Split only by material, after geometric reduction, then join matching
        # material/UV layouts. This preserves the actual existing shader setup
        # and avoids introducing vertex colours into skin/hair primitives.
        groups = collections.defaultdict(list)
        for obj in reduced:
            for material_index in sorted({p.material_index for p in obj.data.polygons}):
                piece = _material_piece(obj, material_index, rig, created)
                mat = piece.data.materials[0]
                key = (mat.as_pointer(), tuple(layer.name for layer in piece.data.uv_layers),
                       tuple((a.name, a.domain, a.data_type) for a in piece.data.color_attributes))
                groups[key].append(piece)
        for pieces in groups.values():
            active = pieces[0]
            if len(pieces) > 1:
                _activate(active)
                for piece in pieces:
                    piece.select_set(True)
                bpy.ops.object.join()
            active.name = 'COLONIST_OPT_' + active.data.materials[0].name.removeprefix('MAT_')
            batches.append(active)
        shadow, shadow_reduction = _shadow_proxy(batches, rig, created)
        for obj in list(created):
            # Joined objects may already have been freed by Blender.
            try:
                if obj.name in bpy.data.objects and obj not in batches and obj != shadow:
                    _remove_object(obj)
            except ReferenceError:
                pass
        report = _geometry_report(batches, rig)
        shadow_report = _geometry_report([shadow], rig)
        report.update({'sourceTriangles': sum(source_counts.values()), 'sourceObjects': source_counts,
                       'omittedEyebrows': [], 'retainedEyebrows': [obj.name for obj in eyebrows],
                       'reduction': reduction,
                       'headProtection': protection, 'targetTriangles': [29000, 32000],
                       'triangleTargetMet': 29000 <= report['triangles'] <= 32000,
                       'primitiveLimit': max_primitives,
                       'primitiveTargetMet': report['skinnedPrimitives'] <= max_primitives,
                       'sourcesRetained': True, 'shadowProxy': shadow_report,
                       'shadowReduction': shadow_reduction,
                       'totalExportTriangles': report['triangles'] + shadow_report['triangles'],
                       'totalExportLimit': 40000,
                       'totalExportTargetMet': report['triangles'] + shadow_report['triangles'] <= 40000})
        if report['unweightedVertices'] or report['invalidUvValues'] or shadow_report['unweightedVertices']:
            raise ColonistOptimizationError('Material batching or shadow reduction introduced invalid geometry data', report)
        if report['skinnedPrimitives'] > max_primitives:
            report['materialActionRequired'] = 'Caller must consolidate source materials; no material was replaced.'
        for source in sources:
            if any(abs(source.matrix_world[r][c] - original_matrices[source.name][r][c]) > 1e-8
                   for r in range(4) for c in range(4)):
                raise RuntimeError('A source object transform changed')
        # Commit the reversible replacement only after its geometry validates.
        for old in old_outputs:
            _remove_object(old)
        # Previous output names existed during the transactional build, so
        # Blender may have suffixed the replacements. Restore stable names
        # after removing the old generation, and update the measured ledger.
        for obj, entry in zip(batches, report['objects']):
            obj.name = 'COLONIST_OPT_' + obj.data.materials[0].name.removeprefix('MAT_')
            entry['name'] = obj.name
        shadow.name = 'COLONIST_shadow_proxy'
        shadow_report['objects'][0]['name'] = shadow.name
        for source in sources:
            if 'colonistSourceVisibility' not in source:
                source['colonistSourceVisibility'] = json.dumps({'render': source.hide_render, 'viewport': source.hide_get()})
            source.hide_render = True
            source.hide_set(True)
        for obj in batches:
            obj.hide_render = False
            obj.hide_set(False)
        rig['colonistOptimizedObjects'] = json.dumps([obj.name for obj in batches] + [shadow.name])
        return {'objects': batches, 'shadowProxy': shadow,
                'exportObjects': batches + [shadow], 'report': report}
    except Exception:
        for obj in reversed(created):
            try:
                if obj.name in bpy.data.objects:
                    _remove_object(obj)
            except ReferenceError:
                pass
        raise
    finally:
        bpy.ops.object.select_all(action='DESELECT')
        for obj in old_selection:
            try:
                if obj.name in bpy.context.view_layer.objects:
                    obj.select_set(True)
            except ReferenceError:
                pass
        try:
            if old_active and old_active.name in bpy.context.view_layer.objects:
                bpy.context.view_layer.objects.active = old_active
        except ReferenceError:
            pass
