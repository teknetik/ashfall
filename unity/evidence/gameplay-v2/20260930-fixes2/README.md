# Gameplay v2 — second fix batch (after the native re-QA)

Branch `ward/gameplay-v2` from integration head `dbde0bed`. Answers [`../20260930-reqa/README.md`](../20260930-reqa/README.md).
Batch Unity 6000.6.0f1 only (no native player, no Editor GUI): layout, focus, light and frame-time effects are
unverified until the integrator's native pass. EditMode **158/158 passed** (152 + 6 new in `GameplayV2Batch2Tests`;
`GameplayV2FixesTests`, `GameplayV2SceneTests`, `WeaponLoadoutTests` updated). Build: see the last section.

| # | Re-QA item | Change |
|---|---|---|
| 1 | Tab leaks to the LOCAL log scrollbar | In every modal except Settings, Tab / Shift+Tab are handled by `CityHud.GuardNavigation`: they cycle through `UiNavigation.TabStops(scope)` — focusable, enabled, displayed controls of the open modal (inventory details when open; startup actions or the New Game confirmation on the menu), never scrollers or a focus-delegating field's insides — and wrap. HUD elements are made unfocusable **and** `tabIndex = -1` at start, on every state change and whenever a HUD scroll view re-lays out (UI Toolkit re-enabled the scroller slider). |
| 2 | Stale radio briefings | `RadioQueue` lines carry tags (`order:<index>:brief / done / engage`) and skip stale ones: a briefing (or engage warning) once its order is complete, a completion line once a later order completed. `FieldOrders` drops stale queued lines as soon as orders complete (the clock is stopped in the fabricator). Urgent lines jump the queue (an interrupted line resumes after, unless it went stale): the Foreman order's briefing (`urgentStart`) and a new `engageLine` spoken the first time the Foreman turns on the player — "It's seen you. When its optics flare red, a slam is coming: step back out of reach." |
| 3 | Cache placement | `SalvageCache.FindSpot`: five downward rays (centre + footprint corners, footprint 0.26 × 0.25 m half-size measured from the tray's LOD0) must land within 0.14 m on up-facing surfaces, and the tray's box resting on the highest must overlap no collider (wrecks, cradle bases, fences, platform lips). Tries the wreck point, then rings at 0.5/1.0/1.5 m; keeps ≥ 0.8 m from other caches; falls back to the old single ray only when nothing qualifies. |
| 4 | Drone wrecks slide 16–18 m | Hover wrecks: horizontal velocity is stopped beyond 2.5 m from the death point (`FeralDroid.wreckMaxTravel`), damping rises to 4 on first contact, and the body turns kinematic once still for 0.35 s (or after 4 s). `LootSource` waits for `WreckSettled` and drops the cache where the wreck rests. |
| 5 | Cache glow | Serialized on `SalvageCache.prefab`. Core emission (HDR) common (0.8, 0.72, 0.58) → uncommon (0.3, 1.35, 1.45) → rare (5, 2, 0.15) with a ±25 % 0.6 Hz pulse (off with reduced motion); luminance ≈ 0.73 / 1.13 / 2.5 (was 1.36 / 1.60 / 1.61, rare ≈ uncommon). Point light: 0.15 / 0.3 / 0.55 intensity, 0.8 / 0.95 / 1.25 m range (was 1.2 and 3.2 m for all), moved down to the core (y 0.45). |
| 6 | UI polish | Slot cards 14/16 px inner padding (titles clear the frame); `#fabricator-craft:disabled` uses the disabled colour; stat-change phrases never wrap inside ("Nano refill 30∕s → 39∕s" with no-break spaces and a division slash, `CraftingText.NoBreak`); inventory details replace the overview beside the grid (no clipping or overlap; title 24 px wraps clear of Close); Basic General ~100 px shorter (balance heads the Sell column, rows 70/54 px) so it fits its 690 px viewport; the colonist named by the interaction prompt hides its nametag, and a guidance marker that would sit on a nametag moves above it. Heap names: patch 2. |
| 7 | Idle droid cost | `FeralWorkerDroid.prefab` (and the Foreman variant): culling bounds fitted to the animation envelope over idle/walk/run/attack/hit/death + 12 % (root-bone space, extents 152 × 169 × 161 cm, was 450 × 180 × 450, ~1/9 the volume), `updateWhenOffscreen` off; legacy Animation culls `BasedOnRenderers` while idle and switches to `AlwaysAnimate` when engaged or dying (fights unchanged). Idle droids beyond 40 m (2.7× the aggro radius) stand still and think at 2 Hz; eye lights are off while unseen and calm; far, unseen idle droids skip foot/rotor presentation. Tool: `AthenHill.Editor.DroidRenderBounds.ApplyBatch` (logs `DROID_BOUNDS {…}`); test `DroidCullingBoundsCoverEveryClip` re-measures and checks coverage. |

Not changed: CPU skinning itself (~41 k vertices per droid). If visible droids still cost too much, Player Settings
→ GPU Skinning is the next lever (project-wide, so left to the integrator), or a droid LOD mesh.

## Scene patch — `AthenHill.Editor.GameplayV2Patch2.ApplyBatch`

Same conventions as Patch 1 (no `-quit`; exits 0/1; one `GAMEPLAY_V2_PATCH2 {…}` line; requires the Patch 1 marker;
refuses twice or over unsaved edits; render-chunk fingerprint check). Changes only the three heap nodes' names and
prompts — `Salvage node · Depot litter` → "Depot litter" / "E · Search the depot litter"; both
`Salvage node · Roadside scrap heap (…)` → "Roadside scrap" / "E · Search the roadside scrap" — plus the EditorOnly
marker `CitySession/Gameplay v2 · patch 2 (GameplayV2Patch2)`. Scene diff here +62/−6. Prefab and data changes
(worker droid bounds/culling, cache glow/footprint, field-order radio flags) come through the merge.

## Native re-QA checklist (`../20260930-reqa/qa.py`)

1. **Tab (bug 2)** — Basic General with salvage: Tab from the last `sell-all-*` wraps to `close`, then `buy0`…; never
   `unity-slider`. Shift+Tab reverses. Same cycle check in the fabricator, pack, pause, dialogue and on the start menu /
   New Game confirmation.
2. **Radio (bug 3)** — repeat `radio-after-fast-orders`: complete orders 2 and 3 back to back inside the fabricator
   (fit the cell, then fabricate and fit the barrel); after closing, no order-3 briefing plays (`radio`/`radioQueued`),
   only order 3's completion line; the Foreman briefing arrives straight away (urgent) and the engage warning plays the
   moment the Foreman alerts.
3. **Caches (bug 4)** — re-shoot `64-persist-*` and `81-cache-drone-*`: no overhang, nothing inside the cradle base or
   across the fence, caches ≥ 0.8 m apart. **Wrecks (bug 5)** — `persistence-test`: drone wreck-to-cache distance < 1.5 m.
4. **Glow** — `13-*`, `44-*` at 1/4/12 m in sun and shade, 17:00: rare reads strongest (pulsing), uncommon calm, light
   pool ≈ 1 m; capture a common-only cache.
5. **UI** — `21`, `25` (slot titles, disabled Fabricate grey, "39∕s" on one line), `50` (details beside the grid, not
   clipped), `60` (no scrollbar, parts help visible), `10` / `70-night-cam_salvage_general` (marker above Ossa's tag,
   Mira's tag hidden while "E · Talk to Mira" shows). Heap prompts: depot litter / roadside scrap.
6. **Perf (bug 1)** — `profile-with-foreman-group-idle` vs `profile-no-foreman-group` and the 20 s depot window; record
   `MeshSkinning.Skin` and main-thread time; walk the city with droids behind the camera (should cost ~0).
7. **Regression** — fights: slam tells, staggers, footsteps behind the player, death animations; `log_errors()`.

## Verification

- Commits on `ward/gameplay-v2`: `df4a98c4` (code, UI, data, prefabs, tests), `54629881` (Patch 2 + scene), this README next.
- `LinuxBuild.Development` of `54629881`: **Build Finished, Result: Success**, 0 compiler errors (a fresh shader-variant
  pass after the perf/APV changes, ~35 min).
- EditMode on the committed tree: 158/158. `DROID_BOUNDS` record: envelope extents (122, 136, 130) cm → fitted
  (152, 169, 161) cm in `Hips` space.
