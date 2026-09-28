# Character feel — progress log

Handover: `HANDOFF.md` (same folder). Append entries newest-last with local time.

- 27 Sep — Handover written. Nothing started.

- 27 Sep ~10:40 — **Warden/colonist idle fix installed (Editor; native verification pending).**
  Cause measured on the rig: `idle_meshy` sweeps the head ~258° yaw at 127°/s with ~100° chest yaw; `talk_meshy` holds
  the head ~54° off the listener. Old Meshy rig task 01a07c81 is 404, so the same model (`original-unrigged.glb`) was
  re-rigged: task and clips in `meshy/character-feel-20260927/` (`rig_guard.py`, `ward-guard/rig.json`, 5 + 10×3 credits
  = 35). New skeleton = installed one (rest rotations within ~1°, joints within ~3 mm) so clips keep rotations + Hips
  translation only (`Editor/CharacterFeelPass.cs`). Candidates measured (head yaw range / deg per s): 243 14°/8, 244
  22°/7, 246 5°/8, 249 3°/9, 251 2°/9, 252 3°/1; talk 309/313/314 5–18°, 47 rejected (23 cm foot drift).
  Installed: prefab default idle_calm_252 + talk_calm_313; Ossa 243/313, Rell 252/314, Torr 244/313, Mira 246/314,
  Linn 252/313, Vex 243/314. `ActorAnimation` now derives idle phase and ±8 % rate from placement
  (`randomIdlePhase`, `idleSpeedJitter`). New `ActorLookAt` on WardGuard: levels gaze (library idles tilt the head),
  turns to the player within 4 m (±45° yaw, ±15° pitch, eased), holds eye contact in dialogue, slow glance every
  10–20 s. Old clips kept (idle_meshy/talk_meshy) for rollback. Scene saved.
  Footsteps: `unity/tools/generate_footstep_audio.py` generated 6 surfaces × walk/run + 5 landing sets
  (2–4 ElevenLabs takes each, sliced at onsets, 8–12 variants per set except metal land 2, concrete land 5), set
  loudness −30 LUFS walk / −28 run / −26 land with surface offsets; old stone steps measured −23.3 LUFS by the same
  method. Runtime `FootstepAudio` written (foot-contact trigger, surface rules + Berms grid, no-repeat, ±5 % pitch,
  ±2 dB), not yet wired. Next: wire footsteps, then gunshots.

- 27 Sep ~11:20 — **Footsteps, gunshots, aim pose, first-person view model and player idle installed; tests 65/65.**
  Footsteps: `FootstepAudio` on the player (foot-bone contact at 0.165 m / lift 0.21 m, no-repeat, ±5 % pitch,
  ±2 dB), surface rules (aprons/jersey concrete, crates wood, wrecks/containers metal, hill grass → sand, hesco sand)
  + Berms grid 88×204 baked from BermsGroundSplat (sand 16444 / gravel 1508 cells), city default stone. CityAudio's
  distance cadence is bypassed when it is present. Mix 0.5 walk / 0.6 run / 0.7 land on the existing source (.55).
  Gunshot: `unity/tools/generate_pistol_audio.py` — 6 mech + 6 body + 6 tail + 3 empty + 2 draw + 2 holster;
  tanh "glue" levels each layer (body −16, mech −22, tail −24 dBFS RMS ±1.5); runtime gains .55/.69/.37 put the
  worst-case aligned sum at −1.5 dBFS. PlayerCombat plays a random no-repeat layer set, closer/drier in FP/ADS, tail
  on its own 2D source; pistol audio now routes to the SFX group (was UI). Draw/holster/empty foley variants.
  Player rig: fresh Meshy rig of the colonist (stripped, 1k tex upload) + 10 library clips (`rig_player.py`,
  `player/rig.json`, 35 credits). Joint frames differ ~110° at hips/chest, so `CharacterFeelPass.Retarget` maps by
  bind-pose deltas. Installed: player idle = lib_idle_252 (was a static frame), `PlayerWeaponPose` (lib_fwd_234
  upper body from Spine02 on legacy layer 5, spine pitch to camera, barrel-to-aim hand fix, recoil; raised on aim,
  0.9 s after hip fire, 0.35 s on draw). First person: `PlayerFPArms.glb` (player forearms/hands split in Blender,
  1373 tris, player materials), `FirstPersonViewModel` on layer 9 "ViewModel" via a URP overlay camera stacked on
  MainCamera (FOV follows main so the tracer lines up), hip/ADS poses, sway, bob, recoil, draw/holster slide,
  reduced-motion aware. `MuzzleFlash` cards (procedural star, additive HDR cyan-white) in both views.
  Editor-only visual checks need `SkinnedMeshRenderer.forceMatrixRecalculationPerRender` (else off-screen renders
  reuse a stale skin). Baseline native run on the 04:43 build: `unity/evidence/character-feel/20260927/native-before`
  (new `unity/tools/check_character_feel.py`). Next: dev/release builds, native after-run, checkpoint + depot checks.

