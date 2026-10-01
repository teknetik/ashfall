# Character progression and equipment

Implementation record for the native Unity game, 1 October 2026. The inventory,
crafting and loadout systems extend the saved Ward city. No scene or environment
assets are part of this change.

## Existing systems reused

- `ShopModel` remains the authoritative item and credit transaction boundary.
  Item IDs and stacks remain in `CityCatalog.asset`; trade, loot and fabrication
  still commit through one pack transaction.
- `CraftingModel` owns known schematics, recipe validation, crafted item counts
  and fitted weapon mods. `CraftingSession` retains the nearby fabricator and
  world pickup flow.
- `WardSaveGame` owns the versioned JSON save and autosave lifecycle.
- `PackPanel`, `CityHUD.uxml` and `CityHUD.uss` remain the inventory surface;
  `PlayerCombat` and `Health` consume calculated combat values.

## Data and integration

1. `CharacterCatalog.asset` defines attributes, skill dependencies, derived stat
   dependencies, item-slot compatibility, installation and operating requirements,
   equipment modifiers, storage bonuses and implant upgrades. `CharacterModel`
   calculates final values from base/trained inputs, level, equipment and effects.
2. `CityCatalog.asset` gives each item a mass. Pack additions are validated against
   both physical carrying ability and installed storage capacity. The first
   storage device is a field backpack; future devices can add capacity through
   catalog modifiers without fixing their fictional mechanism now.
3. Crafting recipes define knowledge, materials, skill thresholds, tools,
   workstation and weapon socket layout independently. Each weapon definition
   has a loadout; the existing scrap-pistol loadout remains the legacy alias for
   field orders and pistol presentation.
4. The inventory's character area exposes Primary, Secondary, Stats, Implants and
   Armour, plus a storage location. Item and socket moves call the model; the UI
   updates only after a successful transaction. The current combat draw remains
   gated by the Outer Berms primer.
5. Save version 2 stores attributes, skills, level/points, equipment and all
   weapon loadouts as authoritative inputs. Version 1 restores catalog character
   defaults and grants the legacy pistol from the saved primer stage. Calculated
   stats are regenerated, not saved.

## Verification and rollout

- The full Edit Mode suite passed on 1 October 2026: 195/195 tests, including
  progression, requirements, storage and carrying limits, crafting, weapon mods,
  UI actions, and both save versions.
- The native Linux build and real-input inventory/Continue check are recorded
  separately under `unity/evidence/character-progression/20261001/`; use that
  evidence to distinguish verified routes from Edit Mode coverage.

The current stack inventory gives one fitted loadout per weapon definition. A
future item-instance model will be needed to own separate mod sets on two copies
of the same weapon. The existing characters and equipment art are unchanged by
this systems pass.
