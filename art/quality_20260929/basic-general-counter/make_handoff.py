"""Assemble handoff.json + materials.json from the generated evidence (plain Python, no Blender).

    env -i HOME=$HOME PATH=/usr/bin:/bin /usr/bin/python3 make_handoff.py
Inputs: textures/manifest.json, build-stats-raw.json, measurements.json, qc-report.json, exports/interchange/bgc-meshes-v1.json
"""
import json, hashlib
from pathlib import Path

OUT = Path('/home/teknetik/code/ao2/art/quality_20260929/basic-general-counter')
man = json.loads((OUT / 'textures/manifest.json').read_text())
raw = json.loads((OUT / 'build-stats-raw.json').read_text())
meas = json.loads((OUT / 'measurements.json').read_text())
qc = json.loads((OUT / 'qc-report.json').read_text())
UNITY_PIVOT = [8.0, 0.5, 15.1]
by_mat = {m['material']: m for m in man['materials']}

# ----- materials.json: one Unity material per slot, mapped to texture files and Unity property names
mats = []
for slot, r in sorted(raw['materials'].items()):
    fam = by_mat[r['maps']]
    base = r['baseColor']
    mats.append({
        'unityMaterialName': 'BGC_' + slot,
        'slot': slot,
        'shader': 'Universal Render Pipeline/Lit (metallic workflow)',
        'baseMap': {'file': 'textures/' + base, 'colourSpace': 'sRGB', 'importer': 'Default, sRGB on, mipmaps on, anisotropic >= 8'},
        'bumpMap': {'file': 'textures/' + r['normal'], 'colourSpace': 'linear', 'importer': 'Normal map (OpenGL / +Y up; do NOT flip green). Unity default handling is correct.'},
        'metallicGlossMap': {'file': 'textures/' + r['metalSmooth'], 'colourSpace': 'linear (sRGB OFF)', 'channels': 'R = metallic, A = smoothness (already smoothness = 1 - roughness), G/B unused',
                             'urpSetting': 'Smoothness Source = Metallic Alpha'},
        'tilingMetres': r['tileMetres'] if not r['uniqueLayoutUV'] else None,
        'uniqueLayoutUV': r['uniqueLayoutUV'],
        'unityScaleOffset': 'Tiling (1,1) offset (0,0). UV0 already carries metric tiling; do not add material tiling.',
        'emission': r['emission'],
        'alphaMode': 'Opaque (no alpha-blended or cut-out materials in this package)',
        'licence': 'Project original, procedurally authored 29 Sep 2026 (make_textures.py, numpy); no third-party or generative image content',
        'parentTextureFamily': r['maps'],
        'note': r['note'],
        'sharesNormalAndMetalSmoothWith': None if base.startswith(r['maps'] + '_BaseColor') else r['maps'],
    })
(OUT / 'materials.json').write_text(json.dumps({'note': 'Unity URP Lit mapping for each BGC_ slot. Files are relative to art/quality_20260929/basic-general-counter/.',
                                                'materials': mats}, indent=2))

# ----- texture memory (uncompressed vs BC7/DXT5 estimate incl. full mip chain)
files = sorted((OUT / 'textures').glob('BGC_*.png'))
tot_px = 0
res = {}
for f in files:
    d = f.read_bytes()[16:24]
    w = int.from_bytes(d[0:4], 'big'); h = int.from_bytes(d[4:8], 'big')
    res[f.name] = [w, h]
    tot_px += w * h
bc7_mib = tot_px * 1.0 * (4 / 3) / (1024 * 1024)          # BC7 = 8 bpp, +33% mips
rgba_mib = tot_px * 4 * (4 / 3) / (1024 * 1024)
# how many maps are actually referenced (variants without their own normal are shared)
used = set()
for m in mats:
    used |= {m['baseMap']['file'].split('/')[-1], m['bumpMap']['file'].split('/')[-1], m['metallicGlossMap']['file'].split('/')[-1]}
