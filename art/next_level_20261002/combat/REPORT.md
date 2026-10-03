# Combat agent report, Ward "next level" programme, 2 October 2026

Scope: rifle orientation, weapon ranges/accuracy, enemy threat tiers and XP, trade sound, music default, the
"gunners attached to other droids" bug, and the salvage NPC model (not delivered). Evidence in
`unity/evidence/next-level/20261002/combat/`. Nothing here was built or run in the native player: verification is
Edit Mode tests (`-nographics`), the `-nographics` install/verify batch and one graphics editor capture (4 cameras).

## 1. Rifle backwards — fixed (explicit muzzle end, guarded)

Cause: `RifleArmourInstall.Rifle()` picked the muzzle as the thinner of the two 12 % end sections of the mesh. On the
Meshy field rifle the front end carries the gas block and folded bipod (12 % section 0.412) and the stock end is
thinner (0.337), so the heuristic mounted the rifle stock-forward and put `rifleMuzzle` at the butt: the tracer left
the stock and crossed the colonist.

Measured: Blender orthographic renders of `Art/Weapons/FieldRifle/FieldRifle.glb`
(`rifle-mesh/side_from_-Y.png`, `top.png`, `end_from_±X.png`; script `render_rifle.py`) and a numpy density profile
(`glb_axis.py`: barrel bins at 20–40 % from the glTF −X end hold 76–888 vertices with a 0.09–0.13 cross-section; the
receiver/magazine bins 1,900–7,100 vertices at 0.55–0.58) show the muzzle at glTF −X and the stock at +X. glTFast
inverts X on import, so the muzzle is at **+X in the imported mesh frame**.

Change: `RifleArmourInstall.MuzzleSign = +1` (explicit, with the measurement in the comment). `Rifle()` no longer
decides from the end sections; it asserts the setting against the mesh (the 20–40 % band from the muzzle end must be
less than half the same band from the butt: 0.176 vs 0.600) and throws instead of flipping if the mesh changes.
New batch entry `RifleArmourInstall.InstallRifleBatch` (opens the scene, re-runs `Rifle()` only, saves). The pistol
holder, muzzle, vest, bindings, cameras and landmarks are untouched. `PlayerCombat` fallback `range` 70 → 30 and a
new `spread` fallback of 4 (used only when no loadout is bound) were also written to the scene instance.

