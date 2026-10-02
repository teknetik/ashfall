# Walk-in Salvage shop (1 October 2026)

Carl (1 Oct 2026): "make the salvage shop walkable. i want it part of the tutorial mission. there is a feild cart where
you can perform the crafting currently. the salvage shop should be open to trade and have the equipment in there and
an npc to trade with and some quest dialog. from the robot tutorial part i get the loot and to to salvage shop and get
to upgrade my pidtol".

Not yet accepted by Carl. Unity side, quest data and tests: `unity/EDITING.md` ("Walk-in Salvage shop, Brann and the
first field order"); evidence: `unity/evidence/salvage-shop/20261001/README.md`.

## What was built here

`salvage_interior.py` opens the Salvage shop (north avenue, root (-18.1, 0, 18), yaw 90) and fits out its ground floor.
It is called by `art/north_avenue_20260930/author_north_shops.py` `salvage()`: `prepare(s)` right after the shop is
created (keeps the porch sand out of the bay, swaps in the walk-in colliders), `add(s)` last (the interior is a deferred
builder after every exterior one, so the exterior's random layout is identical to the 30 Sep shop). Two small hooks in
the shared `art/hall_district_20260930/author_ward_shops.py` support it: `Shop.shutter(open=True)` (curtain rolled
into the box, bottom bar and pulls under it) and `extra_parts` / `post_build` in `Shop.finish` (no effect on other shops).

- Inner skin 0.42 m inside every outer face, coursed ashlar on the Ward masonry kit (rough first course), stone linings
  closing the wall void at the bay and both closed doors, a riveted steel lintel channel over the bay.
- Flagged floor (running under the walls so the wall foot has no slit), a checker plate in front of the bench, a drain.
- Two steel I-beams along the room on padstones and bearing plates (the east one yellow: the monorail of a chain hoist
  with hook and pendant control), timber joists in steel shoes, a board deck (UVs turned so the grain runs along the
  boards).
- Trade counter (1.0 m worktop): steel frame, four salvaged sheet panels in different old paints, timber top with a worn
  steel nosing, recessed kick, a shelf on the dealer's side.
- Conduit runs, a breaker panel, switch boxes; three enamel pendant shades with warm bulbs (lights are added in Unity).
- Separate parts `Salvage_Interior{Masonry,Floor,Metal,Timber,Deck,Glow}_LOD0/1` so Unity can give the room its own
  ambient, light layer and shadow settings. Record: `rec["interior"]` in `Art/WardShops/Models/salvage.json`.

Triangles (LOD0 / LOD1): 122,215 / 21,510 for the whole shop (was 73,583 / 19,068; the exterior is unchanged apart from
the shutter slats).

## Run order

1. `blender.sh art/north_avenue_20260930/author_north_shops.py -- salvage` (Blender 5.2, clean environment, about 1 min)
2. `blender.sh art/salvage_shop_20261001/review_interior.py` (optional source renders into `review/`, not the game's render)
3. Unity: `SalvageShopPass.RunBatch --steps models,install,verify -nographics`, then the graphics step `bake` when the
   room changed (see `unity/EDITING.md`).

Other scripts: `run_tests.sh <out>` (EditMode tests under the Unity lock), `combined_test.sh` (build, the shop playthrough,
city loop, range tutorial check, A/B frame-time walks).

Assets made for this pass by other scripts: Brann (`meshy/salvage-dealer-20261001/`) and the workbench and racks
(`meshy/salvage-shop-props-20261001/`), each with its own provenance README. Heavy media (`.blend`, renders, logs) stays
local per `.gitignore`.
