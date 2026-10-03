# Ward life pass — 3 October 2026

Visual/storytelling pass on three weak spots in the gameplay frame: they should say how Ward survives (aquifer water,
goods through the Quantum Tube, a defended gate) and carry "this place saw a battle long ago" wear. **Not yet accepted
by Carl.** No Meshy credits used; no new realtime lights (the two bastion lamps replace the round-two lamps one for
one). Unity installer: `unity/AthenHill/Assets/AthenHill/Editor/WardLifePass.cs`. Evidence:
`unity/evidence/ward-life/20261003/` (survey, build/install/verify JSON, view budget, editor captures `editor/v1..v4`,
rollback scene copy `rollback/before-ward-life.unity`). Review renders and sheets: `review/`.

## 1. West Gate bastions (Carl's open item: "gabion bastions read as tiled boxes")

Round two (`art/ward_buildings_20261003`, `gate_bastion`) used identical 1 m cells: a flat hessian liner behind a 25 cm
wire grid. Rebuilt as welded-mesh stone gabions (models `WL_GateBastionS/N`, same roots/yaw/footprint, scene root
**Ward life: West Gate bastions**; round-two root `Ward building: West Gate bastions` deactivated):

- **Fill you can see through the mesh**: `bake_gabion.py` packs ~450 angular stones (8–26 cm; sandstone, pale
  limestone, grey basalt, red-brown ironstone, a few broken dressed blocks = rubble of the Fall reused) against the mesh
  plane, front and back layers, tileable 1.5 m bake (albedo / normal / AO+smoothness mask / height) rendered with Cycles.
  The fill uses **Masonry Lit** (copy of `VH_AshlarRough`, `WL_GabionFill`), so every basket gets its own tint, the
  ray-traced occlusion of the kit and the old battle damage/soot channels; parallax 0.025.
- **Wire with alpha**: 100 mm welded mesh, 5 mm wire with weld beads, weathered galvanising (white rust, red rust at
  welds) on an alpha-clipped layer 12 mm in front of the fill, aligned to each basket's own corner (`WL_GabionWire`,
  coverage-preserving mips, no shadow casting). A fresh galvanised set (`WL_GabionWireFresh`) marks the repair.
  LOD1 swaps to a fill bake with the mesh composited in (`WL_GabionFillWired`, no alpha test beyond ~22 m).
- **Shape**: 2 m / 1 m / 1.5 m / 1.5 m bottom baskets, 0.5 m top tier stepped back 10 cm in stretcher bond, per-basket
  corner jitter, faces bulging in the lower half, lids sagging; heavy edge wires and spiral binders at the joints (LOD0).
- **Sandbags that drape**: bags are built on a support heightfield of whatever is under them (baskets, lower courses),
  so they sag into gaps, slump over the blown basket and over edges; tied ears; three hessian tones (`WG_Hessian`,
  `WL_HessianOld`, `WL_HessianPale`). The gun platform bags are draped the same way.
- **Damage story**: south post — a top basket blown out long ago, its mesh peeled down over the face, fill spilled in a
  scree onto the paving, shrapnel/scorch damage in the fill round it. North post — a burst basket re-meshed with fresh
  panels and paler fill, a steel plate ratchet-strapped over the worst bulge, the lost top basket replaced by bag courses.
- Kept from round two (called through `author_buildings.gate_bastion` with its cells/sack boxes swapped): pintle gun,
  shield, platform deck, field telephone, GATE POST plates, ammo box, crate, stool (NPC sit point), binoculars, jersey
  barriers, the clocked post lamp. Colliders: same five boxes (back row 1.84 m high, return 1.56 m).
- Triangles: LOD0 33.9k (S) / 32.3k (N) (+ round-two props), LOD1 5.7k / 7.4k, LOD2 24. Round two was 34.3k / 3.5k.

## 2. The Lattice court → the Wardens' water ration point

Rationale: Ward exists because of its aquifer (lore.md), and the Wardens' "quiet, unbroken duty" includes keeping the
aquifers safe. The hall is the Wardens' house, so its back court is where they hand out the daily water: it explains
the city's survival, gives the empty court people-shaped wear, and fits under the existing Lattice court sail. (A muster
yard was the alternative; it adds no new reading of how the city lives.) Scene root **Ward life: Lattice court water
ration**, model `WL_WaterPoint` at world (1.9, 0, −34.5):

