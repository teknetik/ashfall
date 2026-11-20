# Hero base: the seven armour pieces re-fitted to the new body (20 Nov 2026)

Blender-only work. Nothing under `unity/` was written. Outputs are in `out/`; they are not installed by this folder.

Status: all seven files exist and pass the hard checks in `check.json` (same 54 joints, names and inverse bind
matrices as `build/out/colonist.glb` of 11:14:35, no animations, root `Armature`, triangles within the shipped counts,
at most four normalised weights, material and textures byte-identical to the shipped files). They were looked at in
CPU Cycles renders in the rest pose, the neutral pose, idle, walk, run, a rifle-hold clip and two hand-set poses. They
were **not** looked at in Unity by this pass. Open defects are listed at the end.

## Two things that differ from the brief

1. **The references moved.** `unity/.../Armour/TutorialSet/TS_*.glb` were overwritten on 20 Nov at 11:18 by the hero
   integration (texture-less stand-ins), and `Imported/Meshy/colonist.glb` is the new body since 11:14. The pieces "as
   shipped for the old body" are therefore read from git HEAD `7b4f1889`: copies in `ref_shipped/` (`sha256.txt`; the
   vest, helmet and carrier hashes match `art/colonist_back_20261120/README.md`). Materials and textures are taken
   from those copies byte for byte (`graft.py`).
2. **The vest and the carrier are fitted in the neutral pose, not the rest pose.** The rest pose is Meshy's A-pose.
   Every clip in `hero.blend` holds the collarbones 17-21 degrees off it (`blender/weights_probe.py`), and on this rig
   the collarbones own most of the upper chest and back (0.5-0.9 of the skin weight down to the armpits). A vest
   fitted to the A-pose torso and weighted by the shipped rule (collarbone weight faded out below the armpits) had its
   back plate sheared and its panel edges thrown out as wings in idle and walk (`renders/motion_vest.jpg`); made rigid
   on the spine it measured 28-83 mm inside the collarbone regions in idle, walk and aim (`renders/motion_vest2.jpg`). So the body is posed with the idle
   clip's collarbone and arm rotations on an upright spine (`hlib.set_pose(..., 'neutral')`), the piece is fitted and
   weighted there, and each vertex is carried back to the rest pose by inverse skinning (`hlib.unpose`). In idle the
   piece sits as fitted. **In the A-pose rest it intersects the shoulders and arms** (vest 1,848 split vertices inside,
   deepest 34 mm; carrier 2,254, 34 mm). `check.json` reports both poses. Fitting in the rest pose instead is one
   argument: `fit_torso.py -- vest fit pose=rest` and `skin pose=rest`.

Smaller points: the shipped vest already carries `LeftArm` weight on its shoulder pad (LeftShoulder 0.6 / LeftArm
0.4), so "no arm weights" is not what ships now; that split is kept, on the pad only. The shipped boots are weighted to
the Foot bones only; the new ones use Foot + ToeBase as the brief says. The shipped carrier has 8,993 triangles, not
9,000.

## Rebuild

`./fit_all.sh [helmet vest carrier arms legs boots gloves]` (fit -> `decimate.py` with pymeshlab -> skin and export on
the hero armature -> `graft.py`). Its defaults are the constants below. Every Blender step goes through
`~/.local/state/ward-programme/showcase-phase2-20261120/blender.sh` (single slot, CPU). Then
`blender.sh blender/check_motion.py`, `blender.sh blender/check_armour.py` (writes `check.json`) and
`./review_final.sh` (renders and the two sheets). Shared code: `blender/hlib.py` (adapted copies of
`tutorial_set_20261002/blender/fitlib.py` and `colonist_back_20261120/blender/cblib.py`, plus `conform`, `radial_fit`,
`unpose`, poses). `glbinfo.py` is the GLB reader used by the check.

## Pieces

Triangles are new / shipped. "Rest" and "neutral" are split vertices of the exported file inside the body in that
pose and the deepest one (`check.json`).

