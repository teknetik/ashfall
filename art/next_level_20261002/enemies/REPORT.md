# Next-level enemies pass — report (2 October 2026, enemies agent)

Carl: "3 more enemy droids for the outer berms. scatter a few more places, POI and encounter, loot crates and rewards.
There are higher level droids and once the player finds these comfortable to take on its a sign they should progress to
the next area. they would need good weapons not starter guns and a full set of basic Armour."
Corrections (via the coordinator): the Post Sentinel "was supposed to have a wheel to move around" (a rolling droid), and
the delivered "Ironclad Warden" GLB (a bearded human with a holstered pistol) **is Carl's new model for Brann, the salvage
NPC**, not an enemy. So the pass delivers **two** new droids, four POIs, and Brann on the new body; the hostile Ironclad
Warden built first is retired but recoverable.

## Follow-up (evening): Ironclad retired, Brann rebuilt

- `Prefabs/OuterBerms/FeralIroncladWarden.prefab` and `Prefabs/OuterBerms/Visuals/IroncladWardenVisual.prefab` moved
  (GUIDs kept, setup intact: FeralDroid, Health 760 / armour 24, DroidThreat L4/110, LootSource) to
  `Prefabs/OuterBerms/Retired/` and `Prefabs/OuterBerms/Visuals/Retired/` by the `droids` step (`RetireWarden`). Nothing
  live references them: `loot_ironclad_warden` is removed from `WardCrafting`, `ironclad_plate` from the catalog, its USS
  rule and icon, and from the strongbox table (two parts guaranteed now); the `visuals` step builds the Reaper only.
- POIs re-laid (`layout_nextlevel.py`, 0 problems): "Ironclad camp" is now **Fans camp** (id, landmark
  `nextlevel_ironclad_camp` and the two cameras kept; encounter "Camp holdouts" = Scrap Reaper + Post Sentinel); the
  Southern cache guard is two Reapers + a Sentinel. Crates and dressing unchanged.
- **Brann** (`brann` step, `NextLevelEnemiesInstall.Brann`): `Prefabs/SalvageDealer.prefab` rebuilt **in place** (same GUID
  and root objects, so the scene instance under `npc_brann`, the dialogue id, prompt, counter position at (−20.65, 0.5,
  15.7), routes and `ActorLookAt` wiring are untouched). Visual = the delivered rig at 1.80 m at the soles (uniform 1.059),
  holstered pistol as modelled; clips idle (procedural breathing) / **talk** (new procedural counter talk: nods, right-hand
  explaining gesture, weight shift, 4 s loop) / walk / run (delivered, 1.36 and 4.52 m/s strides) on a legacy `Animation`
  driven by `ActorAnimation`; `ActorLookAt` head `head`, neck `neck_01`; material `NL_IroncladWarden`; rendering layer
  mask 129 (the interior lighting layer the scene instance used to override on the old renderer); culling bounds = all-clip
  envelope + 24 %. Previous model kept: `Prefabs/Retired/SalvageDealer_hauler_20261001.prefab` (copied once, never overwritten).
- `cam_nextlevel_brann`: player-height camera 2.3 m in front of the counter looking at his face (installed with the POI
  cameras); captured with the existing `cam_ss_counter`.
- Verify (-nographics) adds: no live Ironclad prefab, retired prefab present, retired table/item absent, Brann on the
  11,358-tri rig with four distinct clips resolving on the rig, look-at wired, backup present, scene instance found.

## Fix round nl2 (2 Oct, evening; evidence `unity/evidence/next-level/20261002/nl2/`, build `unity/AthenHill/Builds/batch-nl2`)

From the first native batch (`nl1`): the Reaper den took 112 shots / 5 knock-downs, two mixed sites 0 kills; gunners stacked
to 0.68 m while aiming; the check lost crates to "pack full" and to the player being elsewhere.

### 1. Balance (what changed and why)

