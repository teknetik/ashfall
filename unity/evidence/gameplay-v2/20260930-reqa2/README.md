# Gameplay v2 native re-QA 2 (after fix batch 2) — 30 September 2026

Build: `Builds/LinuxDevelopment`, data 30 Sep 06:13, `ward/next-level` HEAD `aa99640b` (fix batch 2 + desert terrain v2 +
sky v4 + perf pass v1). RTX 3060 / i9-10850K, driver 610.57.04, OpenGL 4.5, 1920×1080 windowed, High + TAA, VSync off.
Harness [`qa.py`](qa.py) = [`../20260930-reqa/qa.py`](../20260930-reqa/qa.py) + `tab_cycle`, `cycle_summary`, `project`
(world→screen for annotated overheads). Real XTEST input for every verb. PNGs local; `*-layout.json` are UI bounds.
Runs: `runA-newgame` (no save → city loop → primer → orders 1–4 → Basic General → night → Quit), `runB-continue`
(menu with save, confirm, Continue, placement kills, terrain views, profiles).

## Checklist

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Focus | PASS: Tab and Shift+Tab wrap in Basic General (11 stops empty, 19 with salvage), fabricator (6), dialogue (3), pause (9), start menu (2; 3 with save), New Game confirm (2); never `unity-slider` or behind the modal. Pack: Tab/Shift+Tab close it even from details (as the footer says) | runA `focus-*.json`, `city-and-focus-*.json`, `shop-and-mira-tag.json`; runB `focus-*.json` |
| 2 | Radio | PASS: orders 2+3 finished inside the fabricator → order-3 briefing and order-2 completion dropped as stale, Foreman briefing at once (urgent), then order-3 completion. "It's seen you…" at the Foreman's first Alert, once | runA `radio-fast-orders.json`, `fight-foreman-order4.json`, `60-foreman-engage-radio.png` |
| 3 | Cache placement | PASS: 13 caches flat, ≥ 0.8 m apart; none overhang the cradle platform or sit in the base, fence or post | runA `32`/`33`, `61-*-annotated`; runB `20-*-annotated`, `21-*`, `22-*` |
| 4 | Wrecks | PASS: drone wreck travel 0.39 / 0.10 / 0.45 m; cache 0.5–1.0 m from the wreck | runA `firstcontact-wreck.json`, `depot-primer.json`; runB `depot-fight-placement-1.json` |
| 5 | Glow | PASS with note (below) | runA `20-*` (common), `62-*` (rare), `63-*` (uncommon), `64-*` |
| 6 | UI polish | PASS: slot titles clear, disabled Fabricate grey, "34.5∕s → 39∕s" one line, details beside the grid, Basic General fits (no scrollbar, help visible), marker above Ossa's tag, Mira's tag hidden with her prompt, heap prompts "depot litter"/"roadside scrap" | runA `03`, `10`, `41`, `42`, `50`, `70`–`72`, `heap-tour.json` |
| 7 | Droid cost | Improved, not zero (table) | runB `perf-*.json` |
| — | Regression | PASS: four talks, no modal movement, flask 25→21, coil →22, Lattice, Ring Gate offline, pause/notes/pack, Continue restore; Foreman Mk I 27.7 s, 0 damage. Player.log: no exceptions/errors | runA/runB |

## Issues

1. **Capture artifact (Low-Med, 1 in ~75 captures).** runA `30-depot-drone-wreck-and-cache.png`: the top-left 960×540
   quadrant is a flat beige fill (exactly half resolution). The same view re-captured 1 s later is clean (`31`). Suspect a
   half-res buffer from the perf pass (half-res SSAO) reaching the back buffer for a frame.
2. **Cold first traversal hitches (Low-Med).** The first West Gate → hill walk of runB had 435/326/524 ms stalls; three warm
   repeats (including one straight after 30 s in the Berms) had none (max 28–33 ms).
3. **Objective box vs fabricator (Low).** A three-line order objective grows the Field Notes box to y 233; the fabricator modal
   (top 186) cuts its last line (runA `41`).
4. **Memory (Info).** Player RSS 7.6 GB after ~35 min in runB (texture current 4.5 GB, desired 4.9 GB, streaming on) vs 3.1 GB
   in re-QA 1; dropped to 5.3 GB later.
5. **Glow at range (Low).** Rare amber is clearly strongest at 1–4 m (pulsing core, broad orange pool in sun and shade;
   uncommon calm cyan, ~1 m pool, no flooding; common pale). At 12 m in sun the amber blends into the orange ground while
   cyan still pops (`64-rare-h17-12m-yaw290`).

## Terrain v2 (Berms)

Compared with 29 Sep baselines (`rendering/20260929/baseline`) at 13:00/17:00 (`runB 30-terrain-*`, `31-ground-*`): better.
Real scree/gravel detail with shading replaces the flat beige blur, slopes have form, the depot area is less fog-flattened,
and the 17:00 light rakes nicely. The berm-to-flat-ground transition follows the slope toe with no hard texture seam. But:
steep basin faces carry regular pale, hard-edged diagonal **stripes** (dark stripes before; they look geometry-driven,
e.g. terraced facets picking the rock layer). They are obvious at player height beside the road (`31-ground-edge-west-h13`)
and from the overview. Far ridges read near-white at 13:00 (`30-terrain-cam_berms_road-h13`). The flat playable ground
(range, road) still uses the older smooth orange material and looks plainer than the new slopes beside it. No visible tiling.

## Frame time (`frame-time-summary.json`)

Load 13–20 in clean samples (IO wait, nice-10 ffmpeg). A 16-core Blender job from another session ran 06:16–07:0x; those
samples are marked and excluded.

| Profile | avg FPS | p50 | p95 | p99 | max ms | tris (M) |
|---|---:|---:|---:|---:|---:|---:|
| Depot view, Foreman group idle ×3 | 66.3–67.9 | 14.64–15.05 | 16.0–16.3 | 17.1–17.7 | 19.2–21.5 | 13.2–13.6 |
| Same view, no group ×3 | 71.5–78.7 | 12.67–13.67 | 13.8–17.6 | 14.8–22.0 | 19.9–29.8 | 13.1 |
| Facing away: group / none | 149.4 / 161.3 | 6.61 / 6.05 | 8.17 / 7.10 | 11.93 / 7.79 | 24.4 / 9.6 | 5.3 |
| Depot fight 20 s (nest) | 64.2 | 16.03 | 17.27 | 18.82 | 21.01 | 15.3 |
| `cam_hill` 17:30 | 67.7 | 14.73 | 16.23 | 18.50 | 20.93 | 20.5 |
| West Gate → hill walk, warm ×3 | 57.0–57.9 | 17.57–17.65 | 25.9–26.7 | 27.5–28.2 | 28.2–33.4 | peak 39.8 |

Idle group in view: +1.7 ms p50 (re-QA 1: +2.3 ms), +0.43 M tris, +17 SetPass. `cam_hill`: 60.5 → 67.7 FPS, 27.5 → 20.5 M
tris. The hill heading's peak dropped from 60–81 M to 39.8 M tris but is still ~57 FPS; it's the weakest view. Only the facing-away
views and one of three no-droid depot samples meet p99 ≤ 16.67 ms.