| File | Source | Script and arguments | Triangles | Weights | Rest | Neutral |
| --- | --- | --- | --- | --- | --- | --- |
| `TS_Helmet.glb` | `meshy/tutorial-set-20261002/helmet/model.glb` (19,977) | `fit_helmet.py -- fit mult=1.04 dy=-0.006 dz=0.01`, decimate 12000, `-- skin` | 11,999 / 11,999 | Head 1.0 | 3, 0.8 mm | 3, 0.8 mm |
| `TS_FieldVest.glb` | `.../chest/model.glb` (30,402) | `fit_torso.py -- vest fit mult=1.05`, decimate 14000, `-- vest skin mult=1.05` | 13,995 / 13,999 | torso list; pad LeftShoulder 0.6 / LeftArm 0.4 | 1,848, 34 mm | 147, 15 mm |
| `TS_WardenCarrier.glb` | `unity/.../Art/Armour/WardenPlateCarrier.glb` (24,192; read only) | `fit_torso.py -- carrier fit`, decimate 8990, `-- carrier skin` | 8,990 / 8,993 | torso list | 2,254, 34 mm | 938, 40 mm |
| `TS_ArmGuards.glb` | `.../bracer/model.glb` (12,112) | `fit_limbs.py -- bracer fit`, decimate 3626, `-- bracer skin` | 7,252 / 7,253 | Left/RightForeArm 1.0 | 0 | 0 |
| `TS_Gloves.glb` | the shipped shell, `ref_shipped/TS_Gloves.glb` | `fit_gloves.py` | 4,240 / 4,240 | Hand, finger joints, forearm at the cuff (from the body) | 8, 1.5 mm | 8, 1.5 mm |
| `TS_LegArmour.glb` | `.../kneeshin/model.glb` (16,213) | `fit_limbs.py -- kneeshin fit`, decimate 4188, `-- kneeshin skin` | 8,374 / 8,376 | Left/RightLeg 1.0 | 0 | 0 |
| `TS_Boots.glb` | `.../bootplates/model.glb` (12,308) | `fit_limbs.py -- bootplates fit`, decimate 3773, `-- bootplates skin` | 7,544 / 7,547 | Foot, ToeBase | 0 | 0 |

All seven: 54 joints, names equal, inverse bind matrix difference 0.0 against `build/out/colonist.glb`.

### Fit constants and what changed against the old recipes

- **Helmet.** Shipped rule kept: uniform scale from the head cap (top 13 cm, hair included: 0.239 m deep, old head
  0.215), margin 16 mm. Scale 0.1594 (rule x 1.04), 6 mm forward, 10 mm up. New: `hlib.radial_fit`, because the
  shipped push-out moved the padding through the outer shell and the quiff still came through the dome. The outer
  shell clears the hair by 4 mm on rays from the middle of the head (first pass: 145 outer vertices short, worst
  21.7 mm; after: none through, worst clearance 1.6 mm on one vertex); the padding is kept under the shell.
- **Vest.** Uniform scale from the chest depth as shipped (`depth / (size.y x 0.86)`), x 1.05: 0.2895 (about 0.25
  on the old body by the same rule). Hung from the shoulder line (top of the trapezius at |x| = 0.136: z 1.5925), strap undersides 12 mm above
  it, because the new neck joint is 6 cm below the trapezius and "top at the neck joint" buried the straps. Front and
  back gaps balanced on the chest and back. Hem cut as shipped (back z 1.185, front 1.145). Flanks snugged to 16 mm;
  straps conformed to 7-11 mm (`hlib.conform`); push-out 7 mm, radius 7 cm. Weights from the arm-less torso, torso
  bones, smoothed three times. Each steel plate has one constant blend so it stays a rigid sheet: front LeftShoulder
  0.148, RightShoulder 0.148, Spine02 0.463, Spine01 0.242; back 0.237, 0.237, Spine01 0.278, Spine02 0.248. The canvas
  hem under a plate hangs from that plate. Pad: found by its steel (363 vertices), scaled 0.92 towards the shoulder
  joint, cleared 10 mm off the deltoid, rigid cap.
- **Carrier.** Same script, scale 0.3199 (rule x 1.0), cut at the hip joint + 4 cm (z 1.066) as shipped. Cloth, no
  rigid plates.
- **Bracers.** The new forearm is half as thick again as the old one and only 1.5 cm longer, so the shipped rule
  (scale from the limb radius) ran the bracer past the elbow. Scale from the forearm length: covers 0.80 of it,
  centred at 0.55 (scale 0.1155; by my estimate the shipped fit was about the same size). The girth is taken up by `conform` (gap 6-11 mm,
  radius 3.5 cm, 14 passes): 2,300 of 6,043 vertices started inside the arm, up to 36 mm. Right side fitted, mirrored,
  each side then fitted to its own arm.
- **Knee + shin.** Top 3.5 cm above the knee joint, bottom at z 0.215 (scale 0.1854). `conform` 7-13 mm, radius 4 cm.
  The cross-section grew from 0.147 x 0.171 m to 0.198 x 0.251 m to go round the trouser leg.
- **Boot plates.** The new rest pose stands flat (the old one was on tiptoe), so the plates lie along the sole
  (principal axis of the boot in plan, 6 degrees toe-out), not along the ankle-to-toe bone. Length 1.04 x boot length
  (0.335 m), 12 mm above the ground, `conform` 6-12 mm. ToeBase in front of the toe joint, Foot behind, 3 cm blend
  across the joint (the strap).
