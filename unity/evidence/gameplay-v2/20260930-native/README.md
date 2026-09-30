# Gameplay v2 native acceptance QA — 30 September 2026

Build: `unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64` (data 30 Sep 00:49, from `ward/next-level` 9da08d6e; the
uncommitted `GameSettings.cs` music-default edit is not in it). Native OpenGL 4.5, RTX 3060 12 GB / i9-10850K, driver 610.57.04,
1920×1080 windowed (Hyprland float), High preset + TAA, VSync off, uncapped. One player at a time in a `systemd-run` scope
(MemoryMax 12G). Harness: [`qa.py`](qa.py) (bridge for positioning/camera/captures/state/profiling; every verb by XTEST keys or
mouse). PNG captures are local-only; `*-layout.json` beside them are the UI Toolkit bounds at capture time.

| Run | What |
|---|---|
| `run1-newgame` | New game → city loop → primer → orders 1–5 → Mira salvage sale → Quit from Pause (real Enter) |
| `run2-continue` | Continue from free play; New Game confirmation + Esc |
| `run3-newgame-confirm` | New Game → confirm; primer again; mid-order-2 quit |
| `run4-continue-midorder` | Continue mid-order 2 |
| `run5/6/7` | truncated save / `version: 99` save / unknown item, recipe and slot IDs |
| `run8-freeplay-respawns` | Upgraded fights, depot/Foreman/heap respawn, cache despawn, 1280×720 UI |
| `run9-inventory-arrows` | Inventory arrow-key navigation with 10 items |

## Results

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | West Gate spawn, Mira/Torr/Vex/Linn, no movement in modals | PASS | run1 `02`, `03`; talks recorded in log |
| 1 | Flask 25→21 cr, scrap coil sale →22 cr, atomic | PASS | run1 `05` |
| 1 | Lattice link, Ring Gate offline (walk-in and E), pause/pack/notes | PASS | run1 `06`–`09` |
| 1 | Keyboard focus in modals | PARTIAL — see bugs 2, 4, 6, 10 | |
| 2 | Locker E, 7, three plates by RMB+LMB, first-contact drone, depot nest | PASS | run1 `10`, `11`, `fight-*.json`; run3 `primer.json` |
| 3 | Caches at wrecks, ground-snapped (incl. hover-drone kills), rarity glow, E collect | PASS | run1 `12`–`16`, `35` |
| 3 | Partial collect with full pack, remainder stays, later collectable | PASS | run1 `33` |
| 3 | 9 heap prompts, 1.3 s search, cancel on move, 4:30 respawn | PASS | run1 `heap-tour.json`, `17`–`20`, `27-*`; run8 (292 s → ready) |
| 3 | Field orders 1→5 text, rewards 0/20/25/40/50 cr, briefings, free play | PASS | run1 `26`, `40`, dev-state |
| 3 | Fabricator craft/fit/remove, stats (recoil 38→31→23, nano 100→135, refill 30→34.5, damage 34→40.8, range 70→80, aim 3.5→4.5) | PASS (values) / FAIL (keyboard + layout) | run1 `21`–`41` |
| 3 | Mira Sell 1 / Sell all | PASS (values) / FAIL (focus off-screen) | run1 `42`–`45` |
| 3 | Foreman spawn, pathing hall→yard, 400 HP, core → Mk II, Mk II craft | PASS | run1 `32`, `34`–`39`, `fight-foreman.json` |
| 4 | Continue restores credits, pack, mods, stats, schematics, craft counts, primer, pistol, order, city flags | PASS (free play and mid-order) | run2/run4 `state-*.json` |
| 4 | New Game confirmation (default focus Keep, Esc keeps), `.previous.json` kept | PASS / layout FAIL | run2 `02`, run3 |
| 4 | Truncated / newer / unknown-ID saves | PASS | `save-edge-cases.json`, run5 |
| 5 | Player.log exceptions/errors | PASS — none in 9 runs (the only exception is a deliberate bad bridge command in run2 proving logging works) | `run*/Player.log` |
| 6 | Frame time in Berms fights | recorded | `frame-time-summary.json` |

## Bugs (priority order)

1. **Fabricator keyboard acts on the wrong mod (Medium-High).** Recipe buttons select on focus (`FabricatorPanel.Build`,
   `FocusInEvent → Select`) and the action buttons come after the list in Tab order, so Tabbing from a recipe to *Remove/Fit*
   re-selects every recipe passed. Repro: all three mods fitted; focus *Gyro-Braced Grip*, Enter (no enabled action, focus stays),
   Tab to *Remove …* → Enter removed the **Salvaged Capacitor Cell** (last recipe traversed), not the grip. run1 `41`.
2. **Arrow keys double-step (Medium).** ↓ in the schematic list moves two recipes (coil → plate → cell → gyro → overclocked;
   Charge Cell Core, Stabilised Grip, Bored Barrel, Lattice Barrel unreachable by arrows). Inventory arrows also skip and lose
   focus (Right: flask → alloy → *none*), and `CityHud.InventoryKeyNav` assumes 4 columns while the grid renders 5. Likely cause:
   the `KeyDownEvent` handlers move focus and UI Toolkit's own `NavigationMoveEvent` moves it again.
