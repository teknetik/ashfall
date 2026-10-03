# Ward buildings, round two — 3 October 2026 (night)

Continues round one (`README.md`, `AUDIT.md`). Brief: fix round one's recorded defects (judged from the native batch
`on2` lookbook, `unity/evidence/overnight/20261003/on2/lookbook-p*/cam_wb_*`), re-check the audit and rebuild the next
most visible weak structure. Nothing here is accepted by Carl. No Meshy credits were used (0 of the ~150 budget); no
concept images were generated (the tower B top follows the crenellated perimeter walls and West Gate language).
Evidence: `unity/evidence/ward-buildings/20261003/` (build/install/verify JSON) and `…/round2/` (view budget, Edit Mode
results, pre-round-two scene copy `rollback/before-round2.unity`). Editor captures: `review2/` (sheets
`sheet_towers.jpg`, `sheet_hall.jpg`, `sheet_gate.jpg`, `v2/sheet_v2.jpg`); Blender source renders: `review/`.

## Round-one defects fixed

| Defect (on2 lookbook) | Fix |
| --- | --- |
| Four identical watchtowers | Four per-tower models (`TOWER_VARIANTS` in `author_buildings.py`; prefabs `Watchtower`, `Watchtower2/3/4`; each instance in `layout.json` names its model). Two cabin types: **A** armoured steel cabin (NW 1 hipped roof as before; NE 3 a corrugated gable roof replacing the shot-up hip, two faces with shutters closed, a rust-steel shutter, lashed second whip aerial, mirrored ladder) and **B** an open crenellated fighting top on stone machicolation corbels with sandbagged crenels, steel deck and a shade roof on four posts (SW 2 corrugated roof and radio dish; SE 4 madder canvas sail, dish + short mast, mirrored ladder). Per-tower damage story on the face that does not stand against a wall: NW 1 riveted patch plate (moved from the hidden face), SW 2 front-right corner shot away and rebuilt in paler rubble-dressed blocks under a riveted steel cage, NE 3 breach closed with two overlapping welded plates under a soot plume, SE 4 cracked face held by two raking timber shores with stitch plates. Banner full / stub / torn / full; painted post number (0.95 m) on the city face and "POST n" on the rear; small per-tower props. |
| West conduit inspection hatches face the wall | `TubeSeg` carries a riveted hatch and status lamp on both sides, so the two west-run bays (yaw 180) show one to the city. |
| Nanofab gas-cylinder paint streaks | Cause: `VH_Paint`'s base map is strongly anisotropic (horizontal brush streaks, gradient y/x ≈ 6.7) and the masonry kit's box projection sliced it on curved faces. Added optional cylindrical UVs to the kit (`Part.new_block(cyl=…)`, default off, so no other pass changes) and `cyl_uv()`; cylinders now use new `WB_CylBone` / `WB_CylRed` on the isotropic `VH_SheetSteel` set. |
| AQUIFER 3 tanks dark grey in shade | Same texture cause plus `VH_Paint`'s 0.5 grey base under a 0.66 tint. Tanks use `WB_TankBone` / `WB_TankTeal` (sheet-steel set, compensated colours > 1, cylindrical UVs); the rust tank is unchanged. In the editor capture the bone tank now reads light and the teal tank teal in shade. |
| Hall ruin plain/empty from its apron camera | **Salvage works** (`hall_salvage_works()`): a Warden-permitted crew is taking Processing 11 apart for the city's repairs. City face: tube-and-board scaffold at the shell holes (3 lifts, ladder, ties, gin-wheel jib and rope), ochre dust tarp (madder read near-black in the face's all-day shade), work floodlight (night-only, on the clock); two pallets of reclaimed blocks with chalked lot numbers, handcart, bucket; a rope cordon on yellow posts and a painted permit board ("SALVAGE WORKS / WARDEN PERMIT 11 / UNSAFE WALL – KEEP OUT") by the low east wall. Inside: yellow shear legs over the toppled pier lifting a block in a sling; the stranded crane hook over a scrap skip; cut I-beams sorted on bearers ("CUT – KEEP"); a mason's bench with a block being dressed, vice, sledgehammer, toolbox, work lamp and generator. |
| `cam_wb_aquifer_market` stood inside a market cloth | Moved to (−30.8, 1.65, −19.6). |