- **Precision barrel** `mod_rifle_precision_barrel`: armour penetration **+4 → +8** (shared `WardCrafting` edit, applied by
  `apply_data.py`, re-runnable). The outer droids' flat armour is now a *rifle-with-mod* problem: the modded rifle (pen 16)
  lands its full 28.4 a shot on armour 14; the starter pistol (pen 0) lands 20.
- **Scrap Reaper**: 420 → **400 HP**, armour 16 → **14**, strike 24 → **18** (7.2 on the full kit, 14 on the bare vest),
  wind-up 0.45 → **0.6 s**, recover 0.7 → 0.9, chase 5.4 → **4.6 m/s**, stagger threshold 90 → **60** (immunity 1.4 s),
  repair 10/s, separation 1.8 m.
- **Post Sentinel**: 520 → **560 HP**, armour 14, bolts **3 × 16 at 0.25 s** (was 4 × 16 at 0.15), tell 1.0 → **1.2 s**,
  lead 0.5 → **0.35**, spread 1.3 → **2.0°**, bolt speed 34, volley pause 2.0–3.2 s, repair 6/s, separation 2.4 m.
- Gunner/lancer prefabs: `separation` 2.4 m (one field, set by the `droids` step); worker/drone/Foreman unchanged.

| Droid | HP | Armour | Modded rifle (pen 16) per hit → hits | Pistol (pen 0) per shot → shots (one charge = 11) | Hit on bare + field vest / on the full kit |
| --- | --- | --- | --- | --- | --- |
| Scrap Reaper (L3, 60 xp) | 400 | 14 | 28.4 → **14.1** | 20 → 20 (≈ 8 s under the nano cap) | 14.2 / 7.2 per strike, 0.6 s tell |
| Post Sentinel (L3, 70 xp) | 560 | 14 | 28.4 → **19.7** | 20 → 28 | 37 / 16 per 3-bolt volley every ~4.5 s |

Starter kit (pistol + field vest, 100 vitality) still loses: three Reapers strike for 43 per cycle while the pistol needs
~8 s per Reaper; a sentinel pair lands 74 per volley pair. `NextLevelEnemiesTests` asserts hits-to-kill 13–22 per droid
with the modded rifle and a pistol charge under 60 % of each droid's vitality, reading the barrel's penetration from the
catalog.

**Native result (fixture: field rifle + precision barrel, Rifle 20, plate carrier + helmet + armguards + gloves + leggings +
boots; QA fighter standing at engage range, kiting only on a melee tell, side-stepping sentinel tells), `nl2/enemies/report.json`
(`balance`), build `batch-nl2`:**

| POI | Droids | Kills | Rifle shots (real F) | Seconds | Knock-downs |
| --- | --- | --- | --- | --- | --- |
| Post relay | 2 Sentinels | 2/2 | 105 | 65 | 0 |
| Reaper den | 3 Reapers | 3/3 | 45 | 25 | 0 |
| Fans camp | Reaper + Sentinel | 2/2 | 73 | 41 | 0 |
| Southern cache | 2 Reapers + Sentinel | 3/3 | 64 | 37 | 0 |

(nl1 on the same fixture: 112 shots / 5 downs for the den, 0 kills at both mixed sites.) Shots include misses on moving
targets; Reapers die in about 15 hits, sentinels in about 20 as targeted. An earlier nl2 run with a looser kite still saw
one knock-down at the camp (`enemies-3`); the final run had none.

### 2. Gunner stacking (`FeralDroid.cs`)

Droid-to-droid separation is now a push of its own inside `Steer` (not a steering direction scaled by travel speed), so it
also acts while a droid stands, aims or fires; `Alert` now calls `Steer` with zero speed so alerted droids spread; each
ranged droid holds its own band and side of the player (`preferredRange ± 1.5 m`, a 2 m lateral offset by its flank side).
New serialized field `separation` (1.6 m default, 2.4 m on gunners, lancers and sentinels).
`unity/tools/check_gunner_separation.py` (combat agent's file, one-line fix: the final approach uses
`goto('relay_knoll_approach')` + a short walk instead of a 200 m `walk_to`): **PASS 8/8**, pairwise separation ≥ 1.5 m over
20 s, nest fought and XP toast seen (`nl2/gunners/report.json`).

