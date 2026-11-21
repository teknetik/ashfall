# Brief: `model-bench` — the tools and the bench fixtures

You model everything the player works with and on: the Field Toolkit, Brann's bench tools, and the fixtures on the
worktop.

Read first: `../AGENT-RULES.md`, `../ANYMACHINE.md` (all), `../CONTRACT.md` section A (binding), `../DESIGN.md`
sections 4 to 8 (the verbs tell you what each tool must visibly do), `../FACTS.md` (Brann's bench and shop). Then
AnyMachine as reading only: `/home/teknetik/code/vendor/anymachine/PIPELINE.md` part 2, `hardsurface/NOTES.md`,
`hardsurface/rig2_blender/kit/README.md`, `laptop/NOTES.md` (the 0-1 parameter rig).

The kit is `art/steady_hands_bench_20261120/kit/`, published by `model-pistol` (look for `kit/READY.md`). Do your
sheets and `PARTS.md` first; if the kit is not ready when you need it, copy `pm_geo.py` and `pm_mats.py` from
`art/pistol_mods_20260930/src` into your folder, go on, and switch when it lands. Do not edit the kit.

## 1. Tools (`tools/`)

Ward's tools are old, repaired and looked after: re-handled, taped, engraved with owners' marks, steel worn bright
where hands and work go. Each tool has a `__tip`, a `__grab` and the rigs below. Sizes are real.

- **Field Toolkit** (item `field_toolkit`, the player's): waxed canvas roll with a strap and pockets (rig `unroll`,
  with the tools in their pockets), screwdriver with a collar and two bits, slotted and cross (rig `bit`), pliers
  (`jaws`), wire cutters (`jaws`), wire strippers (`jaws`), wire brush, pick, pin punch, scribe.
- **Brann's bench tools**: mallet, flat file and round file with wooden handles, tin snips (`jaws`), hand drill with a
  crank and a chuck (`crank` continuous, `chuck`) and a bit, soldering iron on a coiled lead with its stand and a
  reel of solder, a third-hand clip (two crocodile clips on a weighted base), oil dropper (`bulb`), nanite applicator
  pen, a rag.

## 2. Fixtures (`fixtures/`)

Laid out for a worktop 2.2 x 1.15 m at 0.864 m, clear in front of the bench's screen (`DESIGN.md` section 4); propose
the layout in `PARTS.md` with a plan drawing, inside reach of a standing player and readable from a camera 40 degrees
down. The existing Meshy bench is too soft for a 0.3 m view, so the surfaces the work sits on are yours.

- **Work surface**: a steel-edged rubber mat about 0.9 x 0.55 m, cut, burnt and stained by years of work, with a
  bench rule let into its front edge (millimetre marks that are real geometry or sharp in the texture) and a mark for
  lead length.
- **Parts mat**: with a worn outline for every part that comes off the pistol and the servo (get the outlines from
  the other two agents' `PARTS.md` and exports; use placeholders until they exist and say so).
- **Bench vise** with soft jaw pads, bolted through the mat: rig `jaw`, a handle that turns with it, real screw
  thread visible. It holds the pistol frame, the servo, the stacked alloy sheets and the strap, and works as a press.
- **Cradle stand** for the stripped frame, **magnetic dish** for fasteners, **salvage tray**, **insulated pad** for
  the charge cell, **solvent jar** with a lid (`lid`) and cloudy fluid, **scrap bin**.
- **Bench tester**: a salvaged meter box with two probes on leads (`probe_l`, `probe_r`), a lamp and a buzzer grille.
- **Nanite press**: a hand-lever press with a keyed bed, a hopper with a level line, vents that glow, a lock, a
  pressure indicator the player reads without any interface (a needle or a rising slug in a sight tube, its green
  band painted on), and a rack of three keyed moulds of which one is the pistol-tang mould (take the cavity from
  `grip/INTERFACE.md`). Rigs `lever`, `platen`, `lock`, `vent`. It should look as if it belongs with the bench's
  yellow print head.
- **Cure lamp** on a two-joint arm (`arm_swing`, `arm_reach`), **card board** with two clips on the rear frame, and
  the **schematic**: a hand-drawn exploded view of the grip on a clipped sheet with a small clip lamp, in seven
  regions matching stages 1 to 7 (draw it with the image model from the other agents' exploded renders once they
  exist; a placeholder until then), plus a chalk-tick overlay per region.

## Method and gate

Reference sheets first (`gen_concept.py`, OpenAI `gpt-image-2`; `FACTS.md` Tooling): one overall sheet per group (roll
and hand tools, bench tools, vise, press, tester and small fixtures, mats) and close-up sheets for the vise, the press
and the drill. Then `PARTS.md`, one `build.py` per family, compare renders beside the sheets, a planned second pass,
the checks in `ANYMACHINE.md` section 3 (parameter sweeps for every rig; the vise closing on each thing it holds),
bake, export, copy to `U/Art/Bench/Tools/` and `U/Art/Bench/Fixtures/`.

Budgets: tools 60k triangles in total (2k to 6k each), fixtures 70k in total; two 2048 sets per family at most.
Meshy allowance: 240 credits, for single-piece or soft things only (the canvas roll's cloth, the rag, the jar, the
bin, the mallet) and only if the result holds at 0.3 m. No Unity runs.

## Report

Milestone 1: sheets, both `PARTS.md` and the layout plan (append to `PROGRESS.md`, keep going). Milestone 2: the
slice set first, because the first playable build needs it: work surface, parts mat, vise, dish, cradle, insulated
pad, card board, toolkit roll, screwdriver, pliers, cutters, punch, mallet, oil dropper. Milestone 3: the rest.
Final report: triangles and textures, `check.json` results, the path of every review sheet, and what still differs
from the sheets. Look at your renders before you report; say what you saw.
