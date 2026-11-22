# SimReady Central Asset Library for Ashfall (Ward / Athen Hill)

**72 curated, metric, PBR-baked 3D assets** pulled from [NVIDIA-Omniverse/simready-central](https://github.com/NVIDIA-Omniverse/simready-central) and processed through the local Blender 5.2.2 LTS pipeline.

## Quick Start for Claude / Agents

- **Master machine-readable index:** [`catalog.json`](catalog.json) (all 72 assets with full semantic tags, placement recommendations, dimensions, triangle counts, and separable part nodes).
- **Per-asset folder:** `assets/<id>/` contains:
  - `<id>_LOD0.glb`, `<id>_LOD1.glb`, `<id>_LOD2.glb` — joined static prop meshes with embedded glTF 2.0 PBR textures (`baseColorTexture`, `normalTexture`, `metallicRoughnessTexture`, `occlusionTexture`), grounded at `(0, 0, 0)` in metres.
  - `<id>_parts.glb` — multi-node GLB preserving all separable sub-parts (`<id>_<part>`) for **Crafting Studio** assembly jobs (`art/crafting_studio_20261121`), hinged toolbox lids, spinning grinder discs, movable vise jaws, or removable respirator filters.
  - `textures/` — standalone PNG maps including pre-packed **Unity URP Lit Mask maps** (`*_Mask.png`: `R = Metallic`, `G = Occlusion`, `B = 0`, `A = Smoothness = 1 - Roughness`) alongside `*_BaseMap.png`, `*_Normal.png`, and `*_ORM.png`.
  - `meta.json` — single-asset metadata card.
  - `thumbnail.png` — preview render from the SimReady package.
- **Contact sheets:** `review/sheet_*.png` (Blender Cycles ortho grids with a 1.8 m human scale reference).

## Asset Summary Table

| ID | Title | Category | Size (W×H×D m) | Parts | LOD0 / 1 / 2 Tris | Where to Use in Ward / Berms |
| --- | --- | --- | --- | --- | --- | --- |
| `bench_vise` | Heavy Workshop Bench Vise | `bench_fixture` | 0.30×0.69×0.66 | 21 | 30,000 / 7,500 / 2,379 | Salvage shop interior (Brann's workbench holder fixture); Crafting Studio (`station.json` holder role) |
| `bar_clamp` | Quick-Release Bar Clamp | `hand_tool` | 0.45×0.05×0.18 | 17 | 29,999 / 7,496 / 3,043 | Field Supply interior (Tamsin's armour/pack crafting table holder); Salvage shop workbench (clamping alloy stock or grip plates) |
| `g_clamp` | Worn Cast-Frame G-Clamp (C-Clamp) | `hand_tool` | 0.13×0.22×0.02 | 9 | 29,998 / 7,498 / 2,398 | Salvage shop workbench (`Steady Hands` / Crafting Studio secondary clamp); Repairs shop welding canopy |
| `angle_grinder` | Corded Industrial Angle Grinder | `power_tool` | 0.21×0.10×0.61 | 21 | 29,999 / 7,499 / 2,398 | Salvage shop workbench (`tool:grinder` fixed bench tool); Tool Exchange sci-fi/industrial tool display |
| `power_drill` | Industrial Cordless Power Drill | `power_tool` | 0.07×0.21×0.23 | 11 | 29,999 / 7,499 / 2,399 | Salvage shop workbench (`op: drill_pattern` tool); Tool Exchange display shelf |
| `handheld_welding_shield` | Handheld Welder's Face Shield | `workshop_ppe` | 0.25×0.44×0.15 | 4 | 13,562 / 3,390 / 1,084 | Salvage shop workbench / hoist bay; Repairs shop forge rack and welding cart |
| `anvil` | Forged Steel Blacksmith Anvil | `bench_fixture` | 0.35×0.17×0.17 | 1 | 17,220 / 4,304 / 1,376 | Repairs shop scrap forge under the braced canopy; Salvage shop interior heavy metalworking corner |
| `screwdriver` | Workshop Slotted/Phillips Screwdriver | `hand_tool` | 0.04×0.04×0.30 | 3 | 7,340 / 1,834 / 586 | Crafting Studio tool roll (`tool:screwdriver`); Salvage shop workbench tray |
| `hammer` | Machinist Ball-Peen / Claw Hammer | `hand_tool` | 0.12×0.03×0.28 | 3 | 30,000 / 7,500 / 2,400 | Crafting Studio bench tool roll; Salvage shop workbench |
| `monkey_wrench` | Heavy Adjustable Pipe / Monkey Wrench | `hand_tool` | 0.06×0.01×0.25 | 4 | 26,150 / 6,536 / 2,092 | Air + Water shop frontage and filter bank; Yard mechanic service loop |
| `spanner` | Drop-Forged Combination Spanner | `hand_tool` | 0.19×0.01×0.05 | 1 | 2,878 / 718 / 230 | Crafting Studio bench tool roll; Salvage shop counter and pegboard |
| `socket_ratchet_wrench` | Reversible Socket Ratchet Wrench | `hand_tool` | 0.04×0.26×0.04 | 13 | 30,000 / 7,500 / 2,400 | Crafting Studio bench (`op: fasten` torque tool); Tool Exchange display |
| `pliers` | Insulated Grip Lineman/Needle Pliers | `hand_tool` | 0.06×0.03×0.17 | 2 | 29,998 / 7,498 / 2,398 | Crafting Studio bench tool roll; Relay Works electronics bench |
| `combination_pliers` | Steel Combination Pliers | `hand_tool` | 0.07×0.21×0.01 | 11 | 30,000 / 7,500 / 2,400 | Field Toolkit sub-part; Crafting Studio bench |
| `split_joint_pliers` | Worn Slip-Joint Pliers | `hand_tool` | 0.07×0.30×0.02 | 12 | 30,000 / 7,500 / 2,400 | Crafting Studio close-up bench tool; Salvage shop workbench |
| `industrial_shears` | Heavy Tin Snips / Industrial Shears | `hand_tool` | 0.45×0.26×0.07 | 17 | 29,998 / 7,498 / 2,394 | Field Supply interior (Tamsin's armour/pack table); Thread + Hide shop balcony/counter |
| `utility_knife` | Retractable Cast-Metal Box Cutter / Utility Knife | `hand_tool` | 0.05×0.02×0.19 | 28 | 23,698 / 5,924 / 1,893 | Crafting Studio bench (`op: solder_join` / lead stripping); Field Supply worktable |
| `puukko_knife` | Fixed-Blade Field Utility Knife | `hand_tool` | 0.03×0.05×0.19 | 1 | 30,000 / 7,499 / 3,805 | Karaveen market stalls (Nadje); Field Supply / Thread + Hide leatherwork bench |
| `hand_saw` | Workshop Hand Saw | `hand_tool` | 0.54×0.12×0.02 | 8 | 25,014 / 6,252 / 2,000 | Salvage shop pegboard / timber deck; Warden training range firing bay timber construction |
| `crowbar` | Forged Steel Wrecking / Pry Bar | `hand_tool` | 0.08×0.04×0.38 | 2 | 8,766 / 2,190 / 700 | Outer Berms salvage caches and scrap heaps; Salvage shop counter / scrap skip |
| `scraper` | Steel Putty / Surface Scraper | `hand_tool` | 0.05×0.02×0.19 | 4 | 11,896 / 2,974 / 950 | Crafting Studio bench (`op: clean` / mould prep); Salvage shop workbench |
| `vernier_calipers` | Precision Stainless Vernier Calipers | `measuring_tool` | 0.23×0.01×0.08 | 6 | 30,000 / 7,499 / 2,400 | Crafting Studio bench (quality / tolerance inspection prop); Tool Exchange precision display |
| `carpenter_square` | Steel L-Square / Layout Rule | `measuring_tool` | 0.30×0.00×0.20 | 1 | 28 / 28 / 28 | Crafting Studio bench (`op: cut_from_stock` scribing guide); Field Supply pattern table |
| `shovel` | Long-Handled Spade / Shovel | `hand_tool` | 0.22×0.08×0.97 | 3 | 29,998 / 7,498 / 2,398 | West Gate sandbag bastions and wall-foot sand drifts; Hydroponics yard compost and potting area |
| `testingTool_multimeter_a01` | Digital Diagnostic Multimeter | `diagnostic_tool` | 0.21×0.05×0.21 | 1 | 30,000 / 7,500 / 2,399 | Crafting Studio bench (`s3.test` continuity / voltage tester); Relay Works counter and storefront |
| `testingTool_battery_analyzer_a01` | Charge-Cell & Battery Load Analyzer | `diagnostic_tool` | 0.41×0.27×0.29 | 17 | 30,000 / 7,500 / 2,394 | Crafting Studio bench (charge-cell upgrade jobs); Warden training range drone charging apron |
| `desk_lamp` | Articulated Metal Architect / Bench Task Lamp | `lighting` | 0.51×0.79×0.19 | 62 | 30,000 / 7,500 / 2,372 | Crafting Studio station task lamp; Player container home fold-down table |
| `gear_meshing_kit` | Precision Spur Gear & Shaft Meshing Set | `salvage_component` | 0.15×0.04×0.13 | 6 | 30,000 / 7,497 / 2,390 | Crafting Studio parts tray / servo teardown sub-parts; Salvage shop counter parts bins |
| `hardware_gear_large_a02` | Heavy Industrial Steel Drive Gear | `salvage_component` | 0.09×0.04×0.09 | 1 | 21,752 / 5,438 / 1,740 | Salvage shop scrap skip and counter shelves; Outer Berms droid wreck loot / salvage caches |
| `consumable_bearing_ball_a01` | Deep-Groove Steel Ball Bearing | `salvage_component` | 0.04×0.01×0.04 | 1 | 14,132 / 3,532 / 1,130 | Crafting Studio bench (`op: clean` spin test / bearing seat); Salvage shop parts dish |
| `consumable_fuse_relay_a01` | Industrial Plug-In Relay & Blade Module | `salvage_component` | 0.06×0.03×0.08 | 1 | 30,000 / 7,499 / 2,400 | Crafting Studio (`op: plug` / cell bus module); Relay Works counter stock |
| `aircraft_ground_power_connector` | Heavy Multi-Pin High-Voltage Power Coupler | `salvage_component` | 0.16×0.23×0.32 | 50 | 30,000 / 7,500 / 2,396 | Lattice Jack / Quantum Tube node power cabling; Warden training range drone charging docks |
| `data_connector_pack` | Modular Industrial Data & Sensor Connector Set | `salvage_component` | 0.25×0.04×0.27 | 35 | 30,000 / 7,500 / 2,240 | Crafting Studio wiring/sensor jobs (`op: unplug` / `op: plug`); Relay Works parts trays |
| `butt_hinge` | Machined Steel Pin Hinge | `salvage_component` | 0.07×0.10×0.01 | 5 | 30,000 / 7,500 / 2,400 | Crafting Studio (`op: drive_pin` hardware part); Salvage shop hardware bins |
| `airSystem_air_filter_box_a01` | Industrial Air Intake Filter Housing | `salvage_component` | 0.31×0.30×0.20 | 1 | 30,000 / 7,499 / 2,400 | Air + Water shop porch filter bank; East yard field generator intake spare |
| `pegboard` | Perforated Steel Workshop Wall Pegboard | `workshop_furniture` | 1.20×0.60×0.02 | 1 | 13,552 / 6,016 / 6,016 | Salvage shop interior wall behind `SS_Workbench`; Field Supply interior workshop wall |
| `workbench_trolley` | Mobile Steel Workbench & Tool Trolley | `workshop_furniture` | 0.66×0.75×1.03 | 98 | 30,000 / 7,500 / 2,545 | Salvage shop interior beside the hoist monorail; Warden training range drone service apron |
| `workshop_trolley_fetra_2436` | Multi-Tier Workshop Service Cart | `workshop_furniture` | 1.22×0.93×0.65 | 53 | 30,000 / 7,500 / 2,394 | Salvage shop interior (staging cart next to workbench); Hydroponics yard dosing trolley |
| `industrial_cabinet` | Heavy Steel Double-Door Workshop Cabinet | `workshop_furniture` | 1.20×1.90×0.83 | 84 | 29,999 / 7,497 / 3,088 | Salvage shop interior back wall; Field Supply interior stock storage |
| `storage_locker_double_bench_b01` | Double Crew Locker with Integrated Bench Seat | `workshop_furniture` | 0.64×2.09×0.83 | 9 | 30,000 / 7,500 / 2,388 | Warden training range prep area; West Gate Warden post (Ossa & Rell) |
| `cabinet_drum_flammable_a02` | Hazardous / Flammable Liquid Safety Cabinet | `workshop_furniture` | 0.87×1.65×0.88 | 8 | 30,000 / 9,634 / 9,634 | Salvage shop interior (solvent & nanite reagent storage); Repairs shop forge / fuel bay |
| `storage_rack` | Heavy-Duty Steel Pallet & Parts Shelving Rack | `workshop_furniture` | 2.70×3.01×1.05 | 102 | 30,000 / 10,402 / 10,402 | Salvage shop interior side wall; Node 07 Quantum Tube goods dock (Pell's bays) |
| `wooden_shelving_worn` | Weathered Timber Shop Shelving Unit | `workshop_furniture` | 1.04×1.80×0.43 | 1 | 12,192 / 3,048 / 974 | Basic General interior/back wall (Mira); Karaveen market stalls (Nadje) |
| `red_tool_chest` | Multi-Drawer Machinist Tool Chest | `workshop_storage` | 0.63×0.26×0.28 | 57 | 20,672 / 5,168 / 1,652 | Salvage shop workbench corner; Crafting Studio (`toolStore` role alternative) |
| `red_metal_toolbox` | Portable Cantilever Steel Toolbox | `workshop_storage` | 0.50×0.34×0.26 | 57 | 30,000 / 7,500 / 2,400 | Field Toolkit (`field_toolkit`) world/bench item visual; Torr's fixer post |
| `hinged_toolbox` | Hinged Rugged Field Utility Case | `workshop_storage` | 0.57×0.29×0.32 | 66 | 30,000 / 7,500 / 2,400 | Outer Berms waystation and salvage caches; Warden training range repair bench |
| `hard_equipment_case` | Pelican-Style Hard Tactical Equipment Case | `containers_cargo` | 0.63×0.31×0.48 | 90 | 30,000 / 7,497 / 2,391 | Outer Berms elite POI strongboxes (Relay knoll, Caravan strongbox, Southern cache); Field Supply weapon/armour counter (Tamsin) |
| `stackable_parts_bin` | Open-Front Stackable Workshop Parts Bin | `workshop_storage` | 0.44×0.29×0.47 | 1 | 30,000 / 7,500 / 2,400 | Crafting Studio bench (`dish` / `scrap` role for removed fasteners and offcuts); Salvage shop shelves and counter |
| `plastic_shelf_bin` | Narrow Shelf Organizer Bin | `workshop_storage` | 0.62×0.15×0.20 | 1 | 3,544 / 886 / 282 | Crafting Studio bench (`role: dish` fastener tray); Relay Works & Tool Exchange shelves |
| `plastic_compartment_tray` | Divided Component Sorting Tray | `workshop_storage` | 0.62×0.11×0.42 | 1 | 30,000 / 7,500 / 2,400 | Crafting Studio bench (`dish` / parts sorting tray); Salvage shop workbench |
| `industrial_pipe_valve` | Flanged Cast-Iron Industrial Pipe Valve with Handwheel | `infrastructure` | 0.48×0.59×0.36 | 33 | 30,000 / 7,500 / 2,382 | Air + Water shop filter bank and steam pipes; Water ration taps behind Vanguard Hall (Oren's water-carrier stop) |
| `warehouse_EF_electricPanel_a01` | Wall-Mounted High-Voltage Breaker & Junction Box | `infrastructure` | 0.15×0.35×0.19 | 4 | 18,542 / 4,634 / 1,482 | Building facades at conduit drop terminations (`Ward rooftops` pass); Relay Works exterior/interior wall |
| `signal_tower` | Industrial Stack Light / Status Signal Beacon | `infrastructure` | 0.10×0.64×0.10 | 8 | 30,000 / 7,500 / 2,400 | Node 07 Quantum Tube goods dock (transfer active beacon); West Gate portal / Ossa's dust-front warning post |
| `power_strip` | Bench Multi-Outlet Power Strip & Cord | `infrastructure` | 0.84×0.04×0.07 | 14 | 29,999 / 7,498 / 2,398 | Crafting Studio bench back rail (powering cure lamp & solder iron); Relay Works counter |
| `gas_cylinder` | High-Pressure Industrial Welding Gas Cylinder | `infrastructure` | 0.22×1.40×0.22 | 5 | 17,868 / 4,466 / 1,428 | Repairs shop forge gas rack; Salvage shop interior welding corner |
| `fire_extinguisher` | Red Steel Dry-Chemical Fire Extinguisher | `infrastructure` | 0.21×0.50×0.12 | 16 | 30,000 / 7,500 / 2,400 | Salvage shop interior pillar beside workbench; Repairs shop forge post |
| `machine_guard` | Yellow Steel Wire-Mesh Safety Partition / Machine Guard | `infrastructure` | 1.37×2.00×0.12 | 39 | 30,000 / 7,500 / 2,712 | Node 07 Quantum Tube goods dock bay divider; Salvage shop hoist bay perimeter |
| `h_frame_scaffolding` | Tubular Steel H-Frame Repair Scaffolding | `infrastructure` | 1.68×1.80×0.97 | 24 | 30,000 / 7,497 / 4,360 | AgainstSalvage shop rubble-patched breach; Perimeter wall collapse repair zones |
| `ladder` | Industrial Aluminum Step / Leaning Ladder | `infrastructure` | 0.48×3.14×0.11 | 25 | 29,998 / 7,498 / 2,398 | Rear service alleys leaning against shop eaves; South-wall container homes roof access |
| `concrete_barrier` | Precast Jersey Concrete Blast / Road Barrier | `infrastructure` | 3.00×1.37×0.79 | 1 | 564 / 400 / 120 | Warden training range machine lane cover barricades; West Gate approach road chicane |
| `platform_dolly` | Four-Wheel Flatbed Cargo Platform Dolly | `logistics_cargo` | 0.85×0.19×0.54 | 59 | 30,000 / 7,500 / 2,384 | Node 07 Quantum Tube goods dock (Pell's bays 1 & 2); Karaveen market cargo unloading zone |
| `wheelbarrow` | Heavy Steel-Tray Construction & Garden Wheelbarrow | `logistics_cargo` | 0.76×0.76×1.39 | 26 | 29,999 / 7,498 / 2,399 | Hydroponics working yard (compost & soil vignettes); Salvage shop rubble breach |
| `pallet` | Standard Timber Cargo Pallet | `logistics_cargo` | 1.00×0.14×1.00 | 1 | 30,000 / 7,500 / 2,798 | Node 07 Quantum Tube goods dock bays; Karaveen market caravan stock overflow |
| `container_box` | Ribbed Industrial Logistics Tote Box | `logistics_cargo` | 0.59×0.28×0.40 | 1 | 30,000 / 7,500 / 2,400 | Node 07 Quantum Tube goods dock; Hydroponics harvest crates |
| `attached_lid_tote` | Interlocking Hinged-Lid Distribution Tote | `logistics_cargo` | 0.60×0.32×0.40 | 5 | 29,578 / 7,393 / 2,363 | Node 07 Quantum Tube goods dock; Outer Berms Warden waystation supplies |
| `small_load_carrier` | KLT Modular Factory Parts Carrier Crate | `logistics_cargo` | 0.40×0.15×0.30 | 5 | 29,998 / 7,391 / 2,284 | Outer Berms rusted conveyor spines and collapsed processing halls; Salvage shop sorted droid parts |
| `steel_drum` | 200L Ribbed Industrial Steel Barrel | `logistics_cargo` | 0.60×0.88×0.60 | 3 | 30,000 / 7,500 / 2,399 | East service yard fuel dump; Air + Water water reserve drums |
| `jerrycan` | Stamped Steel 20L Fuel / Water Jerrycan | `logistics_cargo` | 0.29×0.42×0.29 | 3 | 29,999 / 7,499 / 2,399 | East service yard field generator; Water ration taps behind Vanguard Hall (Oren's stop) |
| `military_canteen` | Weathered Field Water Canteen | `colony_life` | 0.14×0.21×0.09 | 1 | 30,000 / 7,500 / 2,399 | Basic General counter stock (Mira's water flask visual); Oren's water-carrier hand/stop prop (`AGENTS.md` notes 'Oren's drink is an empty hand') |
| `metal_lunch_box` | Domed Steel Worker's Ration Tin / Lunch Box | `colony_life` | 0.29×0.12×0.22 | 20 | 15,632 / 3,908 / 1,250 | Repairs shop tea-break stool vignette; Player container home fold-down table |
| `respirator` | Dual-Cartridge Dust & Nanite Half-Mask Respirator | `colony_life` | 0.16×0.12×0.20 | 7 | 30,000 / 7,500 / 2,399 | Field Supply counter & shelves (Tamsin's survival gear); Salvage shop workbench (nanite paste/grinding protection) |
| `ppe_eyeProtection_goggles_a01` | Sealed Industrial & Desert Dust Goggles | `colony_life` | 0.11×0.07×0.17 | 3 | 29,999 / 7,499 / 2,398 | Salvage shop workbench; Field Supply counter (Tamsin) |
