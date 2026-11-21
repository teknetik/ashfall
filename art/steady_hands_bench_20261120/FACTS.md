# Facts about the existing game that this programme builds on

Gathered 20 November 2026 by three read-only research agents and checked in part by the orchestrator. Treat every line
as a lead with a path: open the file before relying on a number, and report anything that is wrong.
`U` = `unity/AthenHill/Assets/AthenHill`, `R` = `/home/teknetik/code/ao2`.

## The scrap pistol today

- `U/Art/OuterBerms/ScrapPistol.glb`: Meshy text-to-3D (26 Sep 2026, record `meshy/outer-berms-20260926/scrap-pistol/`),
  **one fused mesh**, 12,052 triangles, one material, three 2048 maps. No prefab; it is instanced from the glb.
  Prompt: "chunky bolted steel receiver, short ribbed barrel, a small glass nanite charge cell glowing faint cyan on
  the side, wrapped grip with worn leather strips and tape".
- glTF units 1.9015 x 1.2493 x 0.3698; in-game scale **0.13674**, so 0.260 m long, 0.171 m tall, 0.051 m wide.
  glTF axes: muzzle toward -X, up +Y, player's right -Z. glTFast negates X on import.
- Bore axis: glTF y 0.43038, z -0.00548; stock bore mouth x -0.95143. The stock `Muzzle` transform sits about 29 mm
  below the bore on the dust cover. Dust-cover rail (cell mods): left face ahead of the trigger guard, metric
  x -0.095..-0.03, z 0.021..0.042. Grip: centre 80 mm behind and 30 mm below the origin, raked about 25 degrees
  (`art/pistol_mods_20260930/src/mods_grip.py` `GRIP_C0`, `GRIP_AX`); the present Stabilised grip mod spans glTF
  x 0.42..0.98, y -0.57..-0.18.
- Held in third person: scene object `Berms held pistol` under the colonist's `RightHand`
  (built by `U/Editor/OuterBermsInstaller.cs:609` `AttachPistol`, re-run by `MainCharacterInstall.cs:129`); children:
  the ScrapPistol instance (local pos (0.000674, 0.000124, 0.083761), Y -90, scale 0.136736) and `Muzzle`.
- First person: `First-person view model/Visuals/Weapon mount/View model pistol` (layer 9) with `ScrapPistol`,
  `Pistol mods`, `Muzzle`, `Shooting grip` (0.0448, -0.0828, -0.0295) and `Support grip` (-0.0139, -0.1009, -0.0181).
  Grips are solved at install time by `U/Editor/PlayerFace20261003.cs:489` (`ShootingGrip`), `:572`, `:677`
  (`SolveFingers`). Frame reference: `art/character_feel_20260927/fp_arms/pistol_frame.json`.
