# Fixtures family: parts breakdown and bench layout

`model-bench`, Steady Hands bench programme, 20 November 2026. Written before any geometry, from the reference sheets
in `sheets/`, the look target `../concept/bench_overview_fal.jpg` and a probe of the existing bench
(`src/probe_bench.py`, results in `layout/`). The tools family is in `../tools/PARTS.md`; both share this bench frame.

## Bench frame and export

- Blender, metres, Z up. **Origin on the worktop surface under the `SS_Workbench` pivot.** +X is the player's right,
  -Y is toward the player, +Y toward the back. Unity bench-local `(x, y, z) = (-X, Z + 0.8637, -Y)`.
- `fixtures.glb` and `tools.glb` are exported in this frame with every object at its place on the bench
  (`layout/layout.json` is the single source of positions). Put each GLB root at bench-local `(0, 0.8637, 0)`,
  identity rotation, and the set is laid out.
- One root node per fixture, named `fixtures_<name>`. A fixture with a mechanism has a small rig of its own,
  `fixtures_<name>_rig`, parented to the root node; its sub-parts are meshes named `fixtures_<name>_<sub>`, the moving
  ones bone-parented. Parameters and bones are named `<name>_<param>`, clips `<name>_<param>_param` (1 s, linear in the
  parameter). **Parameter 0 is the as-found pose** (the kit's rule).
- Empties as in `CONTRACT.md` A. Where another family's part rests on a fixture (the pistol on the work mat, the cell
  on the pad, a card under a clip, a part on its outline) there is a **seat mark**, `<node>__mark_seat_<id>`: a mark
  that carries a whole pose (the resting part's origin and axes), which the contract's point marks do not say.

## What the probe of the bench found (measured, 20 Nov)

| Thing | Bench frame (m) | Consequence |
|---|---|---|
| Worktop | flat within 2 mm, x -1.085..1.05, y -0.583..0.567, top at Unity y 0.8637 | as `FACTS.md` |
| Screen | a monitor **in the middle of the top**: plate x -0.45..0.43, y 0.103..0.135, 0.06 to 0.324 above the top, on a foot x -0.18..0.18, y 0.07..0.29 | 0.686 m of clear depth in front of it; the centre rear behind it is hidden from the bench camera |
| Rear frame | nothing between the worktop and 0.97 m above it except the two end uprights; the hook bar is at 0.97 to 1.0 m, the top bar at 1.26 m | **the card board and the schematic cannot hang on the rear frame and still be in the bench camera** (eye is 0.79 m above the top); they stand on their own board at the left rear |
| Pendant control | x 0.675..0.935, y 0.335..0.545, from 0.11 m up, on two cables | the press is kept in front of and left of it; the lever never swings back past vertical |
| Hanging loop and spanner | x -0.94..-0.64, y 0.395..0.495, from 0.111 m up | the board's top edge stops at y 0.35 |
| Print head and gantry | x -0.845..0.83, y -0.165..0.415, from 0.577 m up | out of frame at 40 degrees down; the press (0.42 m) and the cure lamp stay under it |

## Layout (plan: `layout/layout_plan.png`, data: `layout/layout.json`)

Front to back in the centre: bench rule in the front edge, parts mat, work mat, then the bench's own screen. Vise at
the left end of the work surface with its handle toward the player. Dish, cradle and insulated pad down the right
side of the work surface. The Field Toolkit unrolls on the bare top to the left; Brann's tools lie in a row on the
right with the salvage tray behind them. Tall things at the back where they hide nothing: board and schematic left
rear, press and mould rack right rear, tester and solvent jar between. Everything the player handles is within
0.62 m of the front edge except the press bed (0.80 m) and the board (looked at, not touched).

| Node | Centre x, y (m) | Footprint (m) | Height (m) | Stands on |
|---|---|---|---|---|
| `fixtures_worksurface` | 0.000, -0.303 | 0.90 x 0.55 | 0.008 | worktop |
| `fixtures_workmat` | 0.030, -0.195 | 0.36 x 0.26 | 0.006 | work surface |
| `fixtures_partsmat` | 0.030, -0.440 | 0.44 x 0.20 | 0.003 | work surface |
| `fixtures_vise` (jaw line) | -0.325, -0.330 | 0.15 x 0.32 open | 0.135 | work surface, bolted through |
| `fixtures_dish` | 0.360, -0.455 | dia 0.108 | 0.028 | work surface |
| `fixtures_cradle` | 0.335, -0.300 | 0.18 x 0.09 | 0.11 | work surface |
| `fixtures_pad` | 0.360, -0.125 | 0.13 x 0.104 | 0.024 | work surface |
| `fixtures_board` | -0.760, 0.290 | 0.60 x 0.13 | 0.36 | worktop, left rear |
| `fixtures_tester` | -0.580, 0.035 | 0.16 x 0.075 | 0.11 | worktop |
| `fixtures_jar` | -0.760, 0.030 | dia 0.09 | 0.125 | worktop |
| `fixtures_bin` | -0.950, 0.070 | dia 0.20 | 0.14 | worktop |
| `fixtures_lamp` (base) | 0.300, 0.030 | dia 0.11 | arm 2 x 0.24 | worktop |
| `fixtures_tray` | 0.640, -0.060 | 0.30 x 0.20 | 0.03 | worktop |
| `fixtures_press` | 0.560, 0.220 | 0.26 x 0.22 | 0.42 | worktop, right rear |
| `fixtures_mouldrack` | 0.800, 0.190 | 0.11 x 0.13 | 0.15 | worktop |

## Look

From the look target: black rubber mat with a steel edge and a rule along the front, **dark green** cast-iron vise
(the vise sheet's blue-grey is not used; geometry follows the sheet), worn industrial yellow press that belongs with
the bench's yellow print head, small pressed-steel dish, warm single lamp. Old, repaired, looked after: paint chipped
to iron on edges and where hands go, screw and slide bright and oily, hammer marks on the anvil, one jaw pad newer
than the other, cuts, burns and stains on the rubber where work happens (centre and front), not uniform grunge.
No cyan except the press vents and the cure lamp emitter.

## Slice set (Milestone 2)

### `fixtures_worksurface` (fixture, rubber)
Slab of black belting rubber 900 x 550 x 8 mm, corners clipped 12 mm. Steel edging strip 26 x 2 mm on the two ends and
the back, mitred, held by dome rivets every 90 mm (real geometry, 6 mm heads). **The front strip is the bench rule**:
steel 900 x 26 x 2 mm let flush, two slotted screws, engraved millimetre marks (1 mm short, 5 mm middle, 10 mm long)
and centimetre numerals 0 to 90 reading from the player's side, zero at the left end; sharp in the texture (the rule
gets its own strips in the atlas at 4.5 px/mm). A file-cut notch filled with orange paint at **120 mm** is the lead
length mark: `fixtures_worksurface__mark_lead_zero`, `__mark_lead_length`, and `__zone_rule`.
Wear: knife cuts clustered centre front, soldering burns right of centre, a pale solvent ring where the jar used to
stand, ground-in oil under the vise, dust along the back edging.

### `fixtures_workmat` (fixture, canvas class for sound)
Dense grey wool felt 360 x 260 x 6 mm, 18 mm corner radius, bound in stitched brown leather 9 mm wide; flattened and
darkened in the middle. `__mark_seat_pistol` (full pose: the pistol on its right side, muzzle to the player's left, grip toward the player,
as in the look target), `__mark_seat_grip` (full pose, same lie, for the grip sub-assembly in stage 5; the grip family
is in the pistol's frame), `__mark_seat_small` (a point), `__zone_work`.

### `fixtures_partsmat` (fixture, rubber)
Thin dark rubber 440 x 200 x 3 mm with worn pale-yellow outlines, one per part that comes off the pistol and the
servo, grouped as they come off (pistol left, servo right, fasteners in a row at the front). Outlines are in the
texture; each has a seat mark `__mark_seat_<family>_<part>` at the outline's centre with the part's lying-down pose.
**Placeholder outlines until `pistol/PARTS.md`, `servo/PARTS.md` and their exports exist** (see Open).

### `fixtures_vise` (fixture, steel; rig)
Machinist's vise, 240 long closed, 150 wide at the base plate, 135 tall, jaws 80 wide **opening 90 mm** (the sheet's
70 mm would not take the servo, which is 70 mm across). Local frame: origin on the mat under the jaw line, screw axis
along Y, handle toward -Y.

| Sub-part (node) | Made of | Rides on | Notes |
|---|---|---|---|
| `fixtures_vise` (the body, root) | cast iron, dark green paint | root | fixed jaw block with a real square guide hole and a nut bored through (the screw's end shows at the back), anvil pad behind the jaw, a gusset each side, swivel flange dia 118, base plate 150 x 130 x 6 |
| `fixtures_vise_bolts` | steel | root | four hex bolts M8 with washers through the base plate and the mat; swivel lock bolt |
| `fixtures_vise_slide` | cast iron, green; steel bar | bone `slide` | sliding jaw casting with the curved neck, boss for the screw, square guide bar 26 x 22 x 165 bright and oily |
| `fixtures_vise_screw` | steel | bone `screw` (child of `slide`) | lead screw dia 16 x 135 of thread, **square thread pitch 5 mm as real helical geometry**, collar, hub with cross hole, tommy bar dia 8.5 x 124 with 16 mm balls |
| `fixtures_vise_plate_f`, `_plate_m` | steel | root, `slide` | jaw plates 80 x 22 x 8, two countersunk slotted screws each |
| `fixtures_vise_pad_f`, `_pad_m` | copper sheet, leather face | root, `slide` | soft pads folded over the plates, 84 wide; the moving one newer |

Rig `fixtures_vise_rig`: `vise_jaw` is a slider on Y, **0 = open 90 mm (as found), 1 = pads touching** (clip
`vise_jaw_param`). The screw and handle are the continuous joint `vise_handle` on the slide, driven by code
(`ANYMACHINE.md` 2): `parts.json` gives pitch 5 mm, right-hand, 18 turns over the full stroke, and `snug_at`: the
jaw value at which the pads meet each thing (pistol frame 0.602, servo 0.223, from `check.json`).
Seats (full poses, `SEAM.md` 2): `__mark_seat_work` is the **pistol frame upside down in the jaws**, grip up so the
housing slides off upward, its left side and the screw heads toward the player, muzzle to the player's right, held
by the flat sides of the receiver top behind the cell bay (not by the barrel: its sides are round and 4 mm proud).
The whole grip stands over the jaws, its scales 27 mm and the wrap 44 mm above the pad tops, open from in front and
from above (`review/hold_vise.png`, numbers from `src/vise_pose_probe.py`); `__mark_seat_servo` is the servo upright across its 70 mm width. `__mark_seat_flat` is a
point for flat stock (sheets, strap). Also `__mark_jaw_top`, `__mark_anvil`, and on the slide `__mark_handle` (the
tommy bar ball the hand takes).
What it must hold (checked by `check.py`): the pistol frame and the servo with their real geometry placed at the
seat marks; two stacked alloy sheets, the strap blank and the grip core with the gimbal cradle (press fit) as blocks
of placeholder size until those families export.

### `fixtures_dish` (fixture, steel)
Pressed-steel bowl dia 108 x 28 mm with a rolled rim on a black rubber-covered magnet base dia 86.
`__mark_seat_fasteners` (centre of the floor) and `__mark_slot_00..11` (twelve resting places on the floor for screws,
pins and the circlip).

### `fixtures_cradle` (fixture, wood)
Hardwood base 180 x 90 x 18 with chamfered edges, two forged steel forks screwed down with two wood screws each,
their saddles wide and shallow (50 mm flat, 8 mm lips) and padded with leather. The saddles are placed on the
stripped frame's real underside (`layout/pistol_profile.json`): 124 mm apart, the rear one 5.3 mm lower, so the
frame lies level, upright, muzzle to the player's left (`__mark_seat_frame`, a full pose). `__mark_saddle_l`,
`__mark_saddle_r`.

### `fixtures_pad` (fixture, ceramic)
White glazed tile 130 x 104 x 8 with a faded yellow and black hazard border, a ribbed red-brown rubber slab
104 x 78 x 14 on it (ribs real geometry). `__mark_seat_cell` (full pose): the cell lies along the ribs in the
groove between the two middle ones.

### `fixtures_board` (fixture, wood)
Stands at the left rear because nothing on the rear frame is low enough. Hardboard panel 600 x 340 x 5 in a thin
steel angle frame, tilted back 10 degrees on two flat steel feet and a rear strut. Two bulldog clips on the top edge
156 mm apart at the left hold the two test cards (`pistol.card_a`, `_b`: 148 x 105, landscape, hung by the `clip`
mark on a long edge). `__mark_seat_card_before` and `__mark_seat_card_after` are full poses: card X across the board,
Y up it, Z out of it. The right 260 mm is where the schematic sheet (250 x 300) hangs under its own clip
(`__mark_seat_schematic`; `fixtures_schematic` is Milestone 3). Sub-nodes `fixtures_board_clip_a`, `_clip_b`
(static).

## Milestone 3

**Rulings received on 20 Nov (orchestrator, `SEAM.md` section 10 and its messages of 20:35 and 21:00). They overrule
the rows below where they differ.**

- **The tang mould is sized from the grip core**, not 90 x 60 x 40: `grip.core` is 93 x 39 x 115 mm
  (`grip/export/grip.glb`). The cavity is the core's outline plus flash clearance. **The mould parts on the core's
  middle plane, P Y = 0 in the pistol's frame**, where `materials.core_flash`, `core_flash_2`, `core_flash_3` sit;
  there is no fin across the tang slot's mouth. **The sprue channel is on that plane, under the middle of the
  core's base** (`materials.core_sprue`). Take the outline, the parting line and the flash from the published
  `grip.glb` and `materials.glb`. The other two moulds and the press bed's key grow with it.
- **`fixtures.mould_charge`** is a sub-part of the tang mould, hidden at start and shown after `s4.charge`: the heap
  of alloy offcuts (the materials family's `sheet_a_offcut_*` shapes) and grey nanite paste in the cavity.
- **Ids the step table already uses, to be kept as they are**: fixtures `tray` (marks `seat_servo`, `seat_alloy`,
  `seat_vial`), `bin` (`seat_scrap`), `jar` (`seat_swirl`), `press` (`seat_mould`) with `press_lever` (a part and a
  param) and `press_vents`, `mouldrack`, `mould_tang` (zone `cavity`), `lamp` with `lamp_head` and param `lamp_arm`,
  `tester` with `tester_probes` (tag `tool:probe`) and `tester_lamp`, `schematic` with params `schematic_s0..s7`,
  `holster`. Tools: `strippers`, `wirebrush` (tag `tool:brush`), `pick`, `scribe`, `file_flat` (tag `tool:file`),
  `file_round`, `snips`, `drill`, `iron` (tag `tool:solder`), `applicator`, `thirdhand`. Where a row below names a
  param differently (the jar's `lid`, the lamp's `arm_swing`, the schematic's tick quads), the id above wins or the
  difference goes into `PROGRESS.md` at once.
- **Places with no mark** (`bench/README.md`): six on the work mat and parts mat (`place.mat.sheet`, `.plate_l`,
  `.plate_r`, `.strap`, `.spare`, `.retainer`), the entry places and `place.bench.stray` on the bench top,
  `place.holster`, `place.thirdhand`, `place.mould.charge`, `.core`, `place.press.pour`. They become pose marks on
  the owning fixture, each checked with the real part from `materials.glb` or `grip.glb` as the pistol and the servo
  are now.

| Node | What | Rig and empties |
|---|---|---|
| `fixtures_tray` | pressed-steel tray 300 x 200 x 30, rolled rim, worn grey-green enamel, dents | `__mark_seat_servo`, `__mark_seat_alloy`, `__mark_seat_vial` |
| `fixtures_jar` | glass jar dia 90 x 120 with a wire-bail clamp lid and rubber seal, cloudy grey solvent half up, dried drips | rig `jar`: `lid` hinge 0..105 deg on the bail; `__mark_seat_swirl` |
| `fixtures_bin` | bottom of a steel drum dia 200 x 140, hammered-over rim, dents, old paint | `__mark_seat_scrap` |
| `fixtures_tester` | salvaged steel meter box 160 x 110 x 70, sloped front, amber lamp (own emissive material), punched buzzer grille, toggle switch, two brass binding posts, two probes with wooden handles on coiled leads | rig `tester`: `probe_l`, `probe_r` (0 stowed in the side clips, 1 lifted clear); `fixtures_tester_probe_l/_r` with `__tip` |
| `fixtures_press` | hand-lever press, 260 x 220 x 420, cast C-frame in worn yellow with black hazard stripes on the base plate; toothed square ram and pinion, platen, keyed bed (two dowels, cross slot), hopper cup with a painted level line feeding a port at the side of the mould, vent slots that glow (own emissive material), swing-over lock, sight tube with a rising brass slug beside a painted green band | rig `press`: `lever` (hinge 0..70 deg), `platen` (slider 0..38 mm), `lock` (hinge 0..95 deg), `vent` (release valve, hinge 0..90 deg) and `pressure` (the slug, slider 0..46 mm; added, see Departures); `__mark_seat_mould`, `__mark_hopper_line`, `__mark_band_lo`, `__mark_band_hi` |
| `fixtures_mould_tang`, `_mould_b`, `_mould_c` on `fixtures_mouldrack` | three keyed mould blocks 90 x 60 x 40 with different keys (only the tang mould fits the bed); the tang mould's cavity from `grip/INTERFACE.md` | each `__clear` (lifted off its shelf), `__zone_cavity` on the tang mould |
| `fixtures_lamp` | cure lamp: round base, two arms 240 mm on friction knuckles with wing nuts, hooded head dia 90 with a ribbed collar, violet-cyan emitter (own emissive material), cable clipped along the arms | rig `lamp`: `arm_swing` (hinge about Z, -100..+20 deg), `arm_reach` (elbow and shoulder together, folded to reaching the work mat) |
| `fixtures_schematic` | paper sheet 360 x 260 under a bulldog clip on the board, hand-drawn exploded view of the grip in seven regions; a clip lamp on a gooseneck; seven chalk-tick overlay quads `fixtures_schematic_tick_1..7` | `__zone_region_1..7`; placeholder drawing until the other agents' exploded renders exist |

Where the press leaves its sheet: the sheet draws the funnel standing on the mould under the ram. The ram has to
close the mould, so the hopper is a cup on a bracket at the front left of the bed with a spout into a port in the
mould's side. The lever rests 10 degrees forward of vertical and never goes back, to stay clear of the pendant
control's cables.

## Triangles and textures (plan)

Budget 70k. Slice: work surface 2.6k, work mat 0.7k, parts mat 0.2k, vise 10k (thread 2.2k), dish 0.7k, cradle 2k,
pad 0.9k, board 3.2k: about 20k. Milestone 3: tray 0.8k, jar 2.2k, bin 1.6k, tester 5k, press 14k, moulds and rack
4k, lamp 4k, schematic 0.6k: about 32k. Total about 52k.

Two 2048 sets. **F1 "mats"**: work surface, bench rule (two strips at 4.5 px/mm), work mat and parts mat at
3.6 px/mm, laid out by hand. **F2 "hardware"**: everything else. Small materials outside the sets: glass (jar, sight
tube), emissive (tester lamp, press vents, cure lamp).

## Departures from the brief and the contract

1. **Card board and schematic are not on the rear frame.** The frame has no member below 0.97 m above the worktop,
   which is above the bench camera's eye. They are on a standing board at the left rear.
2. **Seat marks** (`__mark_seat_<id>`) carry a whole pose. They are ordinary marks to the contract; the pose is the
   addition.
3. **Parameter, bone and clip names carry the object**: `vise_jaw`, `vise_jaw_param`, id `fixtures.vise_jaw`. Several
   objects in one GLB have a parameter of the same name (`jaws` on four tools), so `<param>_param` alone is not
   unique.
4. **Each rigged fixture or tool has its own small rig**, parented to its root node, so it can become its own prefab;
   the contract's example and the kit have one rig for a whole family (`BenchFamily` in `tools/src/mbk.py` adds this
   on top of the kit, which is not edited).
5. **Press parameter `pressure`** is added for the sight-tube slug; the contract lists `lever`, `platen`, `lock`,
   `vent` and nothing that moves the indicator.
6. **A separate felt work mat** lies on the work surface (`DESIGN.md` section 4 lists both; my brief names only the
   work surface). It gives the dark pistol a lighter ground and lets the close-up surfaces have 3.6 px/mm.
7. Texel density: two 2048 sets cannot give 30 px/cm on 1.5 m2 of fixture surface. The mats and the rule get 36 to
   45 px/cm; the hardware set averages about 17 px/cm with the vise jaws, dish, pad and press bed weighted up. A 4096
   bake of F2 is one flag (`--size 4096`) if the close view needs it.

## Open

- Parts mat outlines and seat marks wait for `pistol/PARTS.md` and `servo/PARTS.md`.
- Vise hold checks use placeholder sizes until the other families export.
- The tang mould's cavity is taken from `grip/export/grip.glb` (93 x 39 x 115 mm core, parted on P Y = 0), see Milestone 3.
- The schematic drawing waits for the other agents' exploded renders.

## Milestone 3 as built (21 Nov 2026)

Built and published with the step table's ids; where this file's M3 rows differ, `README.md` (Milestone 3 and its
Departures) and `export/parts.json` are what was built: params `press_lever` (lever and ram on one clip),
`press_pressure`, `lamp_arm` (one clip over four bones), `schematic_s0..s7` (skinned marks); no `jar` lid param (the lid
stands open), no tester probe params (`tester_probes` is one tool), no press `platen`/`lock`/`vent` params (the vent is
the `press_vents` lamp); dies 120 x 146 x 34 mm with the grip core's own cavity; holster on a hook over the front edge.
