# Warden kit crafting chain (3 October 2026)

Carl, playtest 3 Oct 2026: "why after shooting the tutorial robots did I get a load of armour. that should be a crafting
mission and not so easy to get. not hard but a mission. collect, craft slowly, craft it to armour. should take scavenging
most of the outer berms to get it."

## What changed

- **No free kit.** `BermsTutorial.kitItems` is empty (code default and the saved *Outer Berms* component) and `kitNotice`
  is blank; `GrantKit()` is kept and does nothing when the list is empty. The colonist still starts in the Field vest
  and boots (`CharacterCatalog.initialEquipment`).
- **No shop bypass.** `field_helmet`, `field_armguards`, `field_gloves`, `field_leggings` are `excludeFromTrade: 1` with
  `buyPrice: 0`: Mira no longer sells them and nobody buys them.
- **Three new salvage materials** (CityCatalog, after `micro_capacitor`; tags `salvage`, `material`, `material:armour`,
  `tier:1`; sell-only, `partsPrice: 0` so they are loot-only):

  | id | name | sell | stack | kg | icon |
  | --- | --- | --- | --- | --- | --- |
  | `strap_webbing` | Strap Webbing | 2 cr | 30 | 0.15 | `webbing-icon` (`UI/Art/webbing.png`) |
  | `padded_liner` | Padded Liner | 3 cr | 20 | 0.3 | `liner-icon` (`UI/Art/liner.png`) |
  | `rivet_stock` | Rivet Stock | 2 cr | 30 | 0.2 | `rivets-icon` (`UI/Art/rivets.png`) |

  Icons: Codex image generation (`icons/gen_icons.sh`, prompts in `icons/prompts.json`), fitted to 192 px by
  `icons/fit_icons.sh`; the metas copy `receiver.png.meta`'s importer settings with a GUID derived from the path.