- Mods: `art/pistol_mods_20260930` (Blender 5.2.1, procedural, shared 2048 atlas, GLB in the pistol's own units).
  `U/Scripts/Combat/WeaponModVisuals.cs:30-44` activates the child of `Pistol mods` whose **name equals the fitted
  mod's item id** and moves the muzzle for barrels. Installer `U/Editor/PistolModsInstall.cs`.
  Present Stabilised grip look (`grip_stabilised_pistol`, 2,128 triangles): rubber inner-tube wrap, a Warden-orange
  riveted backstrap brace with a palm swell, brass rivets. Mark II (`grip_gyro_braced`): gyro drum under the base
  plate, alloy backstrap bar, cyan status pod.
- Kit worth reusing: `art/pistol_mods_20260930/src/pm_geo.py` (lathe, prism, rounded_rect, stadium, tube_path,
  boolean, bevel, join), `pm_mats.py` (wear materials with `CH_*` channels for baking), `pm_common.py` (frames,
  `S = 0.13674`, `HOLDER_T`), `build_all.py` (smart project, Cycles CPU bake of base, metal, rough, emit, normal, AO,
  dilation, URP mask and glTF ORM, GLB export; about 8 minutes at 2048), `verify_export.py`, `review.py`.

## Numbers and feel

- `U/Data/Crafting/WardCrafting.asset`: `weapon_scrap_pistol` (item `scrap_pistol`): damage 34, fireInterval 0.28,
  range 30, **recoil 38**, spread 4, accuracy 0, aimAssist 3.5, nanoMax 100, nanoPerShot 9, durability 100,
  wearPerShot 0.15; slots grip, barrel, cell.
- `mod_grip_stabilised` (item `grip_stabilised_pistol`): only effect recoil add -7. Recipe
  `recipe_grip_stabilised_pistol`: station `station_field_fabricator`, inputs tag `component:servo` x1,
  `scrap_alloy` x2, tag `nanite:tier1` x5 (item `nanite_residue`), unlock `identify npc_ossa:servo_look`, tool
  `tool:screwdriver`, 8 s, engineering, 12 XP. Mark II: recoil -15, aimAssist +1.
- Recoil today: `PlayerCombat.cs:338` kick = recoil x `recoilDegreesPerPoint` 0.05 (1.9 degrees), half of it recovered
  in 0.18 s (`FollowCamera.ApplyShotKick`); view model `FirstPersonViewModel.cs:94` pitch 6 x RecoilScale, push-back
  0.05 m, return 0.13 s; third person `PlayerWeaponPose.cs:116`; shake `CameraImpulse.cs:101`.
- Spread: `WeaponBallistics.cs:38`, `PlayerCombat.cs:318`: cone = spread x (1 - accuracy/100) x 0.5 aiming x 1.6
  moving x condition. Uniform disc, ray from the camera.
- Sway is visual only (`FirstPersonViewModel` `swayAmount` 0.012, `swayRotation` 2.5) and never moves the shot.
  There is no sideways kick, no growth of scatter with rapid fire and no stat for sway or recovery.
- Mod effects: `WeaponLoadout.Compute` (`U/Scripts/Crafting/WeaponLoadout.cs:148`) sums `CraftEffect {stat, op, value}`;
  `PlayerCombat.ApplyLoadout` (`:196`) reads the result.
- Items are id and count only (`ShopModel`), fitted mods are slot to item id (`WeaponLoadout.fitted`). **There is no
  per-instance data and no quality anywhere.** Weapon condition on `WeaponLoadout` is the only per-weapon state.
- No 3D model exists for the Damaged Servo (`droid_servo_damaged`), Scrap Alloy (`scrap_alloy`), nanites
  (`nanite_residue`), Copper Filament (`copper_filament`) or the Field Toolkit (`field_toolkit`): icons only
  (`U/UI/Art/*.png`). Style source for the servo: `U/Art/OuterBerms/WorkerDroid.glb` and its 2048 textures
  (`Art/OuterBerms/Textures/WorkerDroid_*`), prompt "heavy hydraulic forearms ending in three-fingered steel clamp
  hands, exposed pistons and cable bundles at elbows and knees"; also `U/Art/WardShops/ToolExchangeProps/TE_servo_arm.glb`.

## Brann's bench and shop

- `U/Prefabs/SalvageShop/SS_Workbench.prefab` (Meshy, LOD0 84,593 triangles, 4096 base colour): 2.20 x 2.13 x 1.17 m,
  pivot floor centre, front +Z. **Worktop at 0.864 m, 2.2 x 1.15 m**, front edge z 0.583, back z -0.567. A welded rear
  frame with a gantry and a yellow print head over the centre (bottom at 1.468 m), a screen plate at the rear centre
  (centre (0.009, 1.055, -0.103)), tool hooks left, pendant control right rear, drawers right, a lower shelf with a
  fused vise. The worktop in front of the screen is empty. Children `Use point` (0, 0, 1.083), `Light point`
  (0, 1.588, 0.224). Measurements: `U/Art/SalvageShop/Props/salvage-shop-props.json`.
- In the scene under root `Salvage shop interior` (world (-18.1, 0, 18), yaw 90; shop-local +X south, +Z out to the
  avenue, floor y 0.5; world = (-18.1 + z, y, 18 - x)): workbench at local (-1.3, 0.5, -5.875), identity rotation,
  so world about (-23.975, 0.5, 19.3) facing world +X; worktop at world y about 1.364.
- `Workbench station` at local (-1.3, 1.4, -4.79): `WorldInteractable` "E · Use Brann's workbench" (range 1.7, no
  collider) and `CraftingStationMarker` `station_field_fabricator`. QA landmark `salvage_bench`.
- Free floor in front: about local x -2.6..1.0, z -5.29..-1.2. Tool cart at (-2.85, -6.0), compressor at (0.12, -6.12).
- Lamps (all rendering layer 7, **no shadows**): pendant over the workbench (-1.3, 3.48, -4.85) spot 2.5, range 5.5,
  120 degrees; cyan "Fabricator glow" point 0.45 at (-1.3, 1.708, -5.53); room bounce; two more pendants.
  `U/Scripts/InteriorLighting.cs` on the root: interior ambient probe, portal test through the bay, lamps off beyond
  34 m. New renderers inside must have rendering layer bit 7 and sit under one of its `interiorRoots`.
- `U/Editor/SalvageShopPass.cs` `install` destroys and rebuilds its whole root: keep the bench set in its own scene
  root. `Salvage shop interior` is not a render-chunk source.
- Brann (`npc_brann`, `U/Prefabs/SalvageDealer.prefab`, 66 joints with fingers, clips idle/talk/walk/run) stands
  behind the counter at shop-local (2.3, 0.5, -2.55) facing -X, 4.3 m from the bench station and about 42 degrees to
  the side. The camera is not confined in this shop. Weapons are holstered automatically inside the walls.

## Runtime hooks

- `U/Scripts/GameSession.cs:11` `enum CityState { Boot, Play, Dialogue, Shop, Grid, Paused, Inventory, Journal,
  Credits, Error, Settings, MainMenu, Fabricator, Stash, Rest, Map }` (append only). `SetState` (private, :486) sets
  `input.SetGameplay(state == Play)`, `player.Blocked`, time scale. `Open(state)` refuses `Fabricator`;
  `OpenFabricator(CraftingStationMarker)` (:458); `Close()` (:469). Esc (`input.Cancel`) closes any non-Play state.
- `U/Scripts/Crafting/CraftingStationMarker.cs` `Use()` calls `session.OpenFabricator(this)`.
- `CraftingModel`: `BeginCraft` (:138), `TickCraft` (:148), `CancelCraft` (:156), `TryCraft` (:186, the only place
  inputs are consumed and output granted), `CanFit`/`TryFit` (:206, :220), `TryRemove` (:232), `Award`/`LastAward`.
  `CraftingSession` requires `State == Fabricator` (`AtStation`, :185) and cancels a timed job when the state leaves
  `Fabricator` (`OnSessionChanged`, :54). A craft in progress is never saved.
- Orders: `U/Scripts/Orders/FieldOrderProgress.cs:11` `enum OrderStage { NotStarted, Gather, Fabricate, Fit, TestFire,
  Hunt, Craft, FreePlay, Report, Identify }`; the stage is derived each time (`Stage`, :66): `TestFire` when the mod
  is fitted on the default pistol, `Fit` when it is in the pack. Read by `QuestConditions.cs` (`stage:NAME`),
  `Journal/QuestJournal.cs:190-204`, `FabricatorPanel.Opened`, Brann's `stage:` entries in `U/Data/npc_brann.asset`.
- Camera: `FollowCamera.LateUpdate` early-outs for photo mode (:60) and `FixedView` (:61), else composes the pose and
  hands it to `ConversationCamera.Compose` (:94) as a weighted overlay. `PhotoMode` (`U/Scripts/Camera/PhotoMode.cs`)
  takes the camera over with a restore ledger. `CinematicCamera.UnderControl` turns shake, sway and bob off.
  `TransientVolume` (`U/Scripts/Camera/TransientVolume.cs`) makes a runtime Volume for depth of field.
- Input: `U/Data/Controls.inputactions` maps `Gameplay`, `UI` (Cancel, Map; always on) and `Photo`. `GameInput`
  (`U/Scripts/GameInput.cs`) owns cursor lock: locked while gameplay or photo input is enabled and Left Alt is not
  held. P and M were added by editing the JSON by hand and a `verify` step that checks the binding is unique
  (`U/Editor/ShowcaseCameraInstall20261119.cs:144`, `WorldMapInstall20261119.cs:266`).
- HUD: `session.Notify(text, speaker)`; `BarkCaptionView.Bind(root).Show(who, text)`; adaptive panels
  `U/Scripts/HudPresentation.cs`; `CityHud.Refresh` shows `#shade` and the `#modal` frame for every non-Play state
  (:295-364); the lower-third dialogue makes the shade transparent with a class on `#shade`
  (`U/UI/CityHUD.uss:793`). `WorldMapPanel` builds its own UI in code with its own stylesheet: the low-collision
  pattern. `BarkDirector` cancels barks outside Play and has no "say this line" method; `NpcAgent.Speak` plays a
  node's voice at the NPC's head; `NpcAgent.barking = true` plays the talk clip.
- Audio: no generic one-shot API. `GameSession.Cue(CitySoundCue)` for four UI cues; otherwise an `AudioSource` on the
  object and `PlayOneShot`. Mixer `U/Audio/City.mixer` groups Master, Music, Ambience, SFX, UI. `VoiceLimiter`
  (`VoiceLimiter.Droids`, 10 voices). `GameSettings.Sound` scales volumes; nothing in audio reads Reduced Motion.
- Reduced Motion: `session.reducedMotion`. Settings: `GameSettings` in PlayerPrefs, `session.Settings.Changed`.
- Save: `U/Scripts/Save/WardSaveData.cs` version 4; `map` was added as a plain extra field with no version bump
  (null = none); weapon condition as `conditionVersion` inside `WeaponLoadoutState`. `WardSaveGame.Capture` (:100).
- QA: `U/Scripts/DevBridgeCommands.cs` (`dev.*` if-chain; example `dev.weapon.condition`, :116-141) and
  `U/Scripts/NativeQa.cs` (`--athen-qa <folder>`, `command.json`, `snapshot.json`, `capture`, `uiSnapshot`).
  Python: `unity/tools/showcase_qa.py`, `unity/evidence/gameplay-v2/20260930-reqa2/qa.py` (real XTEST keys and mouse),
  closest example `unity/tools/check_crafting_flow_native.py`.
- Tests: `U/Tests/Editor/AthenHill.EditModeTests.asmdef`; fixtures in `TimedCraftingTests.cs:24-45` and
  `CraftingSkillsToolsTests.cs:23`. Runtime asmdef `U/Scripts/AthenHill.Runtime.asmdef`; Editor scripts have none.
- Editor pass template: `U/Editor/GateBarrelsPass20261120.cs` (`RunBatch`, `--steps`, install/verify/rollback, record
  json, landmarks, review cameras, chunk fingerprint check). Prefabs from glb: `U/Editor/SalvageShopProps.cs:153-253`.
  glTF textures are compressed to BC7 on import only when their size is a power of two.

## Hands (for a later round)

- `U/Art/Armour/TutorialSet/TS_FPArms.glb` (21,792 triangles, 54 joints, finger bones `index_01_l` .. `thumb_03_r`,
  +X closes). `ViewModelArmsRig`, `PlayerHandGrip` (grips solved at install by stepping joints until capsules touch),
  `SupportHandIK.Solve(target, w)`. All are gated on `combat.Armed`; a bench mode needs its own driver.

## Tooling

- Wrappers: `~/.local/state/ward-programme/steady-hands-20261120/` (`seq.sh`, `build_to.sh` (names `sh-*`),
  `native_check.sh`, `blender.sh`, `slot.sh`, `run.sh`, `wait.sh`, `gpu_free.sh`). See `AGENT-RULES.md`.
- `python3 unity/tools/compile_check.py [runtime|editor|tests]`: about 5 s, no Unity.
- Reference images: `python3 art/salvage_cache_20260930/scripts/gen_concept.py NAME PROMPT [--size 1536x1024]
  [--model gpt-image-2] [--ref img.png ...]` (OpenAI key from `.env`; with `--ref` it uses the edits endpoint).
  Read it and copy it into your folder before use; record prompts beside the images.
- Voice: `art/crafting_assembly_20261120/generate_voices.py` (+ `lines.json`), built on
  `art/showcase_20261119/npc_life/generate_voices.py` (budget guard, caching, -20 LUFS mastering); Brann is voice
  Callum `N2lVS1w4EtoT3dr4eOWO`, Ossa is Victoria `N8SmJJ4vvs5Mz9VaT6u5`, model `eleven_multilingual_v2`, stability
  0.55, similarity 0.78, style 0.12. A better master is in `art/linn_voice_20261120/linn_voice.py`.
- Sound effects: `unity/tools/generate_combat_audio_20261119.py` on `unity/tools/generate_elevenlabs_audio.py`
  (`POST /v1/sound-generation`, `eleven_text_to_sound_v2`, `duration_seconds` 0.5 to 2.5, `prompt_influence` 0.55,
  one take per variant, trim, shape, loudness fit, ledger from the `character-cost` header). On 19 Nov 53 takes cost
  511 credits.
