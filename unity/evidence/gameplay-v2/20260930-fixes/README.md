# Gameplay v2 — fixes from the 30 September native QA

Worktree `/home/teknetik/code/ao2-gameplay`, branch `ward/gameplay-v2` (from integration head `3347fbe1`). Answers every
bug and tuning note in [`../20260930-native/README.md`](../20260930-native/README.md) (on the integration checkout). Batch Unity 6000.6.0f1 only: **no native player and no Editor GUI were run here**, so every layout,
focus and fight-feel claim below is from code, UXML/USS and EditMode tests; the integrator's native re-QA (checklist at
the end) is the acceptance step.

Results: EditMode **152/152 passed** (136 before + 16 new in `GameplayV2FixesTests`; `GameplayV2SceneTests`,
`LootTests`, `SaveGameTests` updated). `LinuxBuild.Development` succeeded — see [Verification](#verification).

## What changed, per QA bug

| # | QA bug | Fix |
|---|---|---|
| 1 | Fabricator keyboard acts on the wrong mod | `FabricatorPanel`: the schematic list is a single Tab stop (roving focus — only the selected schematic is focusable); focusing never selects (the `FocusInEvent → Select` hook is gone). Selection changes only by ↑/↓ in the list, click / Enter on a schematic, a slot card, or opening the window. Tab order is list → enabled actions (Fabricate, Fit, Remove) → the three slot cards. Craft/Fit/Remove always use `Selected`, which is what the title shows. |
| 2 | Arrow keys double-step; inventory assumes 4 columns | Lists and grids handle UI Toolkit's `NavigationMoveEvent` only (no `KeyDown` handlers) and withhold handled moves from the FocusController (`UiNavigation.Consume` → `focusController.IgnoreEvent` + stop), so one press is one step. Inventory columns come from the laid-out tiles (`UiNavigation.Columns`); Left/Right continue across rows, Up/Down move a row and stop at edges (Down onto a shorter last row lands on its last tile). In the fabricator list ↑/↓ step the selection (all 9 schematics reachable), → jumps to the actions. |
| 3 | Fabricator layout at 1080p | New three-column window (`#modal.wide-modal`, 1400 reference px, ≤ 96 % of the window; scroll area 690 px): schematics (312 px) · selected schematic (parts, actions, guidance) · pistol (three slot cards in a row and the stats table). Header cells are separate fixed-width columns: **STAT · NOW · WITH MOD · CHANGE** (the old flex-basis-0 cells overlapped into "NOWWITH SELECTION"). Estimated heights at 1080p: list ≈ 490 px, detail ≈ 400 px, pistol ≈ 390 px, so nothing scrolls; in a 1280×720 window (20 px fonts) the modal scroll view follows focus. Every modal `ScrollView` (modal, inventory) scrolls the focused control into view on `FocusIn` (`UiNavigation.KeepFocusVisible` → `ScrollView.ScrollTo`). |
| 4 | Sell salvage shows two rows; focus off-screen | Basic General is a two-column wide window: Supplies (the three original rows, unchanged names/prices/behaviour, compact 76 px) and **Buy parts** on the left, **Sell salvage** on the right (60 px rows; all six sellable salvage kinds visible at 1080p). Same scroll-to-focus. |
| 5 | New Game confirmation overlaps the footer | The confirmation now replaces the start actions in place (`ShowNewGameConfirm` hides `startup-actions`; `.arrival-confirm` margin matches the actions), so it ends ~150 px above the footer. Continue's labels are left-aligned like New Game / Settings. |
| 6 | HUD takes keyboard focus while walking | Every HUD element is non-focusable (the HUD is mouse + hotkeys: 1–7, Tab/5, 6, Esc, E), and in Play the root withholds `NavigationMoveEvent`/`NavigationSubmitEvent` (WASD, arrows, Tab, Enter) and blurs any focus. |
| 7 | Uncollected caches vanish while crafting | `LootSource.Revived` no longer despawns the old cache. Caches persist until collected or 600 s of game time (`CraftingSession.cacheLifetimeSeconds`); at most 12 at once (`maxCaches`), a new drop retiring the oldest, rare-holding caches last (`SalvageCache.EvictionOrder`). Nest re-form: see tuning. |
| 8 | Foreman marker pinned; bar too high | A guidance key that matches an encounter binding (`foreman`) follows the encounter's live leader (spawn 0, the Foreman) every frame; while its health bar shows, the marker steps aside. Once it is down the marker reads `DEPOT FOREMAN · last seen` at its cache (or wreck) and disappears when both are gone. Bars sit 0.3 m above the droid's head bone as it animates (`FeralDroid.BarAnchor`; the skinned renderers carry deliberately huge culling bounds, so bones are used). In the rest pose: worker 2.15 m (was 2.52; head 1.85 m), Foreman 2.71 m (was 3.01; head 2.41 m = 1.3 × worker), drone 0.46 m above its centre (was 0.9). |
| 9a | Mod descriptions vs base weapon | `FabricatorPanel.ModSummary` compares with the **current** loadout ("Grip mod · replaces Stabilised Pistol Grip: Recoil 31 → 23 · …", "Barrel … Damage 40.8 → 49.3"); a fitted mod shows what it adds over an empty slot. |
| 9b / 10 | Focus lost after Fit / last sale | After Fabricate → Fit (if fittable); after Fit → the selected schematic; after Remove → Fit. Basic General: a sold-out salvage row hands focus to its neighbour, the last one to Close; a control that disables itself (e.g. `Sell` on the last scrap coil) hands focus to its row neighbour, else the next usable control, else Close (`CityHud.EnsureModalFocus`, all modals except Inventory/Settings which manage their own). |
| 11 | Icons | 18 new item illustrations (every salvage part, component and mod has its own; lattice shard no longer borrows the Lattice Jack cube) in the 8 Sep painted style, 192×192 RGBA, import settings copied from `scrap.png`. Source: `refs/ui_20260930/items/` (script, prompts, raw 1024 PNGs, manifest with Meshy task IDs). Icon classes are data-driven from `CityCatalog.icon`. Overview title wraps ("Foreman Control Core"). |
| 12a | Ossa's briefings overwritten / 4 s | New radio channel (`RadioQueue`, `GameSession.Radio`, `#radio` panel under the compass): one line at a time for 2.5 s + 0.3 s/word (5–24 s; a 58-word briefing ≈ 20 s), later lines queue, the clock runs only in Play. Notices drop below the panel while a line is up and last 2.5 s + 0.25 s/word (4–10 s). Primer lines, order completion lines and briefings (with `nextLineDelay` as radio silence between them) use it; rewards are a separate notice. |
| 12b | Pickups show banner and toast | Pickups (and "Nothing useful…") go to the toast and the event log only (`GameSession.Record`). |
| 12c | Every heap says "Search the scrap heap" | Per-node prompts and progress labels (patch 1): *Search the scrap heap / machine debris / roadside scrap*, *Strip the droid carcass / mining droid carcass*, *Salvage the crashed drone*. |
| 12d | Corrupt save shows "(ArgumentException)" | Plain words ("the file is damaged or incomplete", "it was made by a newer build of the game"); details go to the log without exception type names; the notice says a new game started and the file was kept. |
| 12e | Red "Missing parts … Fitted" line | A fitted mod's line is bronze "Fitted to your Scrap Pistol. Another would need …"; carried-but-unfitted reads "Ready to fit." |
| 13 | Art (cache stumps, drone wreck slide) | Not changed (outside this fix list); persistent caches remove the practical cost of a missed drone cache. |

## Tuning (before → after)

**Order 2 (micro capacitors).** Capacitor entries (chance, pity-after):

| Table | Before | After |
|---|---|---|
| `loot_scrap_heap` | 20 %, p4 | **30 %, p2** |
| `loot_wreck_carcass` | 15 %, p5 | **25 %, p2** |
| `loot_drone_wreck` | 35 %, p3 | **50 %, p1** |
| drone / worker / Foreman | 45 % p2 / 20 % p4 / 60 % p1 | unchanged |

[`loot_sim.py`](loot_sim.py) replays `LootBook` exactly (SplitMix64, pity) on the committed vs working tables, 20 000
fresh seeds; results in [`sim-results.txt`](sim-results.txt). Pairs are (extra depot clears, heap searches) after the primer:

| Scenario | Before: ≤1 clear + 3 heaps · p90 · worst | After |
|---|---|---|
| Depot first, every cache collected | 88.7 % · (1, 4) · (1, 8) | **94.4 % · (1, 3) · (1, 6)** |
| Heaps first (nest just cleared) | 62.5 % · (0, 8) · (1, 9) | **74.6 % · (0, 5) · (0, 9)** — never needs a clear |
| QA-like: depot drone caches lost | 60.2 % · (1, 8) · (2, 9); 5.4 % need a 2nd clear | 73.3 % · (1, 5) · (1, 9); 0 % |

Ready straight after the primer stays 34.5 % (the drone odds are unchanged, so order 2 still has a gather step). The QA
run's "two depot clears + nine heaps" matches losing drone caches (a hover wreck slid 6.5 m, and caches despawned on
re-form) — fixed by persistent caches. Credits now also shortcut it: two capacitors cost 24 cr at Basic General.