used_px = sum(res[u][0] * res[u][1] for u in used)
budget = {'pngFilesOnDisk': len(files), 'distinctMapsReferencedByMaterials': len(used), 'pixelsReferenced': used_px,
          'estimatedVRAM_MiB_BC7_withMips': round(used_px * (4 / 3) / (1024 * 1024), 1), 'estimatedVRAM_MiB_RGBA32_withMips_ifUncompressed': round(used_px * 4 * (4 / 3) / (1024 * 1024), 1),
          'residentNote': 'Estimate only. Mip streaming should keep far mips resident only until the player is near Mira. Unity mip streaming / VRAM measurement is game-dev\'s to verify.'}

# ----- handoff.json
parts = []
notes = {
    'BGC_Counter': ('Counter box + steel-clad top with rolled nosing, three bays with raised stiles, service-hatch handle, hasp + closed padlock, 12+7x2 domed fixings, '
                    'rubber end guards/kick strip and banked dust. Replaces: Counter repair fascia, Counter inset plates + rivets, Service ledge, Counter working lip, Counter grip paint loss.',
                    'collider: none needed (existing back collider already fills the wall). Optional: one BoxCollider 4.24x0.94x0.38 at wall if the kiosk should physically stop the player leaning in - NOT required; the porch collider is upstream of this.'),
    'BGC_ShelfBay_L': ('Left shelf bay stock: 2 steel shelves with rolled lips/down-turns/gussets/back angles, bottle-stop rail, olla jar, 3 flasks/bottles, medkits, roll pack, tags, dust. '
                       'Replaces the left half of: Stock shelf x3, Sealed goods tin (x6) and lids/labels.', 'collider: none. Static, non-interactable.'),
    'BGC_ShelfBay_R': ('Right shelf bay: 2 steel shelves, copper wire hanks with twine ties, wire spool, ochre cable coil, canteen, bottles, medkit, tags, dust. '
                       'Replaces the right half of the same old stock objects.', 'collider: none.'),
    'BGC_HookRail_L': ('Wall rail with 5 S-hooks: sling canteen, bottle, hung first-aid kit, tag, copper hank (all on twine bights).', 'collider: none.'),
    'BGC_HookRail_R': ('Wall rail with 5 S-hooks: slate cable coil, roll pack, two copper hanks, tag, red flask.', 'collider: none.'),
    'BGC_CounterProps': ('Counter-top merchandise: sample flask rack (3 flasks), medkit stack, ledger with tie, closed cash tin with hasp, receipt spike with slips, rubber sale mat with copper hank, brass balance scale, loose slips, dust at the wall line.',
                         'collider: none. Do NOT add mesh colliders; these sit behind the service line at least 1.29 m from Mira\'s root.'),
}
for name, p in sorted(raw['parts'].items()):
    pv = p['pivotAuthoring']
    parts.append({
        'part': name,
        'description': notes[name][0],
        'collisionGuidance': notes[name][1],
        'pivotAuthoring_A': pv,
        'pivotUnityLocalToBuilding': [-pv[0], pv[1], pv[2]],
        'pivotUnityWorld_atBuildingPivot_8_0p5_15p1': [round(UNITY_PIVOT[0] - pv[0], 4), round(UNITY_PIVOT[1] + pv[1], 4), round(UNITY_PIVOT[2] + pv[2], 4)],
        'orientation': 'Identity rotation, uniform scale 1. Front faces +Z (avenue). No part is rotated relative to the building.',
        'sizeMetres_XYZ_A': p['sizeA'],
        'boundsA': {'min': p['boundsAmin'], 'max': p['boundsAmax']},
        'lod0': {'glb': f'exports/glb/{name}.glb', 'tris': p['tris'], 'verts': p['verts'], 'materialSlots': p['materialSlots']},
        'lod1': ({'glb': f'exports/glb/{name}_LOD1.glb', 'tris': qc[f'{name}_LOD1.glb']['tris'], 'note': 'decimated (collapse, material/UV/seam-delimited), reviewed vs LOD0 at 3 / 6 / 12 m - see README'} if f'{name}_LOD1.glb' in qc else None),
        'qc': {k: qc[f'{name}.glb'][k] for k in ('tris', 'sizeA', 'uvNaN', 'missingUV', 'degenerateUVTris', 'looseVerts', 'nonManifoldEdges', 'negativeDeterminant')},
        'qcMatchesSourceSizeAndTriCount': bool(qc[f'{name}.glb'].get('sizeMatchesSource') and qc[f'{name}.glb'].get('trisMatchSource')),
        'lightmapUV': 'None authored. Set static-shadow-caster only, no lightmap contribution; use light probes. If baking is required, generate UV1 in Unity (Generate Lightmap UVs) - do not reuse UV0 (metric tiling overlaps).',
    })
