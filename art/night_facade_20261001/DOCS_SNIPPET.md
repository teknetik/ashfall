# Docs snippet for the orchestrator (night facade tune, 1 October 2026)

## For unity/EDITING.md

## Night facade tune (1 October 2026)

Material and light values only; all of them live in `art/night_facade_20261001/facade-tune.json` and are applied by
**NightFacadePass** (`Editor/NightFacadePass.cs`, batch steps `apply`, `verify`, `rollback`; the original values are in
`originals.json`, recorded before the first change).

- **Wall lamps** (the caged `PH_WallLamp` heads on the nine Ward shops and Vanguard Hall, 34 in all): each
  `<lamp> light` under the prefab's **Practical lights** is a **spot** placed 0.15 m further from the wall and 0.1 m
  below its original point, aimed down and 10° out, 140° / 95°, intensity ×1.3, cookie `Art/NightFacade/Textures/NF_WallLampCookie`,
  unshadowed, on the Ward lighting clock (practical + night-only). The bulbs use `NF_WallLampBulb` and the globes
  `NF_WallLampGlass` (both on the clock's emissive list). The edits are in the prefab assets
  (`Prefabs/WardShops/*.prefab`, `Prefabs/VanguardHall/VanguardHall.prefab`), so the scene instances carry no overrides.
  `VH_LampLens` (tree-bed and hill uplights) is unchanged. To retune, edit the `lamps` block and run `apply`: positions
  are always recomputed from the recorded originals. A shop *Build assets* rebuild re-creates point lights and
  `VH_LampLens` bulbs, and *Refresh models and materials* puts `WS_Glass` back on every shop: re-run `apply` after either.
- **West Gate arch bulkheads** (`Prefabs/WestGateArches/WGA_GateA/B`): lens slots on `NF_BulkheadLens` (on the clock's
  emissive list); the *Bulkhead light* sits 0.3 m further from the leaves and leans 8° toward them, 140° / 90°,
  4.2 / 8.5 m, so the leaves and arch A's wicket are lit. Same `apply` (block `bulkheads`); re-run it after a West Gate
  arch prefab rebuild.
- **Shop windows**: `WS_Glass` (Relay Works, Air + Water, Tool Exchange), `Art/NightFacade/Materials/NF_Glass_HallEast`
  (Finery, Field Supply) and `NF_Glass_North` (Salvage, Repairs, Thread + Hide) set the room-lamp intensity
  (`_EmissionColor`), lit fraction, blinds, warm / neutral / cool lamp colours per street. **Athen Hill/Ward Window
  Interior** has a third lamp colour: *Neutral lamp tint* and *Neutral lamp fraction* (0 = the previous two-colour look).
  `VH_Glass` (the hall) is tuned the same way.
- **Ward masonry** `VH_Ashlar` / `VH_AshlarRough`: *Normal Map → Scale* 0.65 (was 1.0) so the worn-rock normal stops
  reading as pillows under grazing lamp light. It is the shared stone of every building on the masonry kit.
- **Defects**: the visible Finery porch streak is the moonlight shadow of *Avenue utility lamp 02*'s mast (the night key
  light; only the warm lamps fill it), not a decal; two orphaned 8 Sep wall-foot decals (*Field Supply and Finery weathering/…/
  Foundation grime 9, 10*) left at the old facade line over the porch are inactive anyway; the floating 13:00 shadow at the hill benches
  was the hoist of the old Tool Exchange jib crane, stripped from *Ward district retrofit/Shop retrofits/Shop retrofits
  Structure* into `Art/NightFacade/Retrofit/Shop_retrofits_Structure_north_avenue_nf.asset` (original asset kept).
- Review cameras `cam_nf_*` (**Night facade review cameras**). Evidence and remaining defects:
  `evidence/night-facade/20261001/README.md`.

## For the AGENTS.md baseline table (one row)

| Night facade tune | 1 Oct 2026 (`art/night_facade_20261001`, `NightFacadePass`): the 34 caged wall lamps of the nine shops and Vanguard Hall are down-and-out cookie spots (no clipped wall discs) with dimmer bulbs and glowing globes, the two West Gate arch bulkheads retuned (lens, spot on the wicket); shop windows on per-street Ward Window Interior materials (lower room light, more blinds, third lamp colour); Ward masonry normal 0.65; orphaned Finery porch decals and the floating jib-hoist remnant (the 13:00 hill-bench shadow) retired. Values in `facade-tune.json`, originals recorded for rollback. Not yet accepted by Carl. |
