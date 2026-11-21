# craft: crafting integration, quality and the pistol's handling

Steady Hands bench programme, `craft` agent, 20 November 2026. Brief: `../briefs/craft.md`. Contract: `../CONTRACT.md`
section B.

## What exists

| Piece | Where |
|---|---|
| Host surface (CONTRACT B, exact names) | `Scripts/Crafting/AssemblyHost.cs` (`CraftQuality`, `AssemblyTicket`, `AssemblyResult`, `WeaponHandling`, `CraftingSession` partial) |
| Model behind it | `Scripts/Crafting/CraftingModel.Assembly.cs` (ticket, reservation, complete, abandon, hand-made record, carried quality, handling, save, dev operations), `WeaponHandlingRules` |
| Quality in loadouts | `WeaponLoadout` (`Quality(slot)`, `Set(slot,item,q)`, `Preview(slot,item,q)`, `Compute` with qualities, `EffectValue`), `CraftEffect.byQuality`, `CraftModifier.qualityScale` |
| Hand-made gate | `CraftingModel.BeginCraft/TryCraft` refuse `hand_made_first`; `CanCraftOnTimer`; `CanCraft` unchanged (order stages) |
| Station and window | `CraftingStationMarker.Use` → `CraftingSession.UseStation`; `FabricatorPanel` **Build by hand** / **Back to the bench** / **Build by hand again** button, **Auto-assemble** once made by hand, reason text |
| Weapon on the bench | `CraftingModel.OnBench`; refused in `CanFit`, `TryRemove`, `CanFieldRepair`, `CanOverhaul`, `PlayerCombat.ToggleDraw` (notice), and the drawn weapon is holstered when a job opens |
| Orders, journal | `FieldOrderProgress` (Fabricate while the job is open, `BenchRoute`, `NoteBenchBuilt`, judged test-fire string, `benched` saved), `FieldOrderSet.benchFormat/benchStepFormat`, `FieldOrder.testFire*`, `QuestJournal` one bench step with the stage label |
| Dialogue conditions | `bench`, `handmade:ID` (`QuestConditions`, default interface members, no GameSession edit) |
| Save | `WardSaveData.benchJob` (the blob), `CraftingState.handMade/carriedQuality/bench`, `SlotEntry.quality`, `FieldOrderState.benched`; all additive, version 4 unchanged |
| Feel | `Scripts/Combat/WeaponFeel.cs` (pure), `PlayerCombat` (heat, side kick, recovery, rattle/damper), `FollowCamera.ApplyShotKick` overload (side step, overshoot), `FirstPersonViewModel` and `PlayerWeaponPose` (idle sway, side kick, slow return with overshoot), `CameraImpulse` (shake x side kick) |
| QA | `Scripts/Crafting/CraftDevCommands.cs` (`dev.craft.handmade/fit/strip/heat`), `Scripts/Crafting/CraftQa.cs` (`bench` block for crafting.json), `unity/tools/capture_pistol_handling_native.py` |
| Data | `data/apply_data.py` (`--check`): WardCrafting, WardFieldOrders, npc_brann |
| Tests | `Tests/Editor/SteadyHandsCraftTests.cs` (19) + fixture updates in 7 older test files |

## Handling numbers (data in `WardCrafting.asset`, written by `data/apply_data.py`)

Kick is `recoil x 0.05` degrees (`PlayerCombat.recoilDegreesPerPoint`); half of each kick is recovered (`recoilRecoverFraction`).
Character recoil control and the weapon skill still apply on top, as before.