- Header tank against the south wall (riveted, on a stone plinth, ladder, battle-damage patch, ID plate "AQUIFER 3 /
  RATION TANK"), fed by a teal main on saddles along the wall foot from the west; gate valve with a red hand wheel.
- The main runs under riveted trench covers (flush, walkable) to a four-tap manifold (brass spouts, red tap handles, a
  flow meter) over a stone trough with a drain grate.
- The Warden's tally desk (open ration ledger, lockbox, stamp, tin mug, stool) and the ration board "WATER RATION / TWO
  CANS A HOUSE / TALLY AT THE DESK / BY ORDER OF THE WARDENS".
- From the street dressing kit: a queue of jerrycans, churn and bucket left in line, a handcart with two household
  drums, a filled can by the trough, bucket and tub at the taps, a bench for waiting elders, spare drums by the tank.
- Decals: damp paving at the taps and the valve (`WL_DecalDamp`), grime at the desk and under the cart.
- Kept clear: hall loop (plaza_west → hall_front_step → hall_terrace → plaza_back → hall_back_off), the Vanguard east
  side walk (x −3.1), walker 03's loop, the sail footings, lamps, refuse point. The old `walk_route.py` leg to the
  retired Jack (0, 0.5, −36.5) is obsolete; the court stays crossable from the avenue.

## 3. Node 07 goods dock (north plaza, east of the Meshy ring)

The plaza round the ring (now the only Lattice Jack, a destination) was broad empty paving. The Quantum Tube carries
goods only, so what arrives through Node 07 is staged, weighed and tallied here before porters carry it into the city.
Scene root **Ward life: Node 07 goods dock**: painted bay outlines and BAY 1/2/3, WEIGH, KEEP CLEAR (in front of the node
door), GOODS (west node) as worn-paint decals (`WL_DecalMarks` atlas from `bake_marks.py`); goods canisters (authored:
bone composite body, black end rings, handles, cyan status strip, manifest tag) chocked and strapped on pallets and
standing on a pallet; a platform scale with a dial at the lane mouth; an outbound pallet of cartons, tote, grain sack;
crates; the tally clerk's standing desk; the dock board "NODE 07 GOODS DOCK / BAYS 1-2 INBOUND / BAY 3 OUTBOUND / WEIGH
AND TALLY ALL GOODS"; porters' handcart, hand truck, stool and a crate with a tea pot; trolley tracks out of both node
doors; a tarp-covered outbound stack and hand truck by the west node. Kept clear: the Lattice approach (x 0, z 21→33)
and the ring/approach box (|x| < 4.4, z 30.5–39), walker 02's loop, both node door lanes, cam_ring_front's view of the
ring.

## Files

- `stones.py` (stone geometry), `bake_gabion.py` (fill/mesh textures), `bake_marks.py` (decal textures),
  `author_life.py` (models; keys `bastion`, `waterpoint`, `dock`), `layout.py` → `layout.json` (placements, decals,
  cameras; validated against the scene survey: 0 problems), `review_render.py`, `sheet.py`.
- Unity: `Art/WardLife/{Textures,Models,Materials}`, `Prefabs/WardLife/WL_*.prefab`, `Editor/WardLifePass.cs`.
- Sources: Poly Haven `worn_rock_natural_01` (CC0, already in `art/vanguard_hall_20260930/polyhaven`), Stardos Stencil
  font (already in `art/west_gate_20260926/fonts`), street dressing kit and West Gate props (existing, CC0 / Meshy).

## Run order

```
O=/home/teknetik/.local/state/ward-programme
$O/blender.sh bake_gabion.py ; $O/blender.sh bake_marks.py
$O/blender.sh author_life.py -- bastion waterpoint dock
python3 layout.py
$O/unity.sh <log> AthenHill.Editor.WardLifePass.RunBatch -nographics -quit --steps build,install,verify,budget
DISPLAY=:0 WAYLAND_DISPLAY=wayland-1 $O/unity.sh <log> AthenHill.Editor.WardLifePass.RunBatch -quit --steps capture:cam_wl_gate --out <dir>
```
`reinstall` replaces the three roots during authoring; `rollback` deactivates them and re-activates the round-two
bastions (or restore `rollback/before-ward-life.unity`).

## Cost (WardLifePass budget, planning estimate at the LOD each group selects; PC LOD bias 2)

Pass triangles in view: cam_hill 8.8k, cam_avenue 7.4k, cam_gate 15.9k, cam_grid 12.8k, cam_whompah 37k,
cam_ring_front 10.4k, cam_ss_lattice_approach 44.9k, cam_wb2_gate_spawn 58k (round two had ≈96k LOD0 incl. props).
Review views 15–130k (cam_wl_dock_bays 130k incl. the kit props' LOD0). Shadow-casting renderers: bastion fill, bags,
metal; the wire layers, sand and glow never cast. Draws: bastions ~9 materials each; water point ~20 material slots
(single LOD0 mesh set); dock props 2–6 each. Lights: 0 new (2 clocked bastion lamps replace 2).

## Open issues

- Gabion fill still reads darker/redder than the sandstone walls in shade in editor captures (`_BaseColor` of
  `WL_GabionFill*` is 1.32/1.27/1.2); judge in the native lookbook at 13:00 and 20:30.
- The blown basket and the north plate patch read subtly from the wide cameras; the round-two sand mounds at the
  bastion feet are flat "pancakes" (kept from round two).
- The stone trough reads close to timber (box-projected `VH_Ashlar` on long thin blocks).
- The damp decal's dark centre barely shows in editor captures (the pale tide line does); check natively.
- Alpha-tested wire may shimmer at 10–20 m under TAA: check moving at the gate (LOD1 swap is at ~22 m).
- `qa_motion_wall` stays 0.35 m from the south return collider (unchanged from round two).