- **Four Armour schematics** at `station_field_fabricator` (Brann's workbench), `RecipeGroup.Armour` (value 5, appended),
  `knownByDefault: 0`, each revealed by `orderStart` of its own order, no stat or tool requirements:

  | recipe | output | inputs | revealed by |
  | --- | --- | --- | --- |
  | `recipe_field_helmet` | field_helmet | alloy_plate 2, padded_liner 1, strap_webbing 2, rivet_stock 2 | `order_kit_helmet` |
  | `recipe_field_armguards` | field_armguards | alloy_plate 2, strap_webbing 2, rivet_stock 2 | `order_kit_arms` |
  | `recipe_field_gloves` | field_gloves | strap_webbing 2, padded_liner 1, rivet_stock 1, copper_filament 2 | `order_kit_hands` |
  | `recipe_field_leggings` | field_leggings | alloy_plate 3, padded_liner 2, strap_webbing 3, rivet_stock 3 | `order_kit_legs` |

  `recipe_alloy_plate` (3 scrap alloy + 2 tier-one nanites, output `alloy_plate`) is also revealed by `order_kit_helmet`
  (its `order_bore_true` unlock is kept). `groupLabels` gains `Armour`; the fabricator and the pack's schematic chips list
  the group (`PackPanel.groupChips`).
- **Four field orders** (CraftItem, speaker Warden Ossa, no encounter, blank gather guidance = free roam, no urgent start
  or engage line) inserted straight after `order_steady_hands`:

  | index | id | title | reward |
  | --- | --- | --- | --- |
  | 1 | `order_kit_helmet` | Warden Kit: Helm (reports to Brann first, guidance `dealer`) | 10 cr |
  | 2 | `order_kit_arms` | Warden Kit: Bracers | 10 cr |
  | 3 | `order_kit_hands` | Warden Kit: Gloves | 10 cr |
  | 4 | `order_kit_legs` | Warden Kit: Leg Plates | 20 cr |

  Long Arm is now index 5, Plate Carrier 6, Keep the Charge 7, Bore It True 8, The Depot Foreman 9, Mark II 10. Long
  Arm's start line now opens "You're kitted out and your pistol's steadier."
- **Dialogue.** Ossa: `warden_kit` (entries for all four orders). Brann: `kit_brief` (helm order, before the report
  visit), `kit_report` (helm order, Report stage), `kit_gather` (any kit order, Gather), `kit_bench` (any kit order,
  Fabricate). The new nodes have no voice clip yet (`voice: {fileID: 0}`; the text is the subtitle and fallback).
- **Saves.** `FieldOrderState.id` records the current order id (`#freeplay` after the last order); Restore prefers it to
  the numeric index. Older saves without an id keep their index, so a save at index 1 (just after Steady Hands, e.g.
  Carl's) continues at Warden Kit: Helm.

## Drop sources and totals

The whole set needs **7 alloy plate (21 scrap alloy + 14 nanites), 9 webbing, 4 liner, 8 rivets, 2 copper filament**.
Entries are appended to the end of each table; every one has bad-luck protection.

| material | table (sources in the scene) | qty | chance | pity | expected per full sweep |
| --- | --- | --- | --- | --- | --- |
| strap_webbing | `loot_berms_outer` (10 heaps spread over the outer sites) | 1-2 | 0.5 | 2 | ~7.5 |
| strap_webbing | `loot_caravan_strongbox` (caravan) | 1-2 | 1 | 0 | 1.5 |
| padded_liner | `loot_wreck_carcass` (4 truck wrecks) | 1 | 0.45 | 2 | ~1.8 |
| padded_liner | `loot_drone_wreck` (5 drone wrecks) | 1 | 0.35 | 3 | ~1.75 |
| padded_liner | `loot_berms_outpost` (2 outpost lockers) | 1-2 | 0.5 | 2 | ~1.5 |
| rivet_stock | `loot_feral_worker_droid` | 1-2 | 0.35 | 3 | ~0.5 per kill |
| rivet_stock | `loot_feral_gunner` | 1-2 | 0.5 | 2 | ~0.75 per kill |
| rivet_stock | `loot_feral_lancer` | 1-2 | 0.45 | 2 | ~0.7 per kill |
| rivet_stock | `loot_scrap_heap` (default heap table) | 1 | 0.35 | 3 | ~0.35 per heap |

So the webbing needs roughly one sweep of the outer-site heaps (they re-stock after 4-5 minutes), the liner most of the
wrecks and lockers, and the rivets a dozen or so droid kills. The first-contact scrap drones (`loot_feral_scrap_drone`)
drop none; the depot nest's worker droids share the worker table, so they can drop rivets. Scrap alloy, nanites and
copper filament remain buyable from the parts counters, so the plate is never the bottleneck ("not hard but a mission").

## Re-running

```
python3 art/armour_mission_20261003/apply_data.py                 # data, icons and the scene component
python3 art/armour_mission_20261003/apply_data.py --skip-scene    # while another job owns AthenHill.unity
python3 art/armour_mission_20261003/staged_cs/apply_cs.py [--check]  # the C# and test edits (idempotent)
```

Run after `art/tutorial_set_20261002/apply_data.py`, `art/rifle_armour_20261002/apply_data.py` and
`art/next_level_20261002/*/apply_data.py`. Both scripts take `--root` (an `Assets/AthenHill` copy) for dry runs, skip
what is already present, back up live files once to `backup/`, and the data script parses the edited assets with pyyaml.
Afterwards in Unity: compile, `AthenHill.Editor.CraftingDataExporter.Export` (refreshes
`Data/Crafting/Export/ward-crafting.v1.json`), Edit Mode tests.

Clobber risks: `SalvageShopPass` `data` rewrites Brann's dialogue and the order texts (re-run this script after it);
`GameplayV2Content.BuildOrders` only with `GAMEPLAY_V2_FORCE=1`. `NpcVoiceAudit.VerifyAndBuild` expects 15 Brann and 6
Ossa nodes, all voiced; it will refuse the build until the five new nodes are voiced and its counts updated (19 / 7).
