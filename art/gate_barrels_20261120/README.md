# Gate barrels: broken barrels you can walk over (20 November 2026)

Carl's playtest note (20 Nov 2026, `art/showcase_phase2_20261120/PLAYTEST-NOTES.md` item 6): "Barrels on the floor by the
waste gate, the broken ones on the floor need to be able to be walked over or need to go". "Waste gate" is the West Gate:
the -X portal by the market into the Outer Berms. Not yet accepted by Carl.

## What was wrong

Ward has exactly one broken-barrel model: the Poly Haven CC0 `wooden_barrels_01` set (two whole wooden barrels plus a
broken third one lying in pieces: a 0.3 m barrel half, two low barrel-side shells, loose staves, hoops and lids). The
Karaveen market (`art/karaveen_market_20260926/build_market.py`) places it twice, both times merged into the stall's
`Goods` mesh and covered by one invisible box collider:

| Place | Where | Collider before | Effect |
| --- | --- | --- | --- |
| **Caravan overflow** by the Karaveen truck | (-45.5, 6.3), 13.8 m inside the West Gate portal, on the way from the market to the gate | `Karaveen caravan market/Caravan stock/COL_barrels`: since 3 Oct a 0.85 x 0.9 x 2.68 m box turned 21 deg, from (-46.6, 7.5) to (-46.2, 4.9) | The 3 Oct fix (`PlaytestFixes20261003 barrels`, Carl's same complaint then) worked out the barrel positions with the set the wrong way round. Its box stood over the **broken staves** at x -46.9..-46.2, z 6.1..7.6 and half of the west barrel, and the **east whole barrel had no collider**. Walking west-east through the staves took 3.2 s instead of 1.7 s (slid round an invisible 0.9 m wall); north-south over the staves was stopped and slid. |
| **Rations stall side** | (-36.8, -16.6), beside the Rations stall at the south end of the market, 28 m from the West Gate | `Karaveen caravan market/Stall Rations/COL_goods.010`: 1.9 x 0.6 x 2.5 m box over the whole set | Two small whole barrels (0.59 m) and every stave, lid and the 0.2 m barrel half under one 0.6 m box: walking onto the stave field was stopped dead (0.4 m of 2 m, and 1.5 m of 3.3 m). |

Where the props really are was measured on the saved scene, not from the build scripts: the `heightmaps` step writes a
0.1 m grid of the highest LOD0 vertex and the highest collider top for each place
(`unity/evidence/showcase_phase2/20261120/gate_barrels/heightmaps.json`). Caravan overflow: whole barrels at
x -46.8..-46.2 and -44.8..-44.1, z 4.9..5.6, 0.79 m tall; pieces at z 6.1..7.6 (the barrel half 0.3-0.39 m at
x -44.85..-44.25, z 6.15..6.85; everything else 0.05-0.19 m). Rations: whole barrels at x -37.7..-37.2 and -36.4..-35.9,
z -17.6..-17.1, 0.59 m tall; pieces at x -37.9..-35.6, z -15.6..-16.8, up to 0.29 m.

**Which barrels Carl meant:** the caravan overflow set by the truck, with high confidence: it is the broken barrel set
nearest the West Gate, he made the same complaint about it on 3 Oct, and the 3 Oct fix left an invisible 0.9 m box
standing in exactly the stave field he would walk through. The Rations stall set is the only other broken barrel set in
the game and had the same fault, so it is fixed too.

## What changed (`Editor/GateBarrelsPass20261120.cs`)

| Object | Change | Why |
| --- | --- | --- |
| `Karaveen caravan market/Caravan stock/COL_barrels` (BoxCollider on the market prefab instance) | Transform to (-46.5, 0.425, 5.25), no rotation; box 0.72 x 0.85 x 0.76 m | Holds the west whole barrel only. The staves the 3 Oct box stood on are walk-over. |
| `Gate barrels colliders/COL_caravan_barrel_east` (new, own scene root, layer 0 like the market colliders) | BoxCollider at (-44.45, 0.425, 5.25), 0.74 x 0.85 x 0.76 m | The east whole barrel had no collider. The 1.3 m gap between the two barrels stays open. |
| `Karaveen caravan market/Stall Rations/COL_goods.010` | Transform to (-36.8, 0.3, -17.35), no rotation; box 1.9 x 0.6 x 0.6 m | Holds the two small whole barrels (0.8 m apart, too narrow to walk between); the stave field is walk-over. |
| `AthenDebugBridge` landmarks | `gb_<line>_a` / `gb_<line>_b` for the five walk lines (ground height) | For the native check's `goto`. |
| `Gate barrels review cameras` (new scene root) | `cam_gb_caravan_east`, `cam_gb_caravan_north`, `cam_gb_rations_west`, `cam_gb_rations_north` at 1.6 m | Review. |

Nothing was moved or removed: every barrel, stave and lid stays where the market put it; only invisible colliders
changed. The debris left without a collider is at most 0.39 m high (the caravan barrel half) and mostly under 0.2 m,
below the 0.4 m knee line in the brief; the colonist's feet pass through it. No collider was added to the debris (a
0.3-0.4 m step would stop or pop the player: the controller's step offset is 0.3 m). The market kit (`KaraveenMarket.glb`
and its prefab) is untouched; the changes are instance overrides and one added object. Walker routes, residents' work
stops, NPCs, doors, the Lattice approach and the terminals are not near (verify: nothing within 1 m of any changed box).