**Depot Foreman** (`FeralDepotForeman.prefab` variant overrides; new `FeralDroid` fields, same AI):

| | Before | After |
|---|---|---|
| Vitality | 400 | **1400** |
| Strike | 30, 1.0 s tell | 26, 0.9 s tell |
| Heavy slam | — | **every 3rd strike: 1.6 s tell (brighter optics, slower swing), 45 damage to anything within 3.6 m regardless of facing, 1.8 s recovery; cannot be interrupted** |
| Stagger | every hit after 5 s immunity, 0.15 s | **160 damage between staggers**, 6 s immunity, 0.35 s |
| Self-repair (after 4 s unhurt) | 5/s | 8/s |
| Escorts | — | **two Feral worker droids spawn beside it** (patch 1) |

With Mark I mods (40.8 damage, 135 nano, 9 per shot, 34.5/s refill) a player sustains ≈ 64 DPS at 85 % hits, so the
Foreman alone takes ≈ 22 s, plus the escorts (2 × 100 HP) and slam dodging: ≈ 25–35 s. The old one died in ≈ 3 s.

**Nest re-form** (`DroidEncounter.awaySeconds` new; `BermsTutorial.depotRespawnSeconds` replaces a hard-coded 120):

| | Before | After |
|---|---|---|
| Depot nest | 120 s after the clear, the moment the player is ≥ 35 m away | 240 s after the clear **and** the player has stayed ≥ 55 m away for 45 s in a row |
| Foreman + escorts | 300 s, ≥ 35 m | 300 s, ≥ 55 m for 45 s |
| Field fabricator distance (encounter roots) | depot 40.4 m, Foreman 46.8 m — both counted as "away" | both inside the clearance: working at the bench never re-arms them |