3. **Fabricator layout at 1080p (Medium).** The stats table sits below the fold (Recoil row clipped; Nano/Refill/Aim rows need the
   mouse wheel), headers render as "NOWWITH SELECTION", the detail column wastes ~250 px, and Tab focus lands on off-screen slot
   cards because the modal ScrollView never scrolls to the focused element. run1 `21`, `22`, `29`, `38`; same at 1280×720 (run8 `10`).
4. **Sell salvage focus off-screen (Medium).** Six salvage rows, two visible; Tab reaches "Sell all" at y=1150 in a 1080-px window
   and Enter sells it unseen. run1 `43`. Same ScrollView fix as 3.
5. **New Game confirmation overlaps the startup footer (Medium).** Panel (y 908–1076) draws over "Tab · Select Enter · Confirm" and
   "WARD / ATHEN HILL". run2 `02`.
6. **HUD takes keyboard focus while walking (Medium, probably pre-v2).** WASD moves focus across notes/pause/inventory/hint buttons;
   Enter in Play then opens Notes. run1 `28`.
7. **Uncollected caches vanish while crafting (Low-Med, design).** The fabricator is 38.9 m from the nest (>35 m clearance), so after
   120 s at the bench the nest re-forms and its caches despawn (run8: all three gone at 121.6 s).
8. **Foreman guidance and bar (Low-Med).** "DEPOT FOREMAN · n m" is pinned to the spawn point, not the droid; its health bar floats
   ~1.5 m above its head (`CombatHud.UpdateBars` offset not scaled for the 1.3× variant). run1 `34`.
9. **Description deltas use the base weapon (Low):** "Recoil 38 → 23" when current is 31; "Damage 34 → 49.3" when current is 40.8.
10. **Focus lost after actions (Low):** after Fit, and after selling the last Scrap Coil, focus becomes none.
11. **Icons (Low):** servo, alloy, nanites, copper, capacitor, actuator and control core all use the scrap-coil illustration in the
    pack and Sell list; the overview title clips ("Foreman Control Cor"). run9 `01`.
12. **Text (Low):** 50–60-word Ossa briefings stay 4 s (`GameSession.Notify`) and are overwritten by the next pickup; pickups show both
    the banner and the toast; every heap prompt says "Search the scrap heap" (carcasses, crashed drone); the corrupt-save notice
    exposes "(ArgumentException)"; the "Missing parts … Fitted to your Scrap Pistol" line is red for a fitted mod.
13. **Art (Low):** caches read as small log stumps and share the Meshy prop with the two roadside heaps; a hover drone's wreck slid
    6.5 m from its cache. Continue's label is centred while New Game/Settings are left-aligned.

## Tuning and pacing

- Order 2 is the only grind: micro capacitors took two depot clears plus nine heaps (pity guaranteed the second drone). Orders 3 and
  5 needed nothing new — alloy had hit its 30 cap during order 2 and the Foreman guarantees actuators. Primer → free play took
  ~20 min with harness overhead, mostly the primer and order 2.
- The Foreman is too easy for an elite: 10 Bored-barrel hits (40.8) and a 135-nano cell holds 15 shots, so a human at the 0.28 s
  interval can kill it in ~3 s. The bot (~0.8 s per shot) needed 12–13 s, took 53–86 damage and went down 0 times. The depot nest
  is harder: two workers striking together downed the bot in three of four clears.
- Six of nine heaps are 1.5–6.5 m from nest spawns (15 m aggro), and every bench visit re-arms the nest. Credits reach 200 with
  nothing to buy but flask, medkit and coil.

## Frame time (profileStart/Stop)

| Fight | avg FPS | p50 | p95 | p99 | max ms | frames >16.67 ms |
|---|---:|---:|---:|---:|---:|---:|
| run1 depot 1 | 73.4 | 14.1 | 16.6 | 17.3 | 19.2 | 47/1217 |
| run1 depot 2 | 71.7 | 14.4 | 17.0 | 19.1 | 26.9 | 92/1324 |
| run1 Foreman | 82.3 | 11.6 | 15.0 | 15.6 | 18.6 | 2/1066 |
| run8 depot (contaminated) | 58.4 | 16.9 | 23.5 | 27.2 | 45.1 | 390/739 |
| run8 Foreman (contaminated) | 47.4 | 21.1 | 25.6 | 27.8 | 32.5 | 518/560 |

Main thread ≈ frame time (CPU-bound); GPU time and draw/batch counters are unavailable in this player; 11–15 M submitted
triangles, 150–260 SetPass. The run8 rows overlap an unrelated `blender -b … build_cache.py` job started at 01:22 (one core
at 100 %, load average 30+, 24 % I/O wait, swapping), so re-measure them on an idle machine. The clean depot fights miss the
p99 ≤ 16.67 ms target.
