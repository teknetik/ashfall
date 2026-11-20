# Light budget — 20 November 2026 (showcase programme, phase 2)

STATUS: installed (lb-6), built (`Builds/batch-p2-lb3`, 22:35) and measured natively on 20 Nov. Not yet reviewed or accepted by Carl.

On the Linux OpenGL Core player URP draws at most 32 lights per camera: the sun, the sky fill and 30 local lights.
At night far more were in view (the night-readability survey counted 26–183 per review camera), so URP dropped lamps
and their pools popped in and out as the player walked. Carl decided on 19 Nov to stay on OpenGL and solve it with a
budget. This pass keeps the lights enabled in the rendering camera's view under a cap **by design**, keeps the nearest
and most important lamps real, gives every demoted lamp a cheap pool that cross-fades with the real light, merges the
lights that duplicated others, and re-aims Mira's lamps at Basic General. Not yet reviewed or accepted by Carl.

## Files

| File | Purpose |
| --- | --- |
| `unity/AthenHill/Assets/AthenHill/Scripts/Lighting/LightBudget.cs` | runtime budget (scene root **Ward light budget**) |
| `Scripts/Lighting/LightBudgetMath.cs` | pure ranking / hysteresis / fade / hard-cap logic (Edit Mode tested) |
| `Scripts/Lighting/LightBudgetQa.cs` | development players only: `light-budget.json`, runtime switch, `ATHEN_LB_TUNE` |
| `Shaders/LampPool.shader`, `Materials/Lighting/LB_LampPool.mat` | the pool of a demoted lamp |
| `Editor/LightBudgetPass20261120.cs` | installer: `survey`, `install`, `mira`, `verify`, `rollback` |
| `Tests/Editor/LightBudgetTests.cs` | Edit Mode tests of the selection logic |
| `unity/tools/check_showcase_light_budget.py` | native check for the combined batch |
| `art/light_budget_20261120/lb-tune.json` | every value the installer sets |
| `art/light_budget_20261120/originals.json` | recorded originals of every light the pass changed |
| `art/light_budget_20261120/survey.json`, `verify.json` | survey of all 245 lights and the saved-scene verification |
| `art/light_budget_20261120/tools/lb_native.py` | the native measurements (views, night walk, frame-time A/B) |
| `art/light_budget_20261120/tunes/` | runtime tune files used without rebuilding (`ATHEN_LB_TUNE`) |

Evidence: `unity/evidence/showcase_phase2/20261120/light_budget/`.

## How URP limits lights here (installed source)

URP 17.6 (`Library/PackageCache/com.unity.render-pipelines.universal@b9a66914c09e`):

- `UniversalRenderPipeline.maxVisibleAdditionalLights` returns `ShaderOptions.k_MaxVisibleLightCountMobile` (= 32,
  `com.unity.render-pipelines.universal-config/Runtime/ShaderConfig.cs:19`) when the device is OpenGL Core, otherwise
  the desktop count (256). The PC renderer is Forward+ (`PC_Renderer.asset` `m_RenderingMode: 2`), so
  `UniversalRenderer.cs:659` sets `cullingParameters.maximumVisibleLights = maxVisibleAdditionalLights` with no +1 for
  the main light: 32 visible lights in total, the sun and the sky fill included, leaving 30 local lights.
- The engine's culling returns at most that many visible lights for the camera (lights whose range meets the frustum);
  any beyond are simply not in `visibleLights`, so a lamp that falls out of the 32 vanishes for that frame. The
  ordering is the engine's, not ours: which lamp is dropped changes as the camera moves, hence the pop.
- The budget therefore works per **rendering camera** (the follow camera, which is also the conversation camera,
  photo mode's lens and the camera the dev bridge moves to review views), on the same test (range box against the
  frustum), and keeps the count at or under `hardCap` itself.

## Design

**Who owns a light.** The survey reads every MonoBehaviour's serialized references (`Owners`), the clock's lists and
the components on each light's own object:

| class | count | handling |
| --- | --- | --- |
| clock lamps (`CityLightCircuit.practicalLights`, nothing else drives them) | 145 (137 after merging) | managed: the clock rewrites `enabled`/`intensity` every LateUpdate; the budget runs after it (execution order 2000) and only lowers what the clock set |
| static lights (no script) | 6 | managed: the budget is their only writer; their own enabled/intensity is tracked |
| salvage search markers (`SalvageNode.readyLight`) | 41 | managed: SalvageNode switches them on change only, so the budget reads the node's `Search.State == Ready` instead |
| interior lamps (`InteriorLighting`), barrel fire (`AmbientLife`), cookfire (`FireFlicker`), arc flashes (`ElectricArc`), muzzle flash, combat FX, droid eyes, loot glows | 14 + 1 + 1 + 2 + 1 + spawned | **not touched, only counted**: every frame their enabled lights in view are subtracted from the cap (rescanned every 2 s so spawned FX count) |
| inactive / disabled in the scene | 32 | ignored (never lit) |

**The cap.** `hardCap` 28 local lights in view in total (managed + counted), which leaves 2 of URP's 30 local slots for
combat FX (FxBurst keeps at most 2 lights) beyond anything already counted. `fadeMargin` 2 more are kept free for
cross-fades, so the steady state is at most 26 real lamps minus the unmanaged ones in view.