handoff = {
    'task': 't_84b69b7e', 'date': '2026-09-29', 'author': '3d-modeler',
    'status': 'SOURCE-RENDER REVIEWED ONLY. Not Unity-integrated, not native-verified, not accepted.',
    'target': 'Basic General authored frontage (scene root "Basic General authored frontage", prefab Assets/AthenHill/Art/Phase1/BasicGeneral/Revision03/BasicGeneral.prefab), Mira service recess only',
    'buildingPivotUnity': UNITY_PIVOT, 'frontUnity': [0, 0, 1],
    'coordinateConvention': ('Authoring "A-space": building-local metres, +X screen-right when viewed from the avenue, +Y up, +Z toward the avenue, origin = building pivot, Y=0 = porch top. '
                             'GLB files are Y-up in A-space. glTFast imports GLB with an X flip, so a part placed under the building root at local (Ax, Ay, Az) arrives at Unity local (-Ax, Ay, Az) - '
                             'i.e. the project rule Blender(x,y,z)->Unity(-x,z,-y) with A==(x,z_b,-y_b). Place each part with position (-pivotA.x, pivotA.y, pivotA.z) relative to the building root, identity rotation, scale 1. '
                             'Verify by checking the counter sits against the rear wall and left/right shelf bays are the correct way round (left bay = olla jar + blue canteen; right bay = copper hanks + spool).'),
    'interchangeAlternative': ('exports/interchange/bgc-meshes-v1.json has per-material submeshes in A-space relative to each pivot, in the same layout as the Basic General v3 interchange, '
                               'for use with the existing Editor-only prepare/install approach (reflect X, reverse winding, regenerate tangents). Prefer this over GLB if you need native .asset meshes + GUID stability.'),
    'supersedesByNamePrefix': ['Sealed goods tin', 'Tin rolled lid', 'Tin label', 'Stock exact label', 'Stock shelf', 'Counter repair fascia', 'Counter inset plate',
                               'Counter plate rivet', 'Service ledge', 'Counter working lip', 'Counter grip paint loss'],
    'keepUnchanged': ['Stock recessed cabinet -1.72 / 1.72 (back panels behind the shelves - the new shelves are designed to sit in front of them)', 'Supplies service title (wall lettering)',
                      'Sign, awning, masonry, porch, step, all six colliders, Mira root (A 0,0,0.7 = Unity 8,0.5,15.8), rear wall and rear services'],
    'howToRetire': 'Disable/hide the superseded renderers (keep them in the prefab for rollback); do not delete. The list is also stored in the review .blend text block "bgc_retired_objects.txt" (90 objects).',
    'measurements': meas['reference'] | {'overall': meas['overall'], 'clearances': {k: v for k, v in meas['clearances'].items() if k != 'preservedColliders'}},
    'parts': parts, 'textureBudget': budget, 'triangleTotals': {'lod0': sum(p['tris'] for p in raw['parts'].values()),
                                                                'lod1_where_provided': sum(qc[f'{p}_LOD1.glb']['tris'] if f'{p}_LOD1.glb' in qc else raw['parts'][p]['tris'] for p in raw['parts']),
                                                                'replacedOldStockAndCounterTris_approx': None},
    'lightingNote': 'No emissive materials and no lights are part of the asset. Any local practical light is an integration decision for game-dev (see README section 8).',
}
(OUT / 'handoff.json').write_text(json.dumps(handoff, indent=2, default=str))
print('handoff.json + materials.json written;', budget)
