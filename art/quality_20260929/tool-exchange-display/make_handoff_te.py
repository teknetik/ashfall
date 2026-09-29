"""Assemble handoff.json + materials.json from the generated evidence (plain Python, no Blender).

    env -i HOME=$HOME PATH=/usr/bin:/bin /usr/bin/python3 make_handoff_te.py
Inputs: textures/manifest.json, build-stats-raw.json, measurements.json, qc-report.json.
"""
import json
from pathlib import Path

OUT = Path('/home/teknetik/code/ao2/art/quality_20260929/tool-exchange-display')
man = json.loads((OUT / 'textures/manifest.json').read_text())
raw = json.loads((OUT / 'build-stats-raw.json').read_text())
meas = json.loads((OUT / 'measurements.json').read_text())
qc = json.loads((OUT / 'qc-report.json').read_text())
UNITY_PIVOT = [-20.6, 0.5, 9.0]
by_mat = {m['material']: m for m in man['materials']}

mats = []
for slot, r in sorted(raw['materials'].items()):
    fam = by_mat[r['maps']]
    base = r['baseColor']
    glass = slot == 'Glass'
    mats.append({
        'unityMaterialName': 'TE_' + slot,
        'slot': slot,
        'shader': 'Universal Render Pipeline/Lit (metallic workflow)',
        'baseMap': {'file': 'textures/' + base, 'colourSpace': 'sRGB', 'importer': 'Default, sRGB on, mipmaps on, anisotropic >= 8' + (', alpha is transparency' if glass else '')},
        'bumpMap': {'file': 'textures/' + r['normal'], 'colourSpace': 'linear', 'importer': 'Normal map (OpenGL / +Y up; do NOT flip green).'},
        'metallicGlossMap': {'file': 'textures/' + r['metalSmooth'], 'colourSpace': 'linear (sRGB OFF)', 'channels': 'R = metallic, A = smoothness (already 1 - roughness), G/B unused',
                             'urpSetting': 'Smoothness Source = Metallic Alpha'},
        'tilingMetres': r['tileMetres'] if not r['uniqueLayoutUV'] else None,
        'uniqueLayoutUV': r['uniqueLayoutUV'],
        'unityScaleOffset': 'Tiling (1,1) offset (0,0). UV0 already carries metric tiling / the unique layout; do not add material tiling.',
        'emission': r['emission'],
        'alphaMode': ('Transparent (Surface Type = Transparent, Blend = Alpha, ZWrite off, receive shadows off). Base map alpha = film opacity 9..55 percent; render queue after opaque; '
                      'the existing Revision04 opaque WardGlass panes (near-black, unlit look) are what hides the display today, so this material REPLACES them (hide, do not delete).') if glass
                     else 'Opaque',
        'licence': 'Project original, procedurally authored 29 Sep 2026 (make_te_textures.py, numpy); no third-party or generative image content',
        'parentTextureFamily': r['maps'],
        'note': r['note'],
        'sharesNormalAndMetalSmoothWith': None if base.startswith(r['maps'] + '_BaseColor') else r['maps'],
    })
(OUT / 'materials.json').write_text(json.dumps({'note': 'Unity URP Lit mapping for each TE_ slot. Files are relative to art/quality_20260929/tool-exchange-display/.', 'materials': mats}, indent=2))

files = sorted((OUT / 'textures').glob('TE_*.png'))
res = {}
for f in files:
    d = f.read_bytes()[16:24]
    res[f.name] = [int.from_bytes(d[0:4], 'big'), int.from_bytes(d[4:8], 'big')]
used = set()
for m in mats:
    used |= {m['baseMap']['file'].split('/')[-1], m['bumpMap']['file'].split('/')[-1], m['metallicGlossMap']['file'].split('/')[-1]}
