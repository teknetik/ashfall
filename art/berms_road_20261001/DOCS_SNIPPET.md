# DOCS_SNIPPET — Berms road ground V2 (1 Oct 2026)

## For unity/EDITING.md (new section after "West Gate exit and Warden outpost")

## Berms road ground V2 (1 October 2026)

**Outer Berms → Berms ground** now uses `Art/BermsRoad/Ground/BermsGroundV2.mat` (shader *Athen Hill/Berms Ground V2*).
It is the basin's V2 ground (scree, sand with wind ripples, rock with strata on slopes; values copied from
`SandstoneBasinV3.mat` by the build step, so the toe matches the basin) plus painted features from two splats over
x −104…−60, z −54…48: `BermsRoadSplat.png` (R road gravel, G sand, B crust, A 1 − compaction — the channels the
footstep map reads) and `BermsRoadSplat2.png` (R loose gravel, G relief height, B varnished-lag share, A smoothed slope).
The road from the outpost to the depot has two compacted wheel paths with ruts, a loose-gravel crown, graded gravel
windrows on both shoulders, sand-filled potholes and pull-off tracks. The outer 7 m of the floor fade to the basin look.
Tune colours, contrast, relief and the inner rock threshold on the material (see `art/berms_road_20261001/README.md`);
regenerate the splats with `make_splat.py` (it reproduces the West Gate painting exactly off the road). The ground mesh
and collider are unchanged. The old `BermsGround.mat` stays for the range's earth bank and for rollback.
**Berms road edge stones** (under Outer Berms) are ordinary `PH_Rock` prefab instances (no collider) plus two cairns
(one box collider each); move or delete them freely, keeping them off the road and spurs. If the splat changes, rebake
the footstep map (`BermsRoadPass --steps install` does it once; `toggle:new` re-applies it). Review cameras:
`cam_br_*` under **Berms road review cameras**. Pass: `Editor/BermsRoadPass.cs` (survey, build, install, verify,
cameras, tune, toggle:old|new, capture).

## For AGENTS.md §3 baseline table (one row)

| Berms road ground | 1 Oct 2026 (`art/berms_road_20261001`): `Outer Berms/Berms ground` on *Berms Ground V2* (the basin's V2 scree/sand/rock model plus a repainted road: wheel paths, ruts, crown, gravel windrows, potholes; seamless 7 m blend to the basin), 24 edge stones and 2 cairns from the checkpoint bend to the depot, footstep map rebaked. Ground mesh/collider, routes, encounters and the range unchanged; old material kept (earth bank, rollback). Not yet accepted by Carl. |
