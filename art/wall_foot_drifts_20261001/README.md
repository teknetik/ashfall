# Wall-foot sand and grounding (1 October 2026)

Art-direction review item 6 (30 Sep, `next-wins.md`): "where buildings meet the paving the junction is knife-clean: no
banked sand, no dust shadow, no splash grime". Verified on the cited stills (`SD-F/cam_sd_repairs_tea-h13.00`,
`cam_sd_field_supply-h13.00`, `hall-district/20260930/after-native/cam_district_field-h12.00`) and the batch-1 paving
captures: the 30 Sep shops, booth, hall and hill each carry a 5 cm, LOD0-only sand wedge that is invisible beyond a few
metres. This pass adds visible, wind-laid sand at the feet of the avenue-ring buildings, posts and steps, plus dust and
grime decals. Unity side: `Assets/AthenHill/Editor/WallFootDriftsPass.cs`. Evidence:
`unity/evidence/wall-foot-drifts/20261001/`. Nothing here is accepted by Carl yet.

## What is built

**Kit** (`author_drift_kit.py` → `Art/WallFootDrifts/Models/WFD_Kit.glb`, prefabs `Prefabs/WallFootDrifts/WFD_<piece>`):
eight height-field sand pieces authored in Unity metres (x along the wall, z out of the face, origin on the wall-foot
line), sunk 8 mm with the field falling smoothly below the paving past the toe, so the visible edge is the noisy contour
where the sand crosses the paving (no tangent sliver, no stair-stepped edge); back rows run 5 cm into the wall.

| Piece | Size (m) | Peak (m) | Triangles LOD0 / 1 / 2 | Use |
| --- | --- | --- | --- | --- |
| Run_L | 1.6 x 0.5 | 0.13 | 774 / 160 / 42 | windward banks, three lobes |
| Run_M | 1.1 x 0.35 | 0.10 | 416 / 90 / 32 | general banks |
| Run_S | 0.7 x 0.28 | 0.06 | 188 / 44 / 16 | step-riser ends, tread pockets, short stretches |
| Run_Low | 1.5 x 0.17 | 0.02 | 332 / 80 / 26 | broken dusting between banks |
| Corner_L | 1.1 x 1.05 | 0.18 | 448 / 184 / 58 | inside corners (hill stair cheeks, hall podium) |
| Corner_S | 0.6 x 0.57 | 0.10 | 250 / 70 / 26 | porch/step junctions, hall deck pier corners |
| Post | 0.84 x 1.13 | 0.08 | 618 / 220 / 66 | collar round a footing (hidden inside it) with a lee tail |
| Sheet | 1.3 x 0.6 | 0.02 | 760 / 244 / 82 | thin sand floor in the shop alleys |

Uniform scale only (0.6–1.45 per instance). LODGroup per prefab: LOD0 to ~10 m, LOD1 to ~28 m, LOD2 to ~60 m, culled
beyond (PC lodBias 2). No shadow casting (receive only; SSAO grounds them), no colliders, motion vectors per camera,
static-batching flag.