used_px = sum(res[u][0] * res[u][1] for u in used)
budget = {'pngFilesOnDisk': len(files), 'distinctMapsReferencedByMaterials': len(used), 'pixelsReferenced': used_px,
          'estimatedVRAM_MiB_BC7_withMips': round(used_px * (4 / 3) / (1024 * 1024), 1),
          'estimatedVRAM_MiB_RGBA32_withMips_ifUncompressed': round(used_px * 4 * (4 / 3) / (1024 * 1024), 1),
          'residentNote': 'Estimate only; nothing measured in Unity. Small-prop families (Twine, Paper, Sand, Stone, Iron, Rubber, ToolSteel, Timber x2, BareSteel x2) are 2048^2 tiling maps '
                          'used on objects a few centimetres across: game-dev should trial 1024 tiles or shared trims for the smallest ones and use mip streaming. Source maps stay at full resolution.'}

notes = {
    'TE_DisplayCase': ('Shadow-board backing (unique 2048 px/m map with painted tool outlines and the ghost of the missing handsaw), timber liners, soffit, shallow bench with skirt, back fence, dust drifts and a palm-polished forearm strip. '
                       'Sits inside the dressed opening behind the existing glazing, against the existing dark recess plane (z 2.435..2.505).',
                       'collider: none. Static, non-interactable, fully inside the closed shell; no interior is walkable.'),
    'TE_PegRail': ('Timber peg rail with six countersunk screws, three rail pegs, the wrench peg, two blank kraft repair tags hung from the empty saw peg, and a cord hank on a spare peg.', 'collider: none.'),
    'TE_ToolPipeWrench': ('Enamel-red pipe wrench (458 mm) hung on a board peg through a real 13 mm bore; cast rib, knurled adjuster, hook-jaw teeth, pivot rivets. Registers with the painted outline.', 'collider: none.'),
    'TE_ToolLumpHammer': ('Lump hammer (306 mm head-to-butt), forged black head with bright struck faces, wedge, palm-polished ash haft; rests on two curl pegs.', 'collider: none.'),
    'TE_ToolBoltCutters': ('Bolt cutters (604 mm) with rubber-dipped grips, forged jaws, replaceable bright blades, pivot bolt; rests on two curl pegs; repair tag on a twine loop round the lower arm.', 'collider: none.'),
    'TE_RestPegs': ('Four curl rest pegs for the hammer haft and the cutter arms.', 'collider: none.'),
    'TE_BenchTools': ('On the bench: whetstone in a timber cradle, cast-iron G-clamp (tag on a twine loop round the T-bar) and a flat file with palm-polished ash handle.', 'collider: none.'),
    'TE_DisplayLamp': ('Swan-neck lamp housing (soffit plate, cast neck, enamel-red shade, brass cap). GEOMETRY ONLY: there is no light and no emissive material in the package; a practical light is a game-dev decision.', 'collider: none.'),
    'TE_ShutterGuide_L': ('Formed steel shutter guide channel on the left masonry reveal: web, rear flange, front flange over the slat edge with return lip, top bracket plate, 11 fixings, and a bare-steel rub plate (0.46 m long, higher on the handle side).', 'collider: none. Front-most z 2.722 = 22 mm proud of the front-wall collider face (z 2.70), 41 mm behind the old lift handles (2.763); the wall collider is unchanged.'),
    'TE_ShutterGuide_R': ('Companion channel on the right reveal; rub plate 0.26 m long (used less).', 'collider: none.'),
    'TE_ShutterHardware': ('Two handle plates with brass D-handles (left plate heavily used, right ~half as much), lock box with brass escutcheon, hasp with padlock (closed through a staple) and a kick plate; unique 2048 px/m atlas carries directional hand wear.', 'collider: none. Protrudes at most 82.8 mm from the slat face (to z 2.738).'),
    'TE_DisplayGlazing': ('The same two panes as revision 04 at the same coordinates (z 2.543..2.577) with clear glass, dust film, edge grime, rain streaks, cloth wipe arcs and fingertip prints (unique RGBA map). Replaces the near-black opaque panes.', 'collider: none.'),
}
parts = []
for name, p in sorted(raw['parts'].items()):
    pv = p['pivotAuthoring']
    parts.append({
        'part': name, 'description': notes[name][0], 'collisionGuidance': notes[name][1],
        'pivotAuthoring_A': pv,
        'pivotUnityLocalToBuilding': [round(-pv[0], 4), round(pv[1], 4), round(pv[2], 4)],
        'orientation': 'Identity rotation, uniform scale 1, no part rotated relative to the building. Front faces +Z (avenue).',
        'sizeMetres_XYZ_A': p['sizeA'], 'boundsA': {'min': p['boundsAmin'], 'max': p['boundsAmax']},
        'lod0': {'glb': f'exports/glb/{name}.glb', 'tris': p['tris'], 'verts': p['verts'], 'materialSlots': p['materialSlots']},
        'lod1': None,
        'qc': {k: qc[f'{name}.glb'][k] for k in ('tris', 'sizeA', 'uvNaN', 'missingUV', 'degenerateUVTris', 'looseVerts', 'nonManifoldEdges', 'negativeDeterminant')},
        'qcMatchesSourceSizeAndTriCount': bool(qc[f'{name}.glb'].get('sizeMatchesSource') and qc[f'{name}.glb'].get('trisMatchSource')),
        'lightmapUV': 'None authored. Static shadow caster only; use light probes. If baking is required generate UV1 in Unity - never reuse UV0 (metric tiling overlaps).',
    })
