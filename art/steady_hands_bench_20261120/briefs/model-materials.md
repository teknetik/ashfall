# Brief: `model-materials` — the worked materials family

Written 20 November 2026, 18:10. You take over one family from `model-servo`, which built the Damaged Servo, wrote
this family's parts breakdown and ran out of context. You build the `materials` family: the Scrap Alloy sheets and
what is cut from them, the leads and the damper loop in their states, the trim resistor, the nanite vial and what the
press turns it into.

## Read first, in this order

1. `../AGENT-RULES.md` (binding: machine limits, wrappers, spending, reporting).
2. `../materials/PARTS.md` (the breakdown you build to: ids, states, marks, paths, wipes; written from the sheet and
   the interface). Treat its ids as fixed: the interaction agent is writing stages 3 to 5 against them now.
3. `../SEAM.md` (names, seat marks, sections 7 and 8: one gimbal, shared colours).
4. `../DESIGN.md` section 3 (the grip's sub-parts) and section 7, stages 3, 4 and 5 (what the player does to each part),
   `../CONTRACT.md` section A, `../ANYMACHINE.md`.
5. `../kit/READY.md` and `../kit/example/` (the shared build kit: geo, mats, contract, rig, bake, check, review).
6. `../servo/README.md`, `../servo/build.py` and `../servo/sv.py` as the pattern: how a family is laid out, how the
   chipped Warden paint, dust and wear were built, the kit defects it met (its README lists them; do not patch the
   kit, `model-pistol` owns it; work round a defect in your own folder and say so).
7. `../grip/INTERFACE.md` and `../grip/interface.json` (plate outline and holes, strap, loop path, the core's pocket).
   `../grip/export/` when it exists.
8. Pictures: `../materials/sheets/materials_stock.png` (the stock that is not part of a weapon) and the accepted look
   target `../concept/bench_overview_fal.jpg` (the two alloy plates with flaking orange paint, the stoppered vial).

## What you own

`art/steady_hands_bench_20261120/materials/**` and `unity/AthenHill/Assets/AthenHill/Art/Bench/Materials/**`.
Nothing else. You do not run Unity.

## What to build

Everything in `materials/PARTS.md`, exported as one GLB to CONTRACT section A with its `parts.json`:

- **Scrap Alloy sheets** A and B with every state the bench needs: whole, scribed line, plate cut out with its margin,
  filed, punched and drilled (plugs that hide), strap strip flat and bent, offcuts, swarf. Plate outline, holes and
  strap exactly as `grip/interface.json`; the finished plates must be the same shapes `model-pistol`'s grip uses (if
  the grip family has exported its plates by the time you get there, compare outlines by numbers and report any
  difference over 0.2 mm; the interface wins).
- **Leads and the damper loop** in the gimbal cradle's own frame (parent `servo.gimbal_cradle` at identity, see
  PARTS.md "Frames"): as cut, trimmed, stripped, tinned, sleeved, soldered to the resistor, tucked. Import
  `../servo/export/servo.glb` to work in the cradle's frame and to check nothing passes through the unit.
- **Nanite vial** (stoppered, settled grey-silver residue with a faint cool glint, not a light), the charge as poured,
  and the raw core's flash and sprue in the grip core's frame when `model-pistol`'s core exists. Until then build the
  rest and leave those three as listed-but-absent in `parts.json` with a note.

Paint and metal: the shared values in `SEAM.md` section 8. The alloy sheets are the look target's plates: large
ragged flakes of Warden orange on brushed alloy, a stencil fragment, old bolt holes. Render review sheets under a warm
key as well as neutral.

Budget: 15k triangles for the family (say where they went), one 2048 texture set plus the as-found set on the same
UVs if a part has a wipe.

## Pictures and spending

- No reference sheet exists for the side plates or the fused core. An earlier prompt that named them as parts of a
  pistol grip was refused by the image service. Do not try again in other words, with any service: build them from
  the interface. If you want more reference, ask only for what is not a weapon part (a flaking painted alloy offcut, a
  stoppered vial, soldered leads with heat-shrink), and stop and report if a service refuses.
- fal: `imagegen/fal_image.py ... --tag model-materials` (cap $3). Grok and OpenAI routes as in AGENT-RULES.
- Meshy: 30 credits at most, single-piece soft things only; nothing here should need it.

## Machine

One Blender slot is shared by four agents: geometry builds with `--nobake` take seconds, a 2048 bake about eight
minutes. Keep slot uses short, bake once when the geometry is settled, and use `SH/run.sh` + `SH/wait.sh` for the
bake. About 13 GB of RAM is available this evening and a player build is queued: do not start anything outside the
wrappers.

## Milestones and report

1. Geometry of every part and state, `check.py` passing at `--nobake`, review renders you have opened yourself beside
   the sheet and the look target. One PROGRESS line.
2. Bake, export, `check.json` passing on the baked export, copy `materials.glb` and `materials.parts.json` (and the
   as-found PNGs) to `Art/Bench/Materials/`. Hand back.

Report as AGENT-RULES says: outcome first; what is on disk; check results; what you looked at and what you did not;
what in PARTS.md, the interface or the kit turned out wrong; open defects; spend.
