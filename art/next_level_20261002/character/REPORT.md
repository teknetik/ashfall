# Character agent report, Ward "next level" programme, 2 October 2026

Carl: "swap out the main character for char_main_OK. NOK is to be used later but put that asset in the right place for
now." Delivered in `meshy/incoming-20261002/` (originals kept): `main_char_OK.glb` (595,052 triangles, unrigged,
1.90 m, three 2048 px JPEG maps) and `main_char_NOK.glb` (11,913 triangles, same shape, baked 2k/4k PNG maps).

## What changed

**Player model.** The colonist is now Carl's main character: a bearded man in an olive flight suit, LOD0
**59,999 triangles / 48,075 vertices** decimated in Blender from the 595k source (collapse ratio 0.1008, the source
UVs kept, so the delivered base colour and metallic/roughness maps apply unchanged), with a **4096 px tangent-space
normal map baked from the 595k source** (geometry plus the source's own 2k normal texture). Rigged and animated by
Meshy (24 joints, the same bone names as the previous rig: Hips, Spine02, Spine01, Spine, neck, Head, …, RightHand,
…, RightToeBase), 1.8 m. Textures in the runtime GLB: base colour 2048 JPEG, metallic/roughness 2048 JPEG, normal
4096 PNG; the glTFast import add-on compresses all three to BC7 (`check.json`: 2048² BC7, 4096² BC7, 2048² BC7).
A 15,000-triangle LOD1 was decimated and exported (`meshy/main-char-20261002/blender/player_lod1.glb`) but **not
installed**: it would need its own skinned renderer and an LODGroup on the player prefab, which the ActorAnimation /
first-person hide / shadow-proxy chain does not expect; it is a record for a later cost pass.

**NOK held for later.** `meshy/main-char-20261002/nok-held-for-later/main_char_NOK.glb` (copy; SHA-256 in
`meshy/main-char-20261002/incoming-sha256.txt`). Nothing references it; its README row says what it is.

**Files.**

| Path | Change |
| --- | --- |
| `unity/AthenHill/Assets/AthenHill/Art/Imported/Meshy/colonist.glb` | Rewritten (same path and GUID) from the Meshy rig: mesh + skin, clips `idle` (library Idle 13 / action 252, 6.03 s), `walk` (Meshy walking, 1.07 s), `run` (Meshy running, 0.67 s), full-resolution textures. 24.2 MB. |
| `Assets/AthenHill/Prefabs/MeshyPlayer.prefab` | Rebuilt by `ImportMeshyPlayer.Install` from the new GLB, then normalised: rig scale 0.99392, offset y 0.0414 m so the sampled idle stands **1.800 m with the soles at y = 0** (measured by CPU skinning in the installer; `install.json`). Previous prefab copy: `meshy/main-char-20261002/previous/MeshyPlayer.prefab.before`. |
| `Assets/AthenHill/Art/CharacterMotion/Source/Player/Player_{idle_252,aim_95,rifleturn_573,lower_334,aimturn_585,left_528,back_233,fwd_234}.glb` | Replaced with the new rig's Meshy clips (the 27 Sep rig's copies stay in `meshy/character-feel-20260927/`). `Player_draw_222`, `idle_243`, `turnl_576`, `turnr_586` are still the 27 Sep rig's clips; the bind-pose-delta retarget handles both rigs. |
| `Assets/AthenHill/Art/CharacterMotion/Player/lib_*.anim` (12), `pistol_hold.anim`, `rifle_hold.anim`, `rifle_carry.anim` | Rebuilt for the new skeleton (`CharacterFeelPass.RetargetPlayerClips`, `RifleArmourInstall.Clips`, `WeaponFeelPass.HoldClip`: pistol = lib_aim_95 at 0.97, rifle hold = lib_rifleturn_573 at 0.95, rifle carry = lib_lower_334 at 0.5). |
| `Assets/AthenHill/Art/CharacterMotion/Player/idle.anim`, `talk.anim`, `jump_*.anim` (5) | Re-authored by `CharacterMotionPass.AuthorPrefab` (private, called by reflection) for the new rest pose: the jump clips are absolute bone rotations and would have been wrong on the new rig. |
| `Assets/AthenHill/Art/CharacterMotion/FirstPerson/FPHands/FPHandsGlow.mat` | Touched by `FPGripPass.Attach` re-running (same values; side effect of the chain). |
| `Assets/AthenHill/Scenes/AthenHill.unity` | Player visual replaced; pistol, pistol mods, first-person view model, rifle, plate carrier, review cameras, landmarks, order bindings and footsteps re-installed on the new rig; `Character review cameras` root added. |
| `Assets/AthenHill/Editor/MainCharacterInstall.cs` (+ .meta) | New: `InstallBatch`, `CheckBatch`, `CaptureBatch`, menu *Athen Hill → Characters → Install main character (next level, 2 Oct 2026)*. |
| `meshy/main-char-20261002/` | Blender script + outputs, Meshy script + records, GLB assembly script, README, held NOK. |

