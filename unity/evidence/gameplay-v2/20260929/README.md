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

## M3 — field orders, economy, fabricator window v2, scene installer

- `Scripts/Orders/`: `FieldOrderSet` (data: goal FitMod/CollectItem/CraftFromGroup, target, test-fire flag,
  encounter to activate, guidance key, brief, radio lines, rewards; Field Notes templates), pure
  `FieldOrderProgress` (index only moves forward; `Advance` completes met orders in sequence; objective text is built
  from the templates plus live recipe have/need), and the `FieldOrders` component (event-driven evaluation, rewards
  once, completion line then the next briefing after `nextLineDelay`, guidance target/label, Foreman activation).
  The old `CraftingSession.TutorialStep` is gone, which removes the audit bug (re-crafting/re-fitting after Done no
  longer resets the step or repeats Ossa's line). `FieldOrders.LegacyGripStep` keeps the dev-bridge/QA field.
- Orders (`Data/Crafting/WardFieldOrders.asset`): 1 Steady Hands (fit grip + test fire; the primer's closing line
  briefs it) · 2 Keep the Charge (fit Salvaged Capacitor Cell, +20 cr) · 3 Bore It True (fit Bored Alloy Barrel,
  +25 cr) · 4 The Depot Foreman (recover the Foreman Control Core; activates the Foreman, +40 cr) · 5 Mark II
  (fabricate any Mark II mod, +50 cr) · free hunting.
- Economy: `ShopModel.Sell(id,count)` (atomic multi-unit sale), `sellOnly` salvage can't be bought, Basic General's
  *Sell salvage* list (`SalvageSalePanel`, Sell 1 / Sell all, rows update in place). Flask purchase and scrap-coil
  sale are unchanged; Ossa's "the rest of the salvage sells at Basic General" is now true (wording kept).
- Fabricator window (`FabricatorPanel` + `CityHUD.uxml/.uss`): grouped schematic list with Locked/Ready/Fitted/×n
  state (↑/↓ moves), have/need rows (green/red), Fabricate/Fit/Remove with worded reasons, three slot cards, and a
  NOW vs WITH SELECTION stats table with coloured deltas. No literal item IDs or "38 → 31" strings remain in CityHud;
  inventory icons come from `ItemSpec.icon`, tiles and details show rarity.
- **Installer** `AthenHill.Editor.GameplayV2Installer.InstallBatch` (run in this worktree; scene committed):
  sets `CitySession/CraftingSession.cachePrefab`; adds `CitySession/FieldOrders` (guidance fabricator/depot/foreman,
  encounter `foreman`); creates `Outer Berms/Encounters/Depot Foreman · processing hall` (spawn chosen by capsule
  clearance: (-81.0, 0.75, -45.8), respawn 300 s); creates `Outer Berms/Salvage heaps` with 9 nodes — 7 on existing
  depot props (Stripped scrap heap, both Machine debris, Stripped worker droid carcass, Crashed scrap drone,
  Stripped mining droid carcass, the active Depot litter on the service road) and 2 new Meshy scrap heaps (uniform
  0.85) at (-88.5, -17.5) and (-78.5, -27.0) ≥4 m off the road; Landmarks `berms_foreman_hall`,
  `berms_scrap_heap`; and an EditorOnly marker `CitySession/Gameplay v2 · installed (GameplayV2Installer)`. It
  refuses if the marker/FieldOrders exist or the scene is dirty, verifies render-chunk sources are untouched, and
  checks nodes stay clear of colonists/Wardens. Scene diff: 1094 lines added, 3 removed (serialization of removed
  `CraftingSession.tutorial` and re-ordered PlayerCombat fields). Nothing existing moved.
- Dev bridge: state gains `fieldOrders`, weapon `stats`/`baseStats`, `slots`, `craftCounts`; `dev.encounter.*`
  accepts the Foreman encounter after the primer.

M3 results: EditMode **128/128 passed** (new: `FieldOrderTests` 7, `ShopSellTests` 5, `GameplayV2SceneTests` 2,
`HudPanelsTests` 3). Dev build **Succeeded, 0 errors, 348 warnings**. The windows were exercised in EditMode against
the real UXML and catalogs; they have **not** been seen rendered in a native player (integrator QA).