**Ranking** (`LightBudgetMath.Score`): `priority × intensity × luminance(colour) × r² / (d² + r²/4 + 1) × 1/(1 + (d/15)²)`, with `d`
the distance from the rendering camera to where the lamp's light lands (a ray along a spot's axis, or down from a
point light, to the first surface) and `r` the range: the apparent brightness and size of the pool on screen. A lamp
whose range covers the player is *pinned* (×4) so the light on the player's own character stays real. Priorities
(`lb-tune.json`): East Gate arch bulkheads 1.5, avenue utility lamps 1.3, hill tree uplights 1.3, others 1.

**Selection per frame** (`LightBudgetMath.Step`):

1. Lamps whose range meets a frustum widened by 1.3× on the field of view are ranked; recent promotions (held
   `minHoldSeconds` 1 s) take slots first, then the best effective scores, up to `hardCap − counted − fadeMargin`.
2. Lamps that are real but outside the widened frustum: the best `offscreenKeep` 12 stay real (so a quick turn finds
   them lit), the rest switch to pools at once (nothing they light is on screen).
3. Demotions in view fade out over `fadeSeconds` 0.6 s; promotions fade in over the same time and wait while the
   cap is full (a fading-out lamp still holds its slot).
4. Hysteresis: a real lamp's score counts ×1.35, so near-equal lamps do not swap as the camera moves.
5. A hard cut (instant, no fade) only if the cap is still exceeded (a camera cut onto a view full of real lamps).

**Pools.** Each managed lamp on the default rendering layer has a runtime pool object (hidden, `DontSave`, under the
budget root): a box of the lamp's range drawn with `Athen Hill/Lamp Pool` (back faces, depth test GEqual, additive,
queue Transparent−120). Each pixel reconstructs the opaque surface from the camera depth texture and adds the lamp's
own Lambert term: URP's distance window `1/d² · (1 − (d²/r²)²)²`, the spot cone (`a`, `b` from the inner/outer
angles), the light's cookie projected along its axis (`NF_WallLampCookie` on the shop lamps), N·L from the depth
normal, an assumed albedo `poolAlbedo` (0.42, 0.36, 0.30 linear: Ward sandstone and paving) and the lamp's linear
colour × the intensity the clock set this frame × `poolGain` 0.65 (× `cookiePoolScale` 0.4 for the cookie wall lamps,
× `shadowedPoolScale` 0.6 for shadowed lamps; calibrated natively, see below), fogged like the scene. The box fits the
lamp: for a spot narrower than 180° it covers only the cone in front of it, and it stops at `poolRangeScale` 0.85 of the
range with a soft edge. So the pool lands on paving, steps, walls and
under sails like the real light would and goes with the clock (hour, night-only, daytime strength, dust fronts). The
real light uses `smoothstep(fade)` and the pool `1 − smoothstep(fade)`, so the sum stays constant through a swap. No
URP light slot is used. Pools are off in daylight (clock strength under 0.15) and beyond 120 m. Bulbs are untouched:
the clock's emissive materials keep every bulb lit whatever the budget decides. The salvage markers, mission-terminal
and hill-terminal screen glows and the hydroponic grow glows get no pool (they are small; their emissive screens and
the marker motes carry them).

**Not changed:** the clock's hour curve, night-only switching, daytime strength, distance fade (90/150 m), shadow
distance and shadow rules, Reduced Motion (the budget has no motion of its own), the dust-front lamp rule, the
NightActorLighting fill, interiors, fires and FX.

## Switch

- `ATHEN_LIGHT_BUDGET=0` (development players): the budget starts off (the component disables itself in `Awake`).
- At runtime (development players with `--athen-qa OUT`): write `OUT/light-budget-cmd.json` with
  `{"id":"x","enabled":false}` (or `true`); `OUT/light-budget.json` reports the state, the lights enabled in view
  (every light, not only the budget's), the lamps the owners want lit in view, real/pool counts and running maxima
  (`"reset":true` restarts them, `"dump":true` lists every lamp).
- In any build: `LightBudget.Active.enabled = false` hands every lamp back exactly as its owner last set it.
- Tuning without a rebuild: `ATHEN_LB_TUNE=file` with `{"budget":{field:value}, "aim":[{"path","aimAt"}], "lights":[...]}`.

## Survey (saved scene, 20 Nov 19:56, `survey.json`)

245 lights: 145 clock lamps, 6 static, 41 salvage markers, 14 interior lamps, 1 barrel fire (AmbientLife), 1 cookfire
(FireFlicker), 2 arc flashes (ElectricArc), 1 muzzle flash, 2 directional, 32 inactive. Lights in view at night with
no budget, by the editor's count (clock lamps within the clock's 150 m, interiors within 34 m; same frustum test):
cam_night_spawn_apron 154, cam_ss_apron_spawn 153, cam_westgate_return 148, cam_night_avenue_west 141,
cam_avenue 126, cam_hill 121, cam_fs_inside_out 120, cam_salvage_general 122, cam_range_bays 115. URP keeps 30.

## Merged and dropped lights