| Stat (id) | What it changes on screen | Bare scrap pistol | Grip Rough | Grip Standard | Grip Fine | Mark II gyro grip |
|---|---|---|---|---|---|---|
| recoil | vertical camera kick per shot (deg = x0.05), view-model and third-person kick, camera shake | 38 (1.90°) | 33 (1.65°) | 31 (1.55°) | 28 (1.40°) | 23 (1.15°) |
| sway (deg) | idle figure of eight (3.2 s) plus a tremor that fades below 1°, on the held pistol in first person (x0.8 aiming) and the raised hand in third person (x0.7). **Visual only: the shot follows the crosshair** | 1.20 | 0.60 | 0.45 | 0.25 | 0.22 |
| sideKick (deg) | random sideways camera step per shot (60-100 % of the value, random side), half recovered, so the aim walks; view-model yaw kick; camera shake x(1 + 0.35 x sideKick); the rattle plays at 0.5 and above | 0.90 | 0.40 | 0.20 | 0.08 | 0.06 |
| recovery (s) | time for the kick to settle (camera and view model); above 0.22 s it swings once past rest by up to 30 % (`OvershootFraction`); 0 = the old 0.18 s | 0.34 (overshoot 18 %) | 0.24 (3 %) | 0.18 (none) | 0.14 (none) | 0.14 |
| scatterGrowth | each shot adds this to the next shot's cone (cone x (1 + heat)); heat halves every 0.35 s, capped at +150 %. The first shot of a string has today's cone | 0.35 (5th shot at the 0.28 s fire rate: cone x1.42) | 0.18 | 0.12 (x1.14) | 0.07 | 0.06 |

Standard removes 62 % of the bare sway, 78 % of the side kick, 66 % of the scatter growth, and brings recovery back to the
old 0.18 s with no overshoot (test `HandlingBareAndGrippedAtEachQuality`). Every other weapon has 0 for the four new stats,
so the rifle feels as before.

Hard limits kept: the bare pistol's base recoil (38), spread (4) and first-shot cone are unchanged; sway never moves the
shot ray; Reduced Motion zeroes the old look sway and bob as before and now keeps 30 % of the new idle sway; the
camera-shake setting still gates `CameraImpulse` (only its amount per shot changed). The range tutorial's plates are shot
with aim assist 3.5°, unchanged.

## Departures from CONTRACT.md / DESIGN.md / the brief

1. **Reservation** takes the inputs out of the pack and locker onto the ticket (not a flag on pack units). It is the
   simplest way to keep them unsellable, unstorable and unusable by other crafts; abandoning puts them back in the pack
   (locker units included, so a full pack can refuse an abandon: `stack_full`/capacity reason, nothing changes).
2. **The ticket is saved in `CraftingState.bench`**; `WardSaveData.benchJob` holds only the bench system's blob as the
   contract says. A blob without a ticket is dropped on load.
3. **`AbandonAssembly(spentInputs)`**: one array entry per spent unit (`["scrap_alloy","nanite_residue","nanite_residue"]`).
4. **Old saves that already made the grip** (no `handMade` record, crafted count > 0) count as made by hand, so they keep
   the timer. A save that never made it must build the first one by hand.
5. **The test fire after a bench build is a judged three-shot string** (`FieldOrder.testFireShots` 3, tight within 3.5°),
   with Ossa's voiced range lines (radio caption plus the take on a 2D source in `FieldOrders`). A poor group asks for one more string,
   the second completes the order. Orders whose part came from the timer keep the one-shot test fire, so the existing
   checks are unaffected. Steady Hands' `completeLine` is now Ossa's `range_done` line.
6. **`HandlingFor`** with no mod returns the weapon as fitted now; `HandlingWithout(weaponId, slot)` gives the bare
   pistol for the before card. `kick` includes the character's recoil control.
7. **Quality on effects** is data per effect (`byQuality`: Rough, Standard, Fine values) with a per-modifier
   `qualityScale` fallback (default 0.75 / 1 / 1.25) for mods without explicit values.
8. **Dialogue**: Brann's new `steady_bench_open` entry (condition `bench`) uses the audio agent's `come_back` take; the
   existing `steady_bench` line ("fabricate the grip, then fit it ... right there") still reads true and was not re-voiced.

## Hooks needed in `bench`-owned files (one line each)