### 3. `check_next_level_enemies.py`

Fixture carries only two medkits (room for drops); fight loop counts knock-downs per site (a result, reported in
`balance`; zero kills is the failure), waits at the landmark for a parked/re-forming cluster instead of returning early,
kites only on a melee wind-up (bounded) and side-steps sentinel tells, regroups via the landmark; after the fight it goes
back to the landmark, collects the nearest wreck's cache and walks to each crate with waypoint detours, accepting only
that crate's own prompt (crate prompts are now unique per site; a neighbour's "Emptied" countdown is not a match); a search
passes when the pack changes or the Field Pack note names loot left in the cache beside it; "a strongbox yields a part" is
checked across every strongbox searched. Layout: the Post relay's cart/sack line moved off the approach side; Fans camp's
QA landmark/approach moved to its open north-west side (the long wall faced the gate).
Final run: **NEXT LEVEL ENEMIES PASS (42 checks, 0 failures)**, no runtime exceptions (`nl2/enemies.out`, `nl2/enemies/`;
earlier attempts kept as `enemies-1..4`).

### Verification of the round

`InstallAll` verify 0 problems (`nl2/install.log`, `install-3/4.log`), dev build `nl2/build.log` → `Builds/batch-nl2`
(rebuilt twice for the scene re-lays), Edit Mode **255/255** (`nl2/run.log`; a final run after the last re-lay is in
`nl2/editmode-final.summary`), native enemies check PASS, gunner separation PASS.

## What changed

### Runtime (`Assets/AthenHill/Scripts/Combat/FeralDroid.cs`, owned by this pass)

- `DroidKind.Wheeled`: ground-steered like a walker (same Steer/Blocked/SnapToGround), `wheel` transform spun by the ground
  speed (`wheelRadius`), the visual child leans into turns (`leanPerTurnRate`) and pitches with acceleration
  (`pitchPerAccel`, `maxLean`), a small bob; dies with the hover droids' physics topple (Rigidbody, `wreckMaxTravel`), so a
  wheeled wreck falls over and its cache drops where it settles.
- `armour` / `armourMinFraction`: a flat amount off every hit after the player's weapon `armourPenetration`, never below
  25 % of the hit. `FeralDroid.MitigatedDamage(incoming, armour, penetration, minFraction)` is static for the combat
  agent's `DroidThreat.Tier` rule. Existing droids keep armour 0 (unchanged balance).
- Nothing else in `FeralDroid` changed for Brann: he is an `ActorAnimation` NPC, not a droid.

### Assets

- `meshy/next-level-enemies-20261002/` (manifest README, `inspect_models.py`, `prep_models.py`, `review_clips.py`,
  `review_side.py`, `handoff.json`, renders): geometry GLBs (WEIGHTS_0 renormalised, extra joint sets dropped for glTFast),
  URP Lit texture sets (BaseMap / Normal / Mask), walk + run from the delivered clips, **procedural** idle / attack / hit /
  death authored in numpy on the rest pose (`renders/sheet_review_*.png`), the sentinel body/wheel split with `Muzzle`, `Head`, `Hat`.