- **Gloves.** The shipped shell (same vertices, faces, UVs, so its texture carries over) is re-posed bone by bone
  from the old hand to the new one (frames from the joints and the palm normal, each segment scaled to the new joint
  spacing and thickness and centred on the finger), then every vertex is laid 3.5 mm above the skin of its own finger
  and takes the body's weights at that point. Hand scale: 1.34 wide, 1.21 long. A new shell cut from the new body
  could not carry the texture: different mesh, different UVs.

## Evidence

- `renders/sheet_kit.jpg`: all pieces on the body from front, back, both sides and three-quarter. Row 1 neutral pose
  with the vest, row 2 neutral pose with the carrier, row 3 rest pose (A-pose) with the vest.
- `renders/sheet_motion.jpg`: walk 25 % and 75 %, run 25 % and 75 %, the hand-set rifle pose, the hand-set deep knee
  bend, and the rifle-hold clip (`rig/rifle_573.glb`), each from front, back and left.
- `renders/final_closeups.jpg`: every piece close up in the neutral pose (the middle tile of each limb row looks from
  inside the body and shows nothing). `renders/final_carrier.jpg`: the carrier in neutral, rest, idle and walk.
- Earlier steps: `motion_vest.jpg` (shipped weight rule: sheared back plate), `motion_vest2.jpg` (rigid on the spine),
  `motion_vest3.jpg` (neutral fit, before the pad and hem fixes), `gloves_b.jpg` (both hands, arms out),
  `limbs_a.jpg`, `helmet_a.jpg` (hair through the dome) and `helmet_b.jpg`, `ref_old_kit.jpg` and `ref_old_idle.jpg`
  (the shipped kit on the old body), `src_all.jpg` (the Meshy sources).
- `check.json`; `work/motion.json`; `work/where_inside_final.txt` (which body part each of vest and carrier touches).

Piece vertices inside the deformed body: inside / deeper than 3 mm / deepest mm (`blender/check_motion.py`):

| Pose | Helmet | Vest | Carrier | Bracers | Gloves | Knee + shin | Boots |
| --- | --- | --- | --- | --- | --- | --- | --- |
| rest | 3 / 0 / -1 | 1848 / 1432 / -34 | 2254 / 1775 / -34 | 0 | 8 / 0 / -2 | 0 | 0 |
| neutral | 3 / 0 / -1 | 147 / 63 / -15 | 938 / 800 / -40 | 0 | 8 / 0 / -2 | 0 | 0 |
| idle 0 % | 3 / 0 / -1 | 321 / 120 / -15 | 1083 / 912 / -40 | 0 | 8 / 0 / -2 | 2 / 0 / -1 | 189 / 75 / -10 |
| walk 25 % | 3 / 0 / -1 | 606 / 389 / -29 | 1786 / 1201 / -39 | 0 | 8 / 0 / -2 | 0 | 874 / 503 / -37 |
| walk 75 % | 3 / 0 / -1 | 1364 / 899 / -31 | 2257 / 1866 / -47 | 3 / 0 / -1 | 8 / 0 / -2 | 0 | 644 / 273 / -24 |
| run 25 % | 3 / 0 / -1 | 979 / 572 / -14 | 2063 / 1584 / -46 | 782 / 638 / -29 | 8 / 0 / -2 | 1007 / 871 / -77 | 645 / 381 / -53 |
| run 75 % | 16 / 0 / -1 | 1062 / 615 / -16 | 2192 / 1864 / -60 | 1089 / 957 / -33 | 8 / 0 / -2 | 985 / 854 / -78 | 1266 / 892 / -53 |
| rifle (hand-set) | 3 / 0 / -1 | 870 / 699 / -33 | 583 / 484 / -54 | 46 / 0 / -2 | 202 / 17 / -4 | 0 | 0 |
| kneel (hand-set) | 3 / 0 / -1 | 1842 / 1399 / -34 | 2268 / 1773 / -34 | 0 | 8 / 0 / -2 | 2209 / 1922 / -79 | 431 / 306 / -23 |
| clip rifle_573 | 3 / 0 / -1 | 1391 / 868 / -43 | 1166 / 603 / -29 | 883 / 760 / -34 | 136 / 10 / -4 | 72 / 44 / -13 | 527 / 338 / -18 |
| clip aim_95 | 37 / 0 / -2 | 1170 / 807 / -24 | 1001 / 726 / -33 | 73 / 8 / -6 | 242 / 26 / -5 | 1372 / 1211 / -79 | 591 / 396 / -32 |
| clip carry_334 | 3 / 0 / -1 | 3109 / 2611 / -50 | 2915 / 2624 / -55 | 18 / 0 / -2 | 71 / 4 / -3 | 171 / 112 / -30 | 589 / 402 / -29 |

