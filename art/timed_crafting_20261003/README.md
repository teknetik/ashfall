# Timed crafting at Brann's workbench (3 October 2026)

Carl, playtest 3 Oct 2026, on the armour: it "should be a crafting mission ... collect, craft slowly, craft it to
armour". The Warden Kit chain (`art/armour_mission_20261003`) made the armour a mission. This pass makes it slow:
fabrication at the bench now takes time. Gameplay code, UI and data only; no art, no Meshy, no scene change.
Not yet accepted by Carl.

## Behaviour

- `CraftRecipe.craftSeconds` (Inspector: *Craft Seconds*; 0 = instant, as before).
- **Fabricate** validates the schematic as before and starts the bench timer (`CraftingModel.BeginCraft` →
  `CraftJob`). Nothing is reserved or taken. One job at a time (`busy`).
- When the time is up, `CraftingModel.TickCraft` re-validates and commits inputs and output in **one**
  `ShopModel.TryApply` (through the unchanged `TryCraft`). If parts left the pack meanwhile the craft fails with
  nothing changed. No duplicates, no losses.
- **Cancel** (button under the actions, focused while working, so Enter or a click cancels), **Esc / closing the
  window** (any state but Fabricator, immediately via `GameSession.Changed`, with an `Update` backstop) and **taking
  damage** (`Health.Damaged`) stop the job with nothing used. Fit and Remove wait while the bench works.
- The window stays modal while working (input blocked, the player stays at the bench, as before).
- UI: progress strip with "Fabricating the … · N s left", a cyan fill on the salvage-search track, Cancel; the working
  schematic reads "Working"; tooltips and the description show the bench time ("Bench time: 8 s",
  "… · 8 s at the bench"); the Fabricate tooltip explains the rule. Reduced motion steps the fill in tenths.
- Audio: the existing trade click on completion, the "unavailable" cue on cancel/failure (`GameSession.Cue`).
- Notices name the bench: start ("Fabricating the …: 8 s at the bench. Cancel or Esc stops it; nothing is used until it
  is done."), completion (unchanged "… fabricated."), stop ("You left the bench. … not made. Nothing was used.").
- **Saves:** a craft in progress is not saved. Saving or quitting mid-craft keeps every part (nothing was consumed)
  and loses only the timer; `CraftingModel.Restore` drops any job.
- QA: `crafting.json` (NativeQa) and `dev.state` gain `craftJob` {recipeId, seconds, progress, remaining};
  `crafting.json` also lists live salvage caches (`caches`), used by the enemies check (see FLAKES.md).

## Data (`apply_data.py`)

| recipe | seconds |
| --- | --- |
| recipe_wound_coil | 4 |
| recipe_charge_cell_core | 5 |
| recipe_alloy_plate | 6 |
| recipe_grip_stabilised_pistol | 8 |
| recipe_cell_salvaged_capacitor | 9 |
| recipe_barrel_bored_alloy | 10 |
| recipe_grip_gyro_braced | 11 |
| recipe_barrel_lattice_focused | 12 |
| recipe_cell_overclocked | 12 |
| recipe_rifle_precision_barrel | 12 |
| recipe_field_rifle | 20 |
| recipe_field_helmet | 15 |
| recipe_field_gloves | 16 |
| recipe_field_armguards | 20 |
| recipe_field_leggings | 25 |

The whole Warden kit is 76 s at the bench plus 7 × 6 s of alloy plate.

```
python3 art/timed_crafting_20261003/apply_data.py            # idempotent; replaces existing values
python3 art/timed_crafting_20261003/apply_data.py --check    # exit 1 when the asset differs
```

Run after `art/armour_mission_20261003/apply_data.py` (and the scripts that run before it). The value is written after
each recipe's `lockedHint` line; recipes not in the table get 0. The script parses the result with pyyaml and checks
every value. Then in Unity: `AthenHill.Editor.CraftingDataExporter.Export` (exports `craftSeconds`, rejects values
outside 0–600 s). The live asset was backed up once to `backup/` before the first change.

## Files

- `Scripts/Crafting/CraftingCatalog.cs` (field), `CraftingModel.cs` (`CraftJob`, `BeginCraft`, `TickCraft`,
  `CancelCraft`, `CraftSeconds`, `Job`; Restore drops a job), `CraftingSession.cs` (timer, cancel rules, notices,
  `CraftFinished`), `CraftingText.cs` (`Duration`, `busy` / `cancelled` reasons), `FabricatorPanel.cs` (progress,
  Cancel, tooltips, focus), `GameSession.cs` (`Cue`), `NativeQa.cs` and `DevBridgeCommands.cs` (`craftJob`, `caches`).
- `UI/CityHUD.uxml` (`fab-progress`, `fab-progress-label`, `fab-progress-track`, `fab-progress-fill`,
  `fabricator-cancel`), `UI/CityHUD.uss` ("Timed crafting" rules, `.fab-recipe.working`).
- `Editor/CraftingDataExporter.cs`, `Data/Crafting/WardCrafting.asset`, `Data/Crafting/Export/ward-crafting.v1.json`.
- Tests: `Tests/Editor/TimedCraftingTests.cs` (9 tests), `HudPanelsTests.cs` (completes the grip's timer).
- Native checks (not run here): `unity/tools/check_salvage_shop_native.py`, `check_rifle_quest.py` (wait for the
  bench timer), `check_rifle_quest.py` and `check_next_level_enemies.py` (flake fixes, FLAKES.md).
- Docs: `unity/EDITING.md` (Timed crafting paragraph), `unity/DESIGN.md` (fabricator progress), `AGENTS.md` (Outer
  Berms loop row).

## Rollback

Set every Craft Seconds to 0 (or restore `backup/Data/Crafting/WardCrafting.asset`), then
`CraftingDataExporter.Export`. With 0 s everywhere the code path is the old instant craft (tested).
