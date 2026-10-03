# Outer Berms expansion — evidence (2 October 2026)

Pass: `art/berms_expanse_20261002` (README there for the pipeline), Unity `Editor/BermsExpansePass.cs`,
`Editor/BermsExpanseInstall.cs`; runtime `Scripts/Combat/FeralDroid.cs` (ranged mode, pack calls, flanking),
`DroidBolt.cs`, `DroidEncounter.cs` (proximity activation, parking, packs), `WardenWaystation.cs`,
`BermsCompassPoint.cs`, `CombatHud.cs` (damage direction, compass places), `PlayerCombat.cs` (HurtFrom, waystation
respawn), `NativeQa.cs` (downs, bolts in the snapshot). Meshy: `meshy/ranged-enemies-20261002`,
`meshy/berms-landmarks-20261002`.

Tested on the working tree on top of `7fdbd282` (which also holds other sessions' uncommitted Salvage shop work).
Machine: RTX 3060 12 GB / i9-10850K / 32 GB, Linux, OpenGL Core, High preset, 1920 × 1080, render scale 100 %.

## Scene changes (install.json, verify.json)

- Ground: 54 tiles (LOD0 132,198 / LOD1 66,772 triangles), MeshCollider on LOD0, `BermsGroundV2.mat`.
- Basin expanse: 84 spatial chunks (first installed as 12 sector chunks), 323,301 triangles (the replaced Basin mountains: 185,257), `SandstoneBasinV3.mat`.
- Boundary: 29 edge walls; the West Gate stays open (verify `gateOpen`).
- Scatter 853 (incl. 18 on the depot rise), props 155 (incl. the 3 Meshy landmarks), 39 site spawns (13 ranged), 21 salvage nodes, 21 trail cairns,
  12 review cameras `cam_bx_*`, compass points for 12 sites and the gate.
- Primer: first contact two drones at (−128, 21) / (−134, 13) (was one at (−83, −13)); depot nest five (3 workers,
  2 drones); the Foreman encounter unchanged.
- Gameplay camera far clip 650 → 1,600 m.
- After the batch: the Tube pylon and tube materials were tinted warm (`_BaseColor` 0.78, 0.69, 0.57; they read near
  white); the final playtest build (12:45) includes it, the measured builds don't.
- Rollback: `rollback/before-berms-expanse.unity` (local, git-ignored) or git; in the scene, deactivate
  `Outer Berms/Berms expanse` and `Basin expanse`, reactivate `Basin mountains` and `Outer Berms/Boundary colliders`.

## Checks

| Check | Result |
| --- | --- |
| `verify` (saved scene, -nographics) | 0 problems (`verify.json`) |
| EditMode suite | 207 / 207 (`tests-4`; `BermsExpanseTests` added; three older scene/prefab assertions restated for the new layout: core encounters and heaps counted outside `Berms expanse`, depot nest five, Foreman HP 1400 instead of 14 x the worker) |
| Native expansion check (`check_berms_expanse.py`, `batch/expanse-2`) | passed 8/8: profiled real-W walks across the bowl; pistol with real E/7; waystation found by walking in; caravan pack activated by proximity and engaged; relay-knoll gunners aimed and fired 9 bolts and hurt the player; knocked down → respawned at the waystation; Tube-pylon lancers fired; no exceptions. (`batch/expanse` failed only on a lookup ordering bug in the new fight profile step, fixed in the script.) |
| City loop (`batch/cityloop`) | CITY LOOP PASS |
| Range tutorial (`batch/tutorial`) | passed, 10 checks |
| Lookbook (`batch/lookbook-p01/p02`, 22 cameras at 13:00 and 20:30) | captured; sheets `sheet-h13.00.jpg`, `sheet-h20.50.jpg` |

### Frame time

Native player, 1920 x 1080, High, OpenGL Core, render scale 100 %. Alternating A/B, 2 runs per arm, 8 s per hour
(`batch/ab/ab-summary.json`): **off** = the same scene snapshot with the expansion off (old basin and boundary on, far clip
650 m), **on** = as installed (84 mountain chunks).

| Camera | off fps / p50 ms | on fps / p50 ms | Δ p50 |
| --- | --- | --- | --- |
| cam_hill 13:00 / 20:30 | 61.2 / 16.29 · 66.0 / 15.14 | 60.5 / 16.45 · 66.3 / 15.04 | +0.16 / −0.10 |
| cam_avenue 13:00 / 20:30 | 53.4 / 18.64 · 55.9 / 17.82 | 54.0 / 18.46 · 55.7 / 17.84 | −0.18 / +0.02 |
| cam_gate 13:00 / 20:30 | 131.0 / 7.60 · 126.7 / 7.84 | 134.6 / 7.38 · 128.8 / 7.66 | −0.22 / −0.18 |
| cam_westgate_mouth 13:00 / 20:30 | 189.3 / 5.11 · 133.6 / 7.46 | 137.2 / 7.21 · 99.3 / 10.08 | +2.10 / +2.62 |
| cam_berms_overview 13:00 / 20:30 | 113.4 / 8.77 · 107.1 / 9.25 | 94.4 / 10.66 · 85.3 / 11.53 | +1.89 / +2.28 |

Inside the city the expansion is within run-to-run drift. Looking out into the Berms it costs about 2–2.6 ms (the bowl,
its ring and the far clip), and those views stay at 85–137 FPS. (cam_hill and cam_avenue are below 60 FPS in both arms:
a pre-existing city cost, not this pass.)

Profiles in the expansion check (`batch/expanse-2/profile-*.json`, warmed): real-W walk across the east of the bowl
218.6 fps avg, p50 4.43 ms, p99 5.99 ms, max 13.3 ms; across the middle 232.9 fps, p99 6.39 ms, max 26.1 ms; the relay-knoll
fight (two gunners and a worker shooting, bolts, laser, HUD) 90.1 fps, p50 11.07 ms, p99 13.66 ms, max 16.0 ms; no frame
over 33 ms. GPU timing counters are unavailable on this player (reported as unavailable, not zero).

## Known defects / limits

- The old Berms ground's south-west slope (7–11 m, the depot conveyor stands on it) still reads as a smooth, bland hill
  from the gate and hides the city from the far west; it belongs to the original ground mesh (kept exactly).
- Outcrop tops read as smooth domes; the BermsGroundV2 rock layer on their steep sides is pale and noisy close up.
- Between sites the floor relies on scatter for interest; no paths/tracks are painted outside the old splat rect.
- The gunner (120k triangles skinned + gun) and lancer (67k) have no LODs; clusters are parked beyond 170 m.
- Meshy known defects: see the meshy READMEs (gunner claw fingers, gun brushing the torso in run/aim; lancer duct lips;
  hauler collider ~0.8 m over the spilled crates, LOD switches pop without fade).
- Noon (13:00) bleaches the far mountains and floor to pale cream (the known basin noon issue); 17:00 and night read better.
- Out in the bowl at night only the waystation is lit; sites are dark by design (feral ground).
