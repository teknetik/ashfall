# Ward rooftops and service lines — evidence, 1 October 2026 (batch 2)

Pass: [art/rooftops_20261001](../../../../art/rooftops_20261001/README.md) (next-wins item 8, rooflines and overhead
service cables). Editor: `Assets/AthenHill/Editor/RooftopsPass.cs`. Not accepted by Carl. Under the revised definition of
done (1 Oct 14:50) this pass ran **no player build, native lookbook, A/B profile or city loop**: frame times, TAA/LOD
behaviour, night views (20:30) and the city loop come from the orchestrator's combined batch test.

## What is in the saved scene

Scene root **Ward rooftops** (installed 15:43, re-installed during authoring at 15:53 and 16:07 with the same rollback
copy): eight shop-roof groups, each with the transform of its shop's root, and **Service lines**. 44 prefab instances:
17 of the 18 kit objects (the flat-roof turbine vent is a spare) + 3 street-kit props (Salvage terrace) + 8 line groups (two-conductor spans across both cross
streets, two short line pairs across the alleys, four conduit drops into junction boxes). No lights, nothing retired,
no render-chunk source touched. Review cameras: **Rooftops review cameras** → `cam_rt_west_north`, `cam_rt_west_south`,
`cam_rt_east_north`, `cam_rt_east_south` (along the avenue rows, 1.62 m), `cam_rt_west_cross`, `cam_rt_east_cross`
(into the cross streets, 1.62 m).

| File | Content |
| --- | --- |
| `audit-before.json.gz` | scene audit taken before placing anything (15:26; includes night life and basin mountains) |
| `layout-report.json` | layout validation: **0 problems**; per-piece skyline check (height above the roofline, avenue viewpoints that see it) |
| `build-assets.json` | 26 prefabs, triangles per LOD, LOD cuts, shadow flags, **0 unmapped materials** |
| `install.json`, `reinstall.json` | groups, counts, chunk fingerprint before = after, review cameras |
| `verify-saved-scene.json` | 44/44 instances prefab-linked, 0 missing materials, 0 error shaders, groups on their shops, uniform scale, chunk fingerprint matches (not editing), 6 cameras disabled, 0 lights |
| `rollback/before-rooftops-install.unity` | the saved scene as it was before the first install |
| `cited-before-after.jpg` | **matched editor captures** (root off in memory / on) of the review's cited views: `cam_district_water`, `cam_district_field`, `cam_district_salvage` (after = v3), `cam_district_repairs`, `cam_hill` (after = v2, before the net/canvas fixes) |
| `editor-v1/`, `editor-v2/`, `editor-v3/`, `editor-cited/` | editor captures (MainCamera clone, saved lighting, no time-of-day clock; JPG) per review round |
| `blender/` | kit line-ups with a 1.8 m figure, layout map, street-level Blender renders before/after from the `cam_rt_*` views, the 30 Sep native stills the review cited |

## Numbers (verify-saved-scene.json)

- LOD0 67.4k triangles (≈21k of them the three street-kit props' scan LOD0s), LOD1 28.2k; most pieces are 10–40 m from
  the player and drawn at LOD1. Kit LOD0 per object 0.2–3.7k (`build-assets.json`).
- 121 renderers; 4 cast shadows (the two water tanks, LOD0+LOD1, 6.5k triangles at LOD0); the street-kit seats' shadows
  are off as instance overrides. 0 lights. Prefabs are batching-static; materials are the shops' shared URP Lit
  materials plus RT_DewNet / RT_SolarCell / RT_Ceramic (512 px procedural maps, mip streaming).
- Performance not measured by this pass (DoD); expected small: no lights, shadows on two objects, ~120 extra renderers.

## Review (editor captures and Blender renders)

- From the review's own cited views (4.7 m, 12 m from the facades) the cornices are now broken where the shops' work
  shows: Air + Water's dew/condensate nets beside its tank, Relay Works' whip, the cross-street mast and lines; Finery's
  tank and rail; Field Supply's ridge ventilators and ridge mast with the east lines; Salvage's shade terrace (madder
  canvas) and Tool Exchange's PV frame; Repairs' dish on the container (`cited-before-after.jpg`).
- At eye height on the avenue, 4–7 m from 7–9 m facades, the parapets hide anything set back more than about a metre;
  there the rails, the whip, the ridge vents and mast, the cross-street lines and, further along the row, the nets and
  tanks carry the change. It is deliberately quiet from there (`editor-v3/cam_rt_*`, `blender/street-cam_rt-before-after.jpg`).
- Fix rounds after v1: PV frame raised 0.9 m; horizontal tank put on a 1.15 m stand; a front rail on Thread + Hide's
  drying terrace; the dew net (read as a blank billboard in v2) rebuilt as two darker, sparser bellied nets on three
  posts (v3 reads as netting); the shade canvas's normals flipped up (it rendered slate-grey from above); seat shadows
  off; cam_rt_east_north moved off ambient walker 03's loop. Closer "roof-targeted" cameras were tried and rejected.
- VRAM: two editor capture runs of wide district views were killed by the watchdog (16:01, 16:07, ≈9.5 GB per run); per
  the orchestrator, further editor captures are close views only (≤ 3 cameras) and the skyline is judged in Blender
  and in the native combined lookbook.

## Known defects / open points

1. Eye-level avenue views show little of the kit (geometry of the street, see above); the combined native lookbook
   should confirm whether that is enough. Candidates if Carl wants more from the near avenue: a second whip or a mast on
   a front corner, taller tank stands, rails on one or two more fronts.
2. The east cross-street lines, seen from `cam_rt_east_cross`, appear to leave the Repairs mast right beside the forge
   flue (perspective: the mast is ≈3 m from the flue and the lines ≥ 2.5 m from its smoke column). Not checked at night with the smoke.
3. The shade canvas and nets use double-sided URP Lit, which (as far as seen in the captures) does not flip normals for
   back faces: the canvas underside is lit like its top (reads warm, not shaded); the nets' far side shades like the near side.
4. Thin lines (Ø 2–2.6 cm) and whip (Ø 0.8–2.2 cm) may shimmer under TAA at distance; not seen in a moving native view.
5. The pre-existing retrofit service-lane poles, their lines and the two cross-street pipe bridges at x ±24.2 stay; the new
   spans are additional (mid-street at x ≈ ±20.5–22.5), not reconciled with them.
6. Ladders are decorative (box collider over their foot; not climbable). Junction-box warning plates are blank.
7. Alley line pairs are only 0.9 m long and barely read.
8. Spans and drops are generated meshes: moving a mast or box means `layout.py` → `author_cables.py` → Build assets.
9. No LOD-transition, motion or night review by this pass.
