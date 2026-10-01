# Warden training range — 1 October 2026

Carl: "the training robot section could use work." The range beyond the West Gate, where the Outer Berms primer
teaches recruits to shoot (three Meshy steel knockdown plates in front of a bare natural mound, a firing bench, the
range control) before they meet the machines on the service road, rebuilt as a working Warden range: firing bays,
a timber-revetted earth backstop, a range officer's post, distance posts, a machine lane with a tethered training
drone and a stripped worker droid in a target frame, and a robot service apron. Sources, run order and licences:
`art/training_range_20261001/README.md`. Editor: `Editor/TrainingRangePass.cs`, `Editor/TrainingRangeInstall.cs`.
Scene root: `Outer Berms/Warden training range`. Not yet accepted by Carl.

## What changed (saved scene)

- **Firing point** (at `checkpoint_firingline`, bay 1): three timber bays with plywood dividers (foot sandbags, ear
  defenders on a hook), shooting benches with sandbag rests and charge-cell cases, lane boards 1–3, spent cells and
  brass, painted firing line and worn standing spots, spent-cell bin, waiting bench and water can.
- **Range officer**: trestle table (range log, radio, megaphone, binoculars, field lantern), stool, nano-cell crates,
  water can; RANGE ORDERS board (seven original orders) facing the path from the gate; red flag and red "range live"
  lamp at the right end of the line; timber flood pole with two floods.
- **Distance posts** 5 / 10 / 15 M on the left edge (outside every line of fire).
- **Backstop**: a 28.6 m earth bank generated on the real Berms ground (4 914 triangles, Berms Ground material, own
  mesh collider; rises 3.15 m with a hand-heaped crest and spill cones at both wall ends), a timber revetment in front
  (posts, sleepers in three timber tones, shot-through sleepers with sand behind at each lane, two courses of
  sandbags, painted lane numbers 1–3), impact-scar decals where the tutorial's lines of fire meet the wall, a red flag
  on the crest, spare sleepers, spade, sledgehammer, sand cart with a tyre-track run and spilled sand, sacks.
- **Machine lane 4**: start frame with a MACHINE LANE 4 board, an agility run of eight tyres laid flat, two timber
  cover barricades, a steel tether gantry with a training drone hung from it, a goal-post target frame holding a
  stripped worker droid (the accepted droid baked in its combat stance, dust-dulled, dead optics), painted lane lines.
- **Service apron**: blast wall, shade shelter over three drone charge docks (cyan charge rings, status lamps; two
  training drones docked), repair bench (vice, test meter, toolbox, rag), welding cart, compressor, generator with
  cable runs, fuel can, tool trolley, caged work lamp, oil stains.
- **Night lighting** on the Ward light clock: range flood (plates), range flood (machine lane), shelter work lamp,
  officer's lantern (night only), red range-live lamp (practical).
- **Retired, inactive** (69 objects, listed in `install.json`): the old firing bench and its sandbags, the flag that
  stood in front of the line, the three floating unlit "PLATE 0n" TextMesh numbers, rocks/boulders/shrubs on the
  range floor (small stones kept where no shot passes and nothing is built).
- **Not moved or changed**: the three plates (health, collision, knock-down, tutorial callbacks), range reset
  station, briefing board, Ossa and Rell, arms locker, encounters, respawn, all `checkpoint_*` landmarks, routes.
- Review cameras (scene root `Training range review cameras`): `cam_range_overview`, `cam_range_line`,
  `cam_range_bays`, `cam_range_backstop`, `cam_range_plates`, `cam_range_machine_lane`, `cam_range_droid`,
  `cam_range_apron` (before + after) and `cam_range_lane_start`, `cam_range_bench` (after only).

## Numbers

- Root: 74 prefab instances, LOD0 674 778 triangles (all LOD levels 821 362), 51 colliders, 24 decal projectors,
  5 lights (all on the light clock), 62 shadow-casting renderers (hand-sized and flat props cast none).
- Heaviest pieces (LOD0): compressor 79 042 (Poly Haven, LOD1 15 808 / LOD2 4 742), revetment 39 824 (LOD1 at 45 %
  screen height), worker droid shell 30 895, training drone 30 859 ×3, welding cart 29 418, work lamp 22 893.
