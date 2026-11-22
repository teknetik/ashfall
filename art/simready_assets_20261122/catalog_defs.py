"""Curated catalog of NVIDIA SimReady Central assets for Ashfall (Ward / Athen Hill).

Every asset listed here is verified from https://github.com/NVIDIA-Omniverse/simready-central
(`submissions/<namespace>/<dataset>`) under CC-BY-4.0, selected for Tir / Ward lore fit,
and annotated with rich semantic metadata so an agent (Claude / Codex) can cherry-pick
assets by role, location, category, dimensions, or assembly part structure.
"""

ASSETS = [
    # =========================================================================
    # 1. CRAFTING STUDIO & BENCH TOOLS / FIXTURES (Brann's bench, Tamsin's table, Tool Exchange)
    # =========================================================================
    {
        "id": "bench_vise",
        "dataset": "ForgeCAD/simready-assets",
        "url": "https://huggingface.co/datasets/ForgeCAD/simready-assets/resolve/0573053fa2c9174ca2a4678a462ec4dfd3035d59/bench_vise",
        "title": "Heavy Workshop Bench Vise",
        "category": "bench_fixture",
        "subcategory": "holder_clamp",
        "description": "Articulated cast-iron and steel workshop bench vise with separable jaws, lead screw, handle bar, and swivel base.",
        "lore_fit": "Fits Brann's Salvage workbench (`station: brann_metal`) or the Repairs bay as a heavy-duty holder fixture (`role: holder`) for weapon and servo teardown.",
        "where_to_use": [
            "Salvage shop interior (Brann's workbench holder fixture)",
            "Crafting Studio (`station.json` holder role)",
            "Repairs shop porch worktable",
            "Warden training range drone service apron"
        ],
        "recommended_usage": "Use `bench_vise_parts.glb` when separate movable jaw/screw nodes are needed for Crafting Studio clamping (`op: clamp`), or `bench_vise_LOD0..2.glb` as a static workshop prop.",
        "tags": ["tool:vise", "bench", "fixture", "holder", "clamp", "crafting_studio", "separable_parts", "brann", "workshop"]
    },
    {
        "id": "bar_clamp",
        "dataset": "ForgeCAD/simready-assets",
        "url": "https://huggingface.co/datasets/ForgeCAD/simready-assets/resolve/0573053fa2c9174ca2a4678a462ec4dfd3035d59/bar_clamp",
        "title": "Quick-Release Bar Clamp",
        "category": "hand_tool",
        "subcategory": "holder_clamp",
        "description": "Steel-bar trigger clamp with separable sliding jaw, trigger lever, release button, pressure pads, and internal spring/plate parts.",
        "lore_fit": "Ideal clamping fixture for Tamsin's Field Supply soft-goods and armour-plate table or Brann's alloy-sheet cutting setup (`op: cut_from_stock`).",
        "where_to_use": [
            "Field Supply interior (Tamsin's armour/pack crafting table holder)",
            "Salvage shop workbench (clamping alloy stock or grip plates)",
            "Tool Exchange display rack"
        ],
        "recommended_usage": "17 cleanly separated mesh parts in `_parts.glb`; can be used as an interactive clamp in Crafting Studio or static bench dressing in `_LOD0..2.glb`.",
        "tags": ["tool:clamp", "bar_clamp", "bench", "tamsin", "brann", "crafting_studio", "separable_parts", "hand_tool"]
    },
    {
        "id": "g_clamp",
        "dataset": "M-XR/marso-simready",
        "url": "https://huggingface.co/datasets/M-XR/marso-simready/resolve/0bf9664adf0f7fdaace26c3e36a518eaac16fc38/g_clamp",
        "title": "Worn Cast-Frame G-Clamp (C-Clamp)",
        "category": "hand_tool",
        "subcategory": "holder_clamp",
        "description": "Weathered industrial I-braced C-clamp with separable Acme threaded spindle, tommy bar, swivel pressure foot, and worn metal textures.",
        "lore_fit": "Pre-weathered industrial salvage aesthetics matching Ward's worn steel look; great for holding armour shells, nanite moulds, or weapon receivers on a bench.",
        "where_to_use": [
            "Salvage shop workbench (`Steady Hands` / Crafting Studio secondary clamp)",
            "Repairs shop welding canopy",
            "Thread + Hide / Field Supply worktable"
        ],
        "recommended_usage": "Use `_parts.glb` to animate spindle rotation (`part_spindle_core`, `part_captured_tommy_bar_001`) during clamping steps, or `_LOD0..2.glb` for prop dressing.",
        "tags": ["tool:clamp", "g_clamp", "c_clamp", "worn_metal", "crafting_studio", "separable_parts", "bench", "hand_tool"]
    },
    {
        "id": "angle_grinder",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/2980a1372e3c59336b47ff52333fb797be8847de/angle_grinder",
        "title": "Corded Industrial Angle Grinder",
        "category": "power_tool",
        "subcategory": "cutting_grinding",
        "description": "Detailed corded angle grinder with separable abrasive cutting disc, wheel guard, cast-aluminum gear case, side handle, trigger, and bolts.",
        "lore_fit": "Matches `tool:grinder` required in `art/crafting_assembly_20261120/PLAN.md` Phase 2 for cutting scrap alloy plates and stripping rusted droid salvage.",
        "where_to_use": [
            "Salvage shop workbench (`tool:grinder` fixed bench tool)",
            "Tool Exchange sci-fi/industrial tool display",
            "Repairs shop porch and yard mechanic work area",
            "Outer Berms drone service apron"
        ],
        "recommended_usage": "21 separate mesh parts in `_parts.glb` (`grinding_disc` can spin independently); use `_LOD0..2.glb` for bench/shelf placement.",
        "tags": ["tool:grinder", "power_tool", "crafting_studio", "separable_parts", "brann", "salvage", "cutting", "bench"]
    },
    {
        "id": "power_drill",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/795bdea281736a43515671e8264e4cc076e5aa46/power_drill",
        "title": "Industrial Cordless Power Drill",
        "category": "power_tool",
        "subcategory": "drilling_fastening",
        "description": "Heavy-duty hand drill with chuck, bit, trigger, housing, and battery pack.",
        "lore_fit": "Directly supports the Crafting Studio `op: drill_pattern` operation (drilling barrel vent ports and mounting holes in alloy plates).",
        "where_to_use": [
            "Salvage shop workbench (`op: drill_pattern` tool)",
            "Tool Exchange display shelf",
            "Repairs shop counter",
            "Warden training range repair bench"
        ],
        "recommended_usage": "Use `_parts.glb` if chuck/trigger articulation is needed at the bench, or `_LOD0..2.glb` as a workshop prop.",
        "tags": ["tool:drill", "power_tool", "drill_pattern", "crafting_studio", "bench", "brann", "workshop"]
    },
    {
        "id": "handheld_welding_shield",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/82d0aa2f1fd8c0391137a97f54f8ebbac9a331c1/handheld_welding_shield",
        "title": "Handheld Welder's Face Shield",
        "category": "workshop_ppe",
        "subcategory": "welding",
        "description": "Industrial welding mask/shield with darkened filter glass window and grip handle.",
        "lore_fit": "Pairs with welding/nanite-press operations at Brann's forge, the Repairs shop welding cart, and the Warden training range drone bay.",
        "where_to_use": [
            "Salvage shop workbench / hoist bay",
            "Repairs shop forge rack and welding cart",
            "Warden training range drone service apron"
        ],
        "recommended_usage": "Place on workbench corners or hanging on pegboards (`_LOD0..2.glb`).",
        "tags": ["tool:welder", "ppe", "welding", "shield", "mask", "repairs", "salvage", "bench"]
    },
    {
        "id": "anvil",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/2262c37902073849a26c702e032dc1985ea5ebe0/anvil",
        "title": "Forged Steel Blacksmith Anvil",
        "category": "bench_fixture",
        "subcategory": "metalworking",
        "description": "Heavy cast-steel horn anvil with hardy hole and flat working face.",
        "lore_fit": "Lore explicitly notes 'nanite workshops hum beside scrap forges' (`lore.md` §The Ward); perfect for Repairs shop scrap forge or Brann's heavy metalworking corner.",
        "where_to_use": [
            "Repairs shop scrap forge under the braced canopy",
            "Salvage shop interior heavy metalworking corner",
            "Outer Berms ruined fabrication yard"
        ],
        "recommended_usage": "Place on a timber block or heavy stand using `anvil_LOD0..2.glb`.",
        "tags": ["anvil", "forge", "metalworking", "bench_fixture", "repairs", "salvage", "scrap_forge"]
    },
    {
        "id": "screwdriver",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/fc2165bed6ff998e55629d688ca9e9cbf3edf1b5/screwdriver",
        "title": "Workshop Slotted/Phillips Screwdriver",
        "category": "hand_tool",
        "subcategory": "fastening",
        "description": "Hand screwdriver with molded grip handle and machined steel shaft/tip.",
        "lore_fit": "Primary tool in the player's Field Toolkit (`tool:screwdriver`) used in every `unfasten`/`fasten` step at the Crafting Studio bench.",
        "where_to_use": [
            "Crafting Studio tool roll (`tool:screwdriver`)",
            "Salvage shop workbench tray",
            "Field Supply / Tool Exchange counter",
            "Player container home fold-down table"
        ],
        "recommended_usage": "Ready for bench tool roll placement or close-up inspection (`_LOD0..2.glb` or `_parts.glb`).",
        "tags": ["tool:screwdriver", "field_toolkit", "hand_tool", "fastener", "crafting_studio", "bench"]
    },
    {
        "id": "hammer",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/992613f48dad8a95ac5fd19e36d6661ab698ea09/hammer",
        "title": "Machinist Ball-Peen / Claw Hammer",
        "category": "hand_tool",
        "subcategory": "striking",
        "description": "Hand hammer with steel head and ergonomic grip.",
        "lore_fit": "Used for `op: drive_pin`, `op: punch`, and `op: seized_fastener` tap operations at the Crafting Studio bench and general settlement maintenance.",
        "where_to_use": [
            "Crafting Studio bench tool roll",
            "Salvage shop workbench",
            "Repairs shop tool cart",
            "Yard mechanic work loop"
        ],
        "recommended_usage": "Use `_LOD0..2.glb` for bench or tool-cart dressing, or `_parts.glb` for bench animation.",
        "tags": ["tool:hammer", "hand_tool", "drive_pin", "crafting_studio", "bench", "workshop"]
    },
    {
        "id": "monkey_wrench",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/994011821a5367ea393bda6165b72097acae05a8/monkey_wrench",
        "title": "Heavy Adjustable Pipe / Monkey Wrench",
        "category": "hand_tool",
        "subcategory": "wrench",
        "description": "Heavy industrial adjustable wrench with worm-gear jaw.",
        "lore_fit": "Iconic fixer tool for Torr, the yard mechanic, Air + Water pipe maintenance, and Quantum Tube node repairs.",
        "where_to_use": [
            "Air + Water shop frontage and filter bank",
            "Yard mechanic service loop",
            "Salvage shop workbench",
            "Tool Exchange display"
        ],
        "recommended_usage": "Separable jaw parts in `_parts.glb`; static prop in `_LOD0..2.glb`.",
        "tags": ["tool:wrench", "monkey_wrench", "pipe_wrench", "hand_tool", "torr", "mechanic", "air_water"]
    },
    {
        "id": "spanner",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/8390635a7354d5ef26eb443ee0cdd7141dc4733b/spanner",
        "title": "Drop-Forged Combination Spanner",
        "category": "hand_tool",
        "subcategory": "wrench",
        "description": "Machined steel open/box-end spanner wrench.",
        "lore_fit": "Essential hand tool for droid teardown, turret mounting bolts, and workbench tool rolls.",
        "where_to_use": [
            "Crafting Studio bench tool roll",
            "Salvage shop counter and pegboard",
            "Warden training range drone repair bench"
        ],
        "recommended_usage": "Low triangle count; use `_LOD0.glb` directly on benches or pegboards.",
        "tags": ["tool:wrench", "spanner", "hand_tool", "crafting_studio", "bench", "pegboard"]
    },
    {
        "id": "socket_ratchet_wrench",
        "dataset": "projectsim/simready-assets",
        "url": "https://huggingface.co/datasets/projectsim/simready-assets/resolve/545c33fd4e8ce0aaa20c8c0ed41fbd6b2b8b4c4b/socket_ratchet_wrench",
        "title": "Reversible Socket Ratchet Wrench",
        "category": "hand_tool",
        "subcategory": "wrench",
        "description": "Precision socket ratchet driver with knurled handle and reversing pawl.",
        "lore_fit": "Fits torque-window fastening steps (`op: fasten`) on weapon receivers, plate carriers, and droid chassis.",
        "where_to_use": [
            "Crafting Studio bench (`op: fasten` torque tool)",
            "Tool Exchange display",
            "Salvage shop workbench"
        ],
        "recommended_usage": "Use `_parts.glb` if separated head/pawl nodes are needed, or `_LOD0..2.glb` for bench layout.",
        "tags": ["tool:ratchet", "wrench", "fastener", "torque", "crafting_studio", "hand_tool"]
    },
    {
        "id": "pliers",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/e844f6b5bb94e6eabf472e6a6c167cae99550f00/pliers",
        "title": "Insulated Grip Lineman/Needle Pliers",
        "category": "hand_tool",
        "subcategory": "pliers",
        "description": "Pivoting steel pliers with insulated two-tone handles.",
        "lore_fit": "Used in Crafting Studio wiring/lead jobs (`op: unplug`, `op: solder_join`, pulling pins and binding wire).",
        "where_to_use": [
            "Crafting Studio bench tool roll",
            "Relay Works electronics bench",
            "Salvage shop workbench"
        ],
        "recommended_usage": "Pivoting jaws preserved in `_parts.glb`; merged static mesh in `_LOD0..2.glb`.",
        "tags": ["tool:pliers", "hand_tool", "wiring", "crafting_studio", "bench", "electronics"]
    },
    {
        "id": "combination_pliers",
        "dataset": "projectsim/simready-assets",
        "url": "https://huggingface.co/datasets/projectsim/simready-assets/resolve/064473b0b9b5b3abbf674ef08dcc714e121e2c52/combination_pliers",
        "title": "Steel Combination Pliers",
        "category": "hand_tool",
        "subcategory": "pliers",
        "description": "Compact combination pliers with serrated gripping jaws and wire cutter.",
        "lore_fit": "Part of the Field Toolkit for stripping copper filament and pulling cotter pins from damaged servos.",
        "where_to_use": [
            "Field Toolkit sub-part",
            "Crafting Studio bench",
            "Tool Exchange counter"
        ],
        "recommended_usage": "Lightweight 6 MB package; `_parts.glb` keeps left/right jaws separate for hinge animation.",
        "tags": ["tool:pliers", "field_toolkit", "hand_tool", "crafting_studio", "separable_parts"]
    },
    {
        "id": "split_joint_pliers",
        "dataset": "M-XR/marso-simready",
        "url": "https://huggingface.co/datasets/M-XR/marso-simready/resolve/0bf9664adf0f7fdaace26c3e36a518eaac16fc38/split_joint_pliers",
        "title": "Worn Slip-Joint Pliers",
        "category": "hand_tool",
        "subcategory": "pliers",
        "description": "High-detail worn steel slip-joint utility pliers with textured handles and pivot bolt.",
        "lore_fit": "Weathered finish fits close-up 0.3 m bench camera views in Steady Hands / Crafting Studio without looking factory-new.",
        "where_to_use": [
            "Crafting Studio close-up bench tool",
            "Salvage shop workbench",
            "Repairs shop counter"
        ],
        "recommended_usage": "Use `_parts.glb` for articulated jaw movement or `_LOD0..2.glb` for bench dressing.",
        "tags": ["tool:pliers", "worn_metal", "crafting_studio", "separable_parts", "hand_tool", "hero_prop"]
    },
    {
        "id": "industrial_shears",
        "dataset": "projectsim/simready-assets",
        "url": "https://huggingface.co/datasets/projectsim/simready-assets/resolve/826f518ce4a49926d3f1009257acea79e937c0ad/industrial_shears",
        "title": "Heavy Tin Snips / Industrial Shears",
        "category": "hand_tool",
        "subcategory": "cutting",
        "description": "Heavy metal-cutting shears / tin snips with pivot bolt and spring.",
        "lore_fit": "Perfect for Tamsin's ballistic fabric/hide cutting (`op: cut_pattern`) at Field Supply or cutting thin shim sheet at Brann's bench.",
        "where_to_use": [
            "Field Supply interior (Tamsin's armour/pack table)",
            "Thread + Hide shop balcony/counter",
            "Salvage shop workbench"
        ],
        "recommended_usage": "Separable blades in `_parts.glb`; static prop in `_LOD0..2.glb`.",
        "tags": ["tool:shears", "tin_snips", "tamsin", "field_supply", "thread_hide", "crafting_studio", "hand_tool"]
    },
    {
        "id": "utility_knife",
        "dataset": "projectsim/simready-assets",
        "url": "https://huggingface.co/datasets/projectsim/simready-assets/resolve/222634e7e42465afaa3f69ba38be01bc6a9f424e/utility_knife",
        "title": "Retractable Cast-Metal Box Cutter / Utility Knife",
        "category": "hand_tool",
        "subcategory": "cutting",
        "description": "Cast-metal retractable utility knife with segmented snap-off steel blade, thumb slider, and internal ratchet track.",
        "lore_fit": "Used for stripping lead insulation (`op: solder_join`), cutting pack straps, and opening ration/salvage cartons.",
        "where_to_use": [
            "Crafting Studio bench (`op: solder_join` / lead stripping)",
            "Field Supply worktable",
            "Basic General counter (Mira's stock unpacking)",
            "Node 07 goods dock tally desk (Pell)"
        ],
        "recommended_usage": "37 separate internal and external parts in `_parts.glb` (blade and slider move independently); `_LOD0..2.glb` for general prop placement.",
        "tags": ["tool:knife", "utility_knife", "cutting", "crafting_studio", "separable_parts", "hand_tool"]
    },
    {
        "id": "puukko_knife",
        "dataset": "M-XR/marso-simready",
        "url": "https://huggingface.co/datasets/M-XR/marso-simready/resolve/0bf9664adf0f7fdaace26c3e36a518eaac16fc38/puukko_knife",
        "title": "Fixed-Blade Field Utility Knife",
        "category": "hand_tool",
        "subcategory": "cutting",
        "description": "Traditional wooden-handled fixed-blade utility/bushcraft knife with worn steel blade.",
        "lore_fit": "Fits Karaveen traders, hydroponics harvesters (Anso), and Tamsin's leather/hide bench.",
        "where_to_use": [
            "Karaveen market stalls (Nadje)",
            "Field Supply / Thread + Hide leatherwork bench",
            "Hydroponics potting bench",
            "Player container home table"
        ],
        "recommended_usage": "Use `_LOD0..2.glb` as a personal table/stall prop.",
        "tags": ["knife", "field_knife", "karaveen", "tamsin", "hydroponics", "hand_tool"]
    },
    {
        "id": "hand_saw",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/d9da01d3922796c7fe0fad6ccbfa1a272b4c7405/hand_saw",
        "title": "Workshop Hand Saw",
        "category": "hand_tool",
        "subcategory": "cutting",
        "description": "Toothed steel blade hand saw with grip handle.",
        "lore_fit": "Useful for timber barricade construction at the Warden training range, crate repairs, and workshop pegboards.",
        "where_to_use": [
            "Salvage shop pegboard / timber deck",
            "Warden training range firing bay timber construction",
            "Repairs shop porch"
        ],
        "recommended_usage": "Hang on pegboard or lay across wooden crates (`_LOD0..2.glb`).",
        "tags": ["tool:saw", "hand_saw", "hand_tool", "pegboard", "workshop", "timber"]
    },
    {
        "id": "crowbar",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/f6060e0205c8d5ac55a59257a573a4dcb5214950/crowbar",
        "title": "Forged Steel Wrecking / Pry Bar",
        "category": "hand_tool",
        "subcategory": "prying",
        "description": "Gooseneck forged steel crowbar with nail-puller slot and chiseled tip.",
        "lore_fit": "Classic scavenging tool for prying open Berms salvage caches, caravan crates, and jammed droid housings.",
        "where_to_use": [
            "Outer Berms salvage caches and scrap heaps",
            "Salvage shop counter / scrap skip",
            "Karaveen market cargo crates",
            "Node 07 goods dock"
        ],
        "recommended_usage": "Lightweight prop; place leaning against crates or on workbenches (`_LOD0..2.glb`).",
        "tags": ["tool:crowbar", "pry_bar", "salvage", "scavenging", "berms", "crates", "hand_tool"]
    },
    {
        "id": "scraper",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/7cf4ce8486f297e0c82f80d5bea41a72a56fd12f/scraper",
        "title": "Steel Putty / Surface Scraper",
        "category": "hand_tool",
        "subcategory": "cleaning_prep",
        "description": "Flat spring-steel blade scraper with handle.",
        "lore_fit": "Fits Crafting Studio surface-cleaning steps (`op: clean`, scraping corrosion/mould residue off servo cans and nanite seams).",
        "where_to_use": [
            "Crafting Studio bench (`op: clean` / mould prep)",
            "Salvage shop workbench",
            "Repairs shop counter"
        ],
        "recommended_usage": "Use `_LOD0..2.glb` on bench mats.",
        "tags": ["tool:scraper", "cleaning", "crafting_studio", "bench", "hand_tool"]
    },
    {
        "id": "vernier_calipers",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/6ccd7cef25b4eaa9042c58cfc63c729dc675921a/vernier_calipers",
        "title": "Precision Stainless Vernier Calipers",
        "category": "measuring_tool",
        "subcategory": "precision",
        "description": "Machined stainless-steel sliding vernier caliper for internal/external measurement.",
        "lore_fit": "High-craft precision tool for checking barrel thread tolerances (`barrel_thread_m14`), gyro bearing seats, and nanofab components.",
        "where_to_use": [
            "Crafting Studio bench (quality / tolerance inspection prop)",
            "Tool Exchange precision display",
            "Salvage shop workbench (Brann's schematic board area)"
        ],
        "recommended_usage": "Sliding jaw is a separate mesh in `_parts.glb`; `_LOD0..2.glb` for bench layout.",
        "tags": ["tool:calipers", "measuring", "precision", "crafting_studio", "separable_parts", "bench"]
    },
    {
        "id": "carpenter_square",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/f0481f404505cc508b4eaab177855f58442c35c7/carpenter_square",
        "title": "Steel L-Square / Layout Rule",
        "category": "measuring_tool",
        "subcategory": "layout",
        "description": "Stamped steel 90-degree layout square with graduated markings.",
        "lore_fit": "Used during `op: cut_from_stock` to scribe straight cut lines on scrap alloy sheet at the Crafting Studio bench.",
        "where_to_use": [
            "Crafting Studio bench (`op: cut_from_stock` scribing guide)",
            "Field Supply pattern table",
            "Salvage shop workbench"
        ],
        "recommended_usage": "Very light mesh; place flat on workbench mats (`_LOD0.glb`).",
        "tags": ["tool:square", "measuring", "scribe", "cut_from_stock", "crafting_studio", "bench"]
    },
    {
        "id": "shovel",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/e1ed7dae3fb6ea1de2f55e10e1d77caa6a7c661c/shovel",
        "title": "Long-Handled Spade / Shovel",
        "category": "hand_tool",
        "subcategory": "excavation",
        "description": "Steel-blade digging shovel with long shaft.",
        "lore_fit": "Essential for clearing windblown desert sand drifts at the West Gate, digging out half-buried Berms wrecks, and tending hydroponics compost.",
        "where_to_use": [
            "West Gate sandbag bastions and wall-foot sand drifts",
            "Hydroponics yard compost and potting area",
            "Outer Berms excavation sites and waystation"
        ],
        "recommended_usage": "Lean against walls, sandbags, or wheelbarrows using `shovel_LOD0..2.glb`.",
        "tags": ["shovel", "spade", "excavation", "hydroponics", "west_gate", "berms", "hand_tool"]
    },
    {
        "id": "testingTool_multimeter_a01",
        "dataset": "nvidia/simready-assets",
        "url": "https://huggingface.co/datasets/nvidia/simready-assets/resolve/653d91e182011f357cf1644013cc94ddf194d349/testingTool_multimeter_a01",
        "title": "Digital Diagnostic Multimeter",
        "category": "diagnostic_tool",
        "subcategory": "electronics",
        "description": "Handheld digital multimeter with rotary selector dial, LCD screen, and probe ports.",
        "lore_fit": "Directly supports the `electronics` skill in `art/crafting_assembly_20261120/PLAN.md` and continuity testing (`op: solder_join` probe pin marks) on charge cells and servo leads.",
        "where_to_use": [
            "Crafting Studio bench (`s3.test` continuity / voltage tester)",
            "Relay Works counter and storefront",
            "Tool Exchange display",
            "Warden training range drone charging dock"
        ],
        "recommended_usage": "Place on the bench electronics mat or Relay Works counter (`_LOD0..2.glb`).",
        "tags": ["tool:multimeter", "electronics", "diagnostic", "crafting_studio", "relay_works", "bench"]
    },
    {
        "id": "testingTool_battery_analyzer_a01",
        "dataset": "nvidia/simready-assets",
        "url": "https://huggingface.co/datasets/nvidia/simready-assets/resolve/653d91e182011f357cf1644013cc94ddf194d349/testingTool_battery_analyzer_a01",
        "title": "Charge-Cell & Battery Load Analyzer",
        "category": "diagnostic_tool",
        "subcategory": "electronics",
        "description": "Industrial battery/cell diagnostic unit with clamp leads, meters, and rugged housing.",
        "lore_fit": "Fits testing overclocked weapon charge cells (`cell_bus_a`), nano cells, and drone battery packs.",
        "where_to_use": [
            "Crafting Studio bench (charge-cell upgrade jobs)",
            "Warden training range drone charging apron",
            "Relay Works workshop"
        ],
        "recommended_usage": "Use `_LOD0..2.glb` on workbenches or diagnostic carts.",
        "tags": ["battery_analyzer", "charge_cell", "electronics", "diagnostic", "crafting_studio", "drone_apron"]
    },
    {
        "id": "desk_lamp",
        "dataset": "projectsim/simready-assets",
        "url": "https://huggingface.co/datasets/projectsim/simready-assets/resolve/97aba880628d4e6b5ff1845901f27d2a60e57f00/desk_lamp",
        "title": "Articulated Metal Architect / Bench Task Lamp",
        "category": "lighting",
        "subcategory": "bench_lamp",
        "description": "Spring-balanced articulated metal task lamp with conical shade and clamp/base.",
        "lore_fit": "Close-range work light for Crafting Studio stations (Brann's bench, Tamsin's table), Pell's tally desk, or the player's container home fold-down table.",
        "where_to_use": [
            "Crafting Studio station task lamp",
            "Player container home fold-down table",
            "Node 07 goods dock tally desk (Pell)",
            "Field Supply / Salvage shop counters"
        ],
        "recommended_usage": "Separable arm links in `_parts.glb` allow custom posing; `_LOD0..2.glb` for fixed placement.",
        "tags": ["lamp", "task_light", "bench_lamp", "lighting", "crafting_studio", "ward_home", "separable_parts"]
    },

    # =========================================================================
    # 2. MECHANICAL & ELECTRONIC SALVAGE PARTS (Bench Sub-Parts, Loot, Scrap)
    # =========================================================================
    {
        "id": "gear_meshing_kit",
        "dataset": "ForgeCAD/simready-assets",
        "url": "https://huggingface.co/datasets/ForgeCAD/simready-assets/resolve/0573053fa2c9174ca2a4678a462ec4dfd3035d59/gear_meshing_kit",
        "title": "Precision Spur Gear & Shaft Meshing Set",
        "category": "salvage_component",
        "subcategory": "mechanical",
        "description": "Set of machined spur gears, shafts, and mounting base plate.",
        "lore_fit": "Ideal internal sub-parts for droid servo teardown, turret actuator repairs, or loose mechanical salvage on Brann's parts mat.",
        "where_to_use": [
            "Crafting Studio parts tray / servo teardown sub-parts",
            "Salvage shop counter parts bins",
            "Tool Exchange display"
        ],
        "recommended_usage": "Use `_parts.glb` to pull individual gears or shafts for assembly recipes.",
        "tags": ["salvage", "gears", "mechanical", "servo", "droid_parts", "crafting_studio", "separable_parts"]
    },
    {
        "id": "hardware_gear_large_a02",
        "dataset": "nvidia/simready-assets",
        "url": "https://huggingface.co/datasets/nvidia/simready-assets/resolve/21b045a878e13d4ca922f0f8ebc2ff1e84bb06d4/hardware_gear_large_a02",
        "title": "Heavy Industrial Steel Drive Gear",
        "category": "salvage_component",
        "subcategory": "mechanical",
        "description": "Machined heavy industrial steel spur gear with lightened web holes and keyway bore.",
        "lore_fit": "High-detail mechanical salvage from heavy mining droids (Depot Foreman, Scrap Reaper) or conveyor spines in the Outer Berms.",
        "where_to_use": [
            "Salvage shop scrap skip and counter shelves",
            "Outer Berms droid wreck loot / salvage caches",
            "Repairs shop worktable"
        ],
        "recommended_usage": "Use `_LOD0..2.glb` as a standalone salvage item or scatter prop.",
        "tags": ["salvage", "gear", "heavy_machinery", "mining_droid", "berms", "mechanical"]
    },
    {
        "id": "consumable_bearing_ball_a01",
        "dataset": "nvidia/simready-assets",
        "url": "https://huggingface.co/datasets/nvidia/simready-assets/resolve/653d91e182011f357cf1644013cc94ddf194d349/consumable_bearing_ball_a01",
        "title": "Deep-Groove Steel Ball Bearing",
        "category": "salvage_component",
        "subcategory": "mechanical",
        "description": "Machined steel radial ball bearing with inner race, outer race, balls, and cage.",
        "lore_fit": "Directly matches the gyro bearing / actuator bearing cleaned and seated in Steady Hands (`s3.bath` to `s3.spin`, `op: clean`).",
        "where_to_use": [
            "Crafting Studio bench (`op: clean` spin test / bearing seat)",
            "Salvage shop parts dish",
            "Droid salvage loot visual"
        ],
        "recommended_usage": "Use `_LOD0..2.glb` or `_parts.glb` for close-up bench assembly.",
        "tags": ["bearing", "gyro_bearing", "salvage", "mechanical", "steady_hands", "crafting_studio"]
    },
    {
        "id": "consumable_fuse_relay_a01",
        "dataset": "nvidia/simready-assets",
        "url": "https://huggingface.co/datasets/nvidia/simready-assets/resolve/653d91e182011f357cf1644013cc94ddf194d349/consumable_fuse_relay_a01",
        "title": "Industrial Plug-In Relay & Blade Module",
        "category": "salvage_component",
        "subcategory": "electronics",
        "description": "Compact electrical relay block with terminal blade pins and housing.",
        "lore_fit": "Matches `op: unplug`/`plug` keyed electrical modules in weapon cell buses, droid control boards, and Relay Works stock.",
        "where_to_use": [
            "Crafting Studio (`op: plug` / cell bus module)",
            "Relay Works counter stock",
            "Salvage shop electronics bin"
        ],
        "recommended_usage": "Small electronics component (`_LOD0..2.glb`).",
        "tags": ["relay", "fuse", "electronics", "salvage", "cell_bus", "crafting_studio", "relay_works"]
    },
    {
        "id": "aircraft_ground_power_connector",
        "dataset": "ForgeCAD/simready-assets",
        "url": "https://huggingface.co/datasets/ForgeCAD/simready-assets/resolve/0573053fa2c9174ca2a4678a462ec4dfd3035d59/aircraft_ground_power_connector",
        "title": "Heavy Multi-Pin High-Voltage Power Coupler",
        "category": "salvage_component",
        "subcategory": "electronics",
        "description": "Rugged industrial high-current power plug and socket assembly with heavy pins and rubber strain housing.",
        "lore_fit": "Reads as a Quantum Tube field power coupler, drone charging umbilical connector, or heavy weapon cell-bus interface.",
        "where_to_use": [
            "Lattice Jack / Quantum Tube node power cabling",
            "Warden training range drone charging docks",
            "Relay Works high-voltage bench",
            "Crafting Studio heavy cell-bus component"
        ],
        "recommended_usage": "Separable plug/socket parts in `_parts.glb` for `op: plug` operations; `_LOD0..2.glb` for scene dressing.",
        "tags": ["power_connector", "coupler", "quantum_tube", "drone_charger", "electronics", "crafting_studio", "separable_parts"]
    },
    {
        "id": "data_connector_pack",
        "dataset": "ForgeCAD/simready-assets",
        "url": "https://huggingface.co/datasets/ForgeCAD/simready-assets/resolve/0c48fab70fb48d580d58b50319e395b85605512e/data_connector_pack",
        "title": "Modular Industrial Data & Sensor Connector Set",
        "category": "salvage_component",
        "subcategory": "electronics",
        "description": "Assortment of keyed multi-pin data/sensor plugs and receptacles.",
        "lore_fit": "Fits Warden sand-boxed AI targeting sub-routine connectors, droid optic harnesses (`sentinel_optic`), and EYE/HEAD implant sockets.",
        "where_to_use": [
            "Crafting Studio wiring/sensor jobs (`op: unplug` / `op: plug`)",
            "Relay Works parts trays",
            "Salvage shop electronics counter"
        ],
        "recommended_usage": "Individual connectors available in `_parts.glb`.",
        "tags": ["connectors", "wiring", "sensor", "implant", "droid_optic", "crafting_studio", "separable_parts"]
    },
    {
        "id": "butt_hinge",
        "dataset": "projectsim/simready-assets",
        "url": "https://huggingface.co/datasets/projectsim/simready-assets/resolve/e4005d73f7e316cbf4a0442dfa6ccc5a7ac0602d/butt_hinge",
        "title": "Machined Steel Pin Hinge",
        "category": "salvage_component",
        "subcategory": "hardware",
        "description": "Two-leaf steel butt hinge with countersunk screw holes and removable center pin.",
        "lore_fit": "Directly usable for `op: drive_pin` and `op: unfasten` practice jobs, ammo crate lids, or locker doors.",
        "where_to_use": [
            "Crafting Studio (`op: drive_pin` hardware part)",
            "Salvage shop hardware bins"
        ],
        "recommended_usage": "Separable leaves and pin in `_parts.glb`.",
        "tags": ["hinge", "hardware", "drive_pin", "fastener", "crafting_studio", "separable_parts"]
    },
    {
        "id": "airSystem_air_filter_box_a01",
        "dataset": "nvidia/simready-assets",
        "url": "https://huggingface.co/datasets/nvidia/simready-assets/resolve/653d91e182011f357cf1644013cc94ddf194d349/airSystem_air_filter_box_a01",
        "title": "Industrial Air Intake Filter Housing",
        "category": "salvage_component",
        "subcategory": "filtration",
        "description": "Molded black industrial air filter housing with metal clips and intake duct neck.",
        "lore_fit": "Fits Air + Water's atmospheric dust-filtration bank, generator air intakes during dust fronts, and heavy droid engine salvage.",
        "where_to_use": [
            "Air + Water shop porch filter bank",
            "East yard field generator intake spare",
            "Outer Berms machine depot salvage",
            "Salvage shop shelves"
        ],
        "recommended_usage": "Use `_LOD0..2.glb` (decimated from 136k source tris to runtime-friendly budgets).",
        "tags": ["air_filter", "filtration", "air_water", "generator", "dust_front", "salvage"]
    },

    # =========================================================================
    # 3. WORKSHOP STORAGE, CABINETS, RACKS & TROLLEYS (Shops, Home, Yard)
    # =========================================================================
    {
        "id": "pegboard",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/c680339fa9ae56759f40d45c1dc11cfe0a9e26f7/pegboard",
        "title": "Perforated Steel Workshop Wall Pegboard",
        "category": "workshop_furniture",
        "subcategory": "tool_storage",
        "description": "Wall-mounted perforated steel tool organizer board with hooks/frame.",
        "lore_fit": "Essential backdrop behind Brann's Salvage workbench, Tamsin's Field Supply table, Tool Exchange, or the player's container home workbench wall.",
        "where_to_use": [
            "Salvage shop interior wall behind `SS_Workbench`",
            "Field Supply interior workshop wall",
            "Tool Exchange tool wall",
            "Player container home (`WallHomeP`) interior wall"
        ],
        "recommended_usage": "Mount on wall behind benches and hang SimReady hand tools on it (`_LOD0..2.glb`).",
        "tags": ["pegboard", "tool_wall", "storage", "salvage_shop", "field_supply", "ward_home", "crafting_studio"]
    },
    {
        "id": "workbench_trolley",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/bdc6b6e641e0c53d93575cfcffc10eedb5d7d206/workbench_trolley",
        "title": "Mobile Steel Workbench & Tool Trolley",
        "category": "workshop_furniture",
        "subcategory": "bench_cart",
        "description": "Heavy wheeled steel worktable trolley with lower storage shelf and push handle.",
        "lore_fit": "Can serve as a secondary mobile assembly station, yard mechanic tool cart, or drone service apron bench.",
        "where_to_use": [
            "Salvage shop interior beside the hoist monorail",
            "Warden training range drone service apron",
            "Service yard (mechanic's loop)",
            "Field Supply rear workshop"
        ],
        "recommended_usage": "Use `_LOD0..2.glb` with a box collider.",
        "tags": ["workbench", "trolley", "cart", "workshop_furniture", "salvage_shop", "training_range", "mechanic"]
    },
    {
        "id": "workshop_trolley_fetra_2436",
        "dataset": "M-XR/marso-simready",
        "url": "https://huggingface.co/datasets/M-XR/marso-simready/resolve/0bf9664adf0f7fdaace26c3e36a518eaac16fc38/workshop_trolley_fetra_2436",
        "title": "Multi-Tier Workshop Service Cart",
        "category": "workshop_furniture",
        "subcategory": "bench_cart",
        "description": "Industrial steel service trolley with tray shelves, swivel casters, and worn paint.",
        "lore_fit": "Fits Hydroponics nutrient dosing trolley, Relay Works parts cart, or Brann's parts staging cart.",
        "where_to_use": [
            "Salvage shop interior (staging cart next to workbench)",
            "Hydroponics yard dosing trolley",
            "Relay Works porch",
            "Node 07 goods dock"
        ],
        "recommended_usage": "Articulated casters in `_parts.glb`; merged prop in `_LOD0..2.glb`.",
        "tags": ["trolley", "service_cart", "workshop_furniture", "salvage_shop", "hydroponics", "separable_parts"]
    },
    {
        "id": "industrial_cabinet",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/41679be3c869a13d673d30aaa1ced88b3dbc4fc2/industrial_cabinet",
        "title": "Heavy Steel Double-Door Workshop Cabinet",
        "category": "workshop_furniture",
        "subcategory": "cabinet",
        "description": "Tall industrial sheet-steel storage cabinet with hinged doors, handles, and internal shelves.",
        "lore_fit": "Fits Brann's Salvage shop back wall, Warden armory locker at the West Gate, or player home stash cabinet.",
        "where_to_use": [
            "Salvage shop interior back wall",
            "Field Supply interior stock storage",
            "West Gate Warden post",
            "Player container home (`StashModel` locker alternative)"
        ],
        "recommended_usage": "Doors are separate meshes in `_parts.glb` if open/close animation is desired; `_LOD0..2.glb` for static placement.",
        "tags": ["cabinet", "locker", "storage", "salvage_shop", "field_supply", "west_gate", "separable_parts"]
    },
    {
        "id": "storage_locker_double_bench_b01",
        "dataset": "nvidia/simready-assets",
        "url": "https://huggingface.co/datasets/nvidia/simready-assets/resolve/653d91e182011f357cf1644013cc94ddf194d349/storage_locker_double_bench_b01",
        "title": "Double Crew Locker with Integrated Bench Seat",
        "category": "workshop_furniture",
        "subcategory": "locker",
        "description": "Industrial double personnel locker unit with slatted lower bench seat.",
        "lore_fit": "Fits the Warden barracks/watch post at the West Gate, Vanguard Hall guard room, or the training range firing line prep area.",
        "where_to_use": [
            "Warden training range prep area",
            "West Gate Warden post (Ossa & Rell)",
            "Vanguard Hall porch / side alcove",
            "Player container home interior"
        ],
        "recommended_usage": "Can carry an `NPC sit point` marker on the integrated bench seat (`_LOD0..2.glb`).",
        "tags": ["locker", "bench", "wardens", "training_range", "west_gate", "sit_point", "storage"]
    },
    {
        "id": "cabinet_drum_flammable_a02",
        "dataset": "nvidia/simready-assets",
        "url": "https://huggingface.co/datasets/nvidia/simready-assets/resolve/653d91e182011f357cf1644013cc94ddf194d349/cabinet_drum_flammable_a02",
        "title": "Hazardous / Flammable Liquid Safety Cabinet",
        "category": "workshop_furniture",
        "subcategory": "cabinet",
        "description": "Industrial safety storage cabinet for volatile fuels, solvents, and nanite reagents.",
        "lore_fit": "Stores solvent baths, nanite suspension vials, and generator fuel in Salvage shop, Repairs, or the training range drone bay.",
        "where_to_use": [
            "Salvage shop interior (solvent & nanite reagent storage)",
            "Repairs shop forge / fuel bay",
            "East service yard generator shed",
            "Warden training range drone apron"
        ],
        "recommended_usage": "Static industrial cabinet (`_LOD0..2.glb`).",
        "tags": ["safety_cabinet", "flammable", "hazmat", "solvent", "nanites", "salvage_shop", "repairs"]
    },
    {
        "id": "storage_rack",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/7f0a55cc48506dac21b6bbd724b93fdf78f47f54/storage_rack",
        "title": "Heavy-Duty Steel Pallet & Parts Shelving Rack",
        "category": "workshop_furniture",
        "subcategory": "shelving",
        "description": "Multi-tier bolted steel industrial storage rack.",
        "lore_fit": "Holds sorted salvage bins, crates, and droid parts in Salvage shop, Node 07 goods dock, or Field Supply.",
        "where_to_use": [
            "Salvage shop interior side wall",
            "Node 07 Quantum Tube goods dock (Pell's bays)",
            "Field Supply interior",
            "Service yard"
        ],
        "recommended_usage": "Populate shelves with `stackable_parts_bin`, `plastic_shelf_bin`, and `container_box` (`_LOD0..2.glb`).",
        "tags": ["rack", "shelving", "storage", "salvage_shop", "quantum_tube_dock", "field_supply"]
    },
    {
        "id": "wooden_shelving_worn",
        "dataset": "projectsim/simready-assets",
        "url": "https://huggingface.co/datasets/projectsim/simready-assets/resolve/c48a2a4c8dbcfc19279b074198335c3da0392523/wooden_shelving_worn",
        "title": "Weathered Timber Shop Shelving Unit",
        "category": "workshop_furniture",
        "subcategory": "shelving",
        "description": "Worn open timber shelving rack with distressed wood grain.",
        "lore_fit": "Fits Basic General stock display, Karaveen market pottery/produce stalls (Nadje), Hydroponics potting shed, or container homes.",
        "where_to_use": [
            "Basic General interior/back wall (Mira)",
            "Karaveen market stalls (Nadje)",
            "Player container home interior",
            "Hydroponics nursery shade"
        ],
        "recommended_usage": "Use `_LOD0..2.glb` and dress with jars, flasks, and bins.",
        "tags": ["shelving", "wooden_shelf", "worn_wood", "basic_general", "karaveen_market", "ward_home"]
    },
    {
        "id": "red_tool_chest",
        "dataset": "projectsim/simready-assets",
        "url": "https://huggingface.co/datasets/projectsim/simready-assets/resolve/04e165dffed33a9a3e913cf61adc0ca9ad610522/red_tool_chest",
        "title": "Multi-Drawer Machinist Tool Chest",
        "category": "workshop_storage",
        "subcategory": "toolbox",
        "description": "Painted steel multi-drawer tabletop machinist tool chest with top compartment.",
        "lore_fit": "Sits on Brann's workbench corner or Tamsin's table to hold fastener bits, taps, dies (`tools.die_m14`), and drills.",
        "where_to_use": [
            "Salvage shop workbench corner",
            "Crafting Studio (`toolStore` role alternative)",
            "Repairs shop counter",
            "Service yard mechanic bay"
        ],
        "recommended_usage": "Drawers and lid are separate objects in `_parts.glb`; compact 1.8 MB asset.",
        "tags": ["tool_chest", "toolbox", "drawers", "crafting_studio", "salvage_shop", "separable_parts"]
    },
    {
        "id": "red_metal_toolbox",
        "dataset": "projectsim/simready-assets",
        "url": "https://huggingface.co/datasets/projectsim/simready-assets/resolve/e66d6c373c9851a0f8dc90ee9c27e7ab531f65aa/red_metal_toolbox",
        "title": "Portable Cantilever Steel Toolbox",
        "category": "workshop_storage",
        "subcategory": "toolbox",
        "description": "Portable painted steel hand toolbox with top carry handle and latches.",
        "lore_fit": "Visual representation of the player's portable `Field Toolkit` (`field_toolkit`) or Torr's fixer kit.",
        "where_to_use": [
            "Field Toolkit (`field_toolkit`) world/bench item visual",
            "Torr's fixer post",
            "Player container home shelf",
            "Basic General / Field Supply stock"
        ],
        "recommended_usage": "Compact 2.4 MB asset; use `_parts.glb` for opening lid or `_LOD0..2.glb` as an item prop.",
        "tags": ["toolbox", "field_toolkit", "portable", "torr", "crafting_studio", "separable_parts"]
    },
    {
        "id": "hinged_toolbox",
        "dataset": "projectsim/simready-assets",
        "url": "https://huggingface.co/datasets/projectsim/simready-assets/resolve/a5bea0a974f150f56c14929c7b9a85fdba127abf/hinged_toolbox",
        "title": "Hinged Rugged Field Utility Case",
        "category": "workshop_storage",
        "subcategory": "toolbox",
        "description": "Compact hinged utility toolbox with latch and handle.",
        "lore_fit": "Fits field repair kits, drone spare-part boxes, or Berms loot containers.",
        "where_to_use": [
            "Outer Berms waystation and salvage caches",
            "Warden training range repair bench",
            "Field Supply stock"
        ],
        "recommended_usage": "Hinged lid is separate in `_parts.glb`.",
        "tags": ["toolbox", "field_kit", "loot_box", "berms", "field_supply", "separable_parts"]
    },
    {
        "id": "hard_equipment_case",
        "dataset": "projectsim/simready-assets",
        "url": "https://huggingface.co/datasets/projectsim/simready-assets/resolve/75c98680553f9aff3601e057e6a330e2172633e6/hard_equipment_case",
        "title": "Pelican-Style Hard Tactical Equipment Case",
        "category": "containers_cargo",
        "subcategory": "equipment_case",
        "description": "Ribbed high-impact polymer waterproof equipment case with twin latches, hinge pins, and pressure valve.",
        "lore_fit": "High-value salvage strongbox for weapon mods, rifle receivers (`Long Arm` quest), Warden plate carriers, or nanite canisters.",
        "where_to_use": [
            "Outer Berms elite POI strongboxes (Relay knoll, Caravan strongbox, Southern cache)",
            "Field Supply weapon/armour counter (Tamsin)",
            "Warden training range officer's table (Ossa & Rell)",
            "Node 07 Quantum Tube high-priority delivery pod"
        ],
        "recommended_usage": "Lid and latches are separable in `_parts.glb` so loot cases can animate open when searched; `_LOD0..2.glb` for static props.",
        "tags": ["strongbox", "equipment_case", "loot_crate", "berms", "field_supply", "wardens", "separable_parts"]
    },
    {
        "id": "stackable_parts_bin",
        "dataset": "projectsim/simready-assets",
        "url": "https://huggingface.co/datasets/projectsim/simready-assets/resolve/e970e8523fb9c22b068aa9f26fef57677b0026a2/stackable_parts_bin",
        "title": "Open-Front Stackable Workshop Parts Bin",
        "category": "workshop_storage",
        "subcategory": "parts_bin",
        "description": "Molded industrial open-front hopper bin for sorting screws, pins, and salvage components.",
        "lore_fit": "Matches the 'slotted rack of salvage bins' in the player's container home (`AGENTS.md` §Container home), Brann's workbench dish/scrap bins, and Relay Works.",
        "where_to_use": [
            "Crafting Studio bench (`dish` / `scrap` role for removed fasteners and offcuts)",
            "Salvage shop shelves and counter",
            "Player container home slotted bin rack",
            "Relay Works parts counter"
        ],
        "recommended_usage": "Very lightweight (3.2 MB); instance in rows on racks or beside the bench (`_LOD0..2.glb`).",
        "tags": ["parts_bin", "hopper_bin", "salvage_bins", "crafting_studio", "ward_home", "salvage_shop"]
    },
    {
        "id": "plastic_shelf_bin",
        "dataset": "projectsim/simready-assets",
        "url": "https://huggingface.co/datasets/projectsim/simready-assets/resolve/4b6bc510f461ee6811296d3ca7b907d0582f7f29/plastic_shelf_bin",
        "title": "Narrow Shelf Organizer Bin",
        "category": "workshop_storage",
        "subcategory": "parts_bin",
        "description": "Compact rectangular parts tray/bin for small hardware and electronic components.",
        "lore_fit": "Sits on the Crafting Studio bench (`role: dish`) to hold backed-out screws, pins, and springs during weapon disassembly.",
        "where_to_use": [
            "Crafting Studio bench (`role: dish` fastener tray)",
            "Relay Works & Tool Exchange shelves",
            "Salvage shop counter"
        ],
        "recommended_usage": "Ultra-lightweight (0.3 MB); ideal for multi-slot bench fastener trays (`_LOD0.glb`).",
        "tags": ["parts_bin", "fastener_dish", "crafting_studio", "bench", "dish", "storage"]
    },
    {
        "id": "plastic_compartment_tray",
        "dataset": "projectsim/simready-assets",
        "url": "https://huggingface.co/datasets/projectsim/simready-assets/resolve/aec2cea7f181837265fd60e0581f22f9fba8c46f/plastic_compartment_tray",
        "title": "Divided Component Sorting Tray",
        "category": "workshop_storage",
        "subcategory": "parts_bin",
        "description": "Multi-compartment tray for keeping disassembled sub-parts sorted by stage.",
        "lore_fit": "Perfect for the Crafting Studio parts mat / dish role (`station.json`), keeping stripped pistol/rifle screws and shims organized.",
        "where_to_use": [
            "Crafting Studio bench (`dish` / parts sorting tray)",
            "Salvage shop workbench",
            "Relay Works counter"
        ],
        "recommended_usage": "Lightweight 2.9 MB asset; place directly on bench surface (`_LOD0.glb`).",
        "tags": ["compartment_tray", "parts_tray", "dish", "crafting_studio", "bench", "salvage_shop"]
    },

    # =========================================================================
    # 4. INDUSTRIAL INFRASTRUCTURE, PIPES, POWER & LOGISTICS (District, Tube Dock, Yard)
    # =========================================================================
    {
        "id": "industrial_pipe_valve",
        "dataset": "projectsim/simready-assets",
        "url": "https://huggingface.co/datasets/projectsim/simready-assets/resolve/02b701df3ce091d169399763b3ce29ed14d99e80/industrial_pipe_valve",
        "title": "Flanged Cast-Iron Industrial Pipe Valve with Handwheel",
        "category": "infrastructure",
        "subcategory": "piping_water",
        "description": "Heavy bolted-flange cast-iron pipe valve with red spoked handwheel and stuffing box.",
        "lore_fit": "Ward's survival depends on deep aquifer pumps and water ration taps (`lore.md` §The Ward); fits Air + Water, ration taps behind Vanguard Hall (Oren's route), and Hydroponics feed lines.",
        "where_to_use": [
            "Air + Water shop filter bank and steam pipes",
            "Water ration taps behind Vanguard Hall (Oren's water-carrier stop)",
            "Hydroponics quonset water feed manifolds",
            "Outer Berms collapsed processing hall pipework"
        ],
        "recommended_usage": "Handwheel is a separate mesh in `_parts.glb` if interactive valve turning is needed; `_LOD0..2.glb` for pipe dressing.",
        "tags": ["pipe_valve", "handwheel", "aquifer", "air_water", "hydroponics", "ration_taps", "infrastructure", "separable_parts"]
    },
    {
        "id": "warehouse_EF_electricPanel_a01",
        "dataset": "nvidia/simready-assets",
        "url": "https://huggingface.co/datasets/nvidia/simready-assets/resolve/21b045a878e13d4ca922f0f8ebc2ff1e84bb06d4/warehouse_EF_electricPanel_a01",
        "title": "Wall-Mounted High-Voltage Breaker & Junction Box",
        "category": "infrastructure",
        "subcategory": "electrical",
        "description": "Industrial steel electrical distribution cabinet with warning labels, conduit knockouts, and door latch.",
        "lore_fit": "Pairs with the rooftop service lines and conduit drops (`art/rooftops_20261001`), Relay Works facade, and the Lattice Jack console power feed.",
        "where_to_use": [
            "Building facades at conduit drop terminations (`Ward rooftops` pass)",
            "Relay Works exterior/interior wall",
            "Lattice Jack court power feed",
            "Salvage shop hoist bay wall",
            "Outer Berms Post Relay POI"
        ],
        "recommended_usage": "Mount on masonry or container walls (`_LOD0..2.glb`).",
        "tags": ["electric_panel", "junction_box", "breaker", "infrastructure", "rooftops", "relay_works", "lattice_jack"]
    },
    {
        "id": "signal_tower",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/4ad7c03e19e92215a7f1fec0a15f909293735689/signal_tower",
        "title": "Industrial Stack Light / Status Signal Beacon",
        "category": "infrastructure",
        "subcategory": "signaling",
        "description": "Multi-stage red/amber/green industrial status light stack on a mounting pole.",
        "lore_fit": "Great visual indicator for Node 07 Quantum Tube transfer status, dust-front warning beacons at the West Gate, or automated turret/factory status.",
        "where_to_use": [
            "Node 07 Quantum Tube goods dock (transfer active beacon)",
            "West Gate portal / Ossa's dust-front warning post",
            "Warden training range firing line live-fire indicator",
            "Salvage shop hoist monorail"
        ],
        "recommended_usage": "Lens segments are separate in `_parts.glb` for selective emissive switching on the city light clock.",
        "tags": ["signal_tower", "beacon", "status_light", "quantum_tube", "west_gate", "training_range", "separable_parts"]
    },
    {
        "id": "power_strip",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/945023ed66d64041e0d72d74d86c979af06ab5a5/power_strip",
        "title": "Bench Multi-Outlet Power Strip & Cord",
        "category": "infrastructure",
        "subcategory": "electrical",
        "description": "Multi-socket power distribution bar with illuminated rocker switch and power cable.",
        "lore_fit": "Essential bench-top detail for powering solder stations, UV nanite cure lamps, and chargers at Brann's bench, Relay Works, or the player's home.",
        "where_to_use": [
            "Crafting Studio bench back rail (powering cure lamp & solder iron)",
            "Relay Works counter",
            "Player container home table",
            "Warden training range drone charging dock"
        ],
        "recommended_usage": "Place along rear edge of workbenches (`_LOD0..2.glb`).",
        "tags": ["power_strip", "electrical", "bench", "crafting_studio", "relay_works", "ward_home"]
    },
    {
        "id": "gas_cylinder",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/8e4d7bbbbb8e366108240d36537b6dccd276dd29/gas_cylinder",
        "title": "High-Pressure Industrial Welding Gas Cylinder",
        "category": "infrastructure",
        "subcategory": "fuel_gas",
        "description": "Tall steel compressed-gas cylinder with brass regulator valve and neck collar.",
        "lore_fit": "Feeds the Repairs shop forge and welding cart, Brann's cutting torch, and Hydroponics CO2 enrichment lines.",
        "where_to_use": [
            "Repairs shop forge gas rack",
            "Salvage shop interior welding corner",
            "Warden training range drone apron welding cart",
            "Hydroponics quonset end wall"
        ],
        "recommended_usage": "Chain upright against walls or racks (`_LOD0..2.glb` with capsule/box collider).",
        "tags": ["gas_cylinder", "welding_gas", "fuel", "repairs", "salvage_shop", "training_range", "hydroponics"]
    },
    {
        "id": "fire_extinguisher",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/821750e8345f04111f54a567571182377890f6a9/fire_extinguisher",
        "title": "Red Steel Dry-Chemical Fire Extinguisher",
        "category": "infrastructure",
        "subcategory": "safety",
        "description": "Pressurized red steel fire extinguisher cylinder with squeeze lever, pressure gauge, and discharge hose.",
        "lore_fit": "Believable workshop safety detail beside Brann's workbench, the Repairs forge, the East yard generator, and the drone service bay.",
        "where_to_use": [
            "Salvage shop interior pillar beside workbench",
            "Repairs shop forge post",
            "East service yard generator station",
            "Node 07 Quantum Tube goods dock"
        ],
        "recommended_usage": "Separable pin/lever/hose in `_parts.glb`; static prop in `_LOD0..2.glb`.",
        "tags": ["fire_extinguisher", "safety", "workshop", "salvage_shop", "repairs", "generator_yard"]
    },
    {
        "id": "machine_guard",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/3d5df7d70d7d9fc09aad6366b29087d57bccecf0/machine_guard",
        "title": "Yellow Steel Wire-Mesh Safety Partition / Machine Guard",
        "category": "infrastructure",
        "subcategory": "barriers",
        "description": "Industrial framed wire-mesh safety barrier fence panel on floor posts.",
        "lore_fit": "Great for partitioning the Quantum Tube molecular disassembly bay at Node 07, Salvage shop hoist zone, or Warden range firing bays.",
        "where_to_use": [
            "Node 07 Quantum Tube goods dock bay divider",
            "Salvage shop hoist bay perimeter",
            "Warden training range firing line divider",
            "Outer Berms machine depot interior"
        ],
        "recommended_usage": "Modular fence segment (`_LOD0..2.glb` with thin box collider).",
        "tags": ["machine_guard", "fence", "partition", "quantum_tube_dock", "salvage_shop", "training_range"]
    },
    {
        "id": "h_frame_scaffolding",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/63fb6fcc4c91dd46a187eff94d69a4fb1c3b8e34/h_frame_scaffolding",
        "title": "Tubular Steel H-Frame Repair Scaffolding",
        "category": "infrastructure",
        "subcategory": "construction",
        "description": "Two-level tubular steel scaffolding frame with cross braces and timber/steel plank deck.",
        "lore_fit": "Visually reinforces the 'Great Rebuild' and ongoing masonry/facade repairs across Ward's half-collapsed buildings and perimeter walls.",
        "where_to_use": [
            "AgainstSalvage shop rubble-patched breach",
            "Perimeter wall collapse repair zones",
            "Rear service lanes and rooftop access points",
            "Outer Berms waystation fortification"
        ],
        "recommended_usage": "Use `_LOD0..2.glb` against building facades undergoing repair.",
        "tags": ["scaffolding", "construction", "great_rebuild", "facade_repair", "perimeter_walls"]
    },
    {
        "id": "ladder",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/d7d72c9f13ae45c18c95f58be4ea201b97a64f1b/ladder",
        "title": "Industrial Aluminum Step / Leaning Ladder",
        "category": "infrastructure",
        "subcategory": "access",
        "description": "Ribbed aluminum maintenance ladder.",
        "lore_fit": "Complements the rooftop service pass (`art/rooftops_20261001`) for accessing shop cornices, water tanks, and container home roofs.",
        "where_to_use": [
            "Rear service alleys leaning against shop eaves",
            "South-wall container homes roof access",
            "Hydroponics quonset maintenance",
            "Salvage shop timber deck access"
        ],
        "recommended_usage": "Use `_LOD0..2.glb`.",
        "tags": ["ladder", "rooftops", "maintenance", "alleys", "ward_home"]
    },
    {
        "id": "concrete_barrier",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/7f0d3a260eda1fa929b8fd18137d52a192cd6b06/concrete_barrier",
        "title": "Precast Jersey Concrete Blast / Road Barrier",
        "category": "infrastructure",
        "subcategory": "fortification",
        "description": "Heavy precast concrete Jersey barrier block with forklift slots and weathered surface.",
        "lore_fit": "Cover barricade for the Warden training range machine lane, West Gate defensive chicane, and Outer Berms road checkpoints.",
        "where_to_use": [
            "Warden training range machine lane cover barricades",
            "West Gate approach road chicane",
            "Outer Berms ambush cover and waystation perimeter"
        ],
        "recommended_usage": "Use `_LOD0..2.glb` with box collider for ballistic cover.",
        "tags": ["concrete_barrier", "jersey_barrier", "cover", "fortification", "west_gate", "training_range", "berms"]
    },

    # =========================================================================
    # 5. CARGO, CONTAINERS, CARTS & COLONY LIFE (Market, Dock, Berms, Home)
    # =========================================================================
    {
        "id": "platform_dolly",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/f50100784f783a9866d077437993150b316e5144/platform_dolly",
        "title": "Four-Wheel Flatbed Cargo Platform Dolly",
        "category": "logistics_cargo",
        "subcategory": "carts",
        "description": "Flatbed warehouse push-cart dolly with folding tubular handle and swivel casters.",
        "lore_fit": "Used by Pell at the Node 07 Quantum Tube goods dock and Daro the Karaveen porter for moving heavy Tube-transferred crates.",
        "where_to_use": [
            "Node 07 Quantum Tube goods dock (Pell's bays 1 & 2)",
            "Karaveen market cargo unloading zone",
            "Basic General rear stock lane",
            "Salvage shop bay entrance"
        ],
        "recommended_usage": "Stack crates or drums on the flatbed deck (`_LOD0..2.glb`).",
        "tags": ["dolly", "flatbed_cart", "cargo", "quantum_tube_dock", "pell", "karaveen_market", "logistics"]
    },
    {
        "id": "wheelbarrow",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/306bfe7ae31c36bf4c925d1c9aea8e87f294c026/wheelbarrow",
        "title": "Heavy Steel-Tray Construction & Garden Wheelbarrow",
        "category": "logistics_cargo",
        "subcategory": "carts",
        "description": "Single-wheel steel-pan wheelbarrow with tubular frame and rubber tire.",
        "lore_fit": "Fits Anso's hydroponics yard (soil/compost hauling), masonry rubble clearing at Salvage shop breach, and Berms scrap hauling.",
        "where_to_use": [
            "Hydroponics working yard (compost & soil vignettes)",
            "Salvage shop rubble breach",
            "Courtyard / Hill planting bed maintenance",
            "Outer Berms scrap heap sites"
        ],
        "recommended_usage": "Use `_LOD0..2.glb`.",
        "tags": ["wheelbarrow", "cart", "hydroponics", "anso", "salvage", "rubble"]
    },
    {
        "id": "pallet",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/e9e248794b75d59da3c950cfe5f2cab3495cb7d2/pallet",
        "title": "Standard Timber Cargo Pallet",
        "category": "logistics_cargo",
        "subcategory": "pallets_crates",
        "description": "Slatted wooden shipping pallet for stacking drums, sacks, and crates off the desert dust.",
        "lore_fit": "Base foundation for cargo clusters at Node 07 goods dock, Karaveen caravan staging, and East service yard tarp stacks.",
        "where_to_use": [
            "Node 07 Quantum Tube goods dock bays",
            "Karaveen market caravan stock overflow",
            "East service yard drum & tarp clusters",
            "Field Supply / Basic General porch stock"
        ],
        "recommended_usage": "Low triangle count; place under crate/drum stacks (`_LOD0..2.glb`).",
        "tags": ["pallet", "timber_pallet", "cargo", "quantum_tube_dock", "karaveen_market", "street_dressing"]
    },
    {
        "id": "container_box",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/fd36c11f49a793cebf2c2a8fdb41864c2a4e0acb/container_box",
        "title": "Ribbed Industrial Logistics Tote Box",
        "category": "logistics_cargo",
        "subcategory": "pallets_crates",
        "description": "Stackable ribbed polymer logistics container box.",
        "lore_fit": "Standardized Quantum Tube matter-transfer container for shipping fabricated components and hydroponic rations.",
        "where_to_use": [
            "Node 07 Quantum Tube goods dock",
            "Hydroponics harvest crates",
            "Basic General & Field Supply stock piles",
            "Player container home storage rack"
        ],
        "recommended_usage": "Stack in 2s or 3s on pallets or racks (`_LOD0..2.glb`).",
        "tags": ["container_box", "tote", "quantum_tube_dock", "cargo", "hydroponics", "storage"]
    },
    {
        "id": "attached_lid_tote",
        "dataset": "ForgeCAD/simready-assets",
        "url": "https://huggingface.co/datasets/ForgeCAD/simready-assets/resolve/2bf134c5b19e0f3d31b82350be9af96c4f5a4e49/attached_lid_tote",
        "title": "Interlocking Hinged-Lid Distribution Tote",
        "category": "logistics_cargo",
        "subcategory": "pallets_crates",
        "description": "Heavy-duty logistics tote bin with two interlocking hinged lid flaps.",
        "lore_fit": "Ideal searchable supply container for Berms waystations, caravan goods, or player home stash organization.",
        "where_to_use": [
            "Node 07 Quantum Tube goods dock",
            "Outer Berms Warden waystation supplies",
            "Field Supply interior stock",
            "Player container home"
        ],
        "recommended_usage": "Lids are separate meshes in `_parts.glb` for open/closed variations.",
        "tags": ["tote", "crate", "hinged_lid", "cargo", "quantum_tube_dock", "separable_parts"]
    },
    {
        "id": "small_load_carrier",
        "dataset": "ForgeCAD/simready-assets",
        "url": "https://huggingface.co/datasets/ForgeCAD/simready-assets/resolve/0573053fa2c9174ca2a4678a462ec4dfd3035d59/small_load_carrier",
        "title": "KLT Modular Factory Parts Carrier Crate",
        "category": "logistics_cargo",
        "subcategory": "pallets_crates",
        "description": "Standardized VDA/KLT ribbed industrial factory crate for automated conveyor handling.",
        "lore_fit": "Pre-Fall corporate factory crate designed for Tir's automated conveyor spines and nanofab lines (`lore.md` §The Planet Tir).",
        "where_to_use": [
            "Outer Berms rusted conveyor spines and collapsed processing halls",
            "Salvage shop sorted droid parts",
            "Tool Exchange nanofab bench",
            "Node 07 goods dock"
        ],
        "recommended_usage": "Use `_LOD0..2.glb` around factory ruins and workshop shelves.",
        "tags": ["klt_crate", "factory_crate", "conveyor", "pre_fall", "salvage_shop", "berms"]
    },
    {
        "id": "steel_drum",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/1d04fac22ecd800cc94089572cca61e19b680157/steel_drum",
        "title": "200L Ribbed Industrial Steel Barrel",
        "category": "logistics_cargo",
        "subcategory": "drums_cans",
        "description": "Standard 55-gallon / 200-litre rolled-rib steel fuel and water storage drum with bung plugs.",
        "lore_fit": "Water aquifer reserve and generator fuel storage across Ward and the Outer Berms.",
        "where_to_use": [
            "East service yard fuel dump",
            "Air + Water water reserve drums",
            "Outer Berms depot and waystation",
            "Warden training range cover obstacles"
        ],
        "recommended_usage": "Use `_LOD0..2.glb` with cylinder/box collider.",
        "tags": ["steel_drum", "barrel", "fuel_drum", "water_drum", "street_dressing", "berms"]
    },
    {
        "id": "jerrycan",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/7cd97a86d455441636ce67fd0d91be7d50a541d3/jerrycan",
        "title": "Stamped Steel 20L Fuel / Water Jerrycan",
        "category": "logistics_cargo",
        "subcategory": "drums_cans",
        "description": "Military-style stamped steel 20-litre jerrycan with triple handle and cam-lock cap.",
        "lore_fit": "Portable water and generator fuel container carried by Karaveen caravans, Oren the water carrier, and Berms patrols.",
        "where_to_use": [
            "East service yard field generator",
            "Water ration taps behind Vanguard Hall (Oren's stop)",
            "Karaveen market truck and stalls",
            "Outer Berms Warden waystation"
        ],
        "recommended_usage": "Place beside generators, trucks, and water points (`_LOD0..2.glb`).",
        "tags": ["jerrycan", "fuel_can", "water_can", "oren", "generator", "karaveen", "wardens"]
    },
    {
        "id": "military_canteen",
        "dataset": "M-XR/marso-simready",
        "url": "https://huggingface.co/datasets/M-XR/marso-simready/resolve/8d385b7a3caaff2262338fac0b6b4ee40e9e668e/military_canteen",
        "title": "Weathered Field Water Canteen",
        "category": "colony_life",
        "subcategory": "survival_gear",
        "description": "Worn military-style field water canteen with screw cap and textured body.",
        "lore_fit": "Matches the purchasable water flask at Basic General (`AGENTS.md` §2: 'flask purchase and scrap sale'), Oren's drinking prop, and Warden field gear.",
        "where_to_use": [
            "Basic General counter stock (Mira's water flask visual)",
            "Oren's water-carrier hand/stop prop (`AGENTS.md` notes 'Oren's drink is an empty hand')",
            "Warden training range officer's table (Ossa & Rell)",
            "Player container home table"
        ],
        "recommended_usage": "Cap and body are separable in `_parts.glb`; `_LOD0..2.glb` for table or character prop attachment.",
        "tags": ["canteen", "water_flask", "flask", "basic_general", "mira", "oren", "survival", "wardens"]
    },
    {
        "id": "metal_lunch_box",
        "dataset": "projectsim/simready-assets",
        "url": "https://huggingface.co/datasets/projectsim/simready-assets/resolve/4cf06c71c8305499a1e2f34ff3f9c4d07289b2b6/metal_lunch_box",
        "title": "Domed Steel Worker's Ration Tin / Lunch Box",
        "category": "colony_life",
        "subcategory": "personal_items",
        "description": "Classic domed sheet-metal worker's lunch box with latch and folding wire handle.",
        "lore_fit": "Lived-in personal detail for the Repairs tea-break vignette, player container home table, or Pell's tally desk.",
        "where_to_use": [
            "Repairs shop tea-break stool vignette",
            "Player container home fold-down table",
            "Node 07 goods dock tally desk (Pell)",
            "Market rest spot picnic table"
        ],
        "recommended_usage": "Compact 1.6 MB package; lid/handle separable in `_parts.glb`.",
        "tags": ["lunch_box", "ration_tin", "colony_life", "repairs", "ward_home", "pell", "separable_parts"]
    },
    {
        "id": "respirator",
        "dataset": "NdotLight/SimReady_Assets",
        "url": "https://huggingface.co/datasets/NdotLight/SimReady_Assets/resolve/c8f22763cc3ac70aa326aa0668c25ec1b8e73ddc/respirator",
        "title": "Dual-Cartridge Dust & Nanite Half-Mask Respirator",
        "category": "colony_life",
        "subcategory": "survival_gear",
        "description": "Industrial half-face respirator mask with dual replaceable particulate/chemical filter cartridges and head straps.",
        "lore_fit": "Essential survival gear on Tir during desert dust fronts (`Ward weather` pass) and inside nanite/salvage workshops; also fits a future HEAD/FACE armour or utility item.",
        "where_to_use": [
            "Field Supply counter & shelves (Tamsin's survival gear)",
            "Salvage shop workbench (nanite paste/grinding protection)",
            "West Gate Warden post (Ossa's dust-front gear)",
            "Player container home table / locker"
        ],
        "recommended_usage": "Filter cartridges are separate nodes in `_parts.glb` (could even be a Service bench job to swap filters!); `_LOD0..2.glb` for prop placement.",
        "tags": ["respirator", "dust_mask", "ppe", "dust_front", "field_supply", "tamsin", "salvage_shop", "separable_parts"]
    },
    {
        "id": "ppe_eyeProtection_goggles_a01",
        "dataset": "nvidia/simready-assets",
        "url": "https://huggingface.co/datasets/nvidia/simready-assets/resolve/653d91e182011f357cf1644013cc94ddf194d349/ppe_eyeProtection_goggles_a01",
        "title": "Sealed Industrial & Desert Dust Goggles",
        "category": "colony_life",
        "subcategory": "survival_gear",
        "description": "Ventilated wrap-around protective goggles with elastic head strap.",
        "lore_fit": "Fits desert dust-front eye protection, workshop grinding goggles at Brann's bench, or visual inspiration/prop for the new `implant_eye` / headgear loadout.",
        "where_to_use": [
            "Salvage shop workbench",
            "Field Supply counter (Tamsin)",
            "Player container home table",
            "West Gate Warden post"
        ],
        "recommended_usage": "Use `_LOD0..2.glb` on tables, benches, or shelves.",
        "tags": ["goggles", "eye_protection", "dust_front", "ppe", "field_supply", "salvage_shop"]
    }
]
