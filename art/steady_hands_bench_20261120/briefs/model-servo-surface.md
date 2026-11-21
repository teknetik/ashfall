# Brief: `model-servo-surface` — the Damaged Servo's last surface pass

Written 20 November 2026, 21:05. The Damaged Servo family (33 parts, 41.5k triangles, two rigs, six params) is built,
checked and published; its geometry and its opened states are accepted. Its outside paint is not finished: the first
repaint was judged through a review rig that was 1.6 EV too bright, and the agents who could have finished it ran out
of context. You do one surface pass on the can's outside and one bake. Nothing structural changes.

## Read first, in this order

1. `../AGENT-RULES.md` (binding: machine limits, wrappers, reporting).
2. `../SEAM.md` section 8 (shared colours, the rule for review renders, the history of the mistake) and section 7.
3. `../servo/README.md`, above all the section "Surface fix round", then `../servo/sv.py` (`add_wear`,
   `add_scratches`, the dust and tarnish layers) and `../servo/build.py`.
4. `../materials/mtl.py` (`alloy_paint()`, `flakes()`, `scratches()`): the accepted Warden paint on the alloy plates.
   Its `flakes()` was written for flat stock (the `rect_m` edge bias assumes a rectangle); the idea carries over, the
   edge bias does not. Coverage is its `lo` threshold (about 0.52 on the plates; higher leaves less bare metal).
5. `../kit/READY.md` (the review rig was fixed and calibrated at 19:46 to 20:00; exposure cards in frame).
6. Pictures, opened yourself: the look target `../concept/bench_overview_fal.jpg`; the servo's sheet
   `../servo/sheets/servo_turn.png`; the accepted plates `../materials/review/glb_hero.png` and `glb_sheets.png`; and
   the servo as it is, re-rendered by you on the fixed rig before you change anything (`../servo/review/states.png`
   and `glb_views.png` on disk are from the old over-bright rig and mislead).

## What you own

`art/steady_hands_bench_20261120/servo/**` and `unity/AthenHill/Assets/AthenHill/Art/Bench/Servo/**`, for surfaces
and the bake only. Not the kit (`kit/**`). You do not run Unity.

## What must not change

Every node name, id, parent, param, rig, clip, helper empty and dimension; the gimbal unit's interface with the grip;
`parts.json` ids and structure. `servo/check.py` must pass on the baked export exactly as it does now (it carries
its own fix for a kit clamp-test defect: leave that). Keep the `.meta` files in `Art/Bench/Servo/` when you publish.

Keep, because they work: the cast end bells with rust in the recesses, the soot gradient at the rear corner, dust on
upward faces and in recesses in the as-found set, the dull outside leads, the formed clips, and everything inside the
case.

## What to do

1. **Re-render first** on the fixed rig, warm and neutral, closed and opened, at 0.3 m and at the bench camera, and
   judge again beside the plates and the look target. Say in your first PROGRESS line what you see.
2. **No bare island in open paint.** The repaint left a large bright bare patch on the lid's shoulder, in the middle
   of a panel. Wear belongs where the thing was handled: rib crests, the lid's flange edge, clip seats, screw bosses
   and lid lugs, the foot corners and its bolt slot, and one long dragged field on the side it lay on. Use the flake
   character of the plates (ragged coast, a thin primer rim) at far lower coverage: the can was painted properly, the
   plates are offcuts.
3. **Shared constants, not typed numbers**: paint from `mats.WARDEN_ORANGE`, bare metal from `mats.BARE_ALLOY` (it
   was darkened at 19:20; the servo may still carry the old bright value through `sv.lin()`).
4. **The clean fields are flat.** Handling stains, a grime gradient towards the foot and into the recesses, slight
   tone variation across the can, scratches along the axis that can be seen at 0.3 m.
5. **Sits with its neighbours.** Beside the alloy plates under the warm key the can must read as the same paint from
   the same works, older and dirtier, not a different orange.
6. One 2048 bake when the look is settled at a small bake, `check.py`, publish, and re-render `states.png` and
   `glb_views.png` (warm and neutral panels, exposure cards in frame). Open them and say honestly how it compares.

## Machine and spending

One Blender slot is shared by several agents and about 13 GB of RAM is available: wrappers only, short jobs, one final
bake (about six minutes). No image generation or Meshy should be needed; if you want a reference, the fal route is
capped at $3 with `--tag model-servo-surface`.

## Report

One PROGRESS line after step 1 and one at the end. Final message as AGENT-RULES says: outcome first, what changed and
what did not, check result, what you saw with your own eyes and where it still differs, open defects.