**Scene objects under the player (all re-created on the new rig, same names):** `MeshyPlayer` (prefab instance,
visual) › `colonist` › `Armature` › bones; `Berms held pistol` + `Pistol mods` + `Muzzle` + `Third-person muzzle flash`
under `RightHand`; `Berms held rifle` + `Rifle muzzle` under `RightHand`; `Warden plate carrier` under `Spine`;
`Player shadow proxy` carried over under the visual. `First-person view model` rebuilt (pistol copy + `Pistol mods`,
`FP hands v2` static cup grip kept, old colonist-cut arms hidden as before). `Rifle armour review cameras` and
`Character review cameras` roots replaced.

**Components re-wired:** `PlayerMotor.visual/actor`; `ActorAnimation` (idle/talk = `lib_idle_252`, walk/run from the
GLB, five jump clips, stride speeds 1.6 / 4.1176 unchanged); `PlayerCombat.heldPistol/muzzlePoint/heldRifle/
rifleMuzzle/thirdPersonFlash/viewModel`; `PlayerWeaponPose` (mixRoot Spine02, spine Spine02/Spine01/Spine, rightHand
RightHand, aim/rifle/carry clips); `PlayerArmourVisuals` (vest under Spine); `WeaponModVisuals` on both pistols;
`FootstepAudio.leftFoot/rightFoot`; `FieldOrders` guidance/encounter bindings (idempotent re-run).

## Meshy and Blender provenance

- Blender 5.2 headless: `meshy/main-char-20261002/blender/prep_player.py` (record `prep.json`, previews
  `blender/previews/`, 25 s). Bake: Cycles CPU, 1 sample, cage 4 mm, max ray 12 mm (a 4 cm ray range hit the shells
  under the collar and beard; a normal recalculation flipped the beard shell; both removed after the first preview).
- Meshy (`rig_main_char.py`, record `rig.json`): rigging task `01a0fd2b-d937-7338-b11d-5afbd92fa01c`
  (model_url data URI of the 2.1 MB rig input, `height_meters` 1.8, 5 credits; the 60k mesh was accepted directly, no
  further decimation or weight transfer was needed) and eight animation tasks at 30 fps (3 credits each): idle_252,
  aim_95, rifleturn_573, lower_334, aimturn_585, left_528, back_233, fwd_234. **29 credits total.** The rig result's
  basic walking/running clips are the player's walk/run.
- GLB assembly: `meshy/main-char-20261002/prepare_player.py` (record `prepare.json`, with the previous colonist.glb's
  SHA-256 and git blob).

## Editor methods to re-run

```
meshy/main-char-20261002/prepare_player.py                                   # colonist.glb + Source/Player clip copies
unity.sh <log> AthenHill.Editor.MainCharacterInstall.InstallBatch -nographics -quit   # whole chain, idempotent
unity.sh <log> AthenHill.Editor.MainCharacterInstall.CheckBatch   -nographics -quit   # writes evidence/.../check.json
DISPLAY=:0 WAYLAND_DISPLAY=wayland-1 unity.sh <log> AthenHill.Editor.MainCharacterInstall.CaptureBatch -quit   # 6 captures
DISPLAY=:0 WAYLAND_DISPLAY=wayland-1 unity.sh <log> AthenHill.Editor.MainCharacterInstall.CaptureRifleBatch -quit   # rifle hold/carry x 3 cams
unity.sh <log> AthenHill.Editor.MainCharacterInstall.MeasureGripsBatch -nographics -quit   # palm vs grip distances
unity.sh <log> AthenHill.Editor.RifleArmourInstall.InstallRifleBatch -nographics -quit      # rifle mount only (combat agent's entry)
```