- `Assets/AthenHill/Art/OuterBerms/NextLevel/` (Models, Source clips, Clips/<Name>/*.anim legacy clips lifted to the
  ground like the gunner pass, Materials `NL_*` incl. `NL_OpticGlow`, Textures BC7 streamed).
- Visual prefabs `Prefabs/OuterBerms/Visuals/{ScrapReaper,IroncladWarden,PostSentinel}Visual.prefab` (uniform scale from the
  standing idle: Reaper 2.05 m, Warden 1.90 m, Sentinel 1.89 m as delivered; culling bounds = all-clip envelope + 24 %).
- Gameplay prefabs `Prefabs/OuterBerms/FeralScrapReaper.prefab` (9,341 tris) and `FeralPostSentinel.prefab` (9,376)
  (the Ironclad Warden prefab is retired, above): `Health`, `FeralDroid`, `LootSource`, `DroidThreat`, capsule + kinematic Rigidbody,
  sparks/smoke/foot-dust copies and the worker's alert/strike/hit/death clips, an emissive "Optic glow" lens at the head
  front (the telegraph) and the optic light, a fresh `Voice` AudioSource (not an instantiated template root). `DroidBolt_Sentinel.prefab` (copy of the gunner bolt).
- `DroidThreat` added to the five earlier prefabs: worker L1/12 xp, scrap drone L1/8, gunner L2/25, lancer L2/30, Foreman L3/150.
- `FixNestedDroids` (part of the droids step): removes a whole droid nested inside the gunner/lancer prefabs if present
  (Carl's "gunners attached to other droids": `BermsExpanseInstall.Droids` instantiated the worker *root* to copy its voice).
  On this run both were already clean (rebuilt earlier today by another pass); the fix stays as an idempotent guard.

### Data (re-runnable: `art/next_level_20261002/enemies/apply_data.py`, then the Editor `loot` step)

- `CityCatalog`: `reaper_blade`, `sentinel_optic` (`ironclad_plate` retired with the Warden) — Rare, `excludeFromTrade` (the catalog rule in
  `ShopSellTests` requires Rare parts to be trade-excluded, so they are crafting rewards, not credits; sell prices are
  recorded for a future parts counter), tags `component`, `component:<blade|optic_targeting>`, `tier:3`, `nextlevel`,
  icons `UI/Art/{reaper-blade,sentinel-optic}.png` (Codex image generation, `icons/prompts.json`) with rules
  appended to `UI/CityHUD.uss`.
- `WardCrafting` loot tables: `loot_scrap_reaper`, `loot_post_sentinel` (each with its part at 45–55 % and pity 2), `loot_nextlevel_crate` (alloy, nanites, capacitors, actuators, shards, medkits, wound coils),
  `loot_nextlevel_strongbox` (both parts **guaranteed until first collected**, then 50 % with pity 3, plus shards,
  actuators, charge-cell cores, medkits, capacitors). No new recipes (none of the existing ones fit); the parts carry
  component tags for later crafting data.
- `WardFieldOrders.freePlayObjective`: one sentence pointing at the far caches and the kit they need (no new field orders).

### Scene (`Outer Berms/Next level sites`, installer `AthenHill.Editor.NextLevelEnemiesInstall`)

Four POIs in the outer third of the bowl (`layout_nextlevel.py` → `sites.json`, validated against the expansion
heightfield: inside the floor, slope, ≥ 60 m from every expansion site, ≥ 25 m from the trail cairns, 0 problems; four
scatter rocks inside prop footprints are parked and listed in `unity/evidence/next-level/20261002/enemies/parked-scatter.json`):

| POI | Centre | Gate distance | Encounter | Loot crates | Landmark / cameras |
| --- | --- | --- | --- | --- | --- |
| Post relay | (−432, 22) | 375 m | 2 Post sentinels on patrol (a roaming pair over the cache) | Dead-letter strongbox, Courier cache | `nextlevel_post_relay`, `cam_nextlevel_post_relay`, `cam_nextlevel_sentinel_close` |
| Reaper den | (−242, 142) | 232 m | 3 Scrap Reapers | Stripped cargo strongbox, Reaper cache (+ a scrap heap) | `nextlevel_reaper_den`, `cam_nextlevel_reaper_den` |
| Fans camp (id `ironclad_camp`) | (−492, −108) | 447 m | Scrap Reaper + Post Sentinel | Caravan strongbox, Camp arms crate | `nextlevel_ironclad_camp`, `cam_nextlevel_ironclad_camp`, `cam_nextlevel_ironclad_close` |
| Southern cache | (−252, −152) | 247 m | 2 Scrap Reapers + Post Sentinel | Pump-house strongbox, Buried arms crate, Spare-parts crate (+ a heap) | `nextlevel_southern_cache`, `cam_nextlevel_southern_cache` |

68 kit props (street dressing / West Gate / depot / training range / rooftops / perimeter walls), 9 loot crates (kit crates
with a `SalvageHeapNode` search on the lid: "E · Force the strongbox", 2 s, 600 s respawn), 2 scrap heaps, 10 spawns,
`DroidEncounter` activateWithin 75 / parkBeyond 170 / respawn 600 s (90 m clearance, 30 s away) / pack 22 m,
`BermsCompassPoint` per site, QA landmarks 22 m toward the gate on clear ground, 6 review cameras at 1.6–1.7 m plus
`cam_nextlevel_brann`. Parked scatter is recorded by path and position (`parked-scatter.json`) so re-runs restore it.
Shared test file `GameplayV2SceneTests` got two commented one-line exclusions (encounters and heaps under "Next level sites").

## Stats and the reasoning (first-pass numbers; superseded by the nl2 table above)

Player at the fixture: 100 vitality (50 + endurance 10 × 5); armour model `incoming × (1 − resistance) − armour × 0.2`.
Starter kit: pistol 34 dmg, 11 shots per charge then 3.3 shots/s on regen; no armour.
Target kit: field rifle 27 × 1.05 = 28.4 dmg, 12-shot bursts then 3.75 shots/s, penetration 8 + 4 (precision barrel) = 12;
plate carrier 24 + helmet 4 + armguards 4 + gloves 2 + leggings 6 + boots 3 = **43 armour (8.6 absorbed per hit), 12 %
resistance**.

| Droid | HP | Armour | Attack | Pistol per shot / to kill | Modded rifle per shot / to kill | Hit on bare colonist / on the kit |
| --- | --- | --- | --- | --- | --- | --- |
| Scrap Reaper (L3, 60 xp) | 420 | 16 | 24 dmg strike, 0.45 s wind-up, chase 5.4 m/s, flank 0.5 | 18 / 24 shots (~8 s under the regen cap; it closes in 4 s) | 24.3 / 18 shots (one burst + 6) | 24 / 12.5 |
| (retired) Ironclad Warden (L4, 110 xp) | 760 | 24 | 30 dmg strike, slam 55 every 3rd; kept in Retired/ | 10 / 76 shots | 16.4 / 47 shots | 30 → 55 / 17.8 → 39.8 |
| Post Sentinel (L3, 70 xp) | 520 | 14 | 4 × 16 dmg bolts after a 1.0 s laser tell, 36 m/s (dodgeable), fires inside 40 m, holds 22 m, retreats inside 9 m, patrols 9 m at 2 m/s | 20 / 26 shots (~8 s while taking 64 per volley) | 26.4 / 20 shots (~5 s) | 64 per volley / 22 |

A pistol colonist with no armour loses: a Reaper pack of three strikes for 72 per cycle against 100 vitality while the pistol
needs 8 s per Reaper; two sentinels put 128 per volley on the bare colonist. With the rifle and the kit the same fights
are hard but fair: Reapers die in a burst and a half and sentinel volleys cost 22 behind the plates and can be sidestepped
on the laser tell. `NextLevelEnemiesTests` asserts the ratios on the prefabs (a full pistol charge is
under half of every new droid's vitality; a modded rifle burst does ≥ 1.3× the pistol charge).

## Verification

- `NextLevelEnemiesInstall.InstallAll` (`-nographics`, under the lock; steps import, visuals, droids [incl. retire + threat +
  nested-droid guard], loot, brann, install, verify; exit 2 when verify lists problems): **verify 0 problems** — 88 prefab
  instances, 0 broken links, 0 missing materials, 4 encounters wired to the player/session (10 spawns on the ground with
  head room, only level ≥ 3 droids), 11 salvage nodes incl. 9 loot crates on real tables, 4 landmarks, 7 cameras, no live
  Ironclad prefab / retired one present / retired table and item absent, Brann on the 11,358-tri rig with idle/talk/walk/run
  resolving on its bones, look-at wired, backup present, instance under `npc_brann`. Evidence in
  `unity/evidence/next-level/20261002/enemies/` (`import.json`, `visuals.json`, `droids.json`, `brann.json`, `install.json`,
  `verify.json`, `parked-scatter.json`, `run.log`, `install-*.log`).
- **Edit Mode tests: 255/255 passed** (`editmode.summary`, `editmode-3.out`): includes `NextLevelEnemiesTests` (armour rule,
  prefab ratios, threat levels on every droid, POIs/crates/landmarks, retired Ironclad + kept hauler, trade-excluded parts)
  and the earlier suites (`ShopSellTests`, `GameplayV2SceneTests`, `BermsExpanseTests` unchanged in counts).
- Editor captures (graphics, droid visuals stood at their spawns, never saved): `editor/contact-sheet.png` (six
  `cam_nextlevel_*` cameras after the re-lay) and `editor/contact-sheet-brann.png` (`cam_ss_counter`, `cam_nextlevel_brann`):
  Brann reads at the counter under the interior lamps, textured, beard/face/holster visible; the sentinel close camera still
  frames its droid at the edge.
- **Not verified**: no player build, no native run (programme rule). `unity/tools/check_next_level_enemies.py` (fixture save
  with rifle + precision barrel + the six armour pieces; per POI: activation, engagement, melee wind-up / sentinel bolts,
  kills with the rifle, a cache collected, every crate searched, the first strongbox part; no exceptions) is written for the
  orchestrator's batch and has **not been run**; it reads the POI data from `sites.json`, so the re-lay needs no script
  change. Brann's talk/walk clips on the new rig have only been judged in Blender renders, not in motion in the game.

## How to re-run

```
art/next_level_20261002/enemies/install.sh            # data patch, InstallAll (lock), capture + contact sheet
art/next_level_20261002/enemies/install.sh unity      # Editor install only (exit 2 = verify listed problems)
~/.local/state/ward-programme/unity.sh <log> AthenHill.Editor.NextLevelEnemiesInstall.VerifyAll -nographics -quit
uv run --offline --with pillow --with numpy python meshy/next-level-enemies-20261002/prep_models.py   # rebuild the clips/GLBs
uv run --offline --with numpy --with matplotlib python art/next_level_20261002/enemies/layout_nextlevel.py  # re-lay the POIs
ATHEN_NEXTLEVEL_EVIDENCE=<dir> DISPLAY=:0 uv run --offline --with python-xlib --with pillow python unity/tools/check_next_level_enemies.py
```

## Known defects and open points

- Procedural clips (Reaper attack/hit/death, Brann idle/talk): readable but stiff (no finger motion; Brann's gesture is a
  single right-hand raise; the Reaper death kneel is quick). About 17 Meshy credits per rig would buy API rigs + library
  clips (balance was 82) if judged necessary.
- Brann: the delivered rest pose stands arms-down, so idle/talk sit well behind the counter; his strike/hit sounds are
  irrelevant (NPC). His old hauler prefab is `Prefabs/Retired/SalvageDealer_hauler_20261001.prefab`; to roll back, copy it
  over `Prefabs/SalvageDealer.prefab` (same component layout) or move the `Retired` assets back.
- Sentinel: fires from the hip (rifle pointing down); the wheel split catches a sliver of the fork bottom inside the tyre
  cylinder (small protrusion at some wheel angles up close); no death clip, it topples by physics.
- The Reaper's glow telegraph is a lens sphere on the head front; its own red weapon lens is not emissive.
- Existing droids keep armour 0; `DroidThreat.Tier`, the bar tint and XP award are the combat agent's.
- Rewards are parts and consumables, not credits (Rare items are trade-excluded by the catalog rules). A parts counter at
  Brann is a natural follow-up with the inventory redesign.
- A re-run of `BermsExpanseInstall.Droids` would re-create the nested-droid bug in the gunner/lancer prefabs; re-run this
  pass's `droids` step afterwards (it removes them again). `BermsExpanseInstall.Install` does not touch this pass's root.