## New rebuild: West Gate bastions (replaces `Ward district retrofit/Gate defences`)

Re-checked the audit (see `AUDIT.md`, "Round two re-check"): ranks 1–6 are done; the Lattice hoop (rank 7) was left
alone (reason below). The weakest structure left in a high-traffic frame was the retrofit's **Gate defences** beside the
spawn: two flat grey HESCO runs, a scrap turret on a white pole with a red box, three jersey barriers — the first thing
the player sees turning from the gate. Replaced by two Warden gun positions, scene root **Ward building: West Gate
bastions** (prefabs `GateBastion` south / `GateBastionN` north, mirrored gun side), roots at world (44.0, 0, −10.75) and
(44.0, 0, 22.5), yaw 270 (street face west, rampart face 1.95 m behind): an L of eight modelled gabion cells (bulging
hessian liner, welded mesh at LOD0, corner coils, sand fill, per-cell height jitter), West Gate sandbag courses on the
back row, a sandbagged platform with a steel deck carrying a pintle-mounted heavy weapon behind a riveted olive shield,
aimed along the wall at the gate passage; ammunition box, crate, stool, binoculars, an authored field telephone with its
cable up the rampart, a "GATE POST 1/2" plate, two scanned jersey barriers in front, one wall lamp on the rampart (clock).

## Lattice hoop (audit rank 7): not touched

It is a gameplay object built from render-chunk sources beside `Lattice interaction`; changing it means Show Sources →
retire → Rebuild Render Chunks for the whole city while another agent saves the same scene, plus a Lattice-travel check
I may not run. The native lookbook (`cam_nl_lattice`) also shows it reading as a deliberate ring (dark segments, stone
clamps, plinth and console) rather than a box. Recommended as its own pass (a Meshy hero piece of the ring and console)
when the scene is not shared.

## Triangles, lights, colliders (Unity, per prefab; LOD0 / LOD1 / LOD2)

| Prefab | LOD0 / LOD1 / LOD2 | Change vs round one | Lights |
| --- | --- | --- | --- |
| Watchtower (NW 1, A hip) | 65.4k / 18.3k / 80 | patch moved, number stencils | door lamp + searchlight (clock) |
| Watchtower2 (SW 2, B corrugated) | 64.8k / 22.0k / 68 | new | same |
| Watchtower3 (NE 3, A gable) | 71.6k / 21.5k / 80 | new | same |
| Watchtower4 (SE 4, B canvas, shores) | 59.3k / 20.0k / 68 | new | same |
| Processing11 + salvage works | 162.0k / 47.4k / 168 (+20.5k / +16.3k) | + props: handcart 45.6k, generator 60.3k, skip 37.6k, work lamp 22.9k, toolbox 14.2k, tarp stack 10.5k, bucket, vice, hammer (scanned props with their own LODs) | +1 floodlight (clock, night-only) |
| Nanofab2 / Aquifer3 / TubeSeg | 118.6k / 102.6k / 7.0k (tube +0.3k) | materials/UVs, hatches | unchanged |
| GateBastion / GateBastionN | 34.3k / 3.5k / 24 each (+ props ≈ 62k at LOD0 each: 3 sandbag courses, 2 jersey barriers, crate, stool, ammo box, lamp) | new (retrofit group ≈ 21k) | 1 wall lamp each (clock) |

