# Walk-in Salvage shop, Brann and the first field order: evidence (1 October 2026)

Request (Carl, 1 Oct 2026): make the Salvage shop walkable and part of the tutorial; it should be open to trade, hold the
crafting equipment (until now a field tool cart at Ossa's post), have a trader with quest dialogue, and the flow should be
robot tutorial → loot → Salvage shop → upgrade the pistol. Not yet accepted by Carl. Editing guide: `unity/EDITING.md`
("Walk-in Salvage shop, Brann and the first field order"); sources: `art/salvage_shop_20261001/README.md`.

## What changed

- **Building**: the Salvage shop's loading bay is open (shutter rolled up) and its ground floor is a furnished room on the
  Ward masonry kit, with walk-in colliders. Exterior geometry is unchanged apart from the shutter.
- **Brann** (new talking NPC, salvage dealer; Meshy model re-rigged with idle and talk clips) behind a trade counter. His
  counter sells crafting parts and buys salvage (no supplies list; Mira's Basic General is unchanged).
- **Workbench** (new Meshy hero prop) is now the crafting station; the outpost tool cart is dressing only.
- **Quest**: Ossa's primer completion line sends the player to Brann. Field order 1 (*Steady Hands*) gained a Report stage:
  once the servo, alloy and nanites are in the pack, Field Notes and the guidance marker point to Brann; talking to him
  moves the order on to Fabricate → Fit (at his bench) → test fire in the Berms. His dialogue opens differently at each
  step (8 openings, 12 nodes, up to 3 choices), and can open the bench or the counter directly. Later orders' texts name
  Brann's bench.
- **Systems** (data-driven, reusable): dialogue openings and per-choice conditions (`QuestConditions`), story flags,
  `fabricator` dialogue action, per-trader shop profiles, the optional Report block on field orders, a third dialogue
  button, `InteriorLighting` (interior ambient probe, actors blend in at the bay, indoor lamps on light layer 7), and a
  line-of-sight test for NPC nametags (no names through walls). Saves gain `orders.reported` and `city.flags` (version
  unchanged; older saves load and ask for the visit once).

## Verification

| Check | Result |
| --- | --- |
| Scene verify (`SalvageShopPass verify`, `verify.json`) | ok: wiring, cart retired, guidance targets, dialogue data, capsule sweep porch → bay → counter → bench, no missing materials, LODGroup holds all interior parts |
| EditMode tests | 203/203 (`tests-2/`, `tests-3/` on the final code), including 8 new `SalvageShopTests` and updated field order / checkpoint / scene / pack tests |
| Native real-input playthrough (`tools/check_salvage_shop_native.py`) | 25/25 on every build (`combined/salvage`, `round2..4/salvage`) |
| City loop (`combined/cityloop`) | CITY LOOP PASS |
| Range tutorial check (`combined/tutorial`) | passed, 10/10 |

Captures: Blender source renders `art/salvage_shop_20261001/review/` (local), editor captures `editor-1..3/` (13:00),
native captures `*/salvage/run/` (review cameras at 13:00 and 20:30, first-person counter and bench, dialogue, workbench,
shop window, street views).

## Frame time (RTX 3060 12 GB, Linux OpenGL Core, 1920×1080 High, development builds)

Warmed real-input north avenue walk (`tools/profile_north_walk.py`, passes the Salvage frontage), alternating the batch-2
final build (`Builds/final`) and the new build, two pairs per round:

| Round (new build) | Noon avg fps / p50 ms final → new | Night avg fps / p50 ms final → new |
| --- | --- | --- |
| 1: first install (`combined/`) | 90.3 / 8.77 → 82.9 / 10.03 | 74.8 / 12.98 → 72.6 / 13.12 |
| 2: props unshadowed, Brann culled off screen (`round2/`) | 90.7 / 8.79 → 82.9 / 10.03 | 75.1 / 12.93 → 72.9 / 13.10 |
| 4: room drawn only when seen + portal test through the bay (`round4/`) | 89.3 / 8.88 → 89.5 / 8.85 | 74.4 / 13.10 → 73.6 / 12.87 |

Attribution in one build (`attrib/`, `attrib2/`; 8 s dwell at `cam_district_salvage`, 13 m in front of the shop, 13:00):
the interior renderers cost 1.4 ms (0.79M triangles over all passes, 76 more SetPass calls), the five lamps about 0.17 ms,
the reflection probe nothing measurable, the per-renderer ambient (MaterialPropertyBlock) nothing measurable. With the
portal test that view is 8.95 ms against 8.65 ms in the final build (`dwell3/`, `attrib2/none-*`). Walk p99 at night
rose about 1.5–3 ms (18–20 → 21 ms; p99 is reported, not a gate in AGENTS.md §7); maxima are unchanged.

## Known defects / follow-ups

- Brann (Meshy): fused fingers, shoulder bulge in the idle, forearm through the hip holster in the idle, back strap
  tearing behind the raised arm in the talk clip (agent renders in `meshy/salvage-dealer-20261001/renders/`).
- Parts racks: small parts are lumpy at 0.8 m; one bin stack runs through a shelf lip.
- The workbench's print head sits at eye height in front of the worktop (first person looks into it at the bench).
- The test save used by the playthrough has no loot state, so its Continue notice mentions a skipped "loot generator
  state" (test artefact, not a game defect).
- The interior is unbaked: a custom ambient probe and a baked box reflection stand in for GI.
- Rollback: `rollback/` (pre-pass scene, Salvage GLBs, record and prefab; local only).
