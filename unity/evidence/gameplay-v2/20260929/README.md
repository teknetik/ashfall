# Gameplay v2 "Scavenger's Arc" — 29 September 2026

Worktree `/home/teknetik/code/ao2-gameplay`, branch `ward/gameplay-v2` (base `f17733c4`). Work in progress;
this file is extended at each milestone. Batch Unity 6000.6.0f1 only (memory-capped `systemd-run` scope);
no Editor GUI and no native player runs were made from this worktree.

## M1 — weapon stats, slots, items, recipes, mods

- `Scripts/Crafting/WeaponLoadout.cs`: `WeaponStats` (8 stats) and a pure `WeaponLoadout` (grip/barrel/cell).
  Effective stat = clamp(round3((base + Σadd) × (1 + Σpercent/100)), minStats, maxStats). Stats are cached and
  recomputed only on a fit/removal/restore (`Changed` event).
- `CraftingModel`: generic `TryFit(item)` (swap returns the old mod in the same `ShopModel.TryApply`, refused on
  `stack_full`), `TryRemove(slot)`, per-recipe craft counts, `Acquire`/`OrderStarted`/`Unlock` schematic reveals,
  `Capture`/`Restore` for saves.
- `PlayerCombat.BindLoadout`: damage, fire interval, range, recoil kick, nano capacity/cost/refill and aim assist
  all come from the bound loadout (serialized fields are only the fallback when unbound). Recoil presentation
  scale = effective recoil / base recoil. `StatsChanged` event; no per-frame lookups.
- `CraftingText`: every failure code becomes words ("Missing parts: 2 × Any capacitor, …").
- Data (`GameplayV2Content.BuildData`, one-time authoring helper; the assets are authoritative):
  `CityCatalog.asset` keeps the first three Basic General rows and all old IDs; adds `rarity`, `sellOnly`, `icon`.

| Item | Rarity | Mira pays | Notes |
|---|---|---:|---|
| scrap_alloy, nanite_residue, copper_filament | Common | 1 | raw salvage |
| droid_servo_damaged, micro_capacitor | Uncommon | 3 | raw salvage |
| optic_lens_cracked (new) | Uncommon | 4 | drones, heaps |
| actuator_intact, lattice_shard, foreman_control_core (new) | Rare | — | not sellable |
| alloy_plate, wound_coil, charge_cell_core (new) | C/C/U | — | fabricated components |
| grip_stabilised_pistol, barrel_bored_alloy, cell_salvaged_capacitor | U | — | Mark I mods |
| grip_gyro_braced, barrel_lattice_focused, cell_overclocked | R | — | Mark II mods |

| Recipe | Inputs | Output effect | Schematic |
|---|---|---|---|
| Wound Copper Coil | copper_filament ×2 + any conductor ×1 (scrap coil preferred) | component | order 2 starts |
| Charge Cell Core | any capacitor ×2 + wound_coil + tier-one nanites ×3 | component | order 2 or first micro capacitor |
| Refined Alloy Plate | scrap_alloy ×3 + tier-one nanites ×2 | component | order 3 starts |
| Stabilised Pistol Grip | any servo + scrap_alloy ×2 + nanites ×5 (unchanged) | recoil −7 | first servo |
| Salvaged Capacitor Cell | charge_cell_core + scrap_alloy ×2 | nano +35, refill +15% | order 2 |
| Bored Alloy Barrel | alloy_plate ×2 + wound_coil | damage +20%, range +10 | order 3 |
| Gyro-Braced Grip | actuator_intact + alloy_plate ×2 | recoil −15, aim assist +1° | Foreman core |
| Lattice-Focused Barrel | lattice_shard + alloy_plate ×2 + wound_coil ×2 + any optic lens | damage +45%, range +25, interval +8% | Foreman core |
| Overclocked Charge Cell | charge_cell_core ×2 + lattice_shard | nano +60, cost −2, refill +30% | Foreman core |

Base Scrap Pistol (taken from the scene's PlayerCombat): damage 34, interval 0.28 s, range 70, recoil 38,
nano 100, 9 per shot, refill 30/s, aim assist 3.5°. The optic lens in the lattice barrel is a deliberate change
from the brief so drone drops have a Mark II use.

M1 results: full EditMode suite **99/99 passed** (82 existing incl. updated `CraftingSliceTests` + 17 new in
`WeaponLoadoutTests` and `RecipeChainTests`). `LinuxBuild.Development` batch build **Succeeded, 0 errors,
348 warnings**. `ward-crafting.v1.json` regenerated (additive fields; schema id unchanged for the dev UI).
