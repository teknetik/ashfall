# Ward shade sails with festoon bulbs — 1 October 2026

Art-direction review of 30 Sep, item 7 (`~/.local/state/ward-programme/next-wins.md`): "The largest open spaces have
nothing overhead and nothing to break the paving: the courtyard by the terminals, the market floor, the West Gate apron and
the Lattice court." Checked on the current batch-2 lookbook before starting (`review/before-day.jpg`, `before-2.jpg`,
local): all four spaces were bare paving with nothing above 4.5 m but lamp heads. Unity pass:
`unity/AthenHill/Assets/AthenHill/Editor/ShadeSailsPass.cs`. Evidence: [unity/evidence/shade-sails/20261001](../../unity/evidence/shade-sails/20261001/README.md).
Not reviewed or accepted by Carl.

## What was added (scene root **Ward shade sails**, four prefab instances)

| Sail (instance) | Where | Form and cloth | Rig |
| --- | --- | --- | --- |
| Courtyard terminals sail | over the mission-terminal slab and the space in front of it (x 3.3–12, z −9 to −15.6) | hypar quad 8.5 × 6.3 m, fixings 3.85 / 4.95 / 3.7 / 4.85 m; madder, natural/ochre repair patches, stencil "WQ 07" | two stone-footed poles on the north side (no guys: the hill stair and the Field Supply steps), two base-plate poles behind the terminals in sandbag rings, each guyed to a sandbagged anchor; turnbuckles |
| Market rest sail | over the market-edge rest spot behind Air + Water (picnic table, stools, bench) | quad, fixings 4.35 / 3.6 / 5.3 / 3.75 m; indigo, madder/natural/bone patches, soot on the barrel side, "M-3" | tied to the two retrofit service poles on the lane (I-beams: wire-rope strops with eyes on the flange faces) and two stone-footed poles on the market side; rope lashings |
| West Gate apron sail | over the caravan goods north of the spawn (x 33–40, z 4.5–12.7) | hypar quad 6.5 × 8 m, fixings 3.7 / 5.0 / 3.75 / 4.85 m; natural canvas with a replaced madder cloth and a khaki cloth, "GATE 2" | stone-footed poles by the arch walk (no guys), guyed base-plate poles on the west side; turnbuckles and one lashing |
| Lattice court sail | over the north half of the approach to the Lattice step and the court east of it | triangle, fixings 5.2 (by the pad) / 3.7 / 4.45 m; natural canvas with indigo cloths, "LJ 11" | three stone-footed poles (the hall edge, the court, east of the step) |

