# Gameplay v2 native re-QA (after the fixes) — 30 September 2026

Build: `unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64`, player data 30 Sep 03:38, `ward/next-level` HEAD `4423b50a`
(fixes merge `b67abd9a` + salvage cache hero prop). Native OpenGL 4.5 core, RTX 3060 12 GB / i9-10850K, driver 610.57.04,
1920×1080 windowed (Hyprland float), High preset + TAA, VSync off, uncapped, one player at a time in a `systemd-run` scope.
Harness: [`qa.py`](qa.py), an adapted copy of [`../20260930-native/qa.py`](../20260930-native/qa.py) (kept unchanged): heap
prompts matched on `E · `, pickups read from the salvage toast, radio fields recorded (`RadioWatch`), a one-pass aim, Foreman
escorts and tell timing (`DroidWatch`), layout/profiling helpers. PNGs are local-only; `*-layout.json` are UI bounds at capture.

| Run | What |
|---|---|
| `run1-newgame` | No save → city loop → primer → orders 1–5 → free play (cache persistence, nest re-form, Buy parts, sales, night, profiles) → Pause/Quit |
| `run2-continue` | Continue menu, New Game confirmation + Esc, Continue restore compared with run1's quit state |
| `run3-newgame-confirm` | New Game over a save → primer → order-2 pacing sample 2 → orders 2–3 → order-4 Foreman captures |
| `run5-corrupt-save` | Truncated save → notice; cache/droid/bridge cost experiments; 20 s depot-fight window |

## Re-QA checklist

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Fabricator keyboard | PASS: ↑/↓ one step per press, 9/9 schematics, stops at edges; title follows selection; Remove on the selected grip emptied only the grip → focus Fit → Enter refits → focus grip schematic; Tab Fit → grip/barrel/cell slots | run1 `fab-keyboard-*.json`, `28` |
| 2 | Fabricator layout | PASS at 1080p and 1280×720 (stats table, header, slots visible, no scroll); cosmetic defects below | run1 `20`, `21`, `25`, `29*`, `fab-layout-1280x720.json` |
| 3 | Inventory arrows | PASS (11 items; 5 columns at 1080p, 7 at 1280×720; shorter-row rule; Enter → details) | run1 `inventory-arrows-11.json`, `48`–`51` |
| 4 | Basic General | PASS values/focus (six Sell rows visible; Buy part 172→160 cr, +1 capacitor; disabled at 11 cr; sell-all deltas atomic; sold-out → neighbour, last → Close; last coil → `buy2`; flask 25→21, coil →22). Tab leaks to the chat scrollbar (bug 2) | run1 `03`, `04`, `60`–`63`, `shop-*.json` |
| 5 | Startup | PASS (confirmation replaces actions, ends y 807 vs footer y 962; default Keep; Esc → New Game focused; `.previous.json` kept; Continue left-aligned) | run2 `01`–`03`, `new-game-confirm.json`; run3 |
| 6 | HUD focus in Play | PASS (W/arrows/Enter: focus None, still Play; Tab toggles pack) | run1 `hud-focus.json` |
| 7 | Caches + nest | PASS: nest stayed cleared ~23 min near bench; 6/6 caches present after 6.5 min at the fabricator; re-formed after ≥45 s away; 3/3 old caches collectable after the re-form. Caches expire at 600 s game time (by design) | run1 `persistence-test.json`, `reform-old-cache-test.json` |
| 8 | Foreman | PASS: two escorts, 1400 HP, every 3rd tell 1.76–1.94 s (others 1.06–1.21 s, 0.1 s sampling), arms-up slam pose; bar ~0.3 m above head; marker on live droid, hidden while bar shows, `last seen` after kill | run1 `40`, `43`, `fight-foreman-3-mk1.json`; run3 `30`–`33`, `fight-foreman-order4.json` |
| 9 | Text/radio | PASS: lines 2.5 s + 0.3 s/word, queued, clock paused in modals; pickups toast/log only; per-node prompts 9/9 (Search/Strip/Salvage). Stale queue (bug 3) | run1 `10`, `11`, `primer-*.json`, `heap-tour.json`; run3 `radio-after-fast-orders.json` |
| 10 | Saves | PASS: "(the file is damaged or incomplete) … kept beside your saves"; Continue restores everything | run5 `02`; run2 `continue-compare.json` |
| 11 | Regression | PASS: 4 talks, no modal movement, trades, Lattice, Ring Gate offline, pause/pack/notes; no exceptions in 4 Player.logs | run1 `city-loop.json`, `run*/Player.log` |

## Bugs (remaining / new)

1. **Performance, Medium.** Each live Feral droid costs ~0.8 ms/frame even idle and 13 m away: same depot view p50
   13.1 → 15.4 ms (76 → 65 FPS) when the Foreman group (3 idle droids) exists (+0.5 M tris, +21 SetPass). With nest + Foreman group,
   fights run 57–65 FPS, p99 19–21 ms. Caches (+0.3 ms) and the QA bridge (0 ms) are not the cause. Suspect the skinned
   renderers' huge culling bounds (never culled, drawn into every shadow cascade) plus a point `eyeLight` per droid (`FeralDroid`).
   run5 `cache-cost-experiment.json`.
