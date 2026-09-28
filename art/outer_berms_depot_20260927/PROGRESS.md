# Outer Berms depot / robots — progress log

Brief: `BRIEF.md` (same folder). Append entries newest-last with local time.

- 00:10 27 Sep — Brief written by the West Gate session. West Gate outpost finished and verified (see
  `unity/evidence/west-gate/20260926/README.md`). Unity Editor is closed; builds in `unity/AthenHill/Builds` are the
  verified West Gate builds. Nothing started on the depot yet.

- 00:20 27 Sep — **Session start (depot/robots pass).** Unity Editor launched. Rollback copies:
  `unity/evidence/outer-berms-depot/20260927/scene-before-depot.unity` and `prefabs-before/` (Prefabs/OuterBerms).
  Baseline Editor captures (robots spawned temporarily at the nest spawns) in `.../20260927/baseline/`.
  Concept: `concept/depot_player_view.png` (gpt-image-1, prompt in `concept/prompts.json`): skeletal portal-frame hall,
  diagonal conveyor spine on trestles, three glowing charging pylons on a plinth, cables, scrap heaps, low broken walls.
  **Baseline defects found:**
  1. Depot = five plain concrete boxes + a 15×11 m white slab; no structure, no storytelling, no lore read.
  2. The desert basin mesh (SandstoneBasin, swirly at close range) pokes up to 1.1 m through the Berms ground over the
     whole SW quadrant of the depot (x −90…−76, z −50…−36): the pad flattening lowered the walkable ground below it.
     That swallows the slab's SW half and is the "swirly/marbled" ground in every depot capture.
  3. Slab/walls hang over the escarpment slope (west wall end floats); mining-droid carcass clips through the west wall.
  4. Worker droid: installed rigged GLB has **only a 2k base colour** (no normal, no metal/roughness) and glTF
     emissiveFactor (1,1,1) → flat, plastic, self-lit look. The Meshy refine model has normal + MR maps on the **same UVs**
     (verified: identical triangle count and UV atlas), so they can be restored.
  5. Scrap drone: rotors are static geometry (never spin); flat toy-orange read; no rotor wash/grounding cue.
  6. Telegraphs are light-only (eye point light); no footstep dust/sound, no wind-up audio, no emissive flare.
  **Plan:** Blender-authored depot kit (hall frame, conveyor spine, charging cradles, drone rack, broken walls) +
  Meshy scrap heaps; `Editor/OuterBermsDepotPass.cs` (layout JSON → prefabs, ground re-sculpt above basin, splat extension,
  retire old boxes inactive, lights, decals, cameras, landmarks); robot material/VFX/SFX pass; then verification.

- 03:03 27 Sep — (coordinator note) First worker was cut off by the usage limit at ~00:45 before logging. State found on
  disk: depot kit authored (`author_depot.py` → `Art/OuterBermsDepot/Structures`, prefabs in `Prefabs/OuterBermsDepot`,
  Poly Haven + Meshy props incl. `meshy/outer-berms-depot-20260927`), `Editor/OuterBermsDepotPass.cs` install **ran and the
  scene was saved at 00:42** (`unity/evidence/outer-berms-depot/20260927/install.json`: 63 placements, ground lifted over
  the basin (backup `BermsGround-before-depot.asset`), 15 old depot objects retired, spawns moved, 3 lights, 2 electric
  arcs via new `Scripts/ElectricArc.cs`, 13 decals, landmarks depot_approach/yard/hall; humClip null). Editor is open,
  scene clean, console clean. Not yet done: post-install review captures, robot material/rotor/telegraph pass (defects
  4–6 above), audio hum, verification (tests, builds, native checks incl. depot, perf), evidence README.