- 27 Sep ~14:30 — **Pass complete; verified natively. Report: `unity/evidence/character-feel/20260927/README.md`.**
  Fixes after the first native run: first-person arms were not animated (glTFast made the armature the instance root, so
  the clip paths missed — arms now sit under a "Player forearms" rig root); the pistol was mounted for the hanging idle hand
  (barrel tilted up when raised) — remounted for the hold; new `pistol_hold.anim` (library 95 settled frame, hips from idle,
  torso squared −8° yaw / −16° lean) replaces lib_fwd_234 for FP and the TP layer; FP pistol seated 5.5 cm higher so the
  support hand doesn't hide the slide; overlay camera enabled only while visible; FollowCamera ignores look for two frames
  on entering aim (cursor-lock recentring snapped the camera down — present in the baseline too).
  Final: tests 65/65; dev + release 0 errors; native character-feel PASS (91 steps over Stone/Concrete/Gravel/Sand,
  Wardens focus the player, FP visible with flashes, holster in Ward, no exceptions), checkpoint 10/10 PASS, depot 7/7 PASS.
  Perf: checkpoint 212.8 fps p99 17.42 ms (was 16.71–16.99); depot walk p99 16.59 (was 16.00); no >50 ms hitches.
  Remaining (see README): TP pistol mostly hidden behind torso from directly behind (aimShoulder option), faceted FP
  hands, strafe/backpedal/turn-in-place clips retargeted but not wired, worker droid untouched, metal landing 2 variants.

- 27 Sep — Next-session handover written: `HANDOFF-NEXT.md` (state, open decisions, prioritised next work, rebuild steps, pitfalls).

- 27 Sep ~14:50 — **Second pass (REQUESTS-2026-09-27-pm.md): quick fixes 1–5 applied in the saved scene (Editor).**
  1. Player run: `MeshyPlayer` ActorAnimation.runStrideSpeed 3.5 → 4.118 (= 3.5/0.85), so playback at 6 m/s drops
     from 1.71× to 1.46× (−15 %). Move speed unchanged (PlayerMotor.runSpeed 6). Measured the run clip's planted-foot
     travel: ~0.51 m per half-cycle of 0.333 s → ~4.6 m/s at rate 1 (×1.08 rig scale). At 1.46× the foot moves ~6.7 m/s
     vs body 6 m/s (was ~7.9 m/s), so the slower cadence *reduces* the overshoot slide; stride not lengthened — accepted.
     `ImportMeshyPlayer.cs` default updated to match.
  2. Wardens: Ossa's lowest skinned vertex (8 idle samples) was 0.18 m below the Berms ground, Rell's 0.24 m below the
     concrete apron (both use the `char1` mesh variant). Raised their `ward-guard` visual child (root/NpcAgent untouched)
     by 0.178 / 0.241 m; now 4 mm/3 mm above ground. The four city guards were already within 2–3 mm.
  3. Road tree: the Searsia shrub-tree (`West Gate outpost/Terrain dressing/searsiasmall` at −79.5, −4.8) stood on the
     tyre track to the depot. Collider was already disabled (visual only). Moved to the verge at (−87.5, −1.18, −7.0).
  4. Karaveen truck: uniform scale 1 → 0.65, re-grounded (wheels at −0.02). Now 7.65 m long, 2.65 m body width
     (mirrors 2.96 m), 3.39 m tall; BoxCollider scales with it. Gate: 6.5 m between piers, ~5.1 m under the gantry.
  5. Dusk start: new `Editor/DuskStartPass.cs` adds a 17:00 frame to `Art/Atmosphere/Dustbowl/WardDustbowl.asset`
     (sun 11° elevation, warm key 0.98, cooler fill/ambient, lamps 0.45, exposure −0.12) and sets defaultHour 16 → 17.
     Before copy: `unity/evidence/character-feel/20260927-pm/WardDustbowl-before-dusk.asset`. Editor previews in
     `unity/evidence/character-feel/20260927-pm/editor/`. Native verification pending.
