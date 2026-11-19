# Combat feel and feedback, 19 November 2026

Outer Berms gunfights: hit markers with critical and kill variants and audio ticks, droid weak points, combat
camera shake, a low-vitality warning, and better droid bolts and critical impacts. Code and installer only:
**nothing here has been run in Unity or the native player yet** (the machine was at its memory limit). Status: not
yet accepted by Carl.

## What already existed (kept, not duplicated)

- A two-stroke hit marker with a red kill tint, the red hurt edge flash and the damage-direction ring (CombatHud).
- Pooled hit flash and droid death burst (sparks, debris, fireball, smoke, embers, burn) from CombatFxBuilder, and
  a camera pitch kick for nearby kills (CombatFx).
- Bolts with a core, a 7 cm trail (the "thin line" in captures) and impact sparks (DroidBolt).
- Random weapon criticals (`criticalChance` / `criticalMultiplier`; 0 on the real weapons in the catalog).

## What changed

1. **Hit markers.** Four short diagonal bars around an open centre. Hit = warm white, Critical = brass and longer,
   Kill = vitality red, longest and heaviest. Kills and criticals open 1.35× and settle in 0.1 s (no pop under
   Reduced Motion), and fade over the last 35 % of their time (hit 0.14 s, critical 0.22 s, kill 0.38 s). A lesser
   marker never replaces a greater one that is still showing (`HitMarkerState`). Three synthesised ticks
   (`Audio/UI/hit-tick.wav` 50 ms, `hit-critical.wav` 110 ms, `hit-kill.wav` 300 ms) play on a 2D source in the
   SFX mixer group; hit and critical ticks closer than 50 ms are dropped so rifle bursts don't buzz; kills always
   sound. A setting turns markers and ticks off.
2. **Weak points.** `DroidWeakPoint` is a sphere that follows the droid's optic (the existing "Optic light", or the
   nearest skeleton bone at that position when the light is not inside the skeleton, so it follows the head's
   animation). A shot whose own ray passes through it is critical: the damage **left after armour** is multiplied, the
   brass marker and critical tick play, a light-free critical flash (glow and sparks) bursts at the optic, the optic
   flashes brighter, and FeralDroid may stagger sooner (below). Aim assist alone never makes a critical. Inspector:
   anchor, offset, radius, multiplier, depth tolerance, label.
