# Docs snippet — Ward buildings (3 Oct 2026), for the orchestrator to merge

## unity/EDITING.md section

### Ward buildings (3 October 2026)

`Assets/AthenHill/Editor/WardBuildingsPass.cs` replaces the 26 Sep district-retrofit buildings that still read as
boxes (`art/ward_buildings_20261003/AUDIT.md`). Each building is authored in Blender on the Ward masonry kit by
`art/ward_buildings_20261003/author_buildings.py -- <key>` (→ `Art/WardBuildings/Models/<Model>_LOD0-2.glb` and
`<key>.json` with colliders, lamp/prop mounts and extra lights) and placed from `art/ward_buildings_20261003/layout.json`
(instances, retired paths, review cameras, the pass's WB_* material settings). Batch steps:
`RunBatch --steps build:<key>,install:<key>,verify[:<key>],capture:<key>[:cam+cam]` (`install` is one time per key;
`reinstall:<key>` during authoring). Rebuilding a prefab updates the installed instances through the prefab link.
Keys and scene roots: `nanofab` (Ward building: Nanofab 2), `watchtower` (… watchtowers, 4 instances), `hall`
(… Processing 11 ruin), `aquifer` (… Aquifer 3), `tubenode` / `tubeseg` / `tubespan` (Quantum Tube nodes and the goods
conduit along the north wall: pylon bays east of the gate, wall-hung spans over the west homes), `homea` / `homeb` /
`homec` (converted container homes on the wall feet; B is stacked with a stair). The old retrofit groups
(`Ward district retrofit/Nanofab workshop`, `Watchtower 1…4`, `Processing hall ruin`, `Aquifer pump station`,
`Quantum Tube conduit`, `Perimeter dwellings`) stay in the scene inactive (activation overrides on the retrofit prefab
instance) for rollback. Wall lamps are the shop family (PH_WallLamp, NF bulb, cookie spot) on the Ward lighting clock;
interior/status glows under "Unclocked lights" are always on. Not render-chunk sources (the chunk fingerprint is
unchanged). Verify also lists marker conflicts (routes, NPCs, landmarks, spawn) and AABB collider overlaps.

## AGENTS.md §3 baseline-table row

| Ward buildings (retrofit replacements) | 3 Oct 2026 (`art/ward_buildings_20261003`, `WardBuildingsPass`): the 26 Sep retrofit boxes rebuilt on the Ward masonry kit with blackened steel and restrained sci-fi: **Nanofab 2** (SE yard: ashlar storey, banded corner piers with banners, composite clean-room module with a cyan status strip, half-raised hazard-framed bay showing a lit fabricator, gas bank, lean-to), **Processing 11** (NE yard: roofless shelled ashlar hall, broken stepped wall tops, barred windows, piers with crane rails and a stranded crane, sagged trusses, rubble), **four Warden corner watchtowers** (ashlar shafts on battered taluses, corbelled armoured cabins with searchlights, ladders up the city face), **AQUIFER 3** (SW: pump hall with clerestory, hoist, strapped corners, well head and rising main, three riveted tanks), the **Quantum Tube** goods nodes and conduit (stone pylons, armoured conduit, "GOODS ONLY"), and five **converted container homes** on the wall feet. Old groups inactive for rollback; 24+ `cam_wb_*` review cameras. Not yet accepted by Carl. |

## Round two additions (3 Oct 2026, night) — merge into the sections above

EDITING.md, append to the Ward buildings section:

Round two (`art/ward_buildings_20261003/README_round2.md`): the four watchtowers are now four models (`Watchtower`,
`Watchtower2/3/4`; an instance in `layout.json` may name its own `model`; build-only keys `watchtower2…4`) with two
cabin types (armoured cabin / open crenellated top) and per-tower damage and repairs; Processing 11 carries a salvage
works (scaffold, tarp, floodlight on the clock, reclaimed stone, cordon and permit board, shear legs, skip, sorted steel,
mason's bench); `gatebastion` (root **Ward building: West Gate bastions**, prefabs `GateBastion` / `GateBastionN`)
replaces `Ward district retrofit/Gate defences` (inactive) with two gabion gun positions beside the spawn. New batch steps:
`cameras:<key>` (re-place review cameras without reinstalling) and `viewbudget[:prefix]` (lights reaching each review
camera and this pass's triangles at the selected LOD → `evidence/ward-buildings/20261003/round2/view-budget.json`). The
masonry kit has opt-in cylindrical UVs (`Part.new_block(cyl=(point, axis))`); painted tanks and cylinders use the
sheet-steel `WB_CylBone`, `WB_CylRed`, `WB_TankBone`, `WB_TankTeal` (VH_Paint's texture streaks on curved faces).
`round2_layout.py` re-applies the layout edits.

AGENTS.md §3, extend the Ward buildings row with:

… Round two (3 Oct night): four distinct watchtowers (two armoured-cabin, two open crenellated tops; patched, rebuilt,
breached and timber-shored), Processing 11 turned into a Warden-permitted salvage works, painted tanks/cylinders fixed,
and the **West Gate bastions** (two gabion gun positions with sandbag courses, pintle guns, lamps) replacing the
retrofit `Gate defences` at the spawn. 15 `cam_wb2_*` cameras. Not yet accepted by Carl.