- 03:40 27 Sep — **Resume session: post-install review + robot pass (milestone 1).**
  Post-install captures: `unity/evidence/outer-berms-depot/20260927/editor-review/install1/` (all review cameras + close-ups).
  **New defects found and fixed:**
  1. Chain-link fence panels rendered as opaque black sheets: the Poly Haven wire base map had been saved as JPG (no
     alpha). New `Props/Textures/PH_modular_chainlink_fence_wire_BaseMap.png` with the Poly Haven opacity in alpha
     (source `polyhaven/modular_chainlink_fence_wire_diff_2k.png`), mip coverage preserved, material re-pointed.
  2. Cradle power-cell windows blew out to white (emission 5.5) → toned to cyan (0.3, 1.45, 1.75).
  3. Concrete (plinth, broken walls) read as clean/bright with a sky-blue sheen → warmer darker tint, smoothness ×0.45.
     Cradle housings (WG bone paint) read as copper canisters → own olive-grey `DP_CradlePaint`.
  4. Apron edge was a 25 cm stair-step with a smeared rim → `ApronMesh()` now traces marching squares, adds an 18 cm
     skirt (slab thickness reads at player height) and drops islands < 2 m².
  5. **Worker droid clips were all static** (every curve constant: Blender 5 slotted actions; `merge_worker_droid.py`'s
     NLA_TRACKS export wrote the rest pose). Fixed the merge (ACTIONS export with the idle slot assigned) and re-exported
     `Art/OuterBerms/WorkerDroid.glb` (clip names/IDs unchanged, prefab refs still resolve). New
     `art/outer_berms_20260926/fix_worker_root_motion.py` (run once after merge) removes the baked horizontal Hips drift
     (idle stood 0.46 m to the side, hit slid 1.5 m, death started 2 m behind the root). The droids now actually idle,
     walk, run, punch, flinch and fall. Old GLB kept: `prefabs-before/WorkerDroid-static-clips.glb`.
  6. The stripped-worker carcass stood upright (death pose never sampled: static clips + legacy SampleAnimation no-op in
     the Editor) → baked via `AnimationMode` → now a sprawled knocked-down wreck.
  7. Cradle hum and arc crackles had no clips → ElevenLabs SFX (cost ~9 chars each; records in
     `unity/staging/elevenlabs-audio/`): cradle-hum (loop), arc-crackle-1/2, droid-windup, drone-windup, droid-step-1/2,
     drone-rotor (loop). Generator: `unity/tools/generate_berms_combat_audio.py` (optional loop field).
  **Robot pass** (`Editor/OuterBermsRobotPass.cs`, menu Robots: build and apply; textures from
  `art/outer_berms_depot_20260927/make_robot_textures.py`): worker → URP Lit `RB_WorkerDroid` (restored normal +
  metal/roughness, optics-only emission map); drone → weathered `RB_ScrapDrone` (desaturated paint), rotors split from
  the fused Meshy mesh into `Meshes/ScrapDrone_Rotor{A,B}` pivoted on their shafts + blur discs, old fused mesh inactive;
  eye lights → forward spots (the point light lit the droid's own arms/pods orange). `FeralDroid.cs` (runtime) gained a
  presentation LateUpdate: emission telegraph via MaterialPropertyBlock (calm → hostile → wind-up flare, hit flash, dead
  stutter), wind-up clip, foot-plant detection from toe bones → dust puff + step sound, rotor spin (counter-rotating,
  rev-up on wind-up, spin-down on death), rotor hum pitch/volume, ground downwash dust. All new fields optional; Health,
  DroidEncounter, tutorial untouched. Captures: `editor-review/fix1/`, `robots1..3/`.
  Pitfall: the URP `_EMISSION` keyword on RB_* materials was found disabled in memory after texture reimports (disk had
  it) → the pass re-asserts it. **Next:** EditMode tests, builds, native checks (checkpoint + depot), perf, README.

- 04:15 27 Sep — **Verification round 1 (milestone 2).** EditMode 61/61 (4 new `Tests/Editor/OuterBermsRobotAssetTests.cs`).
  Dev + release builds OK. Native checkpoint (Editor closed): all 9 checkpoint checks pass but the city-loop pause step
  failed twice; checkpoint route p99 **102 ms** (42 frames > 100 ms). Diagnosis: VRAM paging, not logic — player
  8.35 GiB + desktop ~3.2 GB = 11.8/12 GB; facing the city the GPU sits at 100 % / 70 W with ~100 ms frames; the city
  loop then runs at 7–88 fps and loses a fast second Escape (the same loop passes on a fresh player). The West Gate
  measurement (00:05) had the same content at 14–16 ms with less desktop VRAM. First depot check: nest spawned, but the
  scripted fight idled while the review captures ran and the player was knocked down (check-script issue).
  Native review also found the drone's lens emission was on the wrong side / a flat yellow splat with embers (Meshy
  overlapping lens shells; 3 px mask dilation bled into neighbouring atlas islands).
  Fixes: emission masks 1 px dilation + worker luminance gate; drone lens = fitted emissive cap (`RB_ScrapDroneLens`,
  `Meshes/ScrapDrone_Lens`), softer drone flare; `RealtimeEmissive` GI flag on the RB materials (with flag None, URP's
  validation dropped `_EMISSION` whenever a material sharing their textures was edited; `DeadVariant()` also avoids
  `CopyPropertiesFromMaterial`, which cleared the keyword on the *source*); depot prop textures capped 1k (Standalone).
  `check_depot.py`: captures from out of aggro range, re-arms/rallies after knock-downs, fires inside hip range.

- 05:00 27 Sep — **VRAM fix + final verification (milestone 3).** `ProjectSettings/QualitySettings.asset` PC level:
  mip streaming on, budget 4096 MB (rollback copy in the evidence folder). Textures 6.5 → 4.2 GB, player GPU memory
  8.35 → 6.71 GiB; near-field sharpness unchanged vs the West Gate locker close-up. Batch-built dev + release (0 errors).
  Native checkpoint **passed 10/10 twice**; route avg 203/214 fps, p50 4.2/4.3, p95 15.1/14.6, **p99 16.99/16.71 ms**
  (narrow fail of 16.67), max 21/19, no hitches. Native depot **passed**: nest (2 workers + drone) cleared with real F
  input in 22 s, Windup telegraphs observed, tutorial Complete, no exceptions; fight p99 8.64 ms, depot walk p99 16.0 ms.
  Evidence + honest defects: `unity/evidence/outer-berms-depot/20260927/README.md`, `performance-review.json`.
  Unity Editor left **closed** (VRAM); scene saved. Nothing committed.

## Morning summary (27 Sep)
Depot rebuilt from five boxes into a ruined processing hall / drone nest (hall frame, conveyor spine, charging cradles
with arcs and hum, walls, scrap, decals), reviewed and fixed at player height. Robots: the worker droid now actually
animates (its clips had been exported static), has proper PBR materials and optics that flare on the wind-up; the drone
has spinning rotors, downwash, hum, a weathered finish and a glowing lens. New wind-up / footstep / rotor / arc audio.
Tests 61/61, builds OK, checkpoint + depot real-input checks pass. Open items: checkpoint p99 sits at the 16.67 ms line
(city view), the overnight mip-streaming setting needs a human OK, animation is Meshy library motion, see README.