3. **Camera impulse.** `CameraImpulse`, on the follow camera, is a trauma model (shake = trauma², linear decay
   1.8/s, Perlin rotation up to 2.2°/1.6°/2.4° pitch/yaw/roll and 3 cm of offset at full trauma). It is applied in
   `beginCameraRendering` and removed in `endCameraRendering`, so FollowCamera (not edited), the shot raycasts and
   the HUD projection all see the steady camera. Sources: each shot (0.2, automatic 0.11, × fitted recoil ÷ base
   recoil), damage taken (0.22 + 1.1 × share of maximum vitality), droid wrecks (0.45 × wreck size, quadratic
   falloff to 14 m; replaces CombatFx's pitch kick when an impulse is present). Only in Play, scaled by the new
   **Camera shake** setting, and off entirely under Reduced Motion.
4. **Low vitality.** Below 35 % vitality three nested dark-red edge bands deepen toward 0 and pulse at 1.1 beats per
   second between 60 % and 100 % (held at 80 % under Reduced Motion). Sits behind the HUD panels. The existing hurt
   flash is kept as the hit flash.
5. **Enemy side.** Each droid bolt gains an additive glow halo (0.46 m) and a hot core (0.14 m) that ride with it,
   a 0.1 s impact flash where it ends, and a softer, wider (13 cm tapering) and shorter trail (0.06 s, about 2 m at
   34 m/s) on a new streak texture, tinted from the bolt's original trail colour. **No lights were added** anywhere
   (the OpenGL player draws at most 32 per camera); the installer reports any light a bolt already carries. The
   death burst already had debris and smoke and is unchanged; wrecks now shake instead of kick.

6. **FX light budget** (follow-up). The hit-flash and death-burst point lights are kept but capped: at most
   `CombatFx.maxFxLights` (default 2, static `FxBurst.MaxLights`) are on at once across every FxBurst; a newer effect
   takes the oldest holder's slot and that one stays dark for the rest of its play. Slots are freed when the light
   fades, the effect is disabled or destroyed. Live count in `feel.fxLights` / `feel.fxLightCap`. Muzzle-flash lights
   (MuzzleFlash, PlayerCombat.muzzleLight) are not in the budget.
7. **Weather sight** (follow-up). Idle and returning droids spot the player within
   `aggroRadius × max(weatherSightFloor, WeatherConditions.Visibility)` (`FeralDroid.WeatherSightScale`, floor 0.5,
   so a dust front's peak of about 0.45 gives half range). A damaged droid (shot and not yet repaired) keeps full range;
   droids already fighting are unaffected, as are the ranged droids' fire range (only used once engaged) and pack
   call-ins. `feel.weatherVisibility` shows the live value.

## Balance (weak points)

Multiplier applies to the damage left after armour, so armour still decides whether a weapon gets through.

| Droids | Level | Multiplier | Radius |
| --- | --- | --- | --- |
| Feral worker, scrap drone, gunner, lancer | 1–2 | ×1.5 | walker 0.15 m, hover 0.13 m |
| Scrap Reaper, Post Sentinel, Depot Foreman (variant override) | 3 | ×1.25 | walker 0.15 m, wheeled 0.17 m (× 1.3 Foreman scale) |

Rule kept: the starter pistol (34 damage, 11 shots per charge, no penetration) cannot take the level-3 droids.

| Target | Pistol hit after armour | One charge, no optic | 25 % on the optic | Every hit on the optic |
| --- | --- | --- | --- | --- |
| Scrap Reaper (400, armour 14) | 20 | 220 (55 %) | 234 (58 %) | 275 (69 %) |
| Post Sentinel (560, armour 14) | 20 | 220 (39 %) | 234 (42 %) | 275 (49 %) |
| Depot Foreman (1,400, threat armour 4) | 30 | 330 (24 %) | 351 (25 %) | 413 (29 %) |

The 25 % row holds the same bar the next-level enemy test holds the pistol to (under 60 %): it is close for the
Reaper (58 %), which is why level 3 gets ×1.25 and not more. The modded rifle (28.35 per hit, its penetration covers
the armour) takes a Reaper in 15 hits without the optic, 14 with a quarter on it, 12 with all; a Sentinel in 20, 19
and 16. On the level-1/2 droids ×1.5 makes the pistol one hit faster when it lands on the optic (worker 4 → 3 hits,
scrap drone 3 → 2). The threat tiers (`DroidThreat.Estimate`) deliberately ignore weak points, so grey/green/red and
experience are unchanged.

Stagger: a weak-point hit may stagger again after 0.8 s (ordinary hits wait the droid's 1.3–1.4 s), and counts 1.5×
toward an elite's stagger threshold (Reaper 60, Foreman 160). Slams in wind-up and ranged droids mid-burst still
cannot be interrupted.

## Files

New: `Scripts/Combat/CombatFeel.cs` (pure maths: WeakPointMath, HitMarkerState, ImpulseState, VitalityWarning),
`Scripts/Combat/DroidWeakPoint.cs`, `Scripts/Combat/CameraImpulse.cs`, `Scripts/Combat/CombatFeelQa.cs`,
`Editor/CombatFeelPass20261119.cs`, `Tests/Editor/CombatFeelTests.cs`, `Audio/UI/hit-tick.wav`,
`hit-critical.wav`, `hit-kill.wav`, and this folder's `make_hit_ticks.py`.

Changed (own): `Scripts/Combat/PlayerCombat.cs` (weak-point test, `HitLanded` event and `CombatHit`, counters),
`Health.cs` (`Damage(amount, point, afterMitigation)` overload, `LastDamageDealt`; the two-argument call is
unchanged), `FeralDroid.cs` (critical stagger), `CombatHud.cs`, `CombatFx.cs`, `DroidBolt.cs`, `GameSettings.cs`
(`ControlOptions.cameraShake`, `hitMarkers`; older saved settings keep the defaults), `SettingsPanel.cs` (Controls ›
Combat feedback: Camera shake slider, Hit markers and ticks toggle).

Changed (shared, additive): `UI/CityHUD.uss` (hit-marker variants, low-vitality bands), `Scripts/DevBridgeCommands.cs`
and `Scripts/NativeQa.cs` (one `feel` field each in the combat state).

Created by the installer: `Art/FX/Textures/FX_BoltStreak.png`, `Art/FX/Materials/FX_BoltGlow.mat`,
`FX_BoltStreak.mat`, `Prefabs/FX/CriticalFlash.prefab`; DroidWeakPoint on the six live droid prefabs (the Foreman
inherits it from the worker and overrides the numbers); three particle children on `DroidBolt_Gunner`,
`DroidBolt_Lancer`, `DroidBolt_Sentinel`; in the scene a CameraImpulse on the follow camera, a "Hit feedback audio"
child of CombatHud and CombatFx's critical flash and impulse. The save format (version 4) is untouched.

## Install

Regenerate the ticks if needed (deterministic): `python3 art/showcase_20261119/combat_feel/make_hit_ticks.py`.
Then, with the Editor closed, one Unity job, `-nographics`, in its memory-capped scope:

    Unity -batchmode -nographics -projectPath unity/AthenHill \
      -executeMethod AthenHill.Editor.CombatFeelPass20261119.RunBatch \
      --steps audio,assets,droids,bolts,scene,verify -logFile -

`verify` prints PASS/FAIL, each droid's anchor and the balance table; it exits 2 on FAIL. Every step is safe to
re-run: prefabs already configured are recorded in `record.json` here and skipped, existing bolt children are reused,
the scene wiring is re-applied in place. It does not call any older pass. Then run the Edit Mode tests
(`CombatFeelTests`, plus `CombatBalanceTests`, `NextLevelEnemiesTests`, `HealthTests`).

## Native test plan (real input, after a development build)

Use the QA display and `qa.py` helpers; read `dev.state` → `combat.feel` (and the NativeQa snapshot's `combat.feel`).

1. **Settings.** Esc › Settings › Controls shows Combat feedback: Camera shake 100 %, Hit markers and ticks on.
   Changing them persists after a restart; an older `Controls` pref without the fields loads with the defaults.
2. **Hit marker.** At the range, a landed shot on a plate shows the marker and a tick (the red kill bars when
   it knocks the plate down; plates have no weak point). At the first-contact drones: body hits show white bars; a kill shows the red,
   larger bars and the kill tick, and `marker.kills` matches `kills`.
3. **Weak point.** Aim at a worker droid's optic with the pistol, aiming (RMB): brass bars and the critical tick,
   `weakPointHits` and `criticalHits` rise, `lastHit.zone` = "optic", `lastHit.dealt` ≈ 51 against a worker; a
   chest hit deals 34. A critical flash shows at the optic (`criticalFlashes` rises). A worker hit on the optic
   0.8–1.3 s after a stagger staggers again (`criticalStaggers` rises).
4. **Balance.** Level-1 colonist with the scrap pistol against a Scrap Reaper: one full charge leaves it above 30 %
   even with every shot on the optic (about 45 % with a quarter on it); the Reaper bar stays red. With a modded rifle and the basic armour set the Reaper
   still goes down (about 12–15 hits).
5. **Camera shake.** Firing: a slight shake (`shake.impulses` rises, `shake.peakAngle` under ~0.2° for the pistol).
   Taking a slam: clearly stronger (about 1°). A drone wrecked within a few metres shakes; one 20 m away does not.
   Set Camera shake to 0 % or turn Reduced Motion on: `shake.suppressed` true, `lastAngle` 0. Check that shots still
   land where the crosshair is while shaking (the raycast uses the steady camera).
6. **Low vitality.** Get below 35 % vitality: the red edge appears and pulses; with Reduced Motion it holds steady;
   it clears on healing (medkit, hotbar) and after a knock-down.
7. **Bolts.** Let a gunner fire: the bolt has a glowing core and halo and a short tapered trail, and a flash where it
   hits. Count lights in the frame: unchanged from before the pass.
8. **Regression.** City loop, range tutorial 10/10, rifle quest, next-level enemies check; an A/B frame-time run
   against the previous batch's build at the gate and in a Berms fight (expect within drift: no new lights, a few
   particles per bolt).

## Rollback

    ... -executeMethod AthenHill.Editor.CombatFeelPass20261119.RunBatch --steps rollback

Removes the weak points it added (the Foreman's override is reverted), the bolt children, restores each bolt trail
from `record.json`, and removes the scene components and fields it added. The new assets (textures, materials,
CriticalFlash prefab, tick WAVs) stay in place unused. The code changes are backwards-compatible: without the
installer, markers and the low-vitality warning work without ticks, there are no weak points or bolt glows, and
CombatFx keeps its old pitch kick unless a CameraImpulse exists.

## Known risks and open questions

- Nothing is verified in Unity yet: the prefab edits, the anchor choice per droid, materials and how it looks.
- The weak point anchors to the "Optic light"; if a droid's light does not sit on its optic, the zone is misplaced.
  `verify` logs each anchor and its position relative to the root; check the Scene gizmo (select the droid).
- Shake is applied in URP's per-camera callbacks; this assumes the main camera is a base camera and that no other
  script writes its transform during rendering. TAA treats it as camera motion (expected).
- The 0.35 m depth tolerance lets a shot that strikes the back of a head count as an optic hit; tighten it per droid
  if that reads wrong.
- FX lights are capped at 2 (item 6); not yet seen whether the evicted flash reads as a visible pop.
- `unity/DESIGN.md` and `unity/README.md` do not yet describe the marker variants, low-vitality warning or the new
  settings; they belong to their owners.

## Native QA fixes (19 Nov 2026)

- No game defect found in this package so far (see unity/evidence/showcase/20261119/qa/README.md). QA-only additions:
  `CombatFeelQa` now also reports `weakPointZones` (each live droid's weak-point centre and radius, so a check can aim
  the camera at the optic), `lastShotSoundSet`, `lastCone`, `droidAudio` and the bolt fly-by/impact counters.