| retired light | merged into | change to the keeper | reason |
| --- | --- | --- | --- |
| `Ward district retrofit/Shop retrofits/LIGHT_amber_air_water_rear/Practical light amber` | Air + Water `Rear door lamp light` | intensity ×1.25 | 26 Sep retrofit fill 1.9 m from the rear door lamp the night facade pass gave the same door |
| `…/LIGHT_amber_field_supply_rear/…` | Field Supply `Rear door lamp light` | ×1.25 | same, 2.0 m |
| `…/LIGHT_amber_finery_rear/…` | Finery `Rear door lamp light` | ×1.25 | same, 0.9 m |
| `…/LIGHT_amber_relay_works_rear/…` | Relay Works `Rear door lamp light` | ×1.25 | same, 1.3 m |
| `…/LIGHT_amber_repairs_rear/…` | Repairs `Rear door lamp light` | ×1.25 | same, 1.5 m |
| `…/LIGHT_amber_salvage_rear/…` | Salvage `Rear door lamp light` | ×1.25 | same, 1.5 m |
| `…/LIGHT_amber_thread_hide_rear/…` | Thread + Hide `Rear door lamp light` | ×1.25 | same, 0.9 m |
| `…/LIGHT_amber_tool_exchange_rear/…` | Tool Exchange `Rear door lamp light` | ×1.25 | same, 1.1 m |

Retiring = the Light component disabled (the clock captures that at start and keeps it off); originals of the retired
lights and keepers are in `originals.json`. Looked at and kept: the two range floods on one mast (different lanes), the
three mission-terminal fills 2 m apart and the three hill-terminal screen glows (small; the budget ranks them low and
they get no pool), the market lantern and cookfire 1.9 m apart (different sources), the four upper retrofit ambers and
two red mast lights (they light the upper facades and roofs; the budget demotes them first). The ×1.25 is not yet
judged at player height in the rear alleys (pending).

## Mira (Basic General)

