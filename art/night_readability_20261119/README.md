# Night readability — 19 November 2026

At 20:30 the city was close to black away from lamps and every character a silhouette. This pass makes people and
streets readable at night while keeping the warm lamp pools as the brightest things in frame. Day (06:30, 13:00, 17:00)
is untouched by construction and measured unchanged. Not yet reviewed or accepted by Carl.

Unity pass: `unity/AthenHill/Assets/AthenHill/Editor/NightReadabilityPass20261119.cs`
(`AthenHill.Editor.NightReadabilityPass20261119.RunBatch --steps survey|apply|verify|rollback`).
Runtime: `Scripts/NightActorLighting.cs` (ships), `Scripts/NightReadabilityQa.cs` (development players only, opt-in by
environment). Evidence: `unity/evidence/night-readability/20261119/` (git-ignored). Final build: `Builds/batch-nightfinal`.

## Why characters went black (diagnosis)

Measured in the native player with `NightReadabilityQa` (`ATHEN_NIGHT_DIAG=1`, `night-diag.json` per camera and hour)
and the read-only `survey` step (`survey.json`).

1. **The night ambient was effectively zero.** The live profile is `Art/Atmosphere/Dustbowl/WardDustbowl.asset` (found
   through `Ward lighting clock` → `CityTimeOfDay.profile`). Its night frames (19:00, 00:00, 05:30) set trilight ambient
   colours of about 0.06–0.17 in sRGB terms; in the linear project that is an ambient probe of
   L0 = (0.0049, 0.0065, 0.0114) at 20:30 (read from `RenderSettings.ambientProbe` in the player), roughly 1/20 of noon.
   There are no baked light probes (`lightProbes = 0`), so every character takes that ambient. With albedo around 0.3
   it renders at about 5/255 even after the night post-exposure of +0.55. Anything the moon or a lamp does not hit
   directly is black.
2. **The moon key mostly does not reach people.** The moon is a 0.42 directional at 20–32° elevation with shadow
   strength 0.92. The diagnostic's ray test put the chest of Mira, Torr, Tamsin, Brann, Ossa and walker 03 in moon shadow
   at 20:30; the rest face away from it in the review views. Under 0.92 shadow strength a moon-shadowed street is lit
   only by the near-zero ambient (the night facade pass had already found the "Finery band" was a moon shadow).
3. **The lamps light the ground and walls, not faces.** The shop lamps are down-and-out cookie spots (140° outer / 95°
   inner, aimed down 10° off the wall). For a person standing 1–3 m from the lamp the light arrives from above and
   behind or grazes the body: Mira's two counter lamps reach her chest 60–61° off axis (in the soft rim), her two pier
   lamps 85–86° (outside the cone), while the floor in front of the counter takes the full plateau. Result: lit floor
   (121/255), black Mira (face 13, torso 5).
4. **Ruled out:**
   - *Rendering layers / culling masks.* Every street light uses mask 1; every outdoor actor renderer has bit 1 (survey:
     `layerOk` true for every light reaching an actor). The 14 layer-128 lights belong to the three walk-in interiors,
     whose actors (Brann, Tamsin) carry bit 7 and already read well (faces 103 and 68 before).
   - *Materials.* NPCs and walkers use glTFast's `glTF-pbrMetallicRoughness` with metallicFactor 1 × the Meshy
     metallic-roughness map; the maps are near zero metal (mean 0.00–0.09; `tools/glb_mr.py`) and rough (0.83–0.93), so
     they are diffuse, not dark metal. No specular-off or receive-shadows-off keywords. The yard mechanic (URP Lit,
     metallic 1 × map) has a map that is 0 metal everywhere.
   - *The 32-light cap.* Not the cause for faces. The circuit is 90 m full / 150 m cull (set by lighting v2 on 29 Sep,
     not the 26–42 m in older notes), so 26–138 lights are in view per camera and URP keeps 32. Cutting the circuit to
     26/40 m (`tunes/tCirc.json`, run `tCirc-*`) dropped the lights in view from 95 to 51 at `cam_npcs_mira_body` and
     from 138 to 51 at `cam_avenue` but changed no actor luminance by more than 1/255. Left unchanged.
   - *Grade.* ACES with contrast +16 and lift −0.01 compresses the low end, but it is shared with the day; changing it
     would change 13:00. The clock only drives post-exposure per frame, and raising night exposure lifts the lamp pools
     as much as the shadows, so it was not used.