Every sail has two festoon strings between its pole hooks (the market's along its north hem and down the lane), 0.48 m
bulb pitch, a few dead or missing bulbs, and one or two unshadowed warm point lights at the string middles (7 lights,
intensity 1.4–2.2, range 6–7 m) on the **Ward lighting clock** (`practicalLights` + `nightOnlyLights`); the bulb material
`SS_FestoonBulb` is on the clock's `emissiveMaterials` (4 % by day). Nothing is retired; no render-chunk source changes.

## How it is built

* **Form finding** (`formfind.py`, numpy): each sail is a prestressed membrane solved with the force density method — a
  grid of links at uniform prestress, hem cables whose force density is tuned per side to the cut sag (5–6 % of the
  span), a slight belly, fabric corners pinned 0.5 m short of the pole padeyes (corner plate, ring, turnbuckle or
  lashing). The same parametric grid sampled every 4th node (0.5 m) is LOD1, so both LODs lie on one surface.
* **Layout and validation** (`sails.py`): pole and anchor footprints against active colliders, street-dressing props
  (+0.3 m), shop doors/shutters/first-step approaches, the terminal slab, hall steps, Lattice step, the West Gate arch
  walk, walker/mechanic/droid routes (1.0/1.6 m), NPC and landmark points (1.3 m) and the Lattice/Ring interaction areas;
  guy wires out of routes and keep-clear zones; the solved canvas ≥ 3.0 m over walkable ground, clear (0.3 m) of every
  collider, renderer and probed mesh point (oasis-tree canopy edge, service lines, market bunting) and 0.6 m of lights;
  festoons ≥ 2.55 m and under the canvas; sightlines kept open (cam_grid → Lattice ring and pad front, the approach eye
  → ring top, cam_terminal / cam_courtyard → terminals, the spawn camera → hill tree and Vex, cam_gate → arches,
  cam_market → cookfire). Result: **0 problems** before and after install (`layout-report.txt`,
  `layout-report-installed.txt`). Accepted warning: the faded top of the barrel-fire smoke (it drifts east at 3–4 m,
  NightLifePass) passes just under the market sail's high south-west part.
* **Geometry** (`author_sails.py`, Blender, on the Ward kit `Part` and the rooftop kit's tube/torus/sandbag helpers):
  canvas with planar UVs rotated to fill the square map, rolled hem (shop cloth materials `WS_Cloth*`), corner plates,
  shackles, turnbuckles, rope lashings; 114 mm poles raked 4° outwards with cap, padeye, festoon hook and guy padeye;
  stone footings (`VH_Ashlar`, eroded arrises) with a steel collar, or welded base plates with gussets in two courses of
  sandbags; guys with clips and turnbuckles to sandbagged anchor plates; strops round the service-pole I-beams; festoon
  cable, lampholders and globe bulbs.
* **Canvas maps** (`make_textures.py`): per sail a 2048 px base map (alpha = a few worn-through holes) and a 1024 px
  normal map: 1.37 m cloths with flat-felled seams (two stitch rows), dye-lot variation, sun fading over the high side,
  repair patches in the other dyes (stitched, frayed), corner reinforcements and webbing straps, rust weeping from the
  corner plates and dust/water streaks following each sail's own slope to its low corners, tide marks, a laced tear, the
  stencil (mirrored so it reads from underneath), tension wrinkles fanning from the corners in the normal map; plus a
  shared 512 px plain-weave detail pair (0.2 m tile). Dye tints follow `WS_ClothMadder/Indigo/Bone`.
* **Unity** (`ShadeSailsPass.cs`): canvas material on **Athen Hill/Ward Ground Cover** (two-sided, alpha-clipped holes,
  sun + ambient transmission through the cloth 0.18–0.32 by dye, its wind switched off); pole paints `SS_Pole*` are tinted
  copies of `VH_Steel` (weathered sheet-steel maps; the shared `VH_Paint` texture is grooved). Per site one prefab with
  LODGroups Sail / Rig / Festoons. **Shadows**: the canvas never casts itself; a ShadowsOnly copy of the coarse canvas
  4 cm *below* it (one per LOD) gives the sail's shadow at every distance without self-shadowing the cloth (so the
  underside keeps its transmission and the top its sun); poles and stone footings cast at LOD0 only; hem, hardware,
  bags, wires and festoons never. Colliders: pole capsules, footing/ballast boxes, guy-anchor boxes, and one
  camera-only mesh collider per sail (the coarse canvas, both windings, ≥ 3.67 m up) so the follow camera's sweep stops
  under the canvas instead of rising through it (the player cannot reach it: jump apex ≈ 3.0 m).

## Numbers (`unity/evidence/shade-sails/20261001/verify-saved-scene.json`, `build-assets.json`)

| Site | LOD0 tris (sail / rig / festoons) | LOD1 tris | shadow casters at LOD0 | lights |
| --- | --- | --- | --- | --- |
| Courtyard | 13,352 / 8,432 / 6,784 | 8,948 | 416 (canvas proxy) + 904 (poles, stone) | 2 |
| Market | 10,160 / 3,608 / 4,684 | 5,292 | 256 + 768 | 1 |
| Apron | 14,576 / 8,432 / 5,944 | 8,324 | 480 + 904 | 2 |
| Lattice | 12,322 / 3,300 / 6,928 | 6,216 | 400 + 1,152 | 2 |
| **Total** | **98.5k** | **28.8k** | **5.3k** (16 renderers incl. LOD1 proxies) | **7** |

LOD switches (screen-relative height; PC lod bias 2): sail 0.35 / 0.01, rig 0.40 / 0.02, festoons 0.45 / 0.04.
Textures ≈ 27 MB resident at full mips (4 × 2048 BC7, 4 × 1024 BC5, two 512 weave maps), all streaming.
Head clearance: lowest canvas 3.67 m (the market's south-east corner at the service pole), lowest festoon cable 2.92 m (bulbs ≈ 2.8 m); no walker,
mechanic or droid route passes under any sail.

## Review cameras (scene root "Shade sail review cameras", disabled cameras)

`cam_ss_courtyard_under`, `cam_ss_courtyard_side`, `cam_ss_market_rest`, `cam_ss_market_lane`, `cam_ss_apron_spawn`
(the follow camera's first frame at the spawn), `cam_ss_apron_goods`, `cam_ss_lattice_approach`, `cam_ss_lattice_court`
(13:00 and 20:30). Standard views whose frustum includes a sail (occlusion not tested): cam_hill and cam_avenue (three
sails each), cam_gate (apron), cam_grid and cam_terminal (Lattice, partly), cam_courtyard (courtyard, Lattice) — the wide
views are where the shadow cost of the canvases shows.

## Run order

```sh
O=~/.local/state/ward-programme; A=art/shade_sails_20261001
$O/unity.sh <log> AthenHill.Editor.StreetDressingAudit.DumpBatch --out unity/evidence/shade-sails/20261001/audit-before.json -nographics
$O/unity.sh <log> AthenHill.Editor.ShadeSailsPass.RunBatch --steps survey -nographics      # lights, cameras, sun, mesh probes
#   (copy survey.json to survey-before.json: sails.py reads the pre-install survey so the sails' own lights don't count)
uv run --with numpy --with matplotlib python $A/sails.py --plot          # sail-layout.json + validation + review/layout-*.png
$O/blender.sh $A/author_sails.py [-- Site ...]                            # Art/ShadeSails/Models/*.glb + sails.json
$O/heavy.sh uv run --with numpy --with scipy --with pillow python $A/make_textures.py [Site ...]
python3 $A/review_cams.py                                                 # review-cameras.json
$O/unity.sh <log> AthenHill.Editor.ShadeSailsPass.RunBatch --steps build,install,verify -nographics
#   after the install: geometry/texture changes -> build,verify (prefabs re-saved in place, the instances keep their clock
#   bindings); if the number of sails or lights changes -> build,reinstall,verify (re-creates the instances, re-binds the
#   lights, keeps the first rollback copy); material values only -> materials,verify
$O/unity.sh <log> AthenHill.Editor.StreetDressingAudit.DumpBatch --out unity/evidence/shade-sails/20261001/audit-after-install.json -nographics
uv run --with numpy --with matplotlib python $A/sails.py --installed      # re-validate against the installed scene
$O/unity.sh <log> AthenHill.Editor.ShadeSailsPass.RunBatch --steps "capture:13:cam+cam,capture:20.5:cam" --out ../evidence/shade-sails/20261001/editor-rN
#   graphics, <= 6 close cameras per run; inline cameras as name@x;y;z@x;y;z@fov; ":off" hides the root in memory
```

Blender review renders: `$O/blender.sh $A/review_sails.py -- <tag> <Site,Site|all> [lod] [under,outside,corner,hardware,base,aerial] [night]`
(the sails alone on a ground plane with a 1.8 m figure and the 13:00 sun). A/B for the orchestrator: `toggle:off|on`
(saves the scene) — build both arms from scene copies as BRIEF.md says.

## Sources and licences

All geometry and textures are original and procedural (this folder; the shared Ward masonry kit and rooftop kit
helpers). Materials reused from the hall, shops and street kit (`VH_*`, `WS_Cloth*`, `SD_Sack`, `SD_Rope`). The stencil
lettering is rasterised from Allerta Stencil (SIL Open Font License, `art/west_gate_20260926/fonts/`). No third-party
models, no Meshy credits used.

## Files

| File | Purpose |
| --- | --- |
| `formfind.py` | force density form finding, LOD sampling, planar UVs (shared by all scripts) |
| `sails.py`, `sail-layout.json`, `layout-report*.txt` | layout, validation, review maps |
| `author_sails.py` | Blender geometry → GLBs + `Models/sails.json` |
| `make_textures.py`, `textures.json` | canvas and weave maps |
| `review_cams.py`, `review-cameras.json` | review cameras |
| `review_sails.py` | Blender Cycles review renders |
| `area_map.py`, `q.py`, `sheet.py` | site maps from the audit, audit queries, contact sheets |
| `staging/ShadeSailsPass.cs` | the Unity pass as compile-checked offline before copying into Assets |