**Material** `Art/WallFootDrifts/Materials/WFD_Sand` (URP Lit, instancing on): `WFD_Sand_BaseMap` (2k, DXT1) and
`WFD_Sand_Normal` (2k, BC5), 1.5 m tile on the meshes' metric UV0, smoothness 0.12, metallic 0. The albedo is the masonry
kit's CC0 sand scan with its crusted blotches flattened, graded to the warm Ward palette (mean sRGB ≈ 173/137/104). It was
recalibrated after the first editor captures: at the paving's dust colour the sand rendered ~1.6x brighter and greyer than
the flags (the paving shader's cavity occlusion and per-flag warm tint) and read as snow in shade.

**Decals** (URP projectors, draw distance 40 m, 4 materials, instanced). The shared Ward weathering decal graph has
angle fade off, so ground films were painting the risers and props; `Art/WallFootDrifts/Shaders/WFD_Decal.shadergraph`
is a copy of `Art/Weathering/WardDecal.shadergraph` with angle fade on (nothing else changed). Textures are non-tiling and
fade out at their ends; long walls get overlapping segments of at most 4.5 m.

| Decal | Texture | On |
| --- | --- | --- |
| band | `WFD_DecalFootBand` 2048 x 512 | the ground along each banked stretch: a sand film with a plateau over the drift toes, easing out by 0.8–1.2 m (feathers the sand into the paving) |
| skirt | `WFD_DecalWallSkirt` 2048 x 512 | walls taller than 1 m (shop sides, rears and facades, hill plinth and cheeks, hall deck walls): dark contact grime and spatter at the foot, a pale dust coat to ~0.5–0.7 m |
| post | `WFD_DecalPost` 1024² | under each post collar, lee tail downwind |
| sheet | `WFD_DecalSheet` 1024² | alley floors and inside-corner fans |

## Placement (`faces.py` → `probe_faces.py` → `layout.py`)

- `faces.py`: 119 wall-foot faces, 34 inside corners and 23 posts round the avenue ring and cross streets — the eight
  shops (porch fronts either side of the step, step fronts and ends, tread pockets, side walls, rear walls, porch-deck
  facades), the Basic General booth, Vanguard Hall (podium faces, step corners, deck walls and pier corners), the hill
  plinth (four faces, three stairs' cheeks and cheek corners); avenue utility lamps, night-life lamp posts, service-lane
  poles. Doors, bays, rear doors and rear air conditioners come from the shop records (`WardShops/Models/<shop>.json`).
- `probe_faces.py` (Blender): loads the shipped building models at their scene transforms and ray-casts every 5 cm along
  each face at 3–30 cm, so each bank sits on the real foot line (quoins, plinths and piers stand 4–15 cm proud of the
  nominal lines). Below 0.5 m the shop sides and rears are the old porch slab drawn by the render chunks (not in the
  models): those samples fall back to −5 mm. It also measures the real deck and tread levels (0.496 / 0.246).
- `layout.py`: wind from the west-south-west (the windborne dust moves towards +X/+Z), so faces looking into it get the
  heaviest, near-continuous banks, lee faces moderate ones, faces along it lighter runs with bare or dusted stretches.
  Every inside corner gets a bank, step risers only at their ends (the walked middle stays clean), each post a collar,
  the four shop alleys a sand floor. Kept clear: every prop, collider and chunk-drawn object at the foot (scene audit,
  8 cm margin; dry grass and weeds may stand in sand), walker/mechanic/droid routes (0.35–0.45 m from the sand),
  NPC/landmark points, the Lattice/Ring areas, the stair and hall-step approaches, the terminal slab, the Basic General
  counter and the West Gate arches (their own sand). Each piece's visible sand must sit on its own level (no bank hanging
  off a porch or the narrow hall deck); a piece that does not fit is shrunk (to 60 %) or dropped. Result: 334 pieces,
  320 decals, 0 problems; re-checked against a post-install audit (`review/validate-installed.json`, 0 problems).

Scene: root **Ward wall-foot drifts** with a group per building (`Relay Works`, …, `Hill plinth and stairs`, `Posts`,
`Shop alleys`), each holding its prefab instances (named `<piece> · <face>`) and a `Decals` child. Review cameras under
**Wall-foot drift review cameras**.

## Run order

```sh
O=/home/teknetik/.local/state/ward-programme
$O/heavy.sh uv run --with pillow --with numpy python make_textures.py   # sand + decal textures -> Art/WallFootDrifts/Textures
$O/blender.sh author_drift_kit.py [-- --blend]                          # kit -> Models/WFD_Kit.glb, kit.json
python3 faces.py                                                         # faces.json
$O/blender.sh probe_faces.py                                             # probe.json (real wall feet)
$O/unity.sh <log> AthenHill.Editor.StreetDressingAudit.DumpBatch --out <audit.json> -nographics
uv run --with matplotlib python layout.py --plot [--audit <audit.json>]  # layout.json, review/layout-map*.png
$O/blender.sh review_kit.py -- <run> [eye,close,corner,post,top]         # optional Cycles review of the kit in context
$O/unity.sh <log> AthenHill.Editor.WallFootDriftsPass.RunBatch --steps build,capture:<cams>[:off] --out <dir>   # graphics, <= 6 cams
$O/unity.sh <log> AthenHill.Editor.WallFootDriftsPass.RunBatch --steps build,install,verify -nographics
python3 layout.py --check --audit <post-install audit.json>              # re-validate the installed layout
```

`install` is one time (refuses when the root exists; `reinstall` replaces it during authoring; the first rollback copy is
kept). `capture` never saves; it places the drifts in memory when they are not installed, and `:off` captures the same
views with the root switched off. `toggle:on|off` exists for A/B builds but saves the scene: use scene snapshots instead.

## Sources and licences

- `dense_sand` (Poly Haven, CC0 1.0), the Ward masonry kit's sand scan already in `art/vanguard_hall_20260930/polyhaven`:
  sand albedo (regraded) and grain normal (45 %). Wind ripples, decal shapes and colours are procedural (`make_textures.py`).
- Geometry: procedural (Blender 5.2, this folder). Probe models: the shipped shop, booth, hall and hill GLBs (this repo).
- `WFD_Decal.shadergraph`: copy of the project's `WardDecal.shadergraph` (Unity Shader Graph decal, Unity Companion
  License terms as for the URP package). No Meshy generation was used.

Heavy outputs (`*.blend`, `review/`, `logs/`) are git-ignored; scripts and JSON are tracked.

## Known limitations (for the combined test and Carl)

- Porch decks get little sand: their facades are mostly doors, bays and dressed frontages (planters, stock, benches),
  which stay clear by rule. The street-level risers, sides, rears, hill and hall carry the pass.
- Post collars can read as a soft disc from some angles (cam_wfd_lamp); the lee tail is subtle.
- Sand and films are tuned under the editor's lighting at the saved clock; night (20:30) and native-player look are
  unreviewed by this pass.
- The banks are static meshes: characters walk through them (no collision by design; 2–18 cm high, kept off routes).