A trip back to Ward (to sell) re-arms the nest; searching heaps next to a just-cleared nest stays safe for 4 minutes.

**Economy — Buy parts at Basic General** (`ItemSpec.partsPrice`, `ShopModel.BuyPart/SellsAsPart`, `PartsShopPanel`).
Rare parts (actuator, lattice shard, control core), components and mods stay loot/fabrication-only. A bought part
reveals its schematics like a pickup. Flask / medkit / scrap coil rows unchanged (4/2, 9/4, 2/1 cr).

| Part | Rarity | Mira pays | Mira sells |
|---|---|---:|---:|
| Scrap Alloy, Copper Filament | Common | 1 | 4 |
| Nanite Residue | Common | 1 | 3 |
| Damaged Servo | Uncommon | 3 | 10 |
| Micro Capacitor | Uncommon | 3 | 12 |
| Cracked Optic Lens | Uncommon | 4 | 14 |

## Scene patch — `AthenHill.Editor.GameplayV2Patch1.ApplyBatch`

`Assets/AthenHill/Editor/GameplayV2Patch1.cs`. Batch: `Unity -batchmode -nographics -projectPath …/unity/AthenHill
-executeMethod AthenHill.Editor.GameplayV2Patch1.ApplyBatch -logFile …` (no `-quit`; it calls `EditorApplication.Exit`,
0 = applied, 1 = refused). Requires the GameplayV2Installer marker; refuses if its own marker exists or the scene has
unsaved edits; finds objects by name/component; checks render-chunk sources; logs one `GAMEPLAY_V2_PATCH1 {…}` line.
Changes: depot nest `respawnClearance` 35 → 55, `awaySeconds` 0 → 45; `BermsTutorial.depotRespawnSeconds` = 240;
Foreman encounter gains `Spawn 2/3 · FeralWorkerDroid (escort)` (first two clear capsule spots on the Foreman's floor, in
line of sight, ≥ 2.5 m from nest spawns), clearance 55, away 45; the nine salvage nodes' `readyPrompt`,
`searchingPrompt`, `progressLabel`; EditorOnly marker `CitySession/Gameplay v2 · patch 1 (GameplayV2Patch1)`. The run
here: escorts at (-83.6, 1.04, -46.8) and (-79.8, 0.44, -43.2), 2.8–2.9 m from the Foreman; scene diff +198/−2.
Everything else (prompts' defaults, radio timing, cache lifetime/cap, Foreman tuning, prices, loot odds) lives in code
defaults, the Foreman prefab and the catalog assets. `ward-crafting.v1.json` was regenerated (`partsPrice`, escorts).

## Native re-QA checklist for the integrator (`qa.py`)

Merge, run `GameplayV2Patch1.ApplyBatch` on the integration scene (read the JSON line), build `LinuxBuild.Development`,
then with `qa.py` (1920×1080 unless noted):

1. **Fabricator keyboard (bug 1/2)** — run1 path to all three Mark I mods fitted. `focus_ui('fab-recipe-recipe_grip_stabilised_pistol')`
   should need one Tab from Close (only the selected schematic is a stop); `tap('Down')` × 8 must visit all 9 schematics
   one at a time (`snap()['session']['focused']` = `fab-recipe-<id>` each press). Select the grip, `tap('Tab')` → `fabricator-remove`
   (Craft/Fit disabled), Enter → the **grip** slot empties, cell/barrel stay (`craft()['slots']`), focus = `fabricator-fit`.
   Enter again → refitted, focus = the grip schematic. Tab from Remove/Fit reaches `fab-slot-grip`, `-barrel`, `-cell` in order.
2. **Fabricator layout (bug 3)** — `capture()` on open with a Ready part and with a preview: layout JSON should show
   `fab-stats` rows (8 + header) and all `fab-slot-*` fully inside the modal and window (no scroll offset); header labels
   `STAT/NOW/WITH MOD/CHANGE` non-overlapping. Repeat at `cmd('resize', width=1280, height=720)` (run8 step 10): focus
   every control by Tab and check each focused element's bounds are inside `modal-scroll`.
3. **Inventory arrows (bug 2)** — run9 save (10 items): Right from flask walks every tile in order without losing focus;
   Down/Up move by the rendered column count (5 at 1080p, 3 at 1280×720); Enter opens details.
4. **Basic General (bug 4/10, economy)** — with six salvage kinds carried all six Sell rows are visible without scrolling;
   Tab to the last `sell-all-*` stays on screen; selling the last row focuses `close`; selling the last scrap coil in
   the Supplies row focuses `buy2`. Buy parts: `buy-part-micro_capacitor` 12 cr (credits −12, capacitor +1,
   Charge Cell Core schematic revealed on a new game), disabled when credits < price; flask purchase and scrap-coil
   sale still 25→21 and →22 cr.
5. **Startup (bug 5)** — run2: New Game with a save → the confirmation replaces the buttons, nothing overlaps
   "Tab · Select Enter · Confirm"/"WARD / ATHEN HILL"; Esc restores the buttons with focus on New Game.
6. **HUD focus (bug 6)** — in Play `hold('w',1)`, `tap('Down')`, `tap('Tab')`-free walking, then `tap('Return')`:
   `focused` stays `None` and the state stays `Play` (Notes must not open). Tab still opens/closes the pack.
7. **Caches and nest (bug 7)** — clear the depot, leave caches, walk to the fabricator (≈ 40 m) and idle ≥ 4 min: nest
   does **not** re-form and caches remain (`FindObjectsByType` via dev-state or look). Walk to Ward (> 55 m) for ≥ 45 s
   after 240 s: nest re-forms; old caches still collectable.
8. **Foreman (bug 8, tuning)** — order 4: guidance label follows the droid as it paths hall → yard and hides while its
   bar is up; after the kill `DEPOT FOREMAN · last seen` points at the cache. Bar sits just above the head.
   `fight_foreman(seconds=180, profile_name='profile-foreman-v2')` — expect two `Feral worker droid` escorts in
   `enemies`, every third windup longer (≈ 1.6 s), `hpTaken` higher than before; record the human-equivalent time.
   The bot (0.8 s/shot) will be much slower than a human (≈ 60 s+); a human pass should land at 25–40 s.
9. **Text (bug 12)** — primer: Ossa's lines appear in the radio panel (`snap()['session']['radio']`, `radioSpeaker`,
   `radioQueued`) for their full time while pickups only toast/log (`notice` no longer carries "Collected: …" — the
   `collect_at` record's `notice` field will be empty or a prompt). Heap tour: prompts now start `E · Search`,
   `E · Strip` (carcasses) or `E · Salvage` (crashed drone) — match on `'E · ' in prompt` instead of `'Search'`.
10. **Saves** — run5 truncated save: the notice has no "(ArgumentException)"; run6/7 unchanged.
11. **Regression** — run1 city loop (spawn, four talks, trade rows, Lattice, Ring Gate, pause/notes), `log_errors()` empty,
    and re-profile the depot fight on an idle machine (the Foreman fight now has three droids).

## Verification

- Commits: `5ec1f995` (code, UI, data, icons, tests) and `b3986f7d` (patch 1 + scene + scene tests) on
  `ward/gameplay-v2`; this README in the following commit.
- EditMode on the committed tree: **152/152 passed** (Unity 6000.6.0f1 batch, `-runTests -testPlatform EditMode`).
  New: `GameplayV2FixesTests` (keyboard steps/columns, fabricator tab stop + selection + actions on the visible mod,
  current-loadout descriptions, UXML layout, radio queue and channel separation, cache eviction, nest re-form rule,
  Foreman tuning within the worker variant, bar anchors from the skeleton, Buy parts rules and panel, one icon per
  item with a 192 px texture, plain-word save errors, order 2 pacing on the real tables).
- `AthenHill.Editor.LinuxBuild.Development` on the committed tree (`b3986f7d`): **Build Finished, Result: Success**,
  0 compiler errors (player data 30 Sep 03:27 in this worktree's `Builds/LinuxDevelopment`; the first build here
  compiled 1920 shader variants, ~35 min).
- Not run here (by instruction): the native player and the Editor GUI. No frame-time claims are made; the Foreman fight
  now has three droids, so re-profile it.
- Unity rewrote `ProjectSettings.asset` (a scripting define) and the URP global settings during batch runs; those
  unrelated changes were reverted, not committed. Generated `Assets/Resources/PerformanceTestRun*.json` were removed.