**Final (lb-5/lb-6): the two pier lamps re-aimed, the counter lamps back at their night-facade aim** — see "Mira result"
below. The first install (lb-4, the brief's version) is described here for the record.

`mira` step (lb-4): the two **counter lamps** (`Ward shops (north avenue)/Basic General/Practical lights/Counter lamp west light`
and `… east light`, spots 5.46, 7.5 m, 140°/95°, `NF_WallLampCookie`, at (6.215, 2.515, 14.65) and (9.785, 2.515,
14.65)) re-aimed from straight down (euler 80, 90 / 80, 270; forward (±0.17, −0.98, 0)) to point just in front of her
face and chest: aim points (7.75, 1.7, 16.35) and (8.25, 1.7, 16.35), giving euler (19.6, 42.1) and (19.6, 317.9),
forward (±0.63, −0.34, 0.70). Intensity, range and angles unchanged. Recorded originals: `originals.json`. These lamps
belong to the night facade pass (`art/night_facade_20261001/facade-tune.json`): **re-running NightFacadePass would undo
this re-aim**; the re-aim is a prefab-instance override in the scene, the prefab asset is untouched.

Geometry found by the survey (`survey.json` → `miraArea`): Mira stands at (8.0, 0.5, 15.8) facing +Z (the avenue),
head 1.95 m at z 15.78; the counter `BGC_Counter` is **behind** her (z 14.0–14.5) against the back panel, and the two
counter lamps are on the side walls at z 14.65, 1.1 m behind her face. So the brief's "tilt the counter lamps back over
the counter" can only side-light her: the light reaches her face from behind and to the side, the cheeks and the side of
the face catch it, the front of the face does not (N·L ≈ −0.5 for the face front). The lamps that can light her face
frontally are the two **pier lamps** at (5.6/10.4, 2.165, 17.235), 1 m in front of her face plane; their down-and-out
cones are also what lights the porch floor in front of her (the 124/255 floor). Variants to compare natively without a
rebuild: `tunes/mira-A-counter.json` (what is installed), `tunes/mira-B-pier.json` (piers tilted back at her chest),
`tunes/mira-C-both.json`. If A does not lift the face measurably, change `mira` in `lb-tune.json` to the better variant
and re-run `install,mira,verify`.

## Install, verify, rollback

```
P2=~/.local/state/ward-programme/showcase-phase2-20261120
$P2/seq.sh install lb-N AthenHill.Editor.LightBudgetPass20261120.RunBatch survey,install,mira,verify
$P2/seq.sh install lb-N AthenHill.Editor.LightBudgetPass20261120.RunBatch rollback
```

`install` and `mira` are idempotent (from recorded originals; installed twice on 20 Nov, lb-3 and lb-4). `rollback`
restores every recorded light (retired ones re-enabled, keepers and Mira's lamps back), removes **Ward light budget**
and **Light budget review cameras**, keeps the pool material, and moves `originals.json` aside. Rollback has **not**
been run. Runtime off without rollback: `ATHEN_LIGHT_BUDGET=0` or disable the **Ward light budget** object.

Verified (`verify.json`, lb-8): 184 lamps (137 clock, 6 static, 41 markers), 133 with pools, no lamp driven by
another script, every clock lamp on the clock, 8 retired lights off with originals recorded, Mira's 2 lamps aimed,
13 cameras, no missing scripts. Edit Mode: 413/413 at 20:40 with the first 11 tests (orchestrator); a 12th test
(near preference) was added later and has only been compiled.

## Review cameras

`cam_lb_spawn_apron`, `cam_lb_avenue_west`, `cam_lb_avenue_east`, `cam_lb_hill_stair`, `cam_lb_courtyard`,
`cam_lb_hall_back`, `cam_lb_market`, `cam_lb_berms_return`, `cam_lb_range`, `cam_lb_salvage_inside`,
`cam_lb_fieldsupply_inside`, `cam_lb_home_inside` (player height, copied from the existing views with the worst
counts), `cam_lb_mira` (1.6 m, 3.6 m in front of her counter).

## Native runs (20 Nov 2026)

All on the private QA display, 1920x1080 High (TAA), OpenGL Core, RTX 3060, through `P2/native_check.sh`, with
`art/light_budget_20261120/tools/lb_native.py` (`LB_MODE=views|walk|ab`) and `unity/tools/check_showcase_light_budget.py`.
Tables: `tools/lb_tables.py`. Evidence: `unity/evidence/showcase_phase2/20261120/light_budget/`.

| build | what | used for |
| --- | --- | --- |
| `batch-p2-b1` (orchestrator, 21:13) | scene at lb-4 (Mira variant A) | first views off/on (`views1`), pool calibration (`cal-*`), Mira variants (`mira-*`) |
| `batch-p2-lb2` (21:44) | pool colour fix, Mira variant B | calibration (`cal2-*`), walks (`walk1`, `walk2`) |
| `batch-p2-lb3` (22:35) | near preference, pool gain/cookie/shadow scales | views (`lb3-views`), check 9/9 (`lb3-check`), walk 2 rounds (`lb3-walk`), A/B (`lb3-ab`) |
| `batch-p2-lb4` | pool boxes fitted to the spot cones, cut at 0.85 range, 120 m | final A/B (`lb4-ab`), views (`lb4-views`), check (`lb4-check`) |

### What the first measurement found and what was fixed

1. **Pools 3–8× too bright and far too orange** (b1). Cause: `Material.SetColor` gamma-converts its input in a linear
   project, so the already-linear lamp colour × intensity was converted a second time. Fix: `SetVector`. Measured with a
   calibration (budget forced to 4 real lights so nearly every lamp is a pool, against the same view with the budget off
   where every lamp is real, minus a pools-off frame): pool/real light ratio median after the fix 1.5 (point lamps),
   2.6–5 (cookie wall lamps, shadowed floods). Hence `poolGain` 0.5, `cookiePoolScale` 0.4, `shadowedPoolScale` 0.6.
2. **Far floodlights took slots from the wall lamp beside the player** (lb2 walk, Vanguard Hall door): a 60-intensity
   tree uplight 30 m away outscored a 5.46 wall lamp 5 m away. A pool stands in well for a far lamp but not a near one,
   so the score now has a near preference `1 / (1 + (d / nearMetres)²)`, `nearMetres` 15 (new Edit Mode test).
3. **Pool draws cost 0.5–1.7 ms at the widest night views** (lb3 A/B). The boxes now fit the spot cones (half the volume
   for the 140° wall lamps), stop at 0.85 of the range with a soft edge, and pools beyond 120 m are not drawn (lb4).
4. Trying `offscreenKeep` 0 with a 1.5× ranking frustum (walk2) did not remove the instant cuts during turns and the
   walk ran slower; kept 12 and 1.3.

### Lights in view, 20:30 (lb3; off = `ATHEN_LIGHT_BUDGET=0`, same build)



| camera | lights in view off | on | wanted | real / pools in view | centre p50 off → on | p95 off → on | faces off → on |
|---|---|---|---|---|---|---|---|
| cam_avenue-h20.50 | 132 | 24 | 128 | 18 / 104 | 19.3 → 20.4 | 53.5 → 62.1 | mira 28.9 → 27.1; walker_02 54.1 → 52.1 |
| cam_hill-h20.50 | 99 | 21 | 99 | 21 / 78 | 21.3 → 22.9 | 53.9 → 57.9 |  |
| cam_lb_avenue_east-h20.50 | 88 | 24 | 88 | 24 / 64 | 33.4 → 34.1 | 107.2 → 107.5 | mira 97.1 → 98.9 |
| cam_lb_berms_return-h20.50 | 139 | 25 | 139 | 23 / 114 | 26.0 → 26.4 | 80.4 → 80.5 | Warden Ossa 11.7 → 11.7; Warden Rell 48.7 → 49.2 |
| cam_lb_courtyard-h20.50 | 109 | 26 | 95 | 14 / 69 | 54.4 → 53.6 | 111.9 → 111.7 | torr 48.2 → 45.1; walker_03 8.8 → 9.3 |
| cam_lb_fieldsupply_inside-h20.50 | 150 | 25 | 122 | 12 / 97 | 13.5 → 14.8 | 97.1 → 98.0 | tamsin 57.8 → 59.1 |
| cam_lb_hall_back-h20.50 | 97 | 22 | 97 | 22 / 75 | 34.1 → 34.1 | 63.8 → 63.3 |  |
| cam_lb_hill_stair-h20.50 | 148 | 26 | 120 | 19 / 94 | 8.4 → 10.2 | 45.1 → 50.1 | linn 47.4 → 47.5 |
| cam_lb_home_inside-h20.50 | 109 | 23 | 82 | 13 / 59 | 29.1 → 29.3 | 73.9 → 73.8 |  |
| cam_lb_market-h20.50 | 72 | 24 | 64 | 22 / 40 | 25.5 → 26.1 | 74.8 → 74.0 |  |
| cam_lb_mira-h20.50 | 85 | 25 | 85 | 19 / 60 | 73.9 → 74.2 | 165.4 → 163.4 | mira 99.8 → 99.7 |
| cam_lb_range-h20.50 | 107 | 23 | 107 | 21 / 84 | 36.8 → 36.7 | 71.0 → 71.0 |  |
| cam_lb_salvage_inside-h20.50 | 64 | 25 | 64 | 20 / 39 | 28.4 → 28.4 | 96.8 → 96.8 | brann 46.7 → 49.0; walker_02 21.3 → 18.4 |
| cam_nf_hall_portal-h20.50 | 31 | 22 | 27 | 22 / 5 | 35.3 → 35.3 | 181.4 → 181.4 |  |
| cam_night_avenue_west-h20.50 | 166 | 25 | 134 | 18 / 109 | 40.3 → 41.5 | 80.2 → 81.1 |  |
| cam_night_brann_talk-h20.50 | 76 | 26 | 76 | 19 / 50 | 22.0 → 22.0 | 74.0 → 74.2 | brann 97.4 → 97.0 |
| cam_night_linn_talk-h20.50 | 61 | 25 | 51 | 20 / 26 | 25.9 → 27.3 | 85.6 → 87.8 | linn 53.4 → 53.4 |
| cam_night_mira_talk-h20.50 | 71 | 24 | 71 | 19 / 47 | 76.4 → 76.5 | 155.7 → 155.6 | mira 98.4 → 98.3 |
| cam_night_ossa_talk-h20.50 | 31 | 23 | 23 | 20 / 0 | 30.8 → 30.7 | 179.5 → 179.6 | Warden Ossa 240.4 → 240.4 |
| cam_night_rell_talk-h20.50 | 85 | 24 | 85 | 22 / 61 | 29.1 → 29.5 | 68.7 → 67.1 | Warden Rell 46.8 → 45.8 |
| cam_night_spawn_apron-h20.50 | 178 | 26 | 146 | 19 / 120 | 58.5 → 58.6 | 84.3 → 84.2 | Player 28.3 → 28.3; vex 30.6 → 31.4; walker_01 55.3 → 56.8 |
| cam_night_tamsin_talk-h20.50 | 48 | 25 | 48 | 19 / 23 | 31.3 → 31.3 | 86.1 → 86.6 | tamsin 66.6 → 61.6 |
| cam_night_torr_talk-h20.50 | 30 | 22 | 30 | 22 / 8 | 27.8 → 29.6 | 100.3 → 99.9 | torr 41.5 → 43.0; walker_03 9.2 → 19.4 |
| cam_night_vex_talk-h20.50 | 90 | 24 | 82 | 20 / 58 | 20.9 → 21.6 | 81.9 → 82.1 | Player 38.8 → 38.8; vex 30.5 → 30.6; yard_mechanic 13.7 → 21.0 |
| cam_npcs_mira_body-h20.50 | 89 | 24 | 89 | 18 / 65 | 83.8 → 83.7 | 154.9 → 154.8 | mira 97.6 → 99.3 |
| cam_npcs_mira_face-h20.50 | 65 | 22 | 65 | 18 / 43 | 78.7 → 78.4 | 154.9 → 155.5 | mira 97.7 → 87.0 |


On (the budget) every view is at 21–26 enabled local lights; off it is 30–178 (URP keeps 30). At 13:00 on: 1–26, off:
1–73 (daytime lamps at the clock's 4 %). Frame statistics on vs off agree within 1–2/255 in p50 except where off was
missing the dropped lamps (hill, hill stair, avenue: p95 up 4–9/255 from the far pools that URP had dropped).

### Faces at 20:30 (lb3, budget off → on, display luminance 0–255, `NightReadabilityQa` + `measure.py`)

Unchanged by the budget (within run-to-run noise and walker movement): Linn 53, Vex 31, Torr 42→43, Rell 47→46, the
player 28 at the spawn apron and 39 by Vex, Tamsin 67→62 (her counter view; she is lit by the interior lamps), Brann 97,
Ossa 240 (the known issue-window hot spot). Mira is the deliberate exception (next section).

### Mira result

| variant (b1, budget on, 20:30) | face | torso | floor in front | face/floor | p95 / clipped |
| --- | --- | --- | --- | --- | --- |
| O: original (night facade aims) | 49–53 | 35 | 116–124 | 0.16–0.17 | 136 / 0.07 % |
| A: counter lamps aimed at her (brief) | 66–69 | 38–39 | 107–114 | 0.34–0.40 | 77–129 / 0 |
| **B: pier lamps tilted back onto her chest, counter lamps original (installed)** | 91–98 | 64–68 | 126–136 | 0.45–0.50 | 155–162 / ≤0.07 % |
| C: A + piers tilted down/back | 95–106 | 66–69 | 117–128 | 0.54–0.81 | 119–163 / 0 |

On lb3 (B installed): face 98–100 at `cam_night_mira_talk`, `cam_lb_mira`, `cam_npcs_mira_body` (87 at the close face
camera), torso 64, face/floor 0.52–0.60, clipped ≤ 0.07 %. Looked at (`mira-variants-cam_night_mira_talk.jpg`,
`mira-variants-cam_lb_mira.jpg`): A darkens the shelves behind her and only side-lights her; B lights her face from the
front-side and keeps the shelves lit; nothing is blown out and the conversation framing is not glared, but her face at
~98 is now brighter than the other night faces (31–54): a warm lit shopkeeper in her booth. Carl may want the piers'
intensity lowered (`mira` → `intensityScale`).

### Night walk (lb3, 2 rounds, alternating off/on, 20:30, with 360° turns at 22.5° per 0.12 s)



| segment | state | round | s | avg fps | p50 ms | p95 ms | max ms | lights in view max / mean | frames > 30 | wanted max | hard cuts | swaps |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| spawn-avenue | off | 1 | 58.2 | 31.6 | 27.57 | 54.95 | 280.8 | 178 / 99.46 | 1806 / 1857 | 178 | 0 | 0 |
| courtyard-hall | off | 1 | 39.3 | 41.7 | 25.72 | 31.92 | 205.2 | 157 / 108.91 | 1620 / 1649 | 157 | 0 | 0 |
| market-westgate | off | 1 | 30.6 | 60.5 | 16.06 | 20.90 | 171.5 | 131 / 60.93 | 1745 / 1878 | 131 | 0 | 0 |
| range | off | 1 | 12.0 | 63.8 | 14.07 | 21.47 | 173.5 | 135 / 45.18 | 664 / 768 | 135 | 0 | 0 |
| salvage | off | 1 | 8.0 | 43.7 | 22.66 | 29.02 | 193.1 | 110 / 78.22 | 345 / 369 | 110 | 0 | 0 |
| fieldsupply | off | 1 | 8.2 | 42.3 | 19.92 | 35.11 | 231.2 | 164 / 61.17 | 346 / 346 | 164 | 0 | 0 |
| home | off | 1 | 5.3 | 112.9 | 5.68 | 21.08 | 200.1 | 159 / 40.98 | 158 / 584 | 159 | 0 | 0 |
| waystation | off | 1 | 5.2 | 82.4 | 11.02 | 18.11 | 120.5 | 30 / 10.87 | 0 / 469 | 30 | 0 | 0 |
| spawn-avenue | on | 1 | 58.0 | 38.2 | 25.75 | 32.69 | 228.5 | 28 / 24.96 | 0 / 2226 | 146 | 26 | 161 |
| courtyard-hall | on | 1 | 39.8 | 41.7 | 22.57 | 34.61 | 228.2 | 28 / 25.67 | 0 / 1674 | 125 | 28 | 180 |
| market-westgate | on | 1 | 30.2 | 55.6 | 16.42 | 29.11 | 181.5 | 28 / 23.31 | 0 / 1712 | 131 | 19 | 279 |
| range | on | 1 | 12.4 | 69.0 | 12.79 | 22.09 | 155.0 | 28 / 20.54 | 0 / 865 | 135 | 8 | 131 |
| salvage | on | 1 | 8.1 | 45.6 | 21.87 | 25.24 | 187.8 | 28 / 25.97 | 0 / 384 | 102 | 11 | 62 |
| fieldsupply | on | 1 | 8.0 | 43.7 | 19.65 | 32.18 | 211.8 | 28 / 25.86 | 0 / 354 | 132 | 10 | 57 |
| home | on | 1 | 5.3 | 117.3 | 5.47 | 20.31 | 176.5 | 28 / 14.83 | 0 / 604 | 137 | 13 | 90 |
| waystation | on | 1 | 5.2 | 84.3 | 11.08 | 17.00 | 128.0 | 15 / 6.02 | 0 / 480 | 15 | 0 | 8 |
| spawn-avenue | on | 2 | 56.2 | 40.8 | 24.27 | 30.79 | 65.5 | 28 / 24.94 | 0 / 2309 | 146 | 26 | 159 |
| courtyard-hall | on | 2 | 38.3 | 42.3 | 25.68 | 31.17 | 56.6 | 28 / 25.76 | 0 / 1633 | 125 | 30 | 169 |
| market-westgate | on | 2 | 28.4 | 61.1 | 16.59 | 20.62 | 24.8 | 28 / 23.34 | 0 / 1763 | 131 | 20 | 278 |
| range | on | 2 | 11.1 | 69.6 | 14.05 | 19.42 | 26.1 | 28 / 20.58 | 0 / 783 | 135 | 8 | 127 |
| salvage | on | 2 | 7.2 | 45.6 | 22.22 | 26.99 | 36.3 | 28 / 25.94 | 0 / 347 | 102 | 11 | 62 |
| fieldsupply | on | 2 | 7.2 | 44.5 | 20.56 | 31.21 | 36.2 | 28 / 25.88 | 0 / 323 | 132 | 9 | 52 |
| home | on | 2 | 4.9 | 118.0 | 5.96 | 21.16 | 25.3 | 28 / 15.01 | 0 / 558 | 137 | 13 | 90 |
| waystation | on | 2 | 4.9 | 82.4 | 11.73 | 17.64 | 22.3 | 15 / 6.05 | 0 / 442 | 15 | 0 | 8 |
| spawn-avenue | off | 2 | 56.6 | 41.0 | 24.40 | 30.43 | 410.6 | 178 / 96.79 | 2261 / 2331 | 178 | 0 | 0 |
| courtyard-hall | off | 2 | 38.2 | 41.6 | 26.67 | 31.16 | 63.7 | 157 / 109.83 | 1570 / 1599 | 157 | 0 | 0 |
| market-westgate | off | 2 | 28.5 | 59.3 | 17.06 | 21.35 | 26.5 | 131 / 61.96 | 1618 / 1708 | 131 | 0 | 0 |
| range | off | 2 | 11.0 | 63.1 | 15.63 | 22.22 | 28.5 | 135 / 45.59 | 617 / 701 | 135 | 0 | 0 |
| salvage | off | 2 | 7.2 | 44.5 | 22.91 | 27.39 | 29.6 | 110 / 79.77 | 312 / 337 | 110 | 0 | 0 |
| fieldsupply | off | 2 | 6.8 | 43.8 | 20.69 | 34.49 | 37.9 | 164 / 63.56 | 298 / 298 | 164 | 0 | 0 |
| home | off | 2 | 4.9 | 112.6 | 6.07 | 22.05 | 30.6 | 159 / 39.46 | 139 / 536 | 159 | 0 | 0 |
| waystation | off | 2 | 4.9 | 77.0 | 12.18 | 18.85 | 23.1 | 30 / 11.24 | 0 / 418 | 30 | 0 | 0 |

off: 47.9 fps over 15229 frames, segment p50 mean 18.02 ms, max lights in view 178, frames over 30: 13499

on: 49.7 fps over 15809 frames, segment p50 mean 17.29 ms, max lights in view 28, frames over 30: 0


### Frame time, fixed cameras at 20:30 (3 alternating rounds per build; spread = max − min p50 of one build's runs)

lb3: 

| camera | off fps / p50 ms (runs) / lights | on fps / p50 ms (runs) / lights | phase1 fps / p50 ms (runs) / lights |
|---|---|---|---|
| cam_hill | 56.9 / 17.17 (17.24, 17.03, 17.24) / [99, 99, 99] | 58.2 / 17.12 (17.12, 17.13, 17.11) / [21, 21, 21] | 59.6 / 16.74 (16.51, 17.29, 16.41) / [None, None, None] |
| cam_avenue | 59.3 / 16.85 (16.87, 16.75, 16.93) / [132, 132, 132] | 57.7 / 16.93 (17.11, 16.96, 16.71) / [24, 24, 24] | 59.8 / 16.73 (16.91, 16.95, 16.35) / [None, None, None] |
| cam_night_spawn_apron | 35.3 / 28.13 (28.08, 28.08, 28.23) / [178, 178, 178] | 34.7 / 28.65 (29.01, 28.63, 28.31) / [26, 26, 26] | 35.7 / 27.84 (28.26, 27.80, 27.46) / [None, None, None] |
| cam_night_avenue_west | 43.4 / 22.93 (22.89, 23.03, 22.87) / [166, 166, 166] | 40.5 / 24.60 (24.96, 24.43, 24.42) / [25, 25, 25] | 43.5 / 22.85 (23.13, 22.82, 22.60) / [None, None, None] |


lb4 (final pool geometry):

| camera | off fps / p50 ms (runs) / lights | on fps / p50 ms (runs) / lights | phase1 fps / p50 ms (runs) / lights |
|---|---|---|---|
| cam_hill | 58.6 / 17.00 (16.87, 17.49, 16.65) / [99, 99, 99] | 58.5 / 16.98 (17.01, 17.05, 16.89) / [21, 21, 21] | 59.5 / 16.74 (16.47, 16.46, 17.27) / [None, None, None] |
| cam_avenue | 60.2 / 16.65 (16.58, 16.82, 16.55) / [132, 132, 132] | 60.3 / 16.65 (16.65, 16.71, 16.60) / [24, 24, 24] | 60.3 / 16.67 (16.33, 16.57, 17.11) / [None, None, None] |
| cam_night_spawn_apron | 35.0 / 28.21 (28.35, 28.42, 27.86) / [178, 178, 178] | 35.2 / 28.22 (28.29, 28.35, 28.01) / [26, 26, 26] | 35.2 / 27.93 (27.14, 27.88, 28.78) / [None, None, None] |
| cam_night_avenue_west | 43.7 / 22.80 (22.78, 22.64, 22.98) / [166, 166, 166] | 41.1 / 24.20 (24.05, 24.33, 24.23) / [25, 25, 25] | 44.1 / 22.60 (21.96, 22.34, 23.48) / [None, None, None] |

Reading: hill, avenue and spawn apron are unchanged with the budget on (Δp50 −0.02 to +0.01 ms, spreads 0.15–0.8 ms);
`cam_night_avenue_west` costs **+1.4 ms** (spread 0.3 ms), the view with the most pools (109). The phase 1 build is
within the spread of both at three views and 0.2 ms faster at avenue west. The pass does **not** win frame time back:
URP already shaded only 30 lights per camera, so capping the count saves little, and the pools cost some fill. The night
review views at the spawn apron (35 fps, 28 ms) and avenue west (43 fps) are slow in every build, phase 1 included;
that cost is not lights and is outside this pass. The walk (lb3, 2 rounds): on 49.7 fps / segment p50 mean 17.3 ms,
off 47.9 fps / 18.0 ms, within drift.

## Frames judged by eye (paths under `unity/evidence/showcase_phase2/20261120/light_budget/`)

- `pair-cam_avenue-2030.jpg`, `pair-cam_night_linn_talk-2030.jpg`, `pair-cam_night_torr_talk-2030.jpg` (b1, off top /
  on bottom): pools painted-on, saturated orange and several times too bright — the SetColor defect.
- `cal-*.jpg` / `cal2-*.jpg` (off, pools forced, pools off): colour fixed on lb2; cookie wall lamps (`cal2-cam_nf_hall_portal.jpg`)
  still too strong and lighting the hall doors more than the real lamps do → the cookie scale.
- `mira-variants-cam_night_mira_talk.jpg`, `mira-variants-cam_lb_mira.jpg` (O, A / C, B): chose B.
- `walk1-*.jpg` (lb2, gain 0.45): far facades and hill lamps that URP had dropped now show as pools; the near wall lamp
  at the Vanguard Hall door lost to a far uplight → the near preference.
- `lb3-pair-cam_avenue-2030.jpg`, `lb3-pair-cam_night_linn_talk-2030.jpg`, `lb3-pair-cam_lb_hill_stair-2030.jpg`,
  `lb3-walk-courtyard-hall.jpg`, `lb3-walk-market-westgate.jpg`: pools read as lamp light at player height, no discs;
  the street is not darker; the Vanguard Hall facade and the hill-side shops are lit at a distance where they were dark.
- `lb4-pair-cam_night_avenue_west-2030.jpg`, `lb4-pair-cam_lb_market-2030.jpg`, `lb4-pair-cam_avenue-2030.jpg`,
  `gain-cam_night_avenue_west.jpg`: with the cut boxes and gain 0.5 the near foreground paving at avenue west and the
  stalls in the market were a little darker than with every lamp real → `poolGain` raised to 0.65 (installed lb-8,
  checked at 0.7 on lb4 with `ATHEN_LB_TUNE`: frame means within 2–10 % of the all-real frames).

## Open defects and what is not verified

- **Not in a build:** `poolGain` 0.65 (lb-8, saved scene). lb4 has 0.5; the 0.7 test frames bracket it. The next
  combined build carries it.
- **Pop on promotion is not judged in motion.** No video was taken. The count side is measured: in the check's walk
  122 hard cuts (instant swaps light → pool) in 6,522 frames, nearly all during the scripted 360° turns (190°/s) and the
  teleports between segments; otherwise swaps cross-fade over 0.6 s. Someone should walk it with the mouse at night.
- **Frame time:** neutral at three of four night views, +1.4 ms at `cam_night_avenue_west` (109 pools). Not a win.
- **Cookie projection** orientation is not compared side by side with the real cookie (scaled down instead).
- Pools light characters who walk through a demoted lamp's range (no layer test in the pool); not seen in the frames.
- Mira's face is now ~98/255, brighter than the other night faces (31–54); deliberate, for Carl to judge.
- `pinned` uses the clock's `viewer` (the MainCamera), not the player.
- The 1.25× on the rear-door lamps after the retrofit merge was not looked at in the rear alleys.
- Rollback has not been run (install and mira were re-run eight times idempotently).
- Wrapper finding: `gpu_free.sh`/`user_player_running` treats every QA player as "Carl's game" because `qa.launch`
  starts the player in a `run-p<pid>` scope, not a `ward-*` one; other agents' GPU jobs logged "Carl's game player is
  running" during QA runs all evening.

## Proposed text for unity/EDITING.md (orchestrator to paste)

### Light budget (20 Nov 2026)

URP on the Linux OpenGL player draws 32 lights per camera (sun, sky fill, 30 local). **Ward light budget**
(`LightBudget`) keeps the lights enabled in the camera's view at or under `hardCap` (28): the best-ranked lamps are real,
the rest show a pool (`Athen Hill/Lamp Pool`) and cross-fade over 0.6 s. Every clock lamp, static light and salvage
marker is in its `lamps` list (rebuilt by `AthenHill.Editor.LightBudgetPass20261120 --steps install`); other scripts'
lights (interiors, fires, FX) are only counted. After adding lamps to the clock or the scene, re-run
`install,verify`. Tune values in `art/light_budget_20261120/lb-tune.json` (cap, hysteresis, fade, pool gain/albedo,
priorities, merges, Mira's lamps). Do not re-run NightFacadePass: it would undo Mira's pier-lamp re-aim. Off for a
test: `ATHEN_LIGHT_BUDGET=0` (development players) or disable the object. Record: `art/light_budget_20261120/README.md`.

## Proposed AGENTS.md section 3 row (orchestrator to paste)

| Light budget | 20 Nov 2026 (`art/light_budget_20261120`, `Editor/LightBudgetPass20261120.cs` with `survey`, `install`, `mira`, `verify`, `rollback`; scene roots **Ward light budget** and **Light budget review cameras**): URP's 32-light cap on OpenGL is now kept by design. `LightBudget` (after the light clock, execution order 2000) ranks the 184 clock lamps, static lights and salvage markers for the rendering camera and keeps at most 28 local lights enabled in view (interior lamps, fires and combat FX counted, not touched); demoted lamps keep their bulbs and get a depth-buffer pool (`Shaders/LampPool.shader`) that cross-fades over 0.6 s with hysteresis and a 1 s hold. The light clock's hours, night-only, daytime strength, distance fade, shadows and the dust-front rule are unchanged. 8 retrofit rear-door ambers merged into the shops' rear door lamps; Basic General's two front pier lamps tilted back onto Mira (face 51 → 98 at 20:30; overrides the night facade pass: do not re-run it). Switch: `ATHEN_LIGHT_BUDGET=0`. Native (`Builds/batch-p2-lb4`, `unity/evidence/showcase_phase2/20261120/light_budget`): 21–26 lights in view at every review camera at 20:30 (30–178 without), 0 frames over 30 on the night walk, `check_showcase_light_budget.py` 9/9, faces unchanged except Mira; frame time neutral except +1.4 ms at `cam_night_avenue_west`; pop in motion not judged. Not yet accepted by Carl. |

## Cost round (20 Nov, 00:17, install lb-9; not yet built or measured)

The +1.4 ms at `cam_night_avenue_west` came from drawing every demoted lamp's pool (109 there). Now:
`maxPools` 44 pools per frame at most, chosen by `LightBudgetMath.PoolKey` (brightness × apparent size,
`I · lum · reach² / (d² + 1)`, no near preference, so far facades keep their pools ahead of small dim lamps); a lamp in
the middle of a cross-fade always keeps its pool (cross-fade and cap unchanged); pools under `minPoolPixels` 6 px radius
on screen are skipped. Edit Mode test `PoolCapKeepsBrightestAndNeverDropsAFadingPool`. `light-budget.json` reports
`PoolsDrawn`. Tune files for one build: `tunes/pools24.json`, `pools32.json`, `pools44.json`, `pools64.json`,
`pools-uncapped.json` (lb4 behaviour).
