# Stabilised Pistol Grip (`grip/`)

`model-pistol`, 20 November 2026. What is new when the grip the player builds at Brann's bench exists: the fused core,
two brass grip screws and the two nanite seams, with the marks and paths the other families' parts go on. Parts and
the core's features: [PARTS.md](PARTS.md). What other families fit: [INTERFACE.md](INTERFACE.md) and `interface.json`.
Kit: [../kit/READY.md](../kit/READY.md). Rulings this family follows: `../SEAM.md` sections 2, 7, 8 and 9.

## Files

| Path | What |
|---|---|
| `INTERFACE.md`, `interface.json` | the numbers the servo and materials families build to; "As built" at the end |
| `PARTS.md` | parts breakdown (rewritten 18:40 after SEAM.md section 9) |
| `pgeom.py` | frozen copy of `../pistol/pgeom.py` at the pistol hand-over: frames G and D, plate outline, holes, the grip's lines |
| `build.py` | core, screws, seams, pose marks and paths; stand-in plates and strap; sequence; bake and export |
| `check.py` | the machine checks with the stripped pistol, the servo's gimbal unit and case screws, and the stand-ins |
| `render_fit.py` | renders with the servo's unit and screws appended on the core's marks: `review/[warm_]fit_*.png` |
| `render_asfound.py` | the exported GLB with the as-found texture set swapped in: `review/[warm_]asfound_*.png` |
| `crosscheck_materials.py` | no Blender: the materials family's plates and strap, read from its GLB, against `interface.json` |
| `run_build_check.sh`, `run_final.sh`, `run_review.sh` | one queued job each (build + check; bake + check + every picture; unbaked review + fit renders) |
| `export/grip.glb`, `parts.json`, `stats.json`, `check.json`, `tex/` | the family (metres, frame P) |
| `export/grip.blend` | the source scene: procedural materials, and the stand-in plates and strap |
| `review/` | renders |

Rebuild: `SH/run.sh mp-grip bash grip/run_build_check.sh --nobake` (seconds once it has the slot), then
`SH/run.sh mp-grip2 bash grip/run_final.sh --size 2048 --spp 24` (the bake, the checks and all the pictures).

## Frames

`grip.glb` is in the pistol metric frame P (metres; origin and axes of `ScrapPistol.glb`), like `pistol.glb`: the two
family roots placed together are the fitted pistol. `grip_core`'s rest pose is its seat on `pistol.frame`;
`grip_core__clear` is 75 mm down the tang. Everything that seats on the core does so on a pair of pose marks on
`grip_core` (`seat_x` and `clear_x`, `"pose": true` in `parts.json`): the incoming node takes the mark's world
transform. The plate frames are in `INTERFACE.md`; note that the left plate's +X is −U (a node frame cannot be
mirrored).

## Provenance

Original work, built procedurally in Blender 5.2.2 by `build.py` on the programme's kit. **No reference sheet**: the
image service refused the materials family's prompt that named these parts (its `sheets/materials_overall_REFUSED.prompt.txt`),
so no grip prompt was sent and nothing was reworded; the grip is modelled from the written brief, `DESIGN.md`, the
bench look target and the pistol build. No image generations and no Meshy credits spent on this family.

## Departures and decisions

1. **Five nodes, not nine** (`SEAM.md` section 9): plates and strap belong to `materials`, the gimbal unit and the
   plate screws to `servo`. They are here only as stand-ins (plates, strap) or loaded for the sweep (unit, screws).
2. **No `grip_hand.glb`** (same ruling): `integration` builds the grip in the hand from the seated bench parts.
3. **The plates stand proud; there is no recess.** See PARTS.md. Nothing in `interface.json` changed.
4. **The strap lies in an open channel**, flush on its two legs and 0.4 to 1.1 mm below the core's surface along the
   base and round the heel. The first bed was the strap's own shape and left a skin of core over the strap, which the
   sweep caught (it could not slide on).
5. **The seam is an open line**, not a ring: along the top the plate's edge is the core's own edge under the frame.
6. **`seam_l` and `seam_r` are `flex` parts with a `__clear`** so the contract has a pose for them, but they are a bead
   that appears as it is traced; the as-found texture set (`tex/grip__dirty_*.png`) is the uncured paste.
7. **The core is also the raw core** (`SEAM.md` section 10): its as-found set is the core fresh from the mould, with
   three wipes (`skin`, `flash`, `pocket`) whose zones overlap; see PARTS.md for the rule the shader needs. A band
   1.6 mm wide on the parting plane is its own surface and path `parting` runs along it. The two spring clips are
   part of the core mesh, so they are there from the moment the mould opens.
8. **Cast details not in any brief**: three lightening pockets and a rib under the right plate, six ejector witness
   marks, finger serrations in the front strap. They are what a moulded part has, and they are what the player looks
   at while the core is bare on the bench.
9. **The grip screws' `material` is `steel`** in `parts.json` (the contract's list has no brass); they are brass.

## Kit changes made for this family (all in `../kit/READY.md`)

Pose marks (`CT.pose_mark`), sweeping another family's part between two pose marks (`seat`, `clear`, `unit`, `among`,
`expect` on a sequence event), externals that start absent, stand-ins, loose parts of another family no longer in the
way, and a boolean that refuses a fallback solver's no-op and says when a cut leaves an open solid.