- `DevBridgeCommands.Execute`, after the `adjustable` line:
  `if (action.StartsWith("dev.craft.", StringComparison.Ordinal)) return CraftDevCommands.Execute(action, command, session, adjustable);`
- `NativeQa` `crafting.json` anonymous object, after `craftJob=...`: `,bench=CraftQa.Snapshot(crafting,combat)`
- `GameSession.Choose`, the `"fabricator"` action branch, after the colonist is cleared and before `SetState(CityState.Fabricator)`:
  `if(GetComponent<CraftingSession>()?.UseStation(bench)==true)return;` (Brann's "Use the bench." / "Back to the bench."
  open the hands-on job directly; without it they open the Fabricator, where Build by hand works).
- Optional: set `CraftingSession.AssemblyOpener` from the bench system, or keep `GameSession.OpenAssembly(CraftingStationMarker,string)`
  (found by reflection when the opener is null).
- Audio: no hook needed. The rattle (`asm.rattle.shake`, 3 takes) and damper tick (`asm.damper.tick`, 4 takes) are bound
  by `apply_data.py` to `CraftingCatalog.rattleClips/damperClips` in `WardCrafting.asset`; `PlayerCombat` uses them when
  its own clip fields are empty (no scene edit). Ossa's four range takes are bound to `FieldOrder.testFireVoice`,
  `testFireTightVoice`, `testFirePoorVoice`, `completeVoice` on Steady Hands; `FieldOrders` plays them in order on one 2D
  source in the SFX group as the radio caption is queued (the radio queue itself has no voice path). Brann's
  `steady_bench_open` node uses `npc_brann-come_back.wav`. Nobody has listened to any of them in the game.

## Running the capture

    unity/tools/qa_display.sh up
    ~/.local/state/ward-programme/steady-hands-20261120/native_check.sh pistol_handling unity/tools/capture_pistol_handling_native.py ATHEN_EXE=<build>/AthenHill.x86_64

Output in `unity/evidence/steady_hands/20261120/craft/handling/` (report.json, handling.md, frames per configuration).

## Fix round (20 Nov 2026, orchestrator's three items)

1. **Test fire at the range.** A bench-built grip's judged three-shot string counts only shots fired within 4 m (ground
   plane) of the firing line, centre (-65.47, 9.03): bay 2 of the three bays at 0 / 1.6 / 3.2 m right of
   `checkpoint_firingline` (-66.2, 7.6), from `art/training_range_20261001/layout.py`. Data on the order:
   `testFireAt`, `testFireRadius`, `testFireBrief`, `testFireStep`, `testFireLabel`. A shot from elsewhere starts the
   string again, with a notice (8 s throttle). The objective, the journal step and the marker ("FIRING LINE", a runtime
   transform at `testFireAt` under FieldOrders; no scene edit) point there. Ossa's `range_ready` take plays when the
   player first stands at the line with the grip fitted, and the three plates are raised then. They stay down after the
   primer until someone uses the range reset. A timer-made grip keeps the one-shot test fire anywhere.
2. **The weapon on the bench** cannot be unequipped, swapped into or moved: `CharacterModel.SlotLocked` (an additive hook)
   is set by `CraftingSession` to `CraftingModel.SlotLockFor`. The refusal is the same notice as the draw block, and the
   loadout panel shows "On Brann's bench" (description line and slot tooltip). There is no drop action for equipped items.
3. **Never stuck.** `CraftingSession.BenchPresent(recipeId)` needs an opener (`AssemblyOpener` or
   `GameSession.OpenAssembly`) and an `AssemblyBench` in the scene whose `recipe.Id` is the recipe's assembly id. When
   either is missing:
   - `CraftingModel.HandsOnAvailable` lifts the hand-made gate, so the timer may make the part;
   - the station opens the Fabricator, and Build by hand is hidden;
   - a ticket left open is abandoned with its parts returned;
   - one `Debug.Log` line per recipe and cause says why.
   Test overrides: `OpenAssemblyFound`, `AssemblyRecipeFound`.