`InstallBatch` runs, in order: `ImportMeshyPlayer.Install` → sole/height normalisation → `CharacterMotionPass.
AuthorPrefab/Configure` (Player family) → `CharacterFeelPass.RetargetPlayerClips` → `OuterBermsPass.AttachPistol` →
`WeaponFeelPass.Install` → `RemountPistol` → `PistolModsInstall.Install` → `RifleArmourInstall.InstallAll` → `CharacterFeelPass.
InstallPlayerIdle` → `CharacterFeelPass.InstallFootsteps` → character review cameras. Shared files edited: `Editor/RifleArmourInstall.cs` (three grip constants, one commented line; see the re-tune section).

## Recovery

Previous player: regenerate `colonist.glb` with `unity/tools/prepare_meshy.py` (meshy/mpc sources, unchanged) or from
git (`prepare.json` records the blob), restore `previous/MeshyPlayer.prefab.before`, re-run `InstallBatch`. The
Source/Player clips of the 27 Sep rig are in `meshy/character-feel-20260927/player*/`.

## Review cameras (player height)

`cam_character_idle` (front three-quarter, full body), `cam_character_face` (0.95 m, face and hair),
`cam_character_back` (follow-camera side), plus the rifle pass's `cam_rifle_carry`, `cam_rifle_aim`, `cam_rifle_side`,
`cam_vest_front`, `cam_vest_quarter` (rebuilt, same positions), all at `RifleArmourInstall.Stand` (-75, -1.3, 3), the
colonist facing -X.

## Weapon grips re-tuned on the new rig (coordinator / combat agent request, 16:45–16:55)

The combat agent reported the held rifle floating ~10 cm above the hands after the swap. Measured with
`MainCharacterInstall.MeasureGrips` (CPU-skinned centroid of the `RightHand`-dominated vertices against each holder
origin, `measuregrips-log.txt`): on the new rig the hand's centre is **0.121 m along the hand bone** (the mpc colonist's
mount rule assumed 0.075 m), and the old rifle grip point (40 % from the butt, 15 % of the height from the bottom)
sat at the bottom of the hanging magazine, so the receiver rode ~11 cm above the hand. Rifle profile from the mesh
(`FieldRifle.glb`, 0.278 m tall at 0.9 m): the pistol grip is the slanted part 33–37 % from the butt spanning 5–55 %
of the height; the magazine is the hanging part at 38–43 %.

- `Editor/RifleArmourInstall.cs` (shared file, combat agent's current version with `MuzzleSign=+1`): **one commented
  line changed** — `GripAlong .075 → .11`, `GripFromButt .40 → .35`, `GripFromBottom .15 → .38`. `MuzzleSign` kept at +1;
  re-run through the combat agent's `RifleArmourInstall.InstallRifleBatch` (rc 0, `rifle-install.log`; its log line
  now reads muzzle point local (0, 0.033, 0.585), holder local y 11.1 hand units). Note: that batch entry writes
  `unity/evidence/next-level/20261002/combat/rifle-install.txt`, so the combat agent's copy now holds this re-run's line.
