# Progress — timed crafting and two native flakes (3 October 2026)

- [x] `CraftRecipe.craftSeconds`; `CraftJob` and begin/tick/cancel in `CraftingModel` (atomic commit through `TryCraft`).
- [x] `CraftingSession`: timer in `Update`, cancel on leaving the bench (Changed + Update backstop) and on damage,
      notices, audio cues, `CraftFinished`; Fit/Remove wait while working.
- [x] `FabricatorPanel` + UXML/USS: progress strip, time left, Cancel (keyboard reachable, focused while working),
      bench time in tooltips and description, "Working" state, reduced-motion stepping.
- [x] Data: `apply_data.py` (15 recipes), `CraftingDataExporter` exports and range-checks `craftSeconds`; export refreshed.
- [x] Edit Mode tests: `TimedCraftingTests` (9) + `HudPanelsTests` timer completion. Runs r1 and r2 under
      `unity/evidence/timed-crafting/20261003/` (see the `.summary` files).
- [x] Native check scripts updated (not run): salvage shop and rifle quest wait for the bench timer.
- [x] Flakes: rifle-quest depot marker (check: level pitch, face the marker's own target, diagnostics) and enemies
      cache prompt (check navigation + `caches` in `crafting.json`); see FLAKES.md.
- [x] Docs: EDITING.md, DESIGN.md, AGENTS.md.
- [ ] Native batch (main session): salvage shop, rifle quest, next-level enemies, city loop, range tutorial.
- [ ] Carl's acceptance of the times (all in one table in README.md; 0 = instant).