2. **Focus leak, Low-Med.** In Basic General, Tab after the last row focuses `unity-slider` — the LOCAL log's scrollbar behind the
   modal; nothing visible has focus and Enter does nothing. The HUD non-focusable pass missed the `log-scroll` scroller (`CityHud`).
   run1 `05-shop-focus-on-chat-scroller.png`, `shop-buyparts.json`.
3. **Stale radio, Low-Med.** The radio clock stops in modals, so orders finished inside the fabricator replay afterwards: order 3's
   briefing played with order 4 already on the HUD, and the Foreman warning ("when its optics flare red, step back") arrived
   35–45 s after order 4 started. Suggest dropping a briefing whose order is already complete (`FieldOrders`/`RadioQueue`).
   run1 `40`; run3 `radio-after-fast-orders.json`.
4. **Cache placement, Low.** Single-ray ground snap: caches overhang platform edges (`64-persist-escortB-4m`), sit inside the
   cradle base (`64-persist-nestworkerB-4m`), straddle a fallen fence (`81-cache-drone-*`), and stack ~1 m apart
   (`SalvageCache.Ground`/spawn).
5. **Drone wreck slide, Low (old bug 13).** Wrecks slid 16.8 m and 18 m from their caches (run1 `persistence-test.json`).
6. **UI polish, Low.** Fabricator slot titles collide with the card frame; disabled Fabricate keeps cyan text on a locked recipe;
   "39/ s" wraps (run1 `21`, `25`). Inventory details popup clipped 30 px at the bottom, overlaps the overview, title touches its Close
   button (run1 `50`). Basic General content is 40 px taller than its viewport (parts help hidden, scrollbar shows). Guidance marker
   overlaps Ossa's nametag (run1 `10`); Mira's nametag covers the lit BASIC GENERAL sign (run1 `70-night-cam_salvage_general`).
   "Depot litter" says "roadside scrap" while the two roadside heaps say "scrap heap".
7. **Info.** At 21:30 URP halves punctual shadow resolution: 24 shadow maps don't fit the 4096 atlas (run1 Player.log).

## Visual verdicts

- **Cache prop** (run1 `13-*`, `44-*`, `64-*`, `81-*`): reads as a salvaged droid-housing tray with servo, coil and canister; detail
  holds at 1 m, slightly soft albedo on the curved plate; grounded on flat ground. Uncommon cyan is legible at 4–12 m but floods ground
  and platforms cyan within ~2 m and dominates in shade; **rare amber reads weaker than uncommon** (yellow lamp on orange ground at
  17:00). A common-only cache was not captured (they were collected by `primer()`).
- **Fabricator/Basic General/radio/toast/search bar/startup:** clean at 1080p, consistent bronze UI, everything in view.
- **Foreman fight** (run3 `31`–`33`): elite silhouette, arms-up slam tell with flaring optics, bar tight above the head.
- **Night shop row** (run1 `70-night-cam_avenue`, `…salvage_general`): warm lit windows on Tool Exchange, neon signs, BASIC GENERAL
  letters glow warm; most other windows stay dark and the plaza is moonlit-blue.

## Frame time (`frame-time-summary.json`)

Load average 13–16 throughout (14.6 with no player): IO-wait from root `updatedb` (D state), an orphaned `bfs /` scan and a nice-10
jellyfin ffmpeg; CPU PSI ~0.7 %, memory PSI 0, IO PSI ~40 %, player not swapped. GPU time unavailable; main thread ≈ frame time.

| Profile | avg FPS | p50 | p95 | p99 | max ms | >16.67 ms |
|---|---:|---:|---:|---:|---:|---:|
| Depot fight 20 s window (nest + escorts, run5) | 57.3 | 17.29 | 20.38 | 21.46 | 24.06 | 774/1156 |
| Depot fight 7.4 s (nest, idle Foreman group, run1) | 59.0 | 17.15 | 19.69 | 20.81 | 23.90 | 260/434 |
| Foreman + 2 escorts, Mk I, 30.8 s | 63.9 | 15.50 | 18.37 | 19.21 | 22.30 | 534/1969 |
| `cam_hill` 17:30 static, 20 s (27.5 M tris, 325 SetPass) | 60.5 | 16.45 | 17.27 | 18.57 | 20.10 | 348/1220 |
| City walk 60 s, run | 94.9 | 8.77 | 21.19 | 26.26 | 61.35 | 1055/5729 |

City walk: 6 frames > 33 ms at the West Gate → hill heading (60–81 M submitted tris, 800–1050 SetPass). None of the gameplay
profiles meet p99 ≤ 16.67 ms.

## Pacing

- Order 2: sample 1 had 3 capacitors from primer caches (0 clears, 0 heaps; 5 of the next 8 heaps also dropped one). Sample 2 had
  0 → 6 heap searches, no extra clear. Primer credits (40) already buy both capacitors (24 cr), so the gather step is optional.
- Foreman with Mk I: 27.1 s from first hit (46 shots, no damage, bot backs off every tell), 59.6 s with poor line of sight
  (1 down, 113 damage). Every 3rd strike a slam; recovering from a down resets the count.
- Free play: escorts stand 7–9 m from the nest yard, so nest fights pull in the escorts and often the Foreman (5–6 droids).