## What changed

All through `apply`, values in `night-tune.json`, originals in `originals.json`.

| Change | Before | After | Where |
| --- | --- | --- | --- |
| Night ambient sky (frames 19:00, 00:00, 05:30) | (0.075, 0.105, 0.17) | (0.17, 0.22, 0.32) | `WardDustbowl.asset` via the clock |
| Night ambient equator | (0.06, 0.072, 0.10) | (0.15, 0.17, 0.22) | same |
| Night ambient ground | (0.04, 0.042, 0.05) | (0.08, 0.08, 0.09) | same |
| Moon key intensity | 0.42 (19:00, 00:00), 0.30 (05:30) | 0.50, 0.36 | same |
| Moon shadow strength at full night | 0.92 (the Sun light's authored value, all day) | eases to 0.65 as sun visibility goes 1 → 0 | `NightActorLighting` on `Ward lighting clock` |
| Actor ambient at night | street ambient | street ambient × (1 + 2.0 × night) | same, per actor renderer (custom SH probe) |
| Camera-side actor fill at night | none | SH directional term, linear colour (0.72, 0.78, 0.95), intensity 0.25 × night, from 25° above the actor-to-camera line | same |
| Review cameras | — | 10 `cam_night_*` under *Night readability review cameras* | scene |

`night` = 1 − the clock's sun visibility, so every frame with the sun up (06:30–17:30 in this profile) gets weight 0:
the shadow strength stays at the authored 0.92 and actors keep the engine's probe. Only night frames are edited in the
profile; `verify` checks all 156 other frame fields are bit-identical to the pre-install snapshot.

**NightActorLighting** gives each actor (player and first-person arms, `NpcAgent`, `AmbientWalker`, `ActorAnimation`
roots) a `CustomProvided` light probe at night: the sky's ambient SH scaled up plus one directional SH term pointing
from the actor towards the camera. It is the character-light trick of film lighting done in spherical harmonics: no
real-time light, no shadow map, nothing taken from the 32-light cap. Renderers that already have a custom probe (walk-in
interior props, Brann at the Salvage counter) are left alone; Tamsin (Field Supply) has never had the interior probe
(her renderers take the street ambient, an existing inconsistency), so she gets the night actor ambient too (face 66 → 72), and the player is skipped while `InteriorLighting` has
them inside a room. Cost: one SH evaluation per actor per frame (≈15 actors) and a property block per renderer.

**No lights were added, removed or re-aimed.** Lights in view per camera are identical before and after (table below);
the scene still has 217 lights.

## Measurements (native player, 1920×1080, High, OpenGL, RTX 3060)

Display values are Rec.709 luminance in linear light re-encoded to sRGB 0–255. "Centre" is the play area without the
HUD (x 22–78 %, y 30–84 %). Near-black = share of centre pixels under 12/255. Face/torso boxes and the ground ring
(12 samples 1.1–1.6 m round the feet, visible from the camera) come from `night-diag.json`; ratios are linear-light.
Before = `batch-night1` with no tune (the BEFORE scene; same images as `batch-showcase1` apart from moving actors),
after = `batch-nightfinal`. Tools: `tools/measure.py`, `tools/tables.py`.

At 20:30, all review cameras (standard, NPC and `cam_night_*`). The lamp-pool brightness (p95) rises by 1–23/255 but stays the brightest part of every frame; clipped pixels stay at or below 0.2 % (the 1.9 % at `cam_npcs_torr_face` is the lit mission-terminal screen, unchanged from before). Ossa's face is 240 before and after: the issue-window lamp 1.9 m from her (an existing hot spot, not this pass). Walker rows that change a lot in the wrong direction are a walker in a different place on its route between runs (walker 03 in `cam_npcs_torr_face`, walker 01 in `cam_night_vex_talk`). The yard mechanic rows are left out (his face box falls on his cap).

| camera | centre p50 before → after | near-black share before → after | p95 (lamp pools) before → after | clipped after | lights in view |
|---|---|---|---|---|---|
| cam_avenue | 14.0 → 19.2 | 0.45 → 0.27 | 45.4 → 52.3 | 0.0001 | 138 |
| cam_courtyard | 34.5 → 40.8 | 0.29 → 0.21 | 81.6 → 86.0 | 0.0013 | 53 |
| cam_gate | 26.2 → 31.6 | 0.22 → 0.12 | 60.2 → 66.0 | 0.0000 | 26 |
| cam_hill | 14.3 → 21.4 | 0.37 → 0.19 | 45.8 → 53.8 | 0.0001 | 109 |
| cam_npcs_mira_body | 53.3 → 56.8 | 0.10 → 0.02 | 134.8 → 137.0 | 0.0000 | 95 |
| cam_npcs_vex_face | 11.3 → 28.4 | 0.51 → 0.18 | 73.8 → 80.7 | 0.0001 | 89 |
| cam_player_face_20261003_body_front | 36.3 → 59.0 | 0.39 → 0.13 | 68.3 → 78.0 | 0.0000 | 45 |
| cam_player_face_20261003_face_quarter | 4.1 → 26.9 | 0.68 → 0.28 | 63.3 → 74.7 | 0.0000 | 66 |
| cam_fs_tamsin | 29.4 → 33.2 | 0.02 → 0.01 | 98.6 → 102.0 | 0.0000 | 51 |
| cam_npcs_linn_face | 13.4 → 27.4 | 0.47 → 0.18 | 63.3 → 86.3 | 0.0000 | 64 |
| cam_npcs_mira_face | 8.9 → 30.5 | 0.55 → 0.19 | 80.6 → 100.4 | 0.0000 | 70 |
| cam_npcs_ossa_face | 17.8 → 31.9 | 0.39 → 0.25 | 171.7 → 177.1 | 0.0000 | 29 |
| cam_npcs_rell_face | 19.0 → 28.4 | 0.38 → 0.23 | 57.7 → 71.0 | 0.0000 | 91 |
| cam_npcs_torr_body | 51.3 → 56.4 | 0.12 → 0.04 | 101.4 → 105.8 | 0.0002 | 39 |
| cam_npcs_torr_face | 19.9 → 32.8 | 0.38 → 0.20 | 91.9 → 95.8 | 0.0191 | 31 |
| cam_ss_brann | 24.7 → 26.7 | 0.09 → 0.07 | 84.1 → 85.2 | 0.0000 | 79 |
| cam_nl_courtyard | 31.0 → 35.9 | 0.26 → 0.15 | 89.2 → 93.3 | 0.0022 | 50 |
| cam_nl_hall_corner | 16.1 → 19.7 | 0.43 → 0.32 | 68.1 → 75.6 | 0.0000 | 67 |
| cam_nl_south_lane | 20.2 → 29.3 | 0.34 → 0.24 | 62.9 → 69.3 | 0.0005 | 64 |
| cam_npcs_linn_body | 13.1 → 28.9 | 0.46 → 0.28 | 54.6 → 70.4 | 0.0000 | 69 |
| cam_walkers_grower_face | 20.3 → 28.6 | 0.40 → 0.13 | 65.2 → 71.7 | 0.0001 | 32 |
| cam_walkers_nanotech_face | 28.9 → 36.1 | 0.24 → 0.12 | 98.3 → 100.1 | 0.0000 | 40 |
| cam_walkers_porter_body | 41.5 → 50.2 | 0.08 → 0.05 | 74.5 → 81.4 | 0.0000 | 34 |
| cam_walkers_porter_face | 31.0 → 35.6 | 0.23 → 0.14 | 81.2 → 87.5 | 0.0000 | 21 |
| cam_night_brann_talk | 23.9 → 25.7 | 0.09 → 0.06 | 73.7 → 75.4 | 0.0000 | 82 |
| cam_night_linn_talk | 14.7 → 26.1 | 0.44 → 0.20 | 63.9 → 86.6 | 0.0000 | 65 |
| cam_night_mira_talk | 23.9 → 35.7 | 0.42 → 0.23 | 110.1 → 114.0 | 0.0001 | 77 |
| cam_night_ossa_talk | 20.9 → 31.0 | 0.39 → 0.29 | 178.7 → 179.5 | 0.0007 | 30 |
| cam_night_rell_talk | 21.2 → 29.3 | 0.36 → 0.22 | 54.0 → 67.9 | 0.0000 | 91 |
| cam_night_tamsin_talk | 29.1 → 33.6 | 0.03 → 0.01 | 85.7 → 88.0 | 0.0000 | 54 |
| cam_night_torr_talk | 16.4 → 27.5 | 0.43 → 0.28 | 98.7 → 99.8 | 0.0105 | 32 |
| cam_night_vex_talk | 16.7 → 34.2 | 0.40 → 0.15 | 92.2 → 95.7 | 0.0000 | 92 |
| cam_night_avenue_west | 27.2 → 40.2 | 0.34 → 0.26 | 73.7 → 80.4 | 0.0000 | 171 |
| cam_night_spawn_apron | 51.1 → 59.6 | 0.17 → 0.07 | 80.8 → 87.1 | 0.0000 | 183 |

| camera | actor | face before → after | torso before → after | ground before → after | face/ground before → after |
|---|---|---|---|---|---|
| cam_avenue | npc_mira | 15.0 → 24.3 | 11.0 → 47.0 | 56.8 → 56.8 | 0.1 → 0.2 |
| cam_courtyard | npc_torr | 45.6 → 59.3 | 39.3 → 58.8 | 56.2 → 63.5 | 0.7 → 0.9 |
| cam_courtyard | npc_walker_03 | 14.1 → 67.1 | 11.0 → 56.3 | 36.4 → 48.0 | 0.2 → 1.9 |
| cam_npcs_mira_body | npc_mira | 12.6 → 53.6 | 5.2 → 35.4 | 121.5 → 123.6 | 0.0 → 0.2 |
| cam_npcs_vex_face | npc_vex | 16.7 → 29.9 | - → - | - → - | - → - |
| cam_player_face_20261003_body_front | Player | 26.8 → 47.5 | 5.4 → 39.0 | 57.4 → 64.8 | 0.3 → 0.6 |
| cam_player_face_20261003_body_front | npc_vex | 4.1 → 31.2 | 6.6 → 58.3 | 62.1 → 69.7 | 0.0 → 0.2 |
| cam_player_face_20261003_face_quarter | Player | 2.6 → 35.5 | - → - | - → - | - → - |
| cam_player_face_20261003_face_quarter | npc_vex | 1.4 → 23.0 | - → - | - → - | - → - |
| cam_fs_tamsin | npc_tamsin | 68.4 → 71.0 | - → - | - → - | - → - |
| cam_npcs_linn_face | npc_linn | 17.5 → 46.4 | 16.4 → 54.0 | - → - | - → - |
| cam_npcs_mira_face | npc_mira | 16.5 → 53.7 | - → - | - → - | - → - |
| cam_npcs_ossa_face | Warden Ossa | 129.3 → 129.5 | 50.6 → 52.4 | - → - | - → - |
| cam_npcs_rell_face | Warden Rell | 38.4 → 45.9 | - → - | - → - | - → - |
| cam_npcs_torr_body | npc_torr | 34.0 → 45.5 | 21.0 → 46.0 | 68.7 → 71.0 | 0.3 → 0.4 |
| cam_npcs_torr_face | npc_torr | 30.8 → 43.8 | - → - | - → - | - → - |
| cam_npcs_torr_face | npc_walker_03 | 23.6 → 12.9 | 19.1 → 24.0 | 33.0 → 54.1 | 0.6 → 0.1 |
| cam_ss_brann | npc_brann | 102.7 → 104.2 | 78.3 → 78.6 | - → - | - → - |
| cam_nl_courtyard | npc_torr | 45.9 → 56.2 | 46.5 → 62.1 | 56.7 → 63.2 | 0.7 → 0.8 |
| cam_npcs_linn_body | npc_linn | 25.4 → 52.1 | 9.6 → 50.6 | 11.2 → 22.8 | 2.9 → 4.1 |
| cam_walkers_nanotech_face | npc_mira | 6.6 → 36.0 | 52.4 → 68.3 | 107.5 → 109.8 | 0.0 → 0.1 |
| cam_walkers_porter_body | Player | 24.0 → 35.6 | 37.5 → 63.6 | 51.0 → 61.0 | 0.3 → 0.4 |
| cam_walkers_porter_body | npc_vex | 34.2 → 51.2 | 43.9 → 67.7 | 55.7 → 64.5 | 0.4 → 0.6 |
| cam_walkers_porter_face | Player | 21.9 → 34.3 | 34.5 → 62.7 | 52.8 → 61.0 | 0.2 → 0.3 |
| cam_walkers_porter_face | npc_vex | 34.3 → 51.8 | 41.4 → 68.8 | 54.7 → 63.4 | 0.4 → 0.7 |
| cam_night_brann_talk | npc_brann | 103.3 → 104.3 | 78.5 → 78.7 | - → - | - → - |
| cam_night_linn_talk | npc_linn | 32.3 → 53.7 | 36.7 → 60.5 | - → - | - → - |
| cam_night_mira_talk | npc_mira | 6.7 → 53.0 | 44.0 → 53.0 | - → - | - → - |
| cam_night_ossa_talk | Warden Ossa | 240.3 → 240.4 | 29.5 → 41.3 | - → - | - → - |
| cam_night_rell_talk | Warden Rell | 39.0 → 47.0 | 42.1 → 48.5 | - → - | - → - |
| cam_night_tamsin_talk | npc_tamsin | 65.8 → 72.4 | - → - | - → - | - → - |
| cam_night_torr_talk | npc_torr | 29.0 → 42.9 | 47.0 → 55.1 | - → - | - → - |
| cam_night_vex_talk | Player | 1.3 → 22.7 | - → - | - → - | - → - |
| cam_night_vex_talk | npc_vex | 5.5 → 30.9 | 42.6 → 64.9 | - → - | - → - |
| cam_night_vex_talk | npc_walker_01 | 46.8 → 7.2 | - → - | - → - | - → - |
| cam_night_avenue_west | npc_walker_01 | 2.9 → 18.3 | 4.1 → 49.4 | 44.8 → 53.7 | 0.0 → 0.2 |
| cam_night_spawn_apron | Player | 2.6 → 15.2 | 10.5 → 47.7 | 52.9 → 61.8 | 0.0 → 0.1 |
| cam_night_spawn_apron | npc_vex | 5.7 → 31.2 | 5.4 → 50.9 | 56.0 → 63.6 | 0.0 → 0.3 |


### Day unchanged

Mean frame luminance at 06:30 / 13:00 / 17:00, `batch-showcase1` vs `batch-nightfinal`, same cameras
(`measure.py --compare`): 72 camera-hours (24 cameras × 06:30, 13:00, 17:00): the largest change in frame mean is 1.7/255 (`cam_courtyard` 06:30, a walker in a different place), the average change 0.13/255; median per-pixel difference 0.93/255. Raw list: `unity/evidence/night-readability/20261119/measure/day-compare.txt`; the `cam_night_*` cameras at 13:00 and 17:00 change by at most 0.2/255 in mean.

The per-pixel differences come from moving walkers, idle animation and foliage wind (the largest, 8.7 at
`cam_npcs_vex_face` 13:00, is a walker crossing behind Vex); the frame means agree within 1/255 except where a walker
is in a different place.

### Frame time (alternating A/B, 20:30, 8 s per run, two runs each)

`tools/ab_profile.sh`, runs alternated before/after per camera (`batch-showcase1` vs `batch-nightfinal`), uncapped, 1920×1080 High, OpenGL, RTX 3060; the other agent's builds and QA ran between some runs.

| camera | before p50 ms (r1, r2) | after p50 ms (r1, r2) | before avg fps | after avg fps | before p95 | after p95 | Δ p50 (mean) |
|---|---|---|---|---|---|---|---|
| cam_avenue | 15.93, 16.32 | 15.99, 16.12 | 61.5 | 60.6 | 17.67 | 21.88 | -0.07 |
| cam_gate | 9.96, 10.71 | 9.67, 10.64 | 94.9 | 97.7 | 12.09 | 11.72 | -0.18 |
| cam_hill | 16.35, 16.39 | 16.24, 16.38 | 60.0 | 61.1 | 19.28 | 17.91 | -0.06 |

Within the ±1–1.5 ms run-to-run drift of this desktop: the change is between −0.18 and −0.06 ms p50. The higher after p95 at `cam_avenue` comes from one run (after r1 p95 26.5 ms; after r2 17.3 ms vs before 18.0 and 17.3 ms); avenue average fps 61.5 → 60.6, hill 60.0 → 61.1. Note that `batch-nightfinal` may also contain other packages' edits made between the two builds (14:09 and 14:56 today), so this A/B bounds this pass's cost rather than isolating it.


## Low-sun patchy faces (17:00–18:30)

Not changed. At 17:00 the sun is fully up (sun visibility 1), so nothing in this pass touches it. The blotches on Linn's
forehead and cheeks and Rell's face streaks stay identical under the moonlight, the camera fill and the noon sun; the
materials are rough diffuse with no AO or metal, and Meshy's base colour atlas for these characters
(`evidence/.../linn-albedo.jpg`) is a fragmented projection bake. Most likely the dark patches are baked into the Meshy
albedo; a texture fix (re-texture or paint-over) is the remedy, not lighting. Not proven: no face-region albedo
comparison was made.

## What is still weak

- **Faces in a lamp pool are still darker than the lit floor round them.** Mira at her counter: face 13 → 54, but the
  floor in front of the counter is 124 (face/ground 0.02 → 0.18). The player at the spawn: 0.26 → 0.60. Everywhere
  between pools faces now sit at or above the ground (Linn 2.9 → 4.1, walker 03 0.25 → 1.9, Torr 0.68 → 0.87). Beating
  a down-lit floor would need either a much stronger character fill (which reads as a torch on the face) or re-aimed
  counter lamps; neither was done. A per-shop lamp re-aim (Basic General's two counter lamps tilted back over the
  counter) is the next step if Carl wants Mira brighter.
- The three ambient walkers are not reliably in their review cameras (they walk); they were measured where the
  diagnostic found them in other views.
- `cam_night_*` before images are the final build with `tunes/tBefore-on-final.json` (the original night values and
  NightActorLighting neutral), since the BEFORE scene has no such cameras.
- The 32-light cap still drops lamps in wide views (26–138 in view). Unchanged and outside this pass.

## Rollback

`seq.sh install night AthenHill.Editor.NightReadabilityPass20261119.RunBatch rollback,survey` restores every recorded
frame field, removes the `NightActorLighting` component (it was added by this pass) and the camera root, and moves
`originals.json` aside (`originals.rolled-back-*.json`). The two runtime scripts can stay (inert without the component
and without the environment variables).

Tested 16:03: `rollback` left `WardDustbowl.asset` byte-identical to git HEAD and removed the component and all
`cam_night_*` objects from the scene; `apply,verify` then restored the installed state (verify ok, 156 untuned fields
unchanged). The earlier originals are kept as `originals.rolled-back-20261119-160340.json`.

## Files

| File | Purpose |
| --- | --- |
| `night-tune.json` | every value the pass sets (frames, actor lighting, light edits — none, cameras) |
| `originals.json` | the recorded original values and a full pre-install snapshot of the profile frames |
| `survey.json` | read-only survey (clock, profile, key/fill, every actor's renderers, materials and the lights within range) |
| `verify.json` | saved-scene verification |
| `tunes/` | runtime tune files used for native tuning without rebuilds (`ATHEN_NIGHT_TUNE`) |
| `tools/measure.py`, `tables.py`, `pairs.py` | luminance measurement, README tables, before/after sheets |
| `tools/lookbooks.sh`, `ab_profile.sh` | the native runs |
| `tools/glb_mr.py` | metallic/roughness statistics of the glTF characters |