Lights added in total: 3, all practical + night-only on the Ward lighting clock (hall floodlight, two bastion lamps); no
always-on lights added. Per-view counts (`…/round2/view-budget.json`, `RunBatch --steps viewbudget[:prefix]`) list every
enabled local light whose range box reaches into each review camera's frustum (an upper bound: the runtime circuit also
culls practicals > 42 m from the player, and URP keeps the nearest ~30) and this pass's triangles at the LOD each group
would select. Views this round touches: `cam_wb2_gate_spawn` 18 lights (10 from Ward buildings) / 252k,
`cam_wb2_gate_apron` 18 / 215k, `cam_wb2_gate_north` 9 / 325k, `cam_wb_hall_apron` 20 / 364k, `cam_wb2_hall_salvage`
11 / 332k, `cam_wb2_hall_cordon` 25 / 351k, `cam_wb2_tower_sw_top` 15 / 61k, `cam_wb2_tower_se_shores` 11 / 188k,
`cam_gate` 25 / 69k, `cam_nl_apron_south` 28 / 149k, `cam_nl_apron_north` 17 / 238k, `cam_whompah` 22 / 121k.
Wide views with many lamps in range (`cam_hill` 111, `cam_avenue` 141, `cam_wb_hall_east` 180) were already far over
32 before this pass; this round adds at most 1–2 night-only lamps to any of them.

## Review cameras (player height 1.65 m)

`cam_wb2_tower_sw_top`, `_ne_gable`, `_se_shores`, `_nw_patch`; `cam_wb2_hall_salvage`, `_scaffold`, `_cordon`,
`_shearlegs`, `_bench`; `cam_wb2_gate_spawn`, `_gun`, `_north`, `_apron`; `cam_wb2_nanofab_gas`,
`cam_wb2_aquifer_tanks_shade`, `cam_wb2_tube_hatch_w` (15 new, under each building's review-camera root).

## Known gaps / defects

- Gabion mesh is a 0.25 m wire grid (real mesh is ~7.6 cm): reads as a light grid at 3–6 m.
- The salvage tarp and the hall's south face are in shade most of the day; the tarp reads dark ochre.
- Tower B corbels are plain stepped boxes; the B shade roofs are not visible from the street except at distance.
- `qa_motion_wall` (an old 8 Sep motion-test landmark at (44.5, −7.4)) is 0.35 m from the south bastion's return; the
  old HESCO run was 0.1 m from it. No current check uses it.
- The tower damage stories stay on one face each; the walls still hide the other side faces.
- Hall props are scanned Poly Haven pieces with heavy LOD0s (handcart 45.6k, generator 60.3k); they switch to LOD1
  (~8–11k) within a few metres.

## Run order (round two)

```
O=/home/teknetik/.local/state/ward-programme
python3 round2_layout.py                                                  # layout edits (re-runnable)
$O/blender.sh author_buildings.py -- watchtower watchtower2 watchtower3 watchtower4 hall nanofab aquifer tubeseg gatebastion gatebastionn
$O/unity.sh <log> AthenHill.Editor.WardBuildingsPass.RunBatch --steps build:watchtower,build:watchtower2,build:watchtower3,build:watchtower4,build:hall,build:nanofab,build:aquifer,build:tubeseg,build:gatebastion,build:gatebastionn,reinstall:watchtower,reinstall:hall,install:gatebastion,cameras:nanofab,cameras:aquifer,cameras:tubeseg,verify -nographics
$O/unity.sh <log> AthenHill.Editor.WardBuildingsPass.RunBatch --steps viewbudget:cam -nographics
DISPLAY=:0 WAYLAND_DISPLAY=wayland-1 $O/unity.sh <log> AthenHill.Editor.WardBuildingsPass.RunBatch --steps capture:<key>:<cam prefix> --out <dir>
$O/blender.sh sheet_blender.py -- out.jpg img...                          # contact sheets (no PIL on this host)
```

Rollback: deactivate `Ward building: West Gate bastions` and re-activate `Ward district retrofit/Gate defences`; for the
towers set every instance back to `Watchtower` (or restore `round2/rollback/before-round2.unity`); the hall's salvage
works are part of the Processing11 model (the round-one script, layout and Unity pass are kept in `round1_backup/`).
