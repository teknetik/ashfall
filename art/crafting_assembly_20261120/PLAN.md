# Crafting rework: identification, skills, tools, durability and hands-on assembly

Written 20 November 2026 with Carl. This is the plan; nothing in it is built yet. Each phase below is
self-contained so a different agent or model can pick it up. Read [AGENTS.md](../../AGENTS.md) first
(machine limits, batched verification, Ashfall Kanban board: pass `board="Ashfall"` on every card).

## Why

The first pistol upgrade (Stabilised Pistol Grip, Ossa's *Steady Hands* order) is a progress bar:
picking up a Damaged Servo auto-teaches the schematic, Brann's bench runs an 8 s timer on
1 servo + 2 scrap alloy + 5 tier-1 nanites, and the grip gives recoil −7 (38 → 31). There is no
decision, no physical process, no skill or tool in play and nothing ever wears out.

## Decisions (Carl, 20 Nov 2026)

1. **Identification through people.** Salvage is not self-explaining. You show it to someone who knows
   (Ossa for weapons/armour; later Brann for machines, Tamsin for packs) and they tell you what it
   could become. Ossa's line for the servo: it can be sold or built into guns and armour, "that's how
   it works around here, we salvage what we can"; she looks closer, thinks it would make a pistol
   upgrade, and sends you to Brann.
2. **Skills grow mostly from XP (skill points spent), a little from use.** Crafting steps give small
   use gains in the skill they exercise; the bulk comes from levelling.
3. **Tools are required.** A carried Field Toolkit (screwdriver first) for basic work; later upgrades
   need fixed bench tools that cannot be carried.
4. **Field repair in a pinch.** The Field Toolkit can restore some durability to a weapon in the field,
   less each time, until the weapon is broken for good and needs a bench overhaul.
5. **Physical assembly.** Parts are real 3D models laid on the bench, stacked, seated and screwed
   together. Crafting becomes a small mini-game.
6. **Asset method.** Assembly parts are modelled part by part in Blender Python following
   [AnyMachine](https://github.com/apekshik/anymachine) (MIT) `PIPELINE.md` part 2, not Meshy
   (Meshy fuses parts into one mesh).

## Where things live today

| What | File |
|---|---|
| Recipes, weapons, mods, stations | `unity/AthenHill/Assets/AthenHill/Data/Crafting/WardCrafting.asset` |
| Field orders (Steady Hands etc.) | `Data/Crafting/WardFieldOrders.asset`, `Scripts/Orders/FieldOrderSet.cs` |
| Items, tags, Field Toolkit (`field_toolkit`) | `Data/CityCatalog.asset` |
| Skills, XP, levels | `Resources/CharacterCatalog.asset`, `Scripts/CharacterModel.cs` (`GrantExperience`, `TryRaiseSkill`) |
| Bench runtime (timed craft, fit, remove) | `Scripts/Crafting/CraftingSession.cs`, `CraftingModel.cs`, `CraftingCatalog.cs` |
| Unlock types (`acquireItem`, `orderStart`, `magazine`) | `CraftingCatalog.cs` / `CraftingModel.cs` |
| Order stages (Gather, Report, Fabricate, Fit, TestFire) | `Scripts/Journal/QuestJournal.cs`, `QuestConditions.cs` |
| Ossa's dialogue | `Data/npc_ossa.asset` |
| Mod visuals on the pistol | `Scripts/Combat/WeaponModVisuals.cs` (child named after mod item id) |
| Tests | `Tests/Editor/CraftingSliceTests.cs`, `TimedCraftingTests.cs` |

Data changes go through an idempotent `apply_data.py` in this folder (Codex works in parallel
worktrees; patches must be re-runnable). Weapon stats already include `durability` (pistol 0, rifle 100).

## Phases

Small and ordered. Phases 1–3 are data and logic only and can run on a cheaper model. Phase 4 is the
core system. Phase 5 is art. Each phase ends with Edit Mode tests green and a `verify` step; native
checks run once per batch (AGENTS.md §7), not per phase.

### Phase 1 — Ossa identifies the servo

- New unlock type `identify` (`id: <npc>:<topic>`): the schematic is learned when that dialogue branch
  runs, not on pickup. Remove the `acquireItem droid_servo_damaged` unlock from
  `recipe_grip_stabilised_pistol` (keep it for older saves that already know the recipe).
- Items get an optional `identifyBy` NPC id; the HUD pickup toast and inventory tooltip say
  "Show this to Ossa".
- Ossa gets a branch, offered while you carry an unidentified servo, with the lines above (short,
  her voice; generate with the existing ElevenLabs voice via `art/showcase_20261119/npc_life/generate_voices.py`
  or leave captioned if the voice service is unavailable).
- *Steady Hands* stages become Gather → **Identify (Ossa)** → Report (Brann) → Fabricate → Fit → TestFire.
  Journal and compass guidance updated. Existing saves mid-order skip Identify.
- Done when: a new game cannot fabricate the grip before talking to Ossa; old saves still work; tests
  cover both.

### Phase 2 — Skills and tools in crafting

- Recipes and (later) assembly steps name a `skill` (`engineering`, `electronics`, `nanotechnology`,
  `robotics`). Completing a craft grants character XP (small, data-driven) and a small use gain in that
  skill, capped per craft and with diminishing returns per recipe. Skill points from levelling stay the
  main route.
- Tools become explicit items with tags: `tool:screwdriver` (in the Field Toolkit), later
  `tool:vise`, `tool:grinder`, `tool:solder`, `tool:nanite_press`, `tool:welder`. Carried tools are
  inventory items; fixed tools belong to a station (`stations[].tools`). `requiredTools` matches by tag.
- Brann gives a basic Field Toolkit on the first visit if the player has none.
- Grip recipe: requires `tool:screwdriver`, skill `engineering`.
- Done when: the grip cannot be made without the toolkit; crafting moves XP and engineering; tests.

### Phase 3 — Durability and field repair

- Weapons get condition: `durability` (current) and `maxDurability` (cap) in the loadout save. Shots
  wear it (data: wear per shot); low condition widens spread and adds misfires; 0 = jammed, cannot fire.
- **Field repair** (Field Toolkit, hotbar or inventory action, a few seconds, interrupted by damage):
  restores a falling amount each time (start: +30, +20, +12, +6, then nothing) and each repair lowers
  `maxDurability`. When the cap falls under a threshold the weapon is **broken**: field repair refused,
  needs a bench overhaul (Phase 6) that restores the cap and resets the repair count.
- Set the pistol's base `durability` to 100. All numbers in data, tuned later.
- Done when: repair amounts fall as specified, broken state persists through save/load, tests.

### Phase 4 — Assembly system (greybox)

Build the mini-game with placeholder primitives so it can be tested before any art exists.

- **Data:** `AssemblyRecipe` attached to a craft recipe: parts (item id or produced sub-part, prefab,
  start tray slot), sockets (`socket_*` transforms on parts), fasteners (`screw_*`), and ordered steps.
  Step kinds: `place` (drag part to socket, rotate to key; snap tolerance from skill), `unscrew`/`screw`
  (tool required; hold to drive, release in torque window; over = stripped, under = loose), `remove`
  (lift a part off), `teardown` (a salvage item opens into sub-parts, spare sub-parts go to the pack),
  `trace` (apply nanite paste along a path), `wait` (cure).
- **Runtime:** a bench camera (close three-quarter view), mouse and full keyboard control, Esc/damage
  cancels with nothing used (same rule as timed crafting), progress shown per step.
- **Quality:** the steps' scores combine into Rough / Standard / Fine. Output item records quality;
  mod effects scale by quality (grip: −5 / −7 / −10 recoil).
- **Auto-assemble:** after one hand-made success of a recipe, a button makes Standard quality on a
  timer (the current timed craft), so repeats are not a chore.
- Grip steps: lay out → strip pistol grip (2 screws) → tear down servo (4 screws, take gyro bearing;
  windings → 1 copper filament) → seat bearing in frame → side plates + 4 screws → nanite seam → cure →
  fit to pistol (2 screws).
- Brann comments at a few steps (captions; voice later).
- Done when: the grip can be fully made with greybox parts using keyboard only and mouse only;
  cancel/save rules hold; tests for quality and cancellation.

### Phase 5 — Assembly art (part by part)

- Reference sheets first (Codex/gpt-image-2): scrap pistol exploded view, damaged worker servo
  exploded, grip frame and side plates, screws, screwdriver, bench vise, bench mat.
- Model each part in Blender Python following AnyMachine `PIPELINE.md` part 2 (one script per object,
  real parts, render beside the sheets, second pass where plainer, bake). Check the scripts' Blender
  version against ours before reuse.
- Each part exports with named empties for `socket_*` and `screw_*`; screws and vise jaws use 0–1
  rigs (turn + travel). The scrap pistol is rebuilt as separable parts (also benefits the first-person
  view; keep the current pistol recoverable).
- Install into the bench prefab; replace the greybox. Review cameras `cam_assembly_*`.
- Done when: every part reads correctly at bench distance in sun and under the shop lamps; verify clean.

### Phase 6 — Polish and the bench overhaul

- Audio (screwdriver, bearing seat, nanite hiss), small hand/tool motion, Brann voiced lines.
- Bench overhaul recipe for broken weapons (Phase 3) using the same assembly system.
- Native batch test: city loop, range tutorial, rifle quest, a new assembly check script with real input.

### Phase 7 — Roll out

- Bored Alloy Barrel (needs `tool:vise` + grinder), Salvaged Capacitor Cell (`tool:solder`,
  electronics), then Mark II mods, then armour (welder). Each needs its identification line, parts
  and assembly steps.

## Open questions (not blocking Phase 1)

- Where carried-tool work is allowed besides field repair (any bench, home table, Warden waystation?).
- Whether quality also varies with the salvage's condition (worn / damaged / intact servo from how the
  droid died).
- Exact XP and use-gain numbers; tune after Phase 2 in play.

## Phase 1 — done (20 Nov 2026)

- **Unlock type `identify`**, id `"<npc id>:<dialogue node id>"`. `CraftingModel.Identify(topic)` teaches every recipe with that
  unlock; `GameSession.SpeakDialogue` (runs for every node shown) calls it with `npc:node`. `recipe_grip_stabilised_pistol` now has
  `{type: identify, id: npc_ossa:servo_look}` instead of `acquireItem droid_servo_damaged`; `acquireItem` still works for other recipes,
  and old saves keep the grip through their saved known recipes.
- **Items:** `ItemSpec.identifyBy` (NPC id; servo = `npc_ossa`). `CraftingModel.NeedsIdentifying/UnidentifiedCarried/NeedsIdentification`.
  The pickup log line adds "Show the Damaged Servo to Warden Ossa." and the servo description says to show it to Ossa.
- **Stages:** new `OrderStage.Identify` (appended): recipe unknown, carried salvage with `identifyBy` that an input of the recipe uses.
  `FieldOrder.identifyBrief` / `identifyGuidance` (Steady Hands has the brief; **guidance is empty: no Ossa target exists in the
  scene, so no compass marker yet; adding one needs a scene edit**). Journal gets a "Show the salvage to Warden Ossa" step.
  Old saves that know the recipe skip Identify. A talk with Brann while in Identify does not count as the Report (`FieldOrders.OnTalked`).
- **Conditions:** `carry:ITEM` and `recipe:ID` (IQuestState.HasItem/KnowsRecipe, default interface members so test fakes still compile).
- **Dialogue (voiced, ElevenLabs Victoria/Callum, `generate_voices.py`, lines in `lines.json`):** Ossa entry `servo` first in her list
  (`carry:droid_servo_damaged, !recipe:recipe_grip_stabilised_pistol`). *servo:* "Hold it up. Worker servo. Anything you pull off the
  machines, you can sell, or you can build it into guns and armour. That's how it works around here: we salvage what we can. Let me look
  closer." *servo_look* (teaches): "Hm. The gimbal is still true. Wired into a pistol grip, that should take the kick out of your scrap
  pistol. Brann at Salvage has the bench, on the north avenue. Take him alloy and nanites too." Brann `steady_identify` (stage Identify):
  "That's a worker servo. Good. Before I touch it, show it to Ossa. ..." `NpcVoiceAudit` counts: Brann 20, Ossa 9.
- **Files:** `apply_data.py` (idempotent, `--check`), `generate_voices.py`, `lines.json`; code in `CraftingCatalog/Model/Session/Text`,
  `CityCatalog`, `FieldOrderSet/Progress/Orders`, `QuestConditions`, `GameSession`, `QuestJournal`, editor `CraftingDataExporter`,
  `GameplayV2Content`; tests `Tests/Editor/IdentifyTests.cs` (+ servo calls in CraftingSlice, FieldOrder, SaveGame, HudPanels, RecipeChain tests).
- **Tests:** Edit Mode 435/435 passed (`unity/evidence/crafting_assembly/20261120/phase1/editmode.xml`). No native run.
- **Open:** QA scripts that grab a servo and expect the grip (`tools/check_*_native.py`, `showcase_qa.py`, `check_rifle_quest.py`, devui)
  need an Ossa conversation or `Unlock` first; `Data/Crafting/Export/ward-crafting.v1*.json` not regenerated; Brann's `steady_gather`
  still says "No servo yet?" when only alloy/nanites are short; Ossa compass marker (scene).

## Phase 2 — done (20 Nov 2026)

- **Recipe fields** (`CraftRecipe`, after `craftSeconds`): `skill` (engineering / electronics / nanotechnology / robotics), `craftXp` (character XP on completion) and `skillUse` (skill points from use for the first craft of that schematic). All 26 recipes carry them (grip: engineering, 12 XP, use 1; rifle 25 XP / 1.5; components 3-4 XP / 0.5; mods 10-14 XP / 1; armour kit 10-14 / 0.75; gear 3-12 / 0.5-0.75). Catalog: `useGainCap` 1.5 (per craft) and `useRepeatFactor` 0.5 (each repeat gains half the previous, nothing under 0.05, so one schematic yields at most about 2 x `skillUse` in total). A spent skill point still adds `trainingStep` 5.
- **Skill use storage:** `CharacterModel.GrantSkillUse(id,amount,out whole)` keeps fractional progress in thousandths (`CharacterState.useProgress`, a `CountEntry[]`; version stays 2, a missing array is no progress); whole points are added to the trained skill (capped at the skill maximum). `CraftingModel.TryCraft` grants XP (`GrantExperience`) and use after the commit and records `LastAward` (`CraftAward`: xp, levels, skill, skillGain, skillPoints); the fabrication notice appends "+12 XP · Engineering +1" (or "practice" while under a whole point).
- **Tools by tag:** `requiredTools` entries are item ids OR tool tags; met by the station's tool (`CraftStation.tools`) or a carried item with that id/tag (carried item reserved so it cannot also be an ingredient). `field_toolkit` gains tag `tool:screwdriver`; the rifle recipes keep `field_toolkit`. The grip recipe requires `tool:screwdriver`. Salvage workbench `tools`: `tool:vise`, `tool:grinder`, `tool:solder`, `tool:nanite_press`, `tool:welder` (no screwdriver on purpose, it must be carried; no existing recipe needs the fixed tools yet). `CanFit`/`TryFit` take an optional `stationId`. Tag labels added (Screwdriver, Bench vise, ...).
- **Bench text:** `CraftingText.Reason` now names the missing tool ("Missing tool: Screwdriver. Carry a Field Toolkit.") and the unmet skill ("Your skill is too low. Requires Engineering 35."); tool lines read carried / at this bench / missing; the recipe panel lists "Exercises Engineering · +12 XP".
- **Brann's toolkit:** `CraftingCatalog.nodeGifts` (`topic npc_brann:toolkit`, item `field_toolkit`, flag `brann_toolkit`); `GameSession.SpeakDialogue` calls `CraftingModel.Gift` for every node shown, which adds the item only if not carried and the flag is unset, then sets the flag (a full pack leaves the flag unset). Brann entry `toolkit` (`!flag:brann_toolkit, !carry:field_toolkit`, after first_visit); line: "No toolkit on you? Then you're not touching my bench. Here, take this one: a screwdriver, a few gauges, the basics. Every salvager starts with one. Don't leave it lying about." VOICED (ElevenLabs, `npc_brann-toolkit.wav`, via `generate_voices.py`/`lines.json`). Choices: report (only in the Steady Hands Report stage, goes to report_ready), trade, thanks. `NpcVoiceAudit` Brann 21.
- **Contradiction with the plan:** `field_toolkit` has `startingQuantity` 1, so a new game already carries it and Brann's gift never fires in normal play (it covers lost/odd saves). I did NOT set it to 0: order stages use `CanCraft`, so without the toolkit Steady Hands would sit at Gather with every part in the pack, Brann's `steady_gather` would say "No servo yet?", and about 30 tests/QA scripts craft from a fresh pack. If Carl wants the narrative gift, set `startingQuantity: 0`, add a Gather-stage hint for the missing tool and fix those fixtures.
- **Files:** `CraftingCatalog/Model/Session/Text`, `FabricatorPanel`, `CharacterModel`, `GameSession`, editor `CraftingDataExporter` (tool-tag validation, new fields exported), `apply_data.py` (extended, idempotent, `--check` exit 0), `lines.json`, `Data/Crafting/WardCrafting.asset`, `CityCatalog.asset`, `npc_brann.asset`; tests `Tests/Editor/CraftingSkillsToolsTests.cs` (10: data shape, no grip without toolkit and the reason text, station tools/tags/ids, XP and capped diminishing use, per-craft cap and failed craft, save round trip and older saves, Brann once only, Brann's entry conditions, Steady Hands end to end, every recipe craftable); two earlier fixtures (`IdentifyTests`, `SalvageShopTests`) set `brann_toolkit`.
- **Tests:** Edit Mode 445/445 (`unity/evidence/crafting_assembly/20261120/phase2/editmode.xml`). No native run.
- **Open / Phase 3 hooks:** `CraftingModel.ToolProvided/ToolItems` and `tool:` tags are the extension point for field repair (`tool:screwdriver` from the carried toolkit); `Data/Crafting/Export/*.json` not regenerated; native QA scripts unchanged; no scene edits; skill levels are not yet required by the grip (no `requirements`), only exercised.

## Phase 3 — done (20 Nov 2026)

- **Condition = the weapon's `durability` stat** (pistol base set 100, rifle already 100; a weapon with 0 does not wear). `WeaponLoadout` holds `Durability` (current), `MaxDurability` (cap, starts at the base), `Repairs`; `WeaponCondition` (static, in `WeaponLoadout.cs`) has the pure rules: `SpreadScale`, `MisfireChance`, `BeforeShot` (Fire / Misfire / Jammed), `IsBroken`, `NextRepairAmount`, `Label`. Save: `WeaponLoadoutState` gains `conditionVersion` (1 when saved), `durability`, `maxDurability`, `repairs`; version 0 (older saves) loads at full condition; values clamp on load; save version number unchanged.
- **Data** (`CraftWeapon.wearPerShot`; catalog `condition` = `ConditionRules`; `apply_data.py` patched, idempotent, `--check` exit 0; also corrected the Phase 2 nodeGifts patch's applied-marker, which the new block would have broken): wear per shot pistol 0.15, rifle 0.2 (about 660 / 500 shots to a jam; normal play of the orders is well under 100 shots, about 15 condition); spread widens linearly from x1 at condition 50 to x2 at 0; misfire chance rises linearly from 0 at condition 30 to 35 % just above 0 (a misfire spends no nano and no wear); 0 = jammed, cannot fire. Field repair amounts +30, +20, +12, +6 (never above the lowered cap, refused when it would gain nothing); each repair lowers the cap by 8 (100 → 92 → 84 → 76 → 68); broken when the cap is under 70 or all four repairs are used, which coincide: four field repairs, then a bench overhaul. Repair takes 4 s with `tool:screwdriver` (carried Field Toolkit, not consumed). Overhaul (placeholder until Phase 6): 3 Scrap Alloy + 4 any tier-one nanites at `station_field_fabricator`, restores condition and cap to full and resets the repair count. Exporter (`CraftingDataExporter`) exports and validates all of it.
- **Firing hook** (`PlayerCombat.Fire`): after the armed/ready check, `WeaponCondition.BeforeShot`: jam or misfire plays the dry-fire click, shows a notice (throttled) and returns without nano or wear; a shot wears `WearPerShot` and the cone is multiplied by `SpreadScale`. `PlayerCombat.WeaponHandled` event (draw, holster, trigger pull).
- **Player triggers a field repair:** Tab (field pack) → PRIMARY or SECONDARY tab → the weapon's panel shows "CONDITION" with the state line, the next repair's gain and cap cost, and a **Repair with toolkit** button (becomes **Stop repair** while running). API: `CraftingSession.BeginFieldRepair(weaponId)`. Cancel rules mirror timed crafting: damage, drawing/holstering/firing (`WeaponHandled`), leaving Play and the field pack (any other state), Stop repair; nothing changes unless it completes. Notices say why. The bench window shows the condition in the weapon title and has an **Overhaul weapon** button beside Remove (a new Tab stop; `GameplayV2FixesTests` tab-order expectation updated). Hotbar use was not added (needs a hotbar-assignable item and catalog consumable work).
- **Model API** (`CraftingModel`): `Condition`, `CanFieldRepair/BeginRepair/TickRepair/CancelRepair/RepairJob/RepairGain`, `CanOverhaul/TryOverhaul`; `CraftingText.ConditionReason/Condition/OverhaulCost`.
- **QA:** `dev.recipe.identify` (topic `npc_ossa:servo_look` or `recipeId`) and `dev.weapon.condition` (`weaponId`, `durability`, `maxDurability`, `repairs`, or `full: true`) added to `DevBridgeCommands` (development players only). Most native scripts already seed `known` with the grip, so they were unaffected by Phase 1; `check_home_journal_native.py` now seeds it too. `showcase_qa.start()` (shared by the showcase checks) and `check_gunner_separation`, `check_next_level_enemies`, `check_rifle_quest`, `check_showcase_combat_feel`, `check_showcase_combat_audio` reset both weapons to full condition with `dev.weapon.condition`. `py_compile` clean; no native run.
- **Tests:** `Tests/Editor/WeaponConditionTests.cs` (11: data shape and defaults, wear and no-wear weapons, spread/misfire/jam, repair amounts and cap loss to broken, cap limit and refusals, timed repair and cancel at model level, session cancel on damage / weapon handled / leaving the pack, overhaul and its station and cost, session overhaul only at the bench, save round trip incl. broken state, older saves and clamping, panel text and Overhaul button). Edit Mode 456/456 (`unity/evidence/crafting_assembly/20261120/phase3/editmode.xml`). No native run.
- **Contradictions / notes:** the plan's "repair restores 30, 20, ..." is clipped by the lowered cap, and a repair that could only lower the cap is refused as "in good order". The Field Repair progress is not shown live in the pack panel (the panel refreshes on state change; it says "reopen this tab"); the notice and HUD carry the result. Wear per shot and thresholds are guesses to tune in play. `Data/Crafting/Export/*.json` not regenerated.
- **Open:** native check of jam/misfire feel and the HUD jam notice; hotbar repair; live progress bar in the pack panel; Phase 6 assembly-based overhaul replaces the placeholder; the jam/misfire audio reuses the empty-click.

## Native check p2-craft13 (20 Nov 2026)

- **Build:** `Builds/batch-p2-craft13` from the uncommitted tree (phases 1-3), 10:12-10:16 (about 4 min, warm caches), Result: Success; `compile_check.py` clean; no stray ProjectSettings/Packages/Settings changes after the build.
- **Regression batch (`unity/evidence/showcase_phase2/20261120/qa/craft13/`), all pass:** city loop PASS; range tutorial 10/10; rifle quest 41/41; home/journal 36/36; Field Supply 25/25; Berms expansion 8/8; gunner separation 8/8 (not marginal this time); next-level enemies 42/42.
- **New check `unity/tools/check_crafting_flow_native.py`: 40/40** (`craft13-flow.out`, run in `qa/craft13/flow/run/`, 17 screenshots). Earlier runs (`craft13-flow.run1-3.out`) failed only through script faults: the bridge rejects `dev.weapon.condition repairs=0` (range 1..100; use `full: true` to reset the count), and the UI parser matched the notice log and missed the upper-cased bench title.
  - Identify: fresh save has no grip; Brann's `steady_identify` names Ossa; Ossa `servo` -> `servo_look` (real Tab/Return) teaches the grip; stage Identify -> Report; Brann `report_ready` -> Fabricate. The stage at the start is Identify (not Gather) once salvage is carried.
  - Tools: with the toolkit removed the bench says "Missing tool: Screwdriver. Carry a Field Toolkit." and Fabricate starts nothing.
  - XP: grip fabricated in 8 s; notice "+12 XP · Engineering +1"; engineering 10 -> 11; saved experience 12.
  - Condition: condition 3 misfires with the HUD notice; 0 jams (no shot, notice, stays jammed); field repair 20 -> 50 with cap 92; "You were hit. The Scrap Pistol repair stopped. Nothing changed." cancels; caps 92, 84, 76, 68; after four the panel says "needs a bench overhaul" and a fifth is refused; bench Overhaul gives 100 / 100 (3 Scrap Alloy, 4 nanites) and the repair count resets.
- **Seen in the screenshots:** dialogue, bench refusal, XP notice and condition panel read correctly, no overflow or doubled labels. One text defect: the notice after the fourth repair joins two sentences without a full stop ("...needs a bench overhaul It is as good as the field can make it..."). Not verified: audio, a live repair progress bar (panel says reopen the tab).
