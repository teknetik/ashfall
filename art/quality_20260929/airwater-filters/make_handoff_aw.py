"""Assemble handoff.json + materials.json for the Air + Water filter fittings (plain Python, no Blender).

    env -i HOME=$HOME PATH=/usr/bin:/bin /usr/bin/python3 make_handoff_aw.py
Inputs: textures/manifest.json, textures/layout.json, build-stats-raw.json, measurements.json, qc-report.json.
"""
import json
from pathlib import Path

OUT = Path('/home/teknetik/code/ao2/art/quality_20260929/airwater-filters')
man = json.loads((OUT / 'textures/manifest.json').read_text())
raw = json.loads((OUT / 'build-stats-raw.json').read_text())
meas = json.loads((OUT / 'measurements.json').read_text())
qc = json.loads((OUT / 'qc-report.json').read_text())
layout = json.loads((OUT / 'textures/layout.json').read_text())
by_mat = {m['material']: m for m in man['materials']}
UNITY_PIVOT = [-20.6, 0.5, 9.0]

mats = []
for slot, r in sorted(raw['materials'].items()):
    fam = by_mat[r['maps']]
    unique = r['uniqueLayoutUV']
    mats.append({
        'unityMaterialName': 'AW_' + slot, 'slot': slot,
        'shader': 'Universal Render Pipeline/Lit (metallic workflow)',
        'baseMap': {'file': 'textures/' + r['baseColor'], 'colourSpace': 'sRGB', 'importer': 'Default, sRGB on, mipmaps on, anisotropic >= 8'},
        'bumpMap': {'file': 'textures/' + r['normal'], 'colourSpace': 'linear', 'importer': 'Normal map (OpenGL / +Y up; do NOT flip green).'},
        'metallicGlossMap': {'file': 'textures/' + r['metalSmooth'], 'colourSpace': 'linear (sRGB OFF)',
                             'channels': 'R = metallic, A = smoothness (already 1 - roughness), G/B unused', 'urpSetting': 'Smoothness Source = Metallic Alpha'},
        'tilingMetres': None if unique else r['tileMetres'],
        'uniqueLayoutUV': unique,
        'unityScaleOffset': 'Tiling (1,1) offset (0,0). UV0 already carries metric tiling / the unique layout; do not add material tiling.',
        'emission': r['emission'], 'alphaMode': 'Opaque',
        'licence': 'Project original, procedurally authored 29 Sep 2026 (make_aw_textures.py, numpy); lettering from Liberation Sans Bold (SIL OFL 1.1); no third-party or generative image content',
        'note': r['note'], 'sizes': {k: [v['width'], v['height']] for k, v in fam['maps'].items()},
    })
(OUT / 'materials.json').write_text(json.dumps({'note': 'Unity URP Lit mapping for each AW_ slot. Files are relative to art/quality_20260929/airwater-filters/.', 'materials': mats}, indent=2))

used = set()
res = {}
for m in mats:
    for k in ('baseMap', 'bumpMap', 'metallicGlossMap'):
        f = m[k]['file'].split('/')[-1]
        used.add(f)
for f in used:
    d = (OUT / 'textures' / f).read_bytes()[16:24]
    res[f] = [int.from_bytes(d[0:4], 'big'), int.from_bytes(d[4:8], 'big')]
px = sum(w * h for w, h in res.values())
budget = {'pngFilesReferenced': len(used), 'pixelsReferenced': px, 'estimatedVRAM_MiB_BC7_withMips': round(px * (4 / 3) / (1024 * 1024), 1),
          'estimatedVRAM_MiB_RGBA32_withMips_ifUncompressed': round(px * 4 * (4 / 3) / (1024 * 1024), 1),
          'residentNote': 'Estimate only; nothing measured in Unity. Tiling maps are 2048^2 on fittings a few centimetres to 0.3 m across (texel density 4096-6800 px/m); '
                          'game-dev should trial 1024 for AW_Rubber / AW_Steel / AW_Mineral and use mip streaming. Source maps stay at full resolution.'}