The two hand-set poses start from the rest pose, so their vest and carrier figures are the A-pose figures. These
numbers count armour inside the body (an arm pressed into a pouch counts); they do not show body in front of armour.
For that, look at the renders.

For comparison, the vest as it stood at 11:33-11:47 (rest-pose fit, shipped weight rule), same measure: rest
159 / 70 / -11, idle 812 / 633 / -51, walk 75 % 1238 / 965 / -54, run 25 % 420 / 292 / -34, clip rifle_573
570 / 374 / -29, aim_95 167 / 95 / -19, carry_334 1153 / 1049 / -62. The final vest is cleaner in idle and in walk at
0 % and 50 %, and its plates no longer shear; it has more vertices inside the body in run and in the three weapon
clips. That file is not kept in this folder.

## Open defects

- **Vest and carrier in the A-pose rest:** inside the shoulders and arms as stated above. In `sheet_kit.jpg` row 3
  (vest) it is not noticeable at body scale; the vest was not rendered close up in that pose. The carrier was
  (`final_carrier.jpg`, row 2) and shows no body through it there.
- **Vest and carrier against the arms and belly in motion.** Most of the count is the upper arms resting in the side
  panels and pouches (carrier, neutral pose: 568 + 370 vertices in the right and left arm, up to 40 mm). In the weapon
  clips the vest's lower edge goes into the belly (rifle_573: 618 vertices in the hip region, up to 43 mm; draw_222:
  730, 32 mm) because the plate is rigid, and the straps are up to 9-35 mm inside the shoulders. In the rifle-hold
  frame of `sheet_motion.jpg` the front plate's lower edge appears partly covered by the shirt (small in that frame;
  no close-up was made).
- **Vest hem.** Before the last change the canvas under the plates flared out as a ragged fringe in the carry and aim
  clips (`motion_vest3.jpg`, rows 3-4). It now hangs from the plates. After that change only the full-body sheets
  were rendered; the carry and aim close-ups were not repeated.
- **Carrier:** a dark shading dent in the middle of the upper back (all poses in `final_carrier.jpg`). The yellow
  chest tape has a jagged upper edge; whether the shipped carrier has it too was not checked (no render of it was
  made). Flat texture as shipped.
- **Boots:** the ankle collar is rigid on the Foot bone and stands 9 cm above the ankle joint, so it cuts into the
  shin and trouser hem when the ankle bends (walk up to 874 vertices, 37 mm; run up to 1,266, 53 mm). Sharing the
  collar with the Leg bone would stop it, but that is outside "Foot + ToeBase". Not built.
- **Knee + shin:** the top strap and the edge of the knee cap go into the thigh when the knee bends (walk 50 %: 549
  vertices, 68 mm; run about 1,000-1,500, 77 mm; deep knee bend 2,209, 79 mm). The piece is rigid on the Leg bone. Its
  lower end (z 0.21) overlaps the top of the boot collar (z 0.236) by about 2 cm; the shipped kit overlapped too.
  Plates and buckles are 35-47 % wider than designed because the leg is that much thicker.
- **Bracers:** the elbow end goes into the upper arm when the elbow bends past about 90 degrees (run 298-1,089
  vertices, 15-33 mm; rifle_573 883, 34 mm). A shorter coverage (`cover=0.76 frac=0.575`) was prepared but not built
  or looked at. The elbow end is flared like a gauntlet cuff to go round the forearm.
- **Gloves:** the new rig's finger joints are evenly spaced (23 mm on the index), so the sleeves end about 35 mm past
  the knuckle joint, a little shorter on the finger than before. Where fingers touch there is no room for leather:
  115 welded vertices sit closer than 3.5 mm to the skin (down to 0.3 mm), 8 split vertices are up to 1.5 mm inside a
  neighbouring finger. The rim of the index sleeve is slightly ragged. The body's left wrist band is under the cuff.
  A fist (hand-set) puts 255 vertices inside, deepest 5 mm.
- **Helmet:** 4 % larger than the shipped proportion and swelled locally over the quiff; three vertices 0.8 mm inside.
  The Meshy design is as busy as before.
- Not installed or viewed in Unity by this pass. No texture was changed.

## Provenance

No Meshy credits, no image generation. Sources are the Meshy pieces recorded in
`meshy/tutorial-set-20261002/README.md` and the Warden plate carrier; textures are the shipped ones. pymeshlab (GPL)
is a tool only and is not shipped.