- Pistol: the same 5 cm drift (`WeaponFeelPass.MountPistolForAim` hard-codes 0.075 m). Rather than edit that shared
  pass (which also rebuilds the first-person view model from the held pistol's pose), `MainCharacterInstall.
  RemountPistol` re-seats only the held pistol at `PistolGripAlong = 0.11` m along the hand in the `pistol_hold` pose
  (same rotation rule); it is part of `InstallBatch` after `WeaponFeelPass.Install` and has its own
  `RemountPistolBatch`. The first-person view model is untouched.
- Result (`measuregrips-log.txt` after): palm-to-grip distance **5.1 → 2.4 cm** for rifle hold, rifle carry and pistol
  hold alike; the residual is 1.6 cm up / 1.7 cm toward the body, i.e. the whole-hand centroid versus its palm surface.
- Captures (`captures-rifle/`, `contact-sheet-rifle.jpg`): `rifle_hold` and `rifle_carry` at `cam_rifle_aim`,
  `cam_rifle_side`, `cam_rifle_carry`. Hold: both hands on the rifle, receiver at the hands, stock at the shoulder,
  muzzle forward. Carry: lowered one-hand carry at the hip (the 334 clip's left hand sits by the chest, 0.47 m above the
  grip — the clip's own pose, not a mount error). The main sheet (`contact-sheet.jpg`) was re-shot after the re-tune.
- Edit Mode after the re-tune: **254 / 254 pass** (`editmode.xml`, the other agents' earlier failures fixed by them).

## Verification

All in batch mode under the shared Unity lock; **no player build and no native run** (the orchestrator's combined batch).

- **Install** (`MainCharacterInstall.InstallBatch`, -nographics, rc 0, `unity/evidence/next-level/20261002/character/
  install.json` + `install.log`): every step logged; normalisation measured 1.800 m / soles 0.000 m after the fix;
  retarget 24 bones for all 12 lib clips; pistol under `RightHand`; hold clips built (pistol_hold at 3.59 s, rifle_hold
  at 1.46 s, rifle_carry at 2.60 s); view model + FP hands v2; 6 pistol mods on the held pistol; rifle (29,785 tris,
  scale 0.4728) and vest installed; idle → lib_idle_252; footsteps rebuilt.
- **Check** (`CheckBatch`, -nographics, **pass**, `check.json`): scene loads; visual is a `MeshyPlayer.prefab` instance
  with mesh `lo.003` from `colonist.glb`, 59,999 triangles, 48,075 vertices, 24 bones (all expected names); material
  `PlayerMainChar` (glTF-pbrMetallicRoughness) with base 2048² BC7, normal 4096² BC7, metallic/roughness 2048² BC7;
  shadows on, layer 8; actor idle/talk `lib_idle_252`, walk/run from the GLB (legacy), five jump clips; sampled idle
  height 1.800 m, soles 0.000 m, max bone motion in the idle 10.5°; `PlayerCombat.heldPistol/heldRifle` under the new
  `RightHand`, both muzzles, third-person flash and `WeaponModVisuals` (6 mods); `PlayerWeaponPose` mixRoot Spine02,
  spine Spine02/Spine01/Spine, rightHand, pistol_hold/rifle_hold/rifle_carry all binding 24/24 paths; vest under
  `Spine` via `PlayerArmourVisuals`; footstep feet on the new rig; first-person view model with `FP hands v2`; shadow
  proxy under the visual; all seven review cameras present; **no missing references** on the player hierarchy or the
  view model.
- **Hold poses** (`DebugHoldBatch`, `debughold-log.txt`): hands in the visual's frame, both arms posed by every hold
  (rifle_hold left 1.47 m / right 1.45 m, pistol_hold 1.52 / 1.59 m, rifle_carry 1.11 / 1.08 m; idle 1.03 / 1.00 m).
- **Editor captures** (`CaptureBatch`, graphics batch, 6 cameras at 13:00, 1600×900, `captures/`, `contact-sheet.jpg`):
  01 idle three-quarter, 02 face, 03 pistol carry (back-right quarter, muzzle-down in the right hand), 04 rifle hold
  (front-left quarter, both hands on the rifle, cheek to the stock), 05 vest front, 06 idle at `cam_checkpoint_player`.
  Two earlier rounds are kept as `captures-round1/contact-sheet-round1.jpg`: they showed the body in the idle while the
  bones were posed (no player-loop tick between a pose change and `Camera.Render` in a batch method, so the skinned
  mesh kept its last matrices) and a cyan cast from the Berms muzzle-flash point light, lit in edit mode. The final
  capture renders a CPU-baked copy of the body per shot and switches that light off; neither affects the game.
- **Edit Mode tests** (first run after the install, before the grip re-tune): **245 / 249 pass**; after the re-tune
  **254 / 254** (`editmode.xml`, current). The suite grew from 207 with the
  parallel agents' tests; the four failures are theirs, none touch the player:
  `CombatBalanceTests.CharacterSkillsNarrowTheConeThroughTheSharedPipeline` and
  `CombatBalanceTests.SavedPrefabsAreNormalForTheStarterAndEasyForTheRifleColonist` (both also fail in the combat
  agent's own run, `unity/evidence/next-level/20261002/combat/editmode-1.xml`, 247/249),
  `GameplayV2FixesTests.EveryItemHasItsOwnIllustration` (`ironclad-plate.png` missing) and
  `ShopSellTests.CatalogSellRulesFollowRarityAndKind` (`ironclad_plate`), both from catalogue data landing in the shared
  tree. Every character/motion/feel/FP-hands/pack/checkpoint test passes
  (`CharacterMotionAssetTests`, `CharacterFeelTests`, `FPHandsV2Tests`, `PackPanelTests`, …).
- **Not verified:** native player (movement, jump, walk/run foot sliding at the new stride, aim/carry blending in play,
  first-person hiding, the inventory character preview, the Berms loop), performance of the 60k-triangle body and the
  4k normal, texture streaming/memory, Carl's acceptance of the look. The combined batch should include a walk/run and
  a pistol/rifle draw at `cam_character_*` and `cam_rifle_*`.

## Known defects and not verified

- The rig has no finger bones (as before): both weapons sit in an open hand. Grips re-tuned on this rig (section
  above); a residual ~2 cm between the whole-hand centroid and the grip remains, judged by eye from the captures only.
- Walk/run are Meshy's basic clips on this rig (1.07 s / 0.67 s cycles); stride speeds were kept at 1.6 / 4.1176 m/s.
  Foot sliding at 3.4 / 6.0 m/s is not measured until the native batch; retune `walkStrideSpeed/runStrideSpeed` on the
  prefab if the feet slide.
- Talk = the breathing idle (as for the previous colonist). No facial animation; the source has no blendshapes.
- LOD1 (15k) exported but not installed (see above). The body is 59,999 triangles at every distance; the first-person
  view hides it as before. Cost not measured here.
- `Player_draw_222`, `idle_243`, `turnl_576`, `turnr_586` are still the 27 Sep rig's clips (retargeted by bind-pose
  deltas); only `lib_idle_252` and the weapon holds are used in game.
- The 4k baked normal map carries the decimation's edge detail; at 0.1 ratio, seams on the suit's collar/belt are where
  to look first in the native close-ups. Base colour and metallic/roughness are the delivered 2048 px maps.
- `FPHandsGlow.mat` gained the `_EMISSION` valid keyword from the grip pass re-running (keyword validation, same look).
- `PistolModsInstall.Install` rewrites `unity/evidence/rendering/20260930/pistol-mods-install.json` when it runs; the
  30 Sep file was restored from git and this pass's copy is `unity/evidence/next-level/20261002/character/
  pistol-mods-install.json`.
- The rifle was mounted by the combat agent's current `RifleArmourInstall.cs` (its log line reads "muzzle + (explicit
  MuzzleSign 1 …)", i.e. the rifle-backwards fix), so the two passes are consistent on the new rig; if that file changes
  again, re-run `InstallBatch` (or just `RifleArmourInstall.InstallAll`) once more.
- No salvage-NPC model was delivered (brief); not this agent's task.
- `AGENTS.md` §3 "Player" row still describes the mpc colonist; suggested row text: "Carl's main character
  (`meshy/main-char-20261002`, 2 Oct 2026): 60k-triangle LOD0 of the 595k source with a 4k baked normal, Meshy rig on
  the same 24 bones, library idle 252 + Meshy walk/run; mpc colonist recoverable via `tools/prepare_meshy.py`. Not yet
  accepted by Carl." Left for the orchestrator (shared file).
