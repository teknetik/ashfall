# Fixtures family

Everything fixed to or standing on Brann's bench. Breakdown and layout: `PARTS.md`, `layout/layout_plan.png`,
`layout/layout.json`. How it is built, checked and reviewed, provenance and spend: `../tools/README.md` (the two
families share their code in `../tools/src/mbk.py`).

- `build.py` builds the family; `src/fx_parts.py` has one function per fixture, `src/fx_mats.py` the materials,
  `src/gen_masks.py` the mask images (rule marks, rubber wear, parts mat outlines, hazard border) in `src/gen/`.
- Texture sets: `a` the mats (work surface, bench rule, work mat, parts mat; laid out by hand, projected from above),
  `b` the hardware.
- `src/probe_bench.py` measured the existing bench; its renders and height maps are in `layout/`.
- The parts mat's outlines and seat marks are placeholders (`src/gen/masks.json`, `placeholder: true`) until the
  pistol and servo families export their parts.

## Milestone 3 (21 Nov 2026)

- `src/fx_m3.py` builds the M3 fixtures with the ids the step table uses: `tray`, `bin`, `jar`, `tester` (+ `tester_lamp`,
  `tester_probes` tool `tool:probe`), `press` (+ `press_lever`, `press_ram`, `press_vents`, `press_gauge`, `press_slug`),
  `mouldrack` (+ `mould_tang` with zone `cavity`, `mould_b`, `mould_c`), `mould_charge` (absent at start), `lamp`
  (+ `lamp_turret`, `lamp_arm1`, `lamp_arm2`, `lamp_head`), `schematic` (+ `schematic_marks`, skinned), `holster`, and the
  pose marks for the places that had no mark (`add_places`). `src/fx_mats3.py` has their materials.
- `src/probe_m3.py` reads the grip core, the raw core's sprue, the alloy offcuts, the vial, the pistol and the servo from
  the other families' exports (`layout/m3_probe.json`); the tang mould's cavity is the real `grip.core` mesh (decimated
  to 38 %, grown 0.3 mm) subtracted from the die, parted on P Y = 0, the sprue channel along the sprue's own axis.
- `src/gen_schematic.py` draws the schematic sheet (`src/gen/schematic.png`); `--sketch` lays an image-model drawing
  under the frames.
- The fixtures family has its own copies of the shared scripts since the tools family moved to `model-tools`:
  `src/check_fx.py` (run by `check.py`), `src/review_fx.py`, `src/publish_fx.py`. `tools/src/mbk.py` is still imported,
  unchanged.
- Rigs the kit does not make: `press_lever` (one clip turns the lever 110 degrees and drops the ram 70 mm),
  `lamp_arm` (yaw, shoulder, elbow, wrist on one clip, solved so the head ends over `workmat/seat_grip`),
  `schematic_s0..s7` (a skinned mesh: at 0.5 a wax-pencil ring round the region, at 1 a ring and a tick). Kit rig:
  `press_pressure` (the slug in the sight tube; the green band is 0.55 to 0.80). `check_fx.py` sweeps the rigid ones.

### Departures (Milestone 3)

1. **Four texture sets**, not two: `a` mats (4096 at the hero bake, granted), `b` the slice hardware (2048), `c` the
   schematic sheet (2048; its drawing has to read from the bench camera), `d` the M3 hardware (**4096 at the hero bake,
   not granted**: at 2048 the press, tester and moulds were 5 to 18 px/cm; `--sets d=2048` puts it back). With
   everything in `b` the hardware fell to 4 to 13 px/cm.
9. **The tang mould's cavity is the core's exact shape** (its seven shells subtracted one by one), with no flash
   clearance: growing the core along its normals folded it through itself in the dovetail slot and left die material
   inside the core (checked: 244 to 1085 intersecting triangles, 0.9 mm deep). The check seats the core with contact
   and no penetration. The top die is cut with the core grown 0.9 mm (it is never checked against the core).
10. **Hero bake at spp 16**, not 24: a 4096 pair at 24 samples would not finish inside the Blender slot's 60 minutes.
2. **`lamp_arm` is one param over four bones** (yaw, shoulder, elbow, wrist), the press lever's clip moves the ram too:
   type `custom` in `parts.json` (`bones` lists them). The step table drives one value for each.
3. **The schematic's params are clips on a skinned mesh**, not emission: the bench's glow-on-a-region form exists only
   in the stand-ins. Bind pose shows every mark (`bind_pose_value` 1).
4. **The press's top die rides the ram** (`press_ram`); `mould_tang` is the lower die. Only the tang mould fits the bed:
   cross tongue and dowel holes on its underside (`mould_b`, `mould_c` keyed differently, fixed on the rack).
5. **`lamp_head` is the whole swinging head**; only its emitter is on the emissive material. A lamp variant that lights
   the whole part would light the hood too.
6. **The holster hangs off the worktop's front edge** on a hook, left of the work surface (the stand-in sat on the rule).
7. **The tester's probes are one tool** (`tester_probes`, tip on the red needle); the leads stay on the box and end in
   plugs under the clipped probes.
8. **Place marks** use the bench's numbers where it had them (entry places) and new places where the stand-in numbers put
   the stock under the grip core on the work mat (`workmat/seat_sheet`, `seat_plate_l`, `seat_plate_r`, `seat_strap`,
   `seat_spare` are to the left of and around the core).