handoff = {
    'task': 't_3751e0fd', 'date': '2026-09-29', 'author': '3d-modeler',
    'status': 'SOURCE-RENDER REVIEWED ONLY. Not Unity-integrated, not native-verified, not accepted.',
    'target': 'Tool Exchange revision 04 (prefab Assets/AthenHill/Art/Quality/StoreArchitecture/Revision04/tool_exchange/tool_exchange.prefab, scene instance at Unity (-20.6, 0.5, 9.0), yaw 90, scale 1): street-facing recessed display and rolling-shutter surround ONLY',
    'buildingPivotUnity': UNITY_PIVOT, 'buildingYawUnity': 90.0,
    'coordinateConvention': ('Authoring "A-space": building-local metres, +X screen-right when viewed from the avenue, +Y up, +Z toward the avenue, origin = building pivot, Y=0 = porch top. '
                             'GLBs are Y-up in A-space. glTFast imports with an X flip: a part authored at A pivot (px,py,pz) goes to building-local (-px, py, pz) with identity rotation and scale 1. '
                             'Check by eye: the wrench (red) is in the LEFT pane as seen from the avenue, the bolt cutters in the right pane; the padlock is under the lock box, centre of the shutter.'),
    'interchangeAlternative': 'exports/interchange/te-meshes-v1.json: per-material submeshes in A-space relative to each pivot (Unity installer: reflect X, reverse winding, recalc tangents).',
    'supersedesByNamePrefix': ['tool_exchange Recessed tool display dark recess', 'tool_exchange Recessed tool display glass', 'tool_exchange Shutter guide rail', 'tool_exchange Shutter lift handle'],
    'keepUnchanged': ['dressed sills, mineral reveals and mullions of the display (the new glass runs between the existing mullions)', 'all shutter slats (20), ground rail, drum casing, recessed backing, masonry reveals',
                      'sign, awning, masonry shell, roof, clerestory, services, porch and steps, all 5 colliders and the Vex interaction root'],
    'howToRetire': 'Disable (do not delete) the four superseded renderer groups; list is in the review .blend text block te_retired_objects.txt (7 objects).',
    'measurements': meas['overall'] | {'clearances': meas['clearances'], 'attachments': meas['attachments']},
    'parts': parts, 'textureBudget': budget, 'triangleTotals': {'lod0': sum(p['tris'] for p in raw['parts'].values()), 'replacedRevision04Tris': 7 * 98 - 0},
    'lightingNote': 'No emissive materials and no lights in the asset. The display is a closed alcove behind glass and will read dark in shade; the lamp is geometry only.',
}
(OUT / 'handoff.json').write_text(json.dumps(handoff, indent=2, default=str))
print('handoff.json + materials.json written;', budget, handoff['triangleTotals'])
