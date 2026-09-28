# Outer Berms machine depot and robots — 27 September 2026

User request (00:05): "continue work on the berm. the robots at the far end and that whole area could use work … we
will review in the morning." Brief, sources and running log: `art/outer_berms_depot_20260927/BRIEF.md` and
`PROGRESS.md`. Editor passes: `Editor/OuterBermsDepotPass.cs` (depot install, 00:42, plus the review fixes below) and
`Editor/OuterBermsRobotPass.cs` (robots). Rollback copies in this folder: `scene-before-depot.unity`,
`BermsGround-before-depot.asset`, `prefabs-before/` (droid prefabs, the static-clip `WorkerDroid-static-clips.glb`,
`FeralDroid.cs.before`) and `QualitySettings-before-streaming.asset`.

## What changed

**Depot (far south end of the Berms).** The five plain concrete boxes were replaced overnight (first session, 00:42)
by an authored ruin: a portal-frame processing hall (roofed west bay, collapsed frame, sheared gable), a truss conveyor
spine climbing the escarpment, a drone docking rail, three drone charging cradles on a power plinth (one torn open with
an intermittent electrical arc), broken retaining walls with FERAL CLUSTER / KEEP OUT spray, cable runs, Meshy scrap
heaps, Poly Haven props, a cracked concrete apron, oil/scorch/tyre decals and a stripped worker carcass. The ground was
lifted above the desert basin mesh that had been poking through it. Spawns and landmarks (`depot_approach`,
`depot_yard`, `depot_hall`) were moved to the new layout.

Post-install review (`editor-review/install1/`, then `fix1/`, `final/`) found and fixed:

1. Chain-link fence panels were opaque black sheets (wire base map saved as JPG, no alpha) → PNG with the Poly Haven
   opacity, coverage-preserving mips.
2. Cradle power-cell windows blew out to white → cyan; cradle housings read as copper canisters → olive-grey machine
   paint (`DP_CradlePaint`); plinth/walls were clean white with a sky-blue sheen → warmer, darker, rougher concrete.
3. Apron edge was a 25 cm stair-step with a smeared rim and stray islands → marching-squares outline, an 18 cm slab
   skirt, morphological opening and island removal.
4. The stripped-worker carcass stood upright → baked from the (now working) knock-down clip; sprawled wreck.
5. Cradle hum and arc crackle had no audio → ElevenLabs SFX (loop hum, two crackles).

**Robots.**

- **Worker droid never animated.** Every clip in `WorkerDroid.glb` was the static rest pose (Blender 5 slotted
  actions: the NLA export evaluated nothing). `art/outer_berms_20260926/merge_worker_droid.py` now exports ACTIONS with
  the slot bound; `fix_worker_root_motion.py` removes the baked sideways/backward Hips drift (idle stood 0.46 m off
  its collider, hit slid 1.5 m, death started 2 m back). The droids now idle in a combat stance, walk, run, punch
  with both fists, flinch and fall. Clip names/IDs unchanged, prefab references intact.
