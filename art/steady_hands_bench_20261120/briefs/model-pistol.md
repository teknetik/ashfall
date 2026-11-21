# Brief: `model-pistol` — the shared kit, the separable scrap pistol and the Stabilised Pistol Grip

You model the two hero families, and you publish the Blender kit the other two modelling agents build on.

Read first: `../AGENT-RULES.md`, `../ANYMACHINE.md` (all), `../CONTRACT.md` section A (binding), `../DESIGN.md`
sections 1 to 4, 7 (stages 0, 1, 5, 6, 7) and 10, `../FACTS.md` (The scrap pistol today). Then AnyMachine itself, as
reading only: `/home/teknetik/code/vendor/anymachine/PIPELINE.md` part 2, `hardsurface/NOTES.md`,
`hardsurface/guns/NOTES.md` and its `svd_parts.py` / `detail_parts.py`,
`hardsurface/dugout_blender/props_hand/_common/hs.py`, `laptop/NOTES.md` and `laptop/scripts/{build,check,export,verify_glb}.py`
(the 0-1 parameter rig, the sweep check, the baked `*_param` action).

## 1. The kit (first, within your first hour)

`art/steady_hands_bench_20261120/kit/`, published with a `READY.md` that lists every function and a 20-line example:

- geometry and materials: start from `art/pistol_mods_20260930/src/pm_geo.py` and `pm_mats.py` (copy, do not import
  from there), generalise them, and add what small mechanical parts need (`am_parts.py`: screws with slotted and cross
  heads and real threads where seen, knurled bands, hinge knuckles on a pin, springs, wire and sleeved leads along a
  path, clips, washers, circlips), taking what is worth taking from AnyMachine after reading it, with the MIT notice;
- `bake.py`: the Cycles CPU bake and GLB export from `pistol_mods_20260930/src/build_all.py`, generalised (family
  atlas, `--size`, `--spp`, `--nobake`, glTF ORM, dirty second set for `wipes`);
- `rig.py`: 0-1 parameter rigs in the AnyMachine form (bone on the axis, custom property, driver, limit, baked linear
  one-second `<param>_param` action, extras);
- `contract.py`: writes `parts.json` and `stats.json` from the scene (custom properties on objects are the source),
  creates and checks the `__clear`, `__grab`, `__tip`, `__path_*`, `__mark_*`, `__zone_*` empties;
- `check.py`: the parameter sweep, the **assembly path sweep** (every seated part from clear to seated against what is
  seated at that step, forwards and backwards), the fastener check and the export re-import check, writing
  `check.json` and exiting non-zero on failure;
- `review.py`: renders from a sheet's six directions, from the bench camera (40 degrees down, 0.6 m, 35 mm), a 0.3 m
  close view and an exploded view, and tiles them beside the sheet.

The other agents may not edit the kit. Keep it small and working; announce changes in `PROGRESS.md`.

## 2. The scrap pistol, rebuilt to come apart (`pistol/`)

The in-game pistol is one fused Meshy mesh. Rebuild it as real parts **to the same outline**: import
`U/Art/OuterBerms/ScrapPistol.glb` at scale 0.13674 as the measuring skin and hold these fixed: overall length, height
and width, the bore axis and mouth, the dust-cover rail where the cell mods sit, the trigger and guard, the grip
centre, rake and girth, and the mount origin and axes, so that the five other mods in
`art/pistol_mods_20260930/export` still fit (run a clearance check against them, as `build_all.py` does against the
hands) and the existing `Shooting grip` and `Support grip` points still land on the grip. Assert the fixed numbers in
the build. Export in the same units, axes and origin as `ScrapPistol.glb` so it can replace it in the hand.

It keeps the same character: chunky bolted steel receiver, short ribbed barrel, small glass nanite charge cell with a
faint cyan glow, grip wrapped in worn leather strips and tape. It is a scrap gun that rattles: show why (a cracked
frame tang, a loose backstrap housing, mismatched fasteners).

Parts, at least (write `PARTS.md` first, with what each is made of, what holds it and which way it comes off):
frame/receiver, barrel assembly, dust cover with rail, trigger and its lead with a keyed plug, cell bus, charge cell
(glass and caps), cell latch, left and right grip scales (cracked), leather strips and tape wrap (a peelable part with
a path), two binding-wire twists, upper and lower grip screws (slotted, one rusted), backstrap housing with its
spring, housing pin, status lamp. Rigs: `cell_latch`, `trigger`, `cell_seat`. Also two paper **test cards** (blank,
plus hole decals the game places).

## 3. The Stabilised Pistol Grip (`grip/`)

Per `DESIGN.md` section 3: grip core (fused alloy spine with bearing pocket, side channel with two clips, rear channel
for the trigger lead, dovetail for the frame tang), gimbal cradle, left and right side plates with four screw holes
and locating pegs, reinforcement strap (old Warden orange outward), nanite seam (a surface state), two new grip
screws. The gimbal, rotor, coil, loop and plate screws are modelled by `model-servo`; you define the **interface**
they must fit (pocket bore and depth, gimbal outside diameter, screw size and positions, loop channel) and write it to
`grip/INTERFACE.md` in your first two hours, because `model-servo` is waiting on it. Use nominal values now and hold
them. The assembled grip must seat on your pistol's tang by its dovetail, and read on the pistol as the upgrade of
the present mod (`grip_stabilised_pistol`: orange strap, brass fasteners) without copying its rubber wrap.

Also export the assembled grip as a single low-part-count node named `grip_stabilised_pistol` in the pistol's own
units and origin, for the in-hand view (the existing `WeaponModVisuals` shows the child named after the item id).

## Method and gate

Reference sheets first (`gen_concept.py`, OpenAI `gpt-image-2`; see `FACTS.md` Tooling): an overall sheet, an exploded
sheet and close-up sheets per family, with renders of the existing pistol as input images so the design matches. If
the image service refuses a pistol prompt, do not reword to get round it: model from grey renders of the existing
mesh, written briefs and how the mechanism works, as AnyMachine's rifles were, and say so. Then `PARTS.md`, then
`build.py`, compare renders, a planned second pass, checks, bake, export, copy to
`U/Art/Bench/Pistol/` and `U/Art/Bench/Grip/`.

Budgets: pistol family 45k triangles, grip 25k. Textures: 2048 per family, 4096 if 2048 does not hold at 0.3 m.
Meshy allowance: 60 credits (the leather wrap or tape as a skin to measure, if it helps). No Unity runs.

## Report

Milestone 1: kit published and `grip/INTERFACE.md` written (append to `PROGRESS.md`, keep going). Milestone 2: pistol
family passing `check.py` with compare renders. Milestone 3: grip family, and the two fitted together. In the final
report: triangles and texture sizes per family, `check.json` results, the fixed numbers and their measured error
against the Meshy pistol, the path of every review sheet, and one line per family on what still differs from its
sheets. Look at your renders before you report; say what you saw.