- Verify (`verify-saved-scene.json`): installed, 0 missing materials, nothing retired still active, tutorial targets
  3/3, locker/first contact/depot bound, reset station present, Ossa and Rell present, landmarks unchanged,
  `shotsBlocked` [] (eye at the firing line to each plate's aim point), render-chunk fingerprint matches.
- Frame time: see "A/B frame time" below.

## A/B frame time

Native 1920×1080, High preset, 100 % render scale, uncapped, OpenGL Core, RTX 3060 12 GB / i9-10850K, Editor closed.
Two development builds of the same saved scene, the range root toggled off (`Builds/tr-ab-off`) and on
(`Builds/tr-ab-on`; the saved scene ends ON), profiled alternately on/off/on/off for 8 s per camera
(`art/training_range_20261001/run/ab2.sh`, `ab_city.sh`; raw: `ab/*/lookbook.json`). "Off" still has the replaced
clutter retired, so the difference is this pass's own objects. GPU time is unavailable (null) in this build; the
player is GPU-bound, so mean frame time is the measure. The desktop drifts about ±1–1.5 ms between runs.

| View | Off (ms, run 1 / 2) | On (ms, run 1 / 2) | Change | Tris off → on | SetPass off → on |
| --- | --- | --- | --- | --- | --- |
| `cam_range_overview` 13:00 (wide) | 3.04 / 3.01 | 3.69 / 3.73 | +0.69 ms | 1.31 M → 2.22 M | 128 → 180 |
| `cam_range_overview` 20:30 | 4.04 / 3.77 | 4.73 / 4.61 | +0.77 ms | 1.68 M → 2.65 M | 146 → 205 |
| `cam_range_line` 13:00 (close, firing line) | (4.10) / 2.42 | (killed) / 3.14 | +0.73 ms (run 2) | 0.51 M → 1.36 M | 74 → 139 |
| `cam_westgate_mouth` 13:00 (gate looking out) | 4.35 / 4.35 | 4.57 / 4.48 | +0.17 ms | 2.28 M → 2.61 M | 156 → 174 |
| `cam_hill` 13:00 (district) | 15.05 / 15.19 | 15.94 / 15.30 | drift only | 11.40 M = 11.40 M | 321 = 321 |

p99 stayed below 7 ms on every range view (on: 4.99–6.81 ms) with no hitches; `cam_hill` p99 17.45–19.45 ms in both
states (the district's existing limit; the range submits nothing there). Run-1 close: the "on" run was killed by the
programme's VRAM watchdog (desktop + player above 11.4 GB) and the "off" run (4.10 ms) is a drift outlier, so only
run 2 is paired. The range views stay at 210–320 fps; the cost is over the brief's ~0.5 ms guide at the range's own
wide view and is reported, not hidden (see remaining defects).

## Evidence

- BEFORE (current scene before install, same cameras): `native-before/` (+ `native-before-close/`),
  `native-before-existing/` (30 Sep).
- AFTER: `native-after2/` (install5, 13:00 and 20:30 sheets), `native-after1/` (install4). Side-by-side pairs:
  `compare/*.jpg` (`compare/make_pairs.py`).
- Editor review iterations: `editor-review/install1..5` (+ sheets).
- Install / verify / build records: `install.json`, `verify-saved-scene.json`, `build-assets.json`.
- Rollback: `rollback/scene-before-training-range.unity` (scene before the first install), or deactivate the root and
  reactivate the objects listed in `install.json`.

## Real-input checks (final build 12:01, scene = install5 + camera move, range ON)

- **Range tutorial** (`unity/tools/check_checkpoint.py` via `art/training_range_20261001/run/tutorial.sh`, evidence
  `native-tutorial/`): **passed 10/10** — W through the West Gate, Ossa and Rell dialogue, briefing board, wheel zoom
  to first person, locker issues the pistol once, range reset station responds without bypassing the primer, real F
  input knocks down all three plates and advances to First Contact, holster on return, and its embedded city loop
  (dialogue, trade, travel, modal input). 0 exceptions in `native-tutorial/Player.log`.
- **City loop** (`$O/native.sh cityloop`, `native-cityloop.out`): **CITY LOOP PASS**.

## Best before/after pairs (native, matched cameras)

`compare/cam_checkpoint_range-h13.00.jpg` (the tutorial's own range view), `compare/cam_range_line-h13.00.jpg` and
`-h20.50.jpg` (from behind the firing line), `compare/cam_range_backstop-h13.00.jpg`, `compare/cam_range_droid-h13.00.jpg`,
`compare/cam_range_apron-h13.00.jpg`, `compare/cam_range_overview-h20.50.jpg`. After-only close-ups:
`native-after2/cam_range_bench-h13.00.png`, `native-after2/cam_range_droid-h13.00.png`.

## Remaining defects (honest)

1. Frame cost +0.69–0.77 ms at the range's own wide view (over the brief's ~0.5 ms guide; the views still run at
   210–270 fps), +0.17 ms looking out of the gate, nothing at `cam_hill`. Cheapest reductions not yet done: the three
   training drones are 31 k-triangle single-LOD copies of the live drone (no LOD1), the Poly Haven compressor's LOD0 is
   79 k triangles, 24 decal projectors, 62 shadow casters.
2. The kit is Blender-procedural (boxes, beams, sandbags with tiling scanned timber/steel/hessian textures): convincing
   at range and mid distance, simple at arm's length — no chipped edges, splinters or edge-wear masks on benches,
   dividers, table and posts; sleepers repeat one wood scan in three tones.
3. The stripped worker droid is the live droid baked in its combat stance with dead optics and a dulled paint; its arms
   are raised (not slack) and the frame's chains end at the shoulders without a visible attachment.
4. The training drones are the feral drone model in its original yellow paint, not repainted as Warden kit; the
   tethered one on the gantry is small and hard to read from the firing line.
5. The earth bank was reviewed from the range side only; its back toe (towards the basin wall) was not inspected from
   behind. RANGE ORDERS text is readable only within a few metres.
6. No moving walkthrough or first-person clipping pass beyond the real-input tutorial route; not reviewed by Carl.