- **Materials.** Worker: URP Lit with the Meshy refine normal + metal/roughness maps restored (the installed material
  was base colour wired to emission — flat, self-lit), optics-only emission. Drone: weathered, desaturated paint
  (`make_robot_textures.py`), and a fitted emissive lens cap (the Meshy lens is several overlapping shells).
  Eye lights are forward spots now (the point lights lit the droids' own arms orange).
- **Drone rotors spin.** The fused Meshy mesh is split into body + two rotors pivoted on their shafts
  (`Art/OuterBerms/Meshes/`), counter-rotating with blur discs, revving on the wind-up and spinning down on death,
  with a pitch-following rotor hum and ground downwash dust. The fused original stays in the prefab, inactive.
- **Telegraphs.** `FeralDroid` (runtime, new optional fields; behaviour, Health and DroidEncounter unchanged) drives
  the optic emission per state: calm → hostile → a pulsing white-hot flare through the wind-up → hit flash → dead
  stutter; plays a wind-up clip; detects foot plants from the toe bones for dust puffs and metal footsteps.
- New ElevenLabs one-shots/loops (records in `unity/staging/elevenlabs-audio/`, ~9 characters each): cradle-hum,
  arc-crackle-1/2, droid-windup, drone-windup, droid-step-1/2, drone-rotor.

**Performance/VRAM (project setting).** See below: `QualitySettings` PC level now streams mipmaps (budget 4096 MB).
Depot Poly Haven prop textures capped at 1k on Standalone (crane keeps 2k).

## Verification

| Check | Result |
| --- | --- |
| Edit Mode tests | 61/61 passed (`edit-mode-tests.json`), incl. 4 new `OuterBermsRobotAssetTests` (clips animate without root drift; worker PBR/telegraph/feet; drone rotors/downwash/hum/lens; nest still spawns 2 workers + 1 drone) |
| Linux development build | Succeeded, 0 errors (`development-build.json`, batch build with the final settings) |
| Linux release build | Succeeded, 0 errors (`release-build.json`). Not launched (the release smoke script switches the monitor mode) |
| Native checkpoint (real input) | **Passed** all 10 checks twice on the final build (`native-checkpoint/`, `native-checkpoint-run2/`): gate walk, Ossa/Rell dialogue, board, first-person zoom, locker, range reset, three plates, holster, full city loop |
| Native depot (real input) | **Passed** (`native-depot/report.json`, new `unity/tools/check_depot.py`): tutorial with real keys, service-road drone put down (5 shots), nest spawns 2 workers + 1 drone at the moved spawns, nest cleared with real F presses (11 shots, 22 s, no knock-down) → tutorial Complete; Windup states observed; no exceptions in Player.log. The QA bridge only turns the follow camera toward the nearest droid (`cameraYaw`) — aiming is not mouse-driven |
| Checkpoint route perf | avg 203.1 / 213.7 fps, p50 4.24 / 4.33, p95 15.09 / 14.61, **p99 16.99 / 16.71 ms**, max 21.3 / 19.0, 0 hitches (two runs). **Narrow fail of p99 ≤ 16.67** (West Gate: 16.50 at 00:05). The p99 frames are the east heading into the city (24 M submitted triangles), not the depot |
| Depot fight perf | avg 166.1 fps, p50 5.93, p95 7.62, p99 8.64, max 11.84 ms, 0 hitches — pass |
| Depot walk perf | avg 172.2 fps, p50 4.87, p95 14.15, p99 16.00, max 18.22 ms, 0 hitches — pass |

All runs: Editor closed, 1920×1080, 100% scale, uncapped, PC quality, OpenGL Core, RTX 3060 12 GB, i9-10850K.
Details and the before-fix samples: `performance-review.json`.

**VRAM finding.** Without mip streaming the player held 8.35 GiB of GPU memory (6.5 GB textures) while the desktop
held ~3.2 GB (Hyprland, quickshell, Electron apps, Nautilus, Steam): 11.8 of 12 GB. Facing the city from the checkpoint
the driver paged (GPU 100 % busy at ~70 W, ~100 ms frames: p99 102 ms, 42 frames > 100 ms,
`native-checkpoint-attempt4-no-streaming/`), and the city loop dropped to 7–88 fps and missed a fast second Escape
(`native-checkpoint-attempt2/3`: the pause assertion failed; the same city loop passes on a fresh player). The player
used about the same memory at 00:05 (8.79 GiB) — the desktop's share had grown — but the game was already too close to
the 12 GB limit. Enabling mip streaming (budget 4096 MB, max reduction 2) cut textures to 4.2 GB and player GPU memory
to 6.71 GiB; the same heading renders at p50 14.9 / p99 16.0 ms and both native checks pass. Near-field sharpness
matches the West Gate locker close-up. Rollback: `QualitySettings-before-streaming.asset`.

## Captures to look at

- Native (authoritative): `native-depot/day-cam_depot_*.png` (nest idle at home), `night-cam_depot_*.png`,
  `first-contact-windup-telegraph.png`, `depot-wrecks.png`, and the fight video `native-depot/depot-fight.mp4` (26 s:
  running worker, drone, hits, knock-down death). Checkpoint regression views in `native-checkpoint/`.
- Editor: `editor-review/final/` (robots posed in the yard: `robots_player`, `worker_close` (wind-up flare),
  `worker_full` (walk), `carcass`, depot cameras), `editor-review/final3/drone_close.png` (lens glow),
  before: `baseline/` and `editor-review/install1/`.

## Visual review (0–5, player height, this pass)

| | Before (baseline) | After |
| --- | --- | --- |
| Composition / silhouette | 1 (five boxes) | 4 (hall frame, conveyor, cradles read from the road) |
| Material detail | 2 | 3.5 (tiling PBR sets; cradle UV streaks and some flat concrete remain) |
| Density / storytelling | 1 | 4 (drone nest guarding charging cradles, carcass, scrap, cables, spray) |
| Robots — materials | 2 (self-lit, no normals) | 4 |
| Robots — animation | 1 (static poses sliding) | 3.5 (library clips, readable; generic humanoid motion) |
| Telegraph / VFX / SFX | 2 (light only) | 4 (flare, wind-up audio, rotors, dust, hum) |
| Lighting (night) | 2 | 4 (cyan cradle glow, arc flashes) |

## Remaining defects (honest)

- Checkpoint route p99 16.7–17.0 ms: at/over the 16.67 ms line. The city's east view is the limit; further headroom
  needs city-side work (draw/shadow cost of the 24 M-triangle heading) or a lower default shadow setting.
- Mip streaming is a project-wide setting change made overnight: review it (and its budget) before accepting.
- Worker animations are Meshy library clips on a robot rig: idle is a humanoid combat stance, the punch clip is sped up
  (3.5 s source), the hit reaction still sways ~0.5 m before recovering. No turn-in-place clips.
- Drone lens glow sits slightly low inside the ring (fitted cap over overlapping Meshy shells); blur discs and spinning
  rotors were reviewed in video only at gameplay distance.
- Footstep dust/sound use a toe-height heuristic; audio mix of the new SFX was not reviewed by ear.
- Cradle housings still show vertically stretched rust streaks (box-projected UVs on the octagon).
- Retired objects (old boxes, fused drone mesh) remain inactive for rollback; the fused drone still references its
  glTF textures (~20 MB resident).
- Release player built but not launched; no release play session.