## Survey (`--steps survey`, `survey.json`)

Every enabled non-trigger collider whose top is under 1.2 m above the local ground in the city, the West Gate outpost
and the spawn apron (445), each with the renderers it overlaps and eight walks across it with a CharacterController
copied from the player (height 1.8, radius 0.35, step offset 0.3, slope 45, skin 0.03, walk 3.4 m/s, gravity 22, ground
snap 0.4, PlayerMotor's Move and ground-snap sequence at a fixed 0.02 s), plus every barrel-like or debris renderer
(167) with the colliders under it. Findings besides the two fixed places:

| Place | Object | State | Left as it is because |
| --- | --- | --- | --- |
| West Gate outpost, Berms side | `Outer Berms/West Gate outpost/Outpost/Fuel drum`, two `Water drum`s, propane, jerrycans by the guard post | Upright, whole, own boxes | Obstacles that read as obstacles, beside the post, out of the lane. |
| Inside the West Gate | `AuthoredWorld/COL_PROP_wreck_severed_foot` and `.001` (wreck gantry feet, (-51.0, -4.9) and (-55.5, 5.8)) | Steel base slabs 1.7 x 1.15 x 0.4 m, box matches the mesh | Not barrels and not loose debris; 0.4 m of solid steel the legs would visibly pass through. They stop the player (above the 0.3 m step); off the gate lane. Could get a ramp collider if Carl wants to climb them. |
| East Gate (+X spawn) apron, cam_lb_avenue_west's view | `Ward district retrofit/Street clusters/COL_cluster_3` ((22.6, 3.75), against the Repairs wall): three upright drums and two cement bags lying beside them | Upright drums; the bags (0.35 m) lie inside the cluster's box against the wall | Not broken barrels and not on a walking line. Noted defect: the 26 Sep box is sunk (top 0.5 m, drums 0.9 m) and about 0.3 m short of the southernmost drum (drum to z 2.85, box from z 3.15), so the legs can clip that drum's edge. The other two `drums` clusters ((-29.5, 20.5), (29, -21.5)) use the same recipe and were not measured. |
| Spawn apron | `West Gate approach: caravan goods waiting` (handcart, crates, a sack on a crate) | Upright goods, own boxes | Not debris. |
| City, street dressing | All `drum_*`, `fire_barrel` and the Ward life ration drums | Upright, whole, own small boxes | Keep (brief's rule). |
| Outer Berms machine depot | `Oil drum (spilled)` at (-86.5, -42.1) | A whole drum lying on its side (0.64 m), own box | Not in the city, not broken; a lying drum is an obstacle you would step round. |
| Retrofit shop sides | `Ward district retrofit/Shop retrofits/COL_*_bin` (3.4 x 0.9 x 0.9 m, renderers hidden by the street dressing install) | Invisible boxes along four shop side walls | Against walls, not broken barrels; unchanged. |

## Run

```sh
P2=~/.local/state/ward-programme/showcase-phase2-20261120
$P2/run.sh gb $P2/seq.sh install gb AthenHill.Editor.GateBarrelsPass20261120.RunBatch install,verify; $P2/wait.sh gb
# steps: survey (survey.json), heightmaps (heightmaps.json), lines-before / lines-after (walk the lines, no assertions),
#        install (idempotent: a second run leaves the scene file byte-identical), verify (verify.json), rollback
# rollback: restores both colliders' boxes and transforms from record.json, removes the added collider root, the cameras
#           and the landmarks. Tested (gate_barrels-6): every value back exactly; the market instance keeps three
#           redundant overrides equal to the prefab values.
# scene diff by fileID: python3 art/gate_barrels_20261120/scene_diff.py BEFORE.unity AFTER.unity [OUT.json]
```

Native check (for the orchestrator; not run by this pass):

```sh
$P2/run.sh gb-native $P2/native_check.sh gate_barrels unity/tools/check_gate_barrels.py ATHEN_EXE=<build>/AthenHill.x86_64 \
  ATHEN_OUT=unity/evidence/showcase_phase2/20261120/gate_barrels/native; $P2/wait.sh gb-native
```

It walks each of the five lines both ways with real W from the `gb_*` landmarks (reach the far end within
distance/3.4 x 1.35 + 0.6 s, rise <= 0.3 m, largest step <= 0.25 m, follow camera distance never jumps more than 0.8 m
between samples), captures the colonist half-way along each forward crossing (`mid-<line>.png`, legs among the staves),
then every `cam_gb_*` camera at 13:00 and 20:30. The city loop and the range tutorial (which walks out through the West
Gate) should be run with it.

## Verified, and not

- **Verified (-nographics, saved scene):** `verify` walks the five lines both ways with the player-copy controller:
  10/10 reach the far end in free-walk time (1.70 s for 5.8 m, 0.58 s for 2 m), rise 0.015 m (the teleport offset), no
  collider touched. Before the install the same lines (`lines-before.json`) took 3.24 s / 2.64 s (caravan west-east),
  1.48 s (caravan north-south) and stopped at 0.4 m and 1.5 m (Rations). No walker route segment, NPC or landmark within
  1 m of a changed box; market prefab link intact; no missing scripts; render chunk fingerprint matches (the market is
  not a chunk source). Scene diff (`scene-diff.json`): only the market PrefabInstance's two collider transforms, the two
  BoxCollider sizes, the landmarks' child list, the scene root list and the new objects changed.
- **Not verified:** nothing native (no build, no real input, no camera). I have not looked at the barrels with my own
  eyes: graphics-mode Editor captures are not allowed tonight; positions come from the LOD0 vertex height maps. How it
  looks when the colonist's feet go through the 0.3 m barrel half and the low shells is for the native captures
  (`mid-caravan_staves_ew.png`) and Carl. The follow camera can only meet fewer colliders over the staves than before;
  the new 0.85 m barrel box is the size of the barrel. Camera behaviour is checked natively only by the distance
  samples in the check.

## Proposed text for unity/EDITING.md (after "Dust-bowl grade and Karaveen caravan market")

> ### Market barrel colliders (20 November 2026)
>
> The Poly Haven `wooden_barrels_01` set (two whole barrels and a broken one in pieces) is merged into two market `Goods`
> meshes: the caravan overflow by the truck and the side of the Rations stall. Only the whole barrels collide: the
> caravan's `Caravan stock/COL_barrels` (west barrel) plus `Gate barrels colliders/COL_caravan_barrel_east`, and the
> Rations stall's `COL_goods.010` (both small barrels). The staves, lids and barrel halves have no collider and are walked
> over. If you move a barrel set, move its colliders with it and re-measure with
> `GateBarrelsPass20261120 --steps heightmaps` (the build script's coordinates do not match the imported mesh: the
> 3 Oct fix put its box over the staves that way). Values, survey and rollback: `art/gate_barrels_20261120/README.md`.
> Review cameras `cam_gb_*`; QA landmarks `gb_<line>_a/_b`.

## Proposed AGENTS.md row (section 3)

> | Market barrel colliders | 20 Nov 2026 (`art/gate_barrels_20261120`, `Editor/GateBarrelsPass20261120.cs` with `survey`, `heightmaps`, `install`, `verify`, `rollback`; Carl: "the broken ones on the floor need to be able to be walked over"): the broken Poly Haven barrel sets at the Karaveen caravan overflow (13.8 m inside the West Gate) and beside the Rations stall collide only on their whole barrels; staves, lids and barrel halves (<= 0.39 m) are walk-over. The 3 Oct box had been placed over the staves and left the east barrel open. Instance overrides plus one added collider (scene root **Gate barrels colliders**); market kit untouched. Verify: five walk lines clear both ways with a player-copy CharacterController (before: slowed or stopped). Not natively tested; not yet accepted by Carl. |

## Evidence

`unity/evidence/showcase_phase2/20261120/gate_barrels/`: `survey.json`, `heightmaps.json`, `lines-before.json`,
`install.json`, `verify.json`, `scene-diff.json` (before gate_barrels-4 vs installed), `scene-diff-rollback.json`
(before vs rolled back), `rollback.json`. Unity logs: `unity/evidence/showcase_phase2/20261120/install-gate_barrels-<n>.log`
(1 survey, 2 heightmaps, 3 lines-before, 4 install+verify, 5 second install (scene unchanged)+verify, 6 rollback,
7 install+verify). Rollback record: `art/gate_barrels_20261120/record.json`; scene before the first install:
`~/.local/state/ward-programme/showcase-phase2-20261120/scenes/before-gate_barrels-4.unity`.
