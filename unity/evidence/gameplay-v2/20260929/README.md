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

## M2 — loot v2, caches, scrap heaps, Depot Foreman

- `Scripts/Loot/LootBook.cs`: `LootRng` (SplitMix64; the whole state is one 64-bit value, saved as hex),
  `LootBook` (declared-order rolls, min–max quantities, per table+item consecutive-miss counters with
  `pityAfter` bad-luck protection, `guaranteeUntilCollected` for story parts), `SalvageContents` (collect what
  fits in one pack transaction, keep the rest), `SalvageSearch` (search/cancel/respawn clock).
- `SalvageCache` (prefab `Prefabs/OuterBerms/SalvageCache.prefab`): Meshy industrial-scrap stack at uniform 0.36
  scale, no collider, emissive beacon + point light + motes coloured by the best rarity inside (Common warm white,
  Uncommon Ward cyan, Rare amber). E collects; partial collection leaves the rest inside with a notice.
  Droid caches are ground-snapped at the wreck and despawn when the encounter re-forms (`LootSource.Revived`).
- `SalvageNode` (prefab `SalvageHeapNode.prefab`, marker light + motes, no mesh): E → 1.2 s search that cancels on
  >0.6 m movement or any non-Play state; rolls into the pack, leftovers go to a cache beside the heap; respawn 270 s
  of play time. The HUD shows search progress and a rarity-coloured pickup toast (`CombatHud`).
- `LootSource` audit fix: a kill is marked paid only when the payout succeeded; otherwise it retries each frame.
- `FeralDepotForeman.prefab`: prefab **variant** of FeralWorkerDroid — uniform scale 1.3, 400 HP (4×), strike 30,
  wind-up 1.0 s, chase 2.5, stagger immunity 5 s, crimson optics/eye light, tinted body material
  `RB_ForemanDroid.mat`, voice pitch 0.78, loot `loot_depot_foreman`. No behaviour fork.

| Table | Entries (min–max, chance, pity) |
|---|---|
| loot_feral_scrap_drone | alloy 1–2; nanites 2–3; copper 60% p2; micro capacitor 45% p2; optic lens 30% p3 |
| loot_feral_worker_droid | servo 1; alloy 1–2; nanites 1–2; copper 65% p2; micro capacitor 20% p4; actuator 6% |
| loot_depot_foreman | core (until collected once); actuator 1–2; lattice shard 50% p1; alloy 2–4; nanites 3–5; capacitor 1–2 60% p1; servo 50% |
| loot_scrap_heap | alloy 1–3 90% p1; nanites 1–2 70% p2; copper 1–2 60% p2; capacitor 20% p4; optic 8%; lattice shard 3% |
| loot_wreck_carcass | alloy 1–3; servo 35% p3; nanites 80% p2; copper 50% p2; capacitor 15% p5; actuator 4%; lattice 2% |
| loot_drone_wreck | alloy 1–2; capacitor 35% p3; optic 30% p3; nanites 80% p2; copper 50% p2 |

M2 results: EditMode **111/111 passed** (12 new in `LootTests`, including exact SplitMix64 vectors and seeded
roll assertions). Dev build **Succeeded, 0 errors, 348 warnings**. Scene wiring (cache prefab binding, heap
placement, Foreman encounter) is done by the M3 installer; until it runs, drops fall back to direct pickup.