Proof (`editor-1/`, graphics batch, colonist posed in `rifle_hold` at `RifleArmourInstall.Stand`, red sphere at
`PlayerCombat.rifleMuzzle`, cyan line 1.2 m along the holder's forward, white sphere at the butt):
`cam_rifle_aim.png`, `cam_rifle_side.png`, `cam_rifle_carry.png`, `cam_rifle_muzzle.png`. The barrel, gas block and
bipod are at the front, the stock at the shoulder, the muzzle point on the barrel tip, 0.54 m ahead of the grip
(`verify.txt`: "muzzle point z 0.540", "thin barrel band in front (0.083 m) and the receiver behind (0.284 m)").

Known defect (not mine to fix in this pass): the character agent replaced the player rig at 16:2x and re-ran the
rifle mount on it; in the captures the rifle sits about 10 cm above the hands (grip/hold offsets `GripAlong`,
`GripFromButt`, `GripFromBottom` were tuned on the old rig). Re-tune on the new rig and re-run `InstallRifleBatch`
(the muzzle end is now fixed whatever the mount offsets are).

## 2. Ranges and accuracy

New `Scripts/Combat/WeaponBallistics.cs` (pure maths, tested):

- **Falloff**: full damage to 60 % of the range stat, linear taper to 35 % at the range stat; the hit scan still stops
  at the range stat. Pistol 30 m → full to 18 m; rifle 95 m → full to 57 m. `PlayerCombat.Fire` applies it on the
  distance from the colonist to the hit (`LastHitDamage`, `LastHitDistance` exposed for QA).
- **Cone** = spread × (1 − accuracy/100) × 0.5 while aiming (RMB) × 1.6 while moving faster than 0.6 m/s.
- **Accuracy** (0..100) = weapon base + character `accuracy` derived stat (perception) + weapon skill × 0.25, through
  `WeaponStatPipeline.ApplyCharacter(stats, character, weaponId)`; the skill is found from the weapon id
  (`weapon_scrap_pistol` → `pistol`, `weapon_field_rifle` → `rifle`). The catalog was **not** patched: its skills
  already carry attribute dependencies (pistol 20 + perception/agility/intellect = 30 at start, rifle 10) and are
  in the calculated stat table, so no new derived stats were needed.
- **Droid armour**: flat points per hit minus the weapon's `armourPenetration`, never below 20 % of the hit
  (`DroidThreat.armour`; workers/drones 0, gunners/lancers 2, Foreman 4).
- Aim assist is unchanged in code; it already limits itself to the weapon's range stat, so the pistol's assist now
  stops at 30 m and the rifle's at 95 m.

Data (`art/next_level_20261002/combat/apply_data.py`, idempotent text patch on `WardCrafting.asset`, re-runnable
after Codex lands):

| Weapon | range | spread | accuracy (base) | effective at start (L1) | hip / aim cone |
| --- | --- | --- | --- | --- | --- |
| Scrap pistol | 70 → **30 m** | 0 → **4°** | 0 | 17.5 (10 perception + 30 pistol × 0.25) | 3.3° / 1.65° |
| Field rifle | 100 → **95 m** | 1.2 → **1.8°** | 82 → **20** | 32.5 (20 + 10 + 10 rifle × 0.25) | 1.2° / 0.61° |

Mods: bored alloy barrel range +10 → **+6 m** and **−10 % spread**; lattice-focused barrel +25 → **+12 m** and
**−20 % spread**; rifle precision barrel unchanged (+8 accuracy, −25 % spread, +15 m). Stat labels **Accuracy**
(format 0) and **Spread** (0.0°, lower is better) added, so the Fabricator table and pack tooltips list them.
Existing tests updated for the new numbers (`WeaponLoadoutTests`, `RecipeChainTests`).

## 3. Threat tier and experience

`Scripts/Combat/DroidThreat.cs` (stub replaced, signatures kept, `armour` field added):

- `threat = (player time-to-kill ÷ droid time-to-down) × 1.5^(droid level − player level)` (level difference clamped
  to ±4). Time-to-kill: damage per hit at the typical engagement range (melee 10 m, ranged droids their preferred
  range, capped by the weapon range) with falloff, expected crits and droid armour; the aiming cone's chance to land
  on a 0.35 m half-width droid; shots × fire interval, a nano refill wait when the magazine cannot cover them, plus
  0.5 s to acquire. Time-to-down: the player's max health over the droid's DPS after
  `PlayerCombat.ComputePhysicalDamage` (melee strike cycle, slams averaged in for elites; ranged burst × bolt damage
  × 0.7 hit fraction over wind-up + burst + mean pause).
- **Easy (grey, 0 XP) below 0.04; Danger (red, 1.75× XP) from 0.25; Normal (green, 1× XP) between.** Calibrated
  (`CombatBalanceTests.SavedPrefabsAreNormalForTheStarterAndEasyForTheRifleColonist`, real prefabs and catalogs):
  the level-1 colonist with the scrap pistol and field vest sees workers, drones, gunners and lancers as Normal and
  the Foreman / an armoured level-3 droid as Danger; at level 3 with the field rifle and plate carrier the four depot
  droids are Easy and the Foreman/outer droids Normal — "comfortable means move on".
- `PlayerCombat.AwardKill`: on a kill by the player's shot, `DroidThreat.Tier` at kill time, `AwardFor(experience,
  tier)` → `CharacterModel.GrantExperience`; `ExperienceAwarded(amount, tier, levelled)` event, `Kills`,
  `ExperienceEarned`, `LastKillTier` counters. Experience/level persist through the existing character state.
- `CombatHud`: enemy bars tinted per droid (fill, top edge and name label; classes `tier-easy|normal|danger` on the
  bar, inline colours so `CityHUD.uss` is untouched), re-evaluated every 0.75 s and whenever the weapon stats change
  (weapon switch, mod fitted). The salvage toast is reused as an **EXPERIENCE** toast: "+18 XP · Feral gunner droid"
  (cyan; amber on Danger), "Easy target · no XP" (muted), "Level 2 · 2 attribute, 10 skill points" with a Ward
  notice on level-up, else "Level 1 · 36 / 100 XP".
- Prefab values (`CombatNextLevelPass.Threat`, added only where missing; the enemies agent's own values are kept):
  worker L1 10 XP, scrap drone L1 8 XP, gunner L2 18 XP armour 2, lancer L2 16 XP armour 2, Depot Foreman (variant)
  L2 40 XP armour 4. The enemies agent had not added the component at run time (16:32 and 16:50).

## 4. Trade sound

`Audio/UI/trade-click.wav`: 34 ms synthesized digital click (`make_trade_click.py`, numpy, deterministic; 1.2 ms
transient through a 2.6 kHz resonance + a soft 1.9 kHz blip at −14 dB), 48 kHz mono, peak −14 dBFS, RMS −34 dBFS,
imported PCM without normalization. `CityAudio.tradeConfirm` re-pointed in the scene by `CombatNextLevelPass.Trade`;
the ElevenLabs `trade-confirm.wav` (0.88 s, −20 LUFS, the "bell") stays for rollback. Documented in `unity/AUDIO.md`.
Not heard in the player (no native run): the orchestrator's city loop exercises a buy and a sell.

## 5. Music

`Audio/Music/Oasis of Ruins.mp3` (copy of the delivered file, SHA-256 `4be69277…85dfc`, streaming Vorbis 0.85 like the
8 Sep tracks) is `musicPlaylist[0]`, then Dust of the Giants, Dust of Alshain (`CombatNextLevelPass.Music`).
`CityAudio.Start` plays `musicPlaylist[0]` on every scene load and advances in order with the 3 s crossfade; the
track index is not saved, so the new track plays first on a new game and on Continue. Documented in `unity/AUDIO.md`.

## 6. "Gunners attached to the other droids" — cause found and fixed in the prefabs

`FeralGunnerDroid.prefab` carried a complete, **active** `FeralWorkerDroid` child (its own `FeralDroid` "Feral worker
droid", `Health`, capsule collider, rigidbody, `LootSource`, AudioSource and the whole worker model), and
`FeralLancerDrone.prefab` an active `FeralScrapDrone` child in the same way — leftovers of building the ranged droids
on top of the melee ones. Every gunner therefore spawned with a worker droid welded to it (same transform), its
collider caught the player's shots (damage went to the inert nested Health), its Health registered as an aim-assist
target, and the nested `FeralDroid` appeared in `FeralDroid.Active` (QA snapshots listed five droids at the nest).
The relay-knoll spawn points themselves are 9.6–13 m apart, so spacing was not the cause.

`CombatNextLevelPass.Gunners()`: the ranged droid's `voice` AudioSource lived on the nested body, so it is copied to
the root (`EditorUtility.CopySerialized`) and re-pointed, any other root reference into the nested body fails the
step, then the nested droid is destroyed and the prefab saved (gunner: 4 renderers removed; lancer: 10). Verified:
one `FeralDroid` and one `Health` per prefab, voice on the root, muzzle/animation references intact. Worker, scrap
drone and Foreman prefabs had no nested droid.

Real-input check for the orchestrator's batch: `unity/tools/check_gunner_separation.py` (rifle fixture save,
`goto relay_knoll_approach`, asserts exactly two gunners + one worker at the nest, pairwise separation ≥ 1.5 m over
20 s, no droid at another's position, bars visible when engaged, fights the nest with real F and expects the
"+N XP" toast; captures `knoll-approach`, `knoll-engaged-bars`, `knoll-after-fight`). Not run here.

## 7. Salvage NPC model

No new model was delivered in `meshy/incoming-20261002/`. Brann remains the Meshy salvage hauler
(`Prefabs/SalvageDealer.prefab`). Nothing was invented.

## Editor methods run (all under the shared lock; logs in the evidence folder)

1. `AthenHill.Editor.CombatNextLevelPass.RunBatch -nographics -quit --steps rifle,gunners,threat,trade,music,verify`
   (`install-1.log`, `batch-log.txt`, `rifle-install.txt`, `verify.txt`).
2. `… RunBatch -quit --steps threat,capture:<dir>:cam_rifle_aim+cam_rifle_side+cam_rifle_carry+cam_rifle_muzzle`
   (graphics, `capture-1.log`, `editor-1/`). Nothing saved by the capture step.
3. `… RunBatch -nographics -quit --steps threat,verify` (`threat-2.log`; Foreman variant override).
4. Edit Mode tests: `editmode.sh` → `editmode-4.{xml,log,summary}`: **254 tests, 251 passed, 1 failed** —
   `ShopSellTests.CatalogSellRulesFollowRarityAndKind` on `ironclad_plate`, an item the enemies agent added to
   `CityCatalog.asset` during this run (not from this pass). Runs 1–3 were my own failures (fixed) and a compile error
   in the character agent's `MainCharacterInstall.cs` at 16:32 (fixed by them).

Re-run order after other agents' work lands: `python3 art/next_level_20261002/combat/apply_data.py`, then
`RunBatch --steps rifle,gunners,threat,trade,music,verify`. `RifleArmourInstall.InstallRifleBatch` re-mounts the rifle
alone.

## Files

Runtime: `Scripts/Combat/WeaponBallistics.cs` (new), `Scripts/Combat/DroidThreat.cs`, `Scripts/Combat/PlayerCombat.cs`,
`Scripts/Combat/CombatHud.cs`, `Scripts/Crafting/WeaponLoadout.cs`. Editor: `Editor/RifleArmourInstall.cs`,
`Editor/CombatNextLevelPass.cs` (new). Tests: `Tests/Editor/CombatBalanceTests.cs` (new, 10 tests),
`WeaponLoadoutTests.cs`, `RecipeChainTests.cs`. Data: `Data/Crafting/WardCrafting.asset` (weapons, two barrel mods,
statLabels). Prefabs: `OuterBerms/FeralGunnerDroid`, `FeralLancerDrone` (nested droid removed, DroidThreat),
`FeralWorkerDroid`, `FeralScrapDrone`, `FeralDepotForeman` (DroidThreat). Scene: held rifle re-mounted, PlayerCombat
fallback, `tradeConfirm`, `musicPlaylist`. Audio: `Audio/UI/trade-click.wav` (+meta, folder meta),
`Audio/Music/Oasis of Ruins.mp3` (+meta). Docs: `unity/AUDIO.md`. Tools: `unity/tools/check_gunner_separation.py`.
Scripts here: `apply_data.py`, `make_trade_click.py`, `render_rifle.py`, `glb_axis.py`, `prefab_dump.py`,
`editmode.sh`, `install_batch.sh`, `capture_batch.sh`. No Codex-owned file was edited. No Meshy credits used.

## Not verified

- Native player: HUD bar tints, the XP toast and level-up notice, the click and the music in the mix, the gunner
  separation after the fix, the rifle hold in motion (`check_gunner_separation.py` and the city loop cover the first
  four in the orchestrator's batch).
- Balance in play: the tier thresholds are calibrated on paper from the saved prefabs; the enemies agent's new droids
  need `DroidThreat` values (level, experience, armour) to be rated, else they default to L1 / 10 XP / 0 armour.
- The rifle hold offsets on the new player rig (see §1).