notes = {
    'AW_FilterMount_1': 'Vessel 1 (x 0.9): two hoop straps (y 0.78 / 1.50) with rubber liners, anchored ears and a tension lug on the right-hand front; U-cradle under the bottom collar with two gusseted wall plates; curved FILTER 1 plate; HOSE outlet (union, elbow, hose tail, rubber hose, worm-drive clamp); inlet UNION with rubber gasket; mineral crust, stalactites and vessel-skin runs.',
    'AW_FilterMount_2': 'Vessel 2 (x 1.7): straps at y 0.83 / 1.56 (left-hand lug on the lower, right on the upper); cradle plates 30 mm higher and bedded on steel packers because they straddle a 43 mm plaster spall; FILTER 2 plate; CAPPED outlet (union, elbow, gasketed cap); bolted gasketed FLANGE inlet with a domed reducer.',
    'AW_FilterMount_3': 'Vessel 3 (x 2.5): straps at y 0.80 / 1.53; FILTER 3 plate; 45-degree drain BEND ending in a gasketed 4-bolt flange (drips at the mouth); inlet union, reducing bush and a capped vent stub.',
    'AW_FilterHeader': 'New DN60 header (x 0.552..3.09) replacing the old manifold + wall-mount bars: blanked left end, three tees with dropped bosses, two wall-anchored hangers (rubber-lined / bare), flanged isolation ball valve with red lever (open, along the pipe), bottom-entry pressure gauge (unique dial map, needle 2.6 bar, red limit flag 4.5 bar), 45-degree set to the riser and an ISOLATE plate (SHUT | OPEN) on the wall.',
    'AW_FeedRiser': 'Union at the header joint, elbow, riser at the existing axis (x 3.18, z 3.03) with a gasketed 4-bolt flange joint at y 2.95, roof turns (R 0.12) and an end flange at the existing roof pipe (x 1.7, y 7.08, z 0.80). Existing retaining clamps, stand-offs and masonry anchors on the riser are kept as they are.',
}
guidance = {n: 'collider: none. Static, non-interactable; all parts lie in front of the wall plane (z 2.73) inside the 3.23 m front line; no walkable interior.' for n in notes}
parts = []
for name, p in sorted(raw['parts'].items()):
    pv = p['pivotAuthoring']
    q = qc[f'{name}.glb']
    parts.append({
        'part': name, 'description': notes[name], 'collisionGuidance': guidance[name], 'pivotAuthoring_A': pv,
        'pivotUnityLocalToBuilding': [round(-pv[0], 4), round(pv[1], 4), round(pv[2], 4)],
        'orientation': 'Identity rotation, uniform scale 1, no part rotated relative to the building. Front faces +Z (avenue).',
        'sizeMetres_XYZ_A': p['sizeA'], 'boundsA_absolute': {'min': p['boundsAmin'], 'max': p['boundsAmax']},
        'lod0': {'glb': f'exports/glb/{name}.glb', 'tris': p['tris'], 'verts': p['verts'], 'materialSlots': p['materialSlots']}, 'lod1': None,
        'qc': {k: q[k] for k in ('tris', 'sizeA', 'uvNaN', 'missingUV', 'degenerateUVTris', 'looseVerts', 'nonManifoldEdges', 'negativeDeterminant')},
        'qcMatchesSourceSizeAndTriCount': bool(q.get('sizeMatchesSource') and q.get('trisMatchSource')),
        'lightmapUV': 'None authored. Static shadow caster only; use light probes. If baking is required generate UV1 in Unity - never reuse UV0 (metric tiling overlaps).',
    })
retired = ['air_water Filter manifold', 'air_water Filter manifold inlet 0.9', 'air_water Filter manifold inlet 1.7', 'air_water Filter manifold inlet 2.5',
           'air_water Filter wall mount 0.9', 'air_water Filter wall mount 1.7', 'air_water Filter wall mount 2.5', 'air_water Roof to filter downfeed']
handoff = {
    'task': 't_bd3d9fe3', 'date': '2026-09-29', 'author': '3d-modeler',
    'status': 'SOURCE-RENDER REVIEWED ONLY. Not Unity-integrated, not native-verified, not accepted.',
    'target': 'Air + Water revision 04 (prefab Assets/AthenHill/Art/Quality/StoreArchitecture/Revision04/air_water/air_water.prefab, scene instance at Unity (-20.6, 0.5, 9.0), yaw 90, scale 1): the three exterior filter vessels right of the door and their visible connections ONLY',
    'buildingPivotUnity': UNITY_PIVOT, 'buildingYawUnity': 90.0,
    'coordinateConvention': ('Authoring "A-space": building-local metres, +X screen-right when viewed from the avenue, +Y up, +Z toward the avenue, origin = building pivot, Y=0 = porch top. '
                             'GLBs are Y-up in A-space. glTFast imports with an X flip: a part authored at A pivot (px,py,pz) goes to building-local (-px, py, pz) with identity rotation and scale 1. '
                             'Check by eye from the avenue: FILTER 1 is nearest the door, FILTER 3 furthest; the red valve lever and gauge are at the far (right) end, the riser drops from the roof beyond them.'),
    'interchangeAlternative': 'exports/interchange/aw-meshes-v1.json: per-material submeshes in A-space relative to each pivot (Unity installer: reflect X, reverse winding, recalc tangents).',
    'supersedesByNamePrefix': retired,
    'keepUnchanged': ['the three canisters (silhouettes, position, 9 Sep surface pass) and their retainer collars', 'Feed retaining clamps / stand-offs / masonry anchors on the riser (y 2.4, 3.9, 5.8)',
                      'Vessel feed / Twin vessel cross feed / feed flanges on the roof', 'rainwater pipe and its clamps', 'facade masonry, door and its surround, awning, sign, roof, all colliders and the interaction roots'],
    'howToRetire': 'Disable (do not delete) the eight superseded renderers (listed above; text block aw_retired_objects.txt in airwater-filters-source-v1.blend). All 65 bank renderers are already m_Enabled=0 in the saved scene instance because they are baked into render chunks: run Show Sources, disable these eight, install the five prefab modules, then Rebuild Render Chunks.',
    'labels': {'file': 'textures/layout.json', 'note': 'Plates are baked into UV space of AW_Labels; lettering is FILTER 1/2/3, ISOLATE, SHUT | OPEN only. No lore.'},
    'measurements': meas['overall'] | {'clearances': meas['clearances'], 'attachments': meas['attachments']},
    'parts': parts, 'textureBudget': budget,
    'triangleTotals': {'lod0': sum(p['tris'] for p in raw['parts'].values()), 'replaced9SepTris': None},
    'sourceWarnings': raw.get('warnings', []),
    'lightingNote': 'No emissive materials and no lights in the asset. The gauge dial is not emissive.',
}
(OUT / 'handoff.json').write_text(json.dumps(handoff, indent=2, default=str))
print('handoff.json + materials.json written;', budget, handoff['triangleTotals'])
