# Brief: `craft` — crafting integration, quality, and the before/after feel of the pistol

You connect the new bench job to the game's existing crafting, orders, journal and save, add crafted quality, and make
the difference between the bare scrap pistol and the gripped one something the player sees and feels.

Read first: `../AGENT-RULES.md`, `../DESIGN.md` sections 2, 9 and 10, `../CONTRACT.md` section B (binding),
`../FACTS.md` (Numbers and feel, Runtime hooks), and `art/crafting_assembly_20261120/PLAN.md` including its three
"done" records: you are continuing that work in the same style (idempotent `apply_data.py` with `--check`, Edit Mode
tests per feature, notes on what contradicts the plan).

## What you own

`Scripts/Crafting/**`, `Scripts/Orders/**`, `Scripts/Journal/**`, `Scripts/Save/**`, `Scripts/QuestConditions.cs`,
feel code in `Scripts/Combat/**` and `FirstPersonViewModel`, your tests, and
`art/steady_hands_bench_20261120/data/apply_data.py` for `WardCrafting.asset`, `WardFieldOrders.asset`,
`CityCatalog.asset`, `npc_brann.asset`, `npc_ossa.asset`. Another agent (`bench`) owns `Scripts/Assembly/**`,
`GameSession.cs`, `GameInput.cs`, `FollowCamera.cs`, `CityHud.cs`, `DevBridgeCommands.cs`, `NativeQa.cs` and is
coding against your surface now. **Write `Scripts/Crafting/AssemblyHost.cs` with the full surface of `CONTRACT.md`
section B first** (compiling, bodies may be minimal), so `bench` can link to it within your first half hour. If you
need a `dev.craft.*` command or a `CityState` check that lives in a `bench`-owned file, write the method on your side
and name the one-line hook you need in your report; do not edit those files.
One exception: `FollowCamera.cs` is shared. You may make one small additive edit to its shot-kick path only
(`ApplyShotKick` and its recovery); `bench` is adding a camera overlay elsewhere in the same file, so re-read it
immediately before you edit.

## What to build

1. **The host surface**: reserve inputs and take the weapon to the bench (`BeginAssembly`), keep the open ticket and
   the opaque blob, save both additively (`WardSaveData.benchJob`, no version bump, null = none), complete (consume,
   grant with quality, fit to the weapon in the same transaction, award XP and skill use as `TryCraft` does, grant
   by-products, mark hand-made) and abandon (return the weapon and unspent inputs). While a ticket is open the weapon
   cannot be drawn, fitted, repaired or overhauled, with a plain notice. Inputs reserved for the bench must not be
   sellable or usable by another craft. Old saves and saves from before this change load unchanged.
2. **Hand-made gate**: a recipe with `assembly` set cannot be made on the timer until it has been made by hand once;
   after that the timer makes Standard quality (Auto-assemble). `CraftingStationMarker.Use()` and the Fabricator panel
   behave as `CONTRACT.md` says (a **Build by hand** button; the reason text when the timer is refused). The timed
   craft for every other recipe is untouched.
3. **Quality** Rough / Standard / Fine: stored for fitted mods and for carried ones, saved additively, scaling the
   mod's effects through `WeaponLoadout.Compute`, shown in the bench window and the loadout tooltip ("Stabilised
   Pistol Grip · Fine"). Items stay id and count; do not rebuild the inventory. Old saves read as Standard.
4. **Order and journal**: with a bench job, fabricating and fitting happen in one visit, so the `Fit` stage is not
   seen for this order. Update the journal step ("Build and fit the grip at Brann's bench", with the bench stage
   label from `ReportAssemblyStage` as its progress), Brann's stage entries, and every test and QA script that
   expects `Fit` for Steady Hands. Keep `Fit` working for mods made on the timer.
5. **Before and after** (`DESIGN.md` section 10). Add handling stats to weapons and mod effects (names your choice,
   in data, exported by `CraftingDataExporter`): aim sway, side kick, recovery, scatter growth under rapid fire. Read
   them in `PlayerCombat`, `FollowCamera` kick, `FirstPersonViewModel`, `PlayerWeaponPose` and `CameraImpulse` where
   each belongs. Hard limits: the bare pistol's first aimed shot is as accurate as today, the range tutorial's plates
   and every existing native check stay passable with the bare pistol (do not make aim sway move the shot ray unless
   you can show that), and Reduced Motion and the camera-shake setting still reduce what they reduce today. The grip
   by quality: start at recoil -5 / -7 / -10 with sway, side kick, recovery and scatter growth scaled so Standard
   removes more than half of the bare pistol's roughness. Add the rattle and damper-tick sound hooks (clip fields that
   may be empty until the audio agent delivers `asm.rattle.*` and `asm.damper.*`).
   Provide `HandlingFor(weaponId, withModId, quality)` for the bench's test cards.
6. **Data**: `CraftRecipe.assembly = "assembly_grip_stabilised_pistol"` on the grip recipe; anything else the above
   needs; voiced-line bindings for Brann's and Ossa's new lines once the audio agent's `audio/lines.json` lists them
   (bind what exists, captions only for what does not).
7. **Tests** (Edit Mode): reservation and its exclusions, complete and abandon, save round trips with an open ticket
   and from old saves, the hand-made gate, quality storage and scaling for fitted and carried mods, order stages with
   and without a bench job, handling stats with and without the grip at each quality, the weapon refused while on the
   bench. Run the suite through `SH/seq.sh tests craft-<n>`; it must stay green including the 456 existing tests.

## Feel is judged in play

You cannot play it. So make every handling number data, write a table in your README (`craft/README.md` under the
programme folder) of each number, what it changes on screen, and the bare and gripped values, and write a native
capture script (`unity/tools/capture_pistol_handling_native.py`) that fires the same timed five-shot string with the
bare pistol and with each grip quality at the range plates from the same spot, saves frames through the string and
logs where each shot landed, so the orchestrator can run it and look. You may not build the player or run native
checks yourself.

## Report

Milestone 1 is item 1 and 2 with tests (report, then continue). Milestone 2 is the rest. In each report: what in
`CONTRACT.md` you had to depart from, and the exact hooks you need in `bench`-owned files.
