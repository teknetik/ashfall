# Ward residents (showcase phase 2, 20 Nov 2026)

Status: **installed in the saved scene and verified** (20 Nov 2026, 22:11, `-nographics` verify OK:
`unity/evidence/showcase_phase2/20261120/residents/verify.json`). Meshy was blocked on the free plan at 19:51; Carl
upgraded it and the orchestrator put a paid key in `.env` (balance 1100). The residents cost 123 credits (balance 977).
Not natively tested (the orchestrator's batch does that), no Editor captures (not allowed tonight), not accepted by Carl.
The voices are unheard.

## Who and why

The city has one player, eight talking colonists (Mira, Torr, Vex, Linn, Brann, Tamsin, Wardens Ossa and Rell) and four
ambient walkers (Daro, Sel, Anso and the yard mechanic). Three places built to show how Ward lives had nobody in them.
The survey (`unity/evidence/showcase_phase2/20261120/residents/survey.json`, read-only `Editor/WardResidentsSurvey20261120.cs`;
maps `survey/*.png`) put the residents here:

| Resident | Role | Place | Why there | Distinct from |
| --- | --- | --- | --- | --- |
| **Nadje** (`npc_resident_nadje`) | Karaveen produce and pottery trader, woman ~55, tall, indigo tunic, rust sash, linen apron, braid down her back | Karaveen caravan market by the West Gate (the -X portal): caravan stock crates, pottery stall, behind the produce counter | Six stalls and a cookfire with no one selling. Lore: the Karaveen still trade with outposts; the market is their link to Ward | Daro (Karaveen man, porter on the east avenue) |
| **Pell** (`npc_resident_pell`) | Node 07 goods dock tally clerk, lanky man ~24, orange dock vest, bay tags, cyan slate | Node 07 goods dock east of the Meshy ring: tally desk, platform scale, bays 1 and 2, porters' handcart | The dock was dressed for weighing and tallying Tube goods but had no clerk. Lore: the Tube carries goods only | Sel (nanofab technician looping by the Tube gate) |
| **Oren** (`npc_resident_oren`) | Old water carrier, ~70, stooped, white beard, quilted waistcoat, steel water can on a back carrier | From his door in the stacked south-wall container homes (Wall home south 1) to the Wardens' ration taps behind Vanguard Hall, and home | Ties two empty places together: the container homes and the water ration point ("two cans a house"). Lore: Ward lives on its aquifer | Linn (elder colonist who stands at the hill) |

Hydroponics yard: Anso is already the grower; with three residents the market, the dock and the water court were emptier.

## Concepts (OpenAI gpt-image-2)

`concept/trader_sheet_v2.png` (v1 had the braid over the shoulder in front but down the back from behind: rejected for
multi-view inconsistency), `concept/clerk_sheet_v1.png`, `concept/carrier_sheet_v1.png`. Prompts `concept/p_*.txt`,
records `concept/concepts.json`, script `concept/gen_api.py`. `codex exec` image generation (`concept/gen.sh`) failed:
the ChatGPT plan hit its usage limit until 21 Nov 11:01 (`concept/codex_*.log`), so the `.env` OpenAI key was used.
Checked by eye: full body, front/side/back, A-pose, faces evenly lit, hands open, nothing crossing the body. Known risks:
Nadje's apron also shows on the back panel and her hair came out dark instead of silver; Pell's bay tags carry
numbers (07, 28, 41), which is fine as tags; Oren's tin cup hangs near his right hand.

## Meshy

Task ids, options and credits: `meshy/ward-residents-20261120/README.md` (123 credits: three models at 30, three rigs
at 5, six clips at 3). Models: Meshy 7.1 multi-image, 60k triangles, PBR, 4k base colour (kept through the rig and the
import), rigs with finger bones (66-68 bones; the 7.1 rig root is `SmartRigArmature`, not `Armature`).

| Resident | Height | Walk | Planted-foot stride | Route speed | Playback | Idle slot | Talk slot |
| --- | ---: | --- | ---: | ---: | ---: | --- | --- |
| Nadje | 1.74 m | Walking 2 (566, own rig) | 0.907 m/s | 0.90 | 0.99 | Bend Over Pick Up Inspect (281, own) | Checkout Gesture (34, Pell's rig) |
| Pell | 1.86 m | Walking 2 (566, own) | 0.967 m/s | 0.95 | 0.98 | 281 (Nadje's rig) | Checkout Gesture (34, own) |
| Oren | 1.66 m | Walking 2 (566, Pell's rig) | 0.838 m/s | 0.80 | 0.95 | 281 (Nadje's rig) | Stand and Drink (342, own) |

Changes from the plan, found while building:
- The bought Elderly Shaky Walk (553) shuffles at 0.17 m/s (0.5 m of hip travel in 2.8 s): unusable on a 62 m route.
  Oren walks on Pell's Walking 2 instead (3 credits not used in game; the clip is kept in the Meshy folder).
- The 7.1 rigs are a new generation (`SmartRigArmature`, extra `Bone_006/012`), so the planned reuse of Mira's talk_313
  and Linn's idle_252 (old `Armature` rigs) was dropped; only clips from these three rigs are shared.
- On these rigs the root-motion speed of Walking 2 is 17-28 % above what the in-place clip's planted foot does
  (1.09 vs 0.91 m/s for Nadje). The prefab now uses the planted-foot speed, the one that keeps feet still.
- The LOD0 renderer on 7.1 rigs is `Mesh_0`, not `char1`.

Looked at with my own eyes (Cycles, `meshy/ward-residents-20261120/*/renders/`, sheets `faces.png`, `bodies_cc.png`,
`trader/renders/body_sheet.png`, `rig_trader.png`, `rig_clerk_carrier.png`): all three accepted. Faces read as real,
distinct people at 0.9 m (Nadje's lined face, earrings and headband; Pell young and freckle-free with a moustache and
pencil; Oren bald with a white beard); hands have five separate fingers, nothing fused; silhouettes match the
concepts (Nadje's braid hangs free down her back, Oren's can sits high on his back). Rigged LOD0 at rest and the
walk/work clips skin cleanly. **Defect: the skin carries a fine crosshatch (woven-fabric-like) pattern, baked into the
albedo** (fragmented Meshy atlas, `carrier/tex/`), strongest on Oren's forehead and beard, faint on Nadje and Pell.
At conversation distance in the native build it may show; a Meshy retexture (10 credits each) is the likely fix and is
outside the plan. Smaller: Stand and Drink is an empty hand at the mouth (his tin cups hang at his hip); Oren's cups sit
close to his right hand; Nadje's apron also shows on her back; Pell's tags carry numbers (07, 28, 41).
Not seen: anything in Unity (no captures tonight), the 17:00 low-sun face look, night.

## Routes and work stops

`routes.json` (source of truth; the installer rebuilds the waypoints from it). Waypoints at y 0, stops pause at a
waypoint, yaw 0 = +Z. Checked offline by `check_routes.py` (survey colliders, 0.28 m body half-width, talking
colonists 3 m, other walkers' lanes, the Lattice approach box |x| < 4.4, z 21-39) and in Unity by the `simulate` step
(the real scene's colliders, body capsule r 0.25 m every frame for two laps). Both clean:
`route_check.json`, `unity/evidence/showcase_phase2/20261120/residents/simulate.json`.

| Resident | Speed | Lap | Stops (seconds, clip) | Nearest talking colonist |
| --- | ---: | ---: | --- | ---: |
| Nadje | 0.90 m/s | 57.5 m, 128 s | caravan stock crates 14 s (idle), pottery stall 12 s (idle), behind the produce counter 38 s (talk) | 16.4 m (Brann) |
| Pell | 0.95 m/s | 19.3 m, 82 s | tally desk 20 s (talk), platform scale 10 s, bay 2 10 s, bay 1 10 s, handcart 12 s (idle) | 15.6 m |
| Oren | 0.80 m/s | 62.4 m, 129 s | home door 25 s (idle), ration tap 16 s (talk = drink), waiting for the can 10 s (idle) | 12.5 m |

Kept clear: doors and stairs (Oren stands in front of his own step, not on it), the Lattice ring approach, terminals,
trade counters (Nadje stands inside the produce stall between its back and counter, 0.35 m from each), the talking
colonists' spots, Daro/Sel/Anso/mechanic lanes (Oren's lane along z -24.5 runs 1.45 m south of Anso's loop edge),
the water court's jerrycan queue and the dock's handcart.

## Code

- `Scripts/AmbientWalker.cs` (additive): `WorkStop` (waypoint, seconds, facing yaw, talk clip, label), `stops`,
  `easeDistance` 0.9 m / `slowFactor` 0.45 (speed eases in and out of a stop; ActorAnimation scales the walk playback
  with it, so feet do not slide), `AtWork`, `CurrentStop`, `StopSecondsLeft`. A stop at the same place as the previous
  one (zero-length segment) follows it. **Walkers without stops run the original code path unchanged** (same `Start`
  arithmetic, same `Update` line); the installer's verify compares every existing walker against `before.json`.
- `Scripts/Npc/NpcBarker.cs` (+`AtWork`) and `Scripts/Npc/BarkDirector.cs` (one line): a walker standing at a work stop
  may also make Idle remarks (player within 9 m, in sight). Existing walkers never stop and have no Idle lines.
- `Editor/WardResidentsInstall20261120.cs`: steps `barks, simulate, import, prefab, install, verify, rollback, capture`
  (header comment lists what each does). One scene root **Ward residents** (walker roots, `Routes`), cameras under
  **Ward residents review cameras**.
- `Editor/WardResidentsSurvey20261120.cs`: read-only survey.
- `Tests/Editor/AmbientWalkerStopsTests.cs`: 3 Edit Mode tests (stop reached, facing, walks on; easing and one stop per
  pass; no stops = no work state).

## Voices (ElevenLabs, unheard)

`barks.json` (source of truth), `generate_voices.py` (copy of the phase 1 tool: same model `eleven_multilingual_v2`,
settings, mastering, records), `voice_manifest.json`. Takes: `unity/AthenHill/Assets/AthenHill/Audio/ElevenLabs/NpcBarks/resident_*-*.wav`,
sources `unity/staging/elevenlabs-audio/npc-barks-20261120/`. Spent 305 subscription characters (35,302 -> 35,607 of
46,736; the per-request cost headers sum to 339). Voices not used elsewhere: Nadje = **Kirsty** (`3HCsOhirtjbPmdcSOPBt`,
Yorkshire), Pell = **Alfie** (`BuptxElFd80GDtsmyQIU`), Oren = **Bill** (`pqHfZKP75CvOlQylNhV4`, old). BarkSets
`Data/Barks/barks_resident_{nadje,pell,oren}.asset` exist with every take bound (step `barks`); they are not referenced
by the scene until `install`.

| Speaker | id | trigger | hours | line |
| --- | --- | --- | --- | --- |
| Nadje | pass_caravan | Passing | | Fresh off the caravan. Dates, beans and salt. |
| Nadje | pass_jars | Passing | | Water jars, sealed and tested. Mind your feet. |
| Nadje | idle_berms | Idle | | Every jar on this table crossed the Berms on a beast's back. |
| Nadje | idle_dust | Idle | 10-18 | Dust front's coming. I can smell it. Cover the grain. |
| Nadje | idle_lamps | Idle | 18-23 | Ward keeps its lamps low. Good for prices, bad for eyes. |
| Nadje | weapon | Weapon | | Holster that. Nobody haggles at gunpoint. |
| Pell | pass_bay | Passing | | Bay two's live. Stand clear of the canisters. |
| Pell | pass_count | Passing | | Forty-one in, nine out. Don't make me count again. |
| Pell | idle_goods | Idle | | Goods only through the Tube. People still ask. |
| Pell | idle_scale | Idle | | Scale's reading heavy again. Sand in the plate. |
| Pell | idle_night | Idle | 20-5 | Night shift. The node runs on half power, so we count slow. |
| Pell | weapon | Weapon | | Not near the canisters. Please. |
| Oren | pass_ration | Passing | | Two cans a house. Same as in my father's day. |
| Oren | pass_slow | Passing | | Mind the old man. Slow, but he gets there. |
| Oren | idle_tap | Idle | | Cold, from the deep rock. Best water on Tir. |
| Oren | idle_wall | Idle | | Forty years I've lived on that wall. It's never fallen. |
| Oren | idle_dust | Idle | 12-20 | Dust front tonight, mark me. My knees know. |
| Oren | weapon | Weapon | | Put it away, son. The Wardens are watching. |

Note: `NpcLifeInstall20261119 --steps scene` rebuilds `BarkDirector.speakers` from its own list; re-running it would
drop the residents' barkers. Re-run this pass's `install` afterwards (it appends them again).

## Install, verify, rollback

```sh
P2=~/.local/state/ward-programme/showcase-phase2-20261120
# models (done): meshy/ward-residents-20261120/residents_meshy.py NAME, then ./prepare_unity.sh
$P2/run.sh residents-N $P2/seq.sh install residents-N AthenHill.Editor.WardResidentsInstall20261120.RunBatch import,prefab,install,verify
$P2/run.sh residents-N $P2/seq.sh install residents-N AthenHill.Editor.WardResidentsInstall20261120.RunBatch rollback   # root and cameras off, barkers out of the director
```
Runs: residents-9 (import, prefab), residents-10 (install), residents-12 (prefab, install, verify: OK). Verify:
LOD0 19,999 / 20,000 / 19,999 and LOD1 6,000 triangles; soles within 0-2.4 cm of the ground over the walk; work clips
lowest point within -1.7 to +3.2 cm; planted stride matches; playback 0.95-0.99; routes touch no collider; nearest talking
colonist 12.5 m; existing walkers identical to `before.json`; 14 `cam_res_*` cameras; 6 voiced lines each in the
BarkDirector (14 speakers). Saved-scene roster: 19 active ActorAnimation, 7 active AmbientWalkers (Daro, Sel, Anso,
mechanic and the three residents), 8 talking colonists.

`unity/tools/capture_building_audit.py` and `check_district_actor.py` asserted 9 actors (stale since October); both now
expect 19, the saved-scene count verify records. The native run should confirm the runtime count.

## Review cameras (created by install)

17 cameras under **Ward residents review cameras**:
- `cam_res_<name>_face`, `_body`, `_beside` (nadje, pell, oren): **these follow the resident** (`Scripts/Npc/ResidentReviewCamera.cs`,
  LateUpdate in development builds only; it tries nine directions round the facing and takes the first with a clear
  sphere-cast line from the head, never closer than 0.65 / 2.0 / 1.0 m): face ~0.9 m in front of the face, body ~3 m, beside = conversation distance
  (~1.4 m, 30 degrees off the face, player eye height 1.62 m). A fixed face camera at one stop usually showed a wall
  (orchestrator's b2 lookbook, 23:02), because the walkers are elsewhere on their routes when the clock is paused. NativeQa
  "view" copies the camera's pose at the moment it is called, so re-issue the view before each capture.
- One fixed camera per other work stop (frames the stop; the resident is in it only while working there):
  `cam_res_nadje_caravan_stock_crates`, `cam_res_nadje_pottery_and_water`, `cam_res_pell_platform_scale`,
  `cam_res_pell_bay_2_canisters`, `cam_res_pell_bay_1_canisters`, `cam_res_pell_porters_handcart`, `cam_res_oren_ration_tap`,
  `cam_res_oren_ration_tap_waiting`.
- QA landmarks `res_nadje`, `res_pell`, `res_oren` under Landmarks: where the player stands beside each resident's main
  stop (for `goto`).

Native frames: `unity/tools/capture_residents_native.py` (ATHEN_EXE, ATHEN_OUT): face and body of each resident at 13:00,
17:00 and 20:30 wherever they are; one walk-in / stop / walk-out sequence per resident from that stop's fixed camera
(a frame every 0.5 s); the player on `res_<name>` facing the resident at work (follow view) plus the `_beside` frame.

Note: another agent's character arms pass (Carl's playtest note on arm posture) is data-driven and re-runs over Nadje,
Pell and Oren; their clips must not be changed here for arm posture.

## Native batch (when installed)

City loop and NPC life check (BarkDirector speakers now 14, `>= 11` still holds); lookbook of the `cam_res_*` cameras
at 13:00 and 20:30; frame-time A/B with the **Ward residents** root on and off (three ~20k skinned meshes, culled
off-screen); walk past each resident for a Passing line, stand 5 m from Nadje at her counter for an Idle remark;
NightActorLighting picks the residents up through their AmbientWalker roots (check faces at 20:30).

## Proposed text for the orchestrator

AGENTS.md section 3, "Additional ambient actor" row, replace "The current roster is one player, four talking NPCs and
four ambient walkers." with: "The current roster is one player, eight talking colonists (Mira, Torr, Vex, Linn, Brann,
Tamsin, Wardens Ossa and Rell), four ambient walkers (Daro, Sel, Anso, the yard mechanic) and three residents with work stops (Nadje, Pell, Oren; `art/ward_residents_20261120`)." Add a row:
"| Ward residents | 20 Nov 2026 (`art/ward_residents_20261120`, `Editor/WardResidentsInstall20261120.cs`, scene root
**Ward residents**): Nadje (Karaveen trader, caravan market), Pell (Node 07 dock tally clerk), Oren (old water carrier,
south wall homes to the ration taps), AmbientWalkers with work stops (`AmbientWalker.stops`; walkers without stops
unchanged) and voiced barks (Kirsty, Alfie, Bill; idle remarks while at work). Meshy 7.1 models with 4k base colour and finger-bone rigs, LOD0 20k / LOD1 6k, culled off-screen; skin albedo shows a fine crosshatch at close range. Installed and verified 20 Nov; not natively tested. Not yet accepted by Carl. |"
Section 7: "all nine current actors" -> "every current actor (the player, eight talking colonists, four ambient walkers
and three residents)".

unity/EDITING.md, new section "Ward residents (20 Nov 2026)": "Routes and stops live in
`art/ward_residents_20261120/routes.json`; edit there and re-run `WardResidentsInstall20261120 --steps simulate,install,verify`
(install rebuilds the waypoints under Ward residents/Routes). In the Inspector, an AmbientWalker's Stops list sets each
pause (waypoint index, seconds, facing yaw, Talk Clip = the second work motion); Ease Distance and Slow Factor shape the
approach. Bark lines are in `Data/Barks/barks_resident_*.asset` (Inspector edits make a line caption-only). Switch the
residents off with the Ward residents root."

## Skin de-weave (20 Nov, after the b4 native frames)

The b4 frames showed the crosshatch at conversation distance (Pell's cheeks and forehead, Oren's forehead). Fixed without
Meshy: `tex/deweave.py` + `tex/apply_deweave.py`. Mask = base-colour texels under LOD0 triangles skinned mainly to the
head, neck, hands, fingers and forearms AND in the YCbCr skin range (cloth weave elsewhere kept). In 128 px tiles (Hann,
50 % overlap) FFT peaks in the 2.5-32 px period band above 1.5x the radial median are cut back to it (phase kept), each
texel changes by at most 18 levels (stops ringing specks at chart borders), blended through the feathered mask; the
re-baked normal map is flattened 75 % toward flat in the same mask. Originals kept as `meshy/.../<key>/rigged_fixed_weave.glb`;
masks and textures in `tex/`. LOD0 and LOD1 share the material, so both get it. Installed: residents-16 (verify OK).
Seen in Blender close renders (`meshy/ward-residents-20261120/zoom2.png`, `zoom3.png`, `deweave_faces.png`; weave_* =
before): Nadje and Pell clearly cleaner (canvas look gone from cheeks and forehead, wrinkles and brows kept); Oren's
forehead only partly (his pattern is a coarser, less periodic pebble). Next if the native face frames still show it on
Oren: a Meshy retexture of his model (10 credits, original UVs).

## Open defects and unverified

- Crosshatch: reduced by the de-weave on Nadje and Pell, only partly on Oren (see above).
- Not natively tested: walking, stopping and turning at the stops, foot sliding at the eased speeds, LOD switch, culling,
  night lighting, frame cost (three 20k skinned meshes with 4k base colour, ~100 MB of textures).
- Unity never rendered them: no Editor captures were allowed tonight.
- The voices are unheard. Stand and Drink on an empty hand.
- Phase-2 `seq.sh` copies the scene before it waits for the Unity lock, so "scene-changed" can be a false positive.
