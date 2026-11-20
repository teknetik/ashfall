# The player colonist seen from behind (showcase phase 2, 20 November 2026)

The phase 1 conversation camera (`ConversationFraming.Shot.Default`: 40°, 1.25 m behind the head) puts the colonist's
back, shoulder and helmet across about a third of every dialogue frame. In `unity/evidence/showcase/20261119/qa/previews/final3-conversations.jpg`
the suit read as speckled camouflage, the chest rig had torn dark edges and blotches, and the helmet was a dense noisy
pattern. This pass found the causes, fixed the four asset files, and adds review cameras. Not yet accepted by Carl.

## Causes found (Blender renders of the shipped files, confirmed in one Unity Editor frame)

| Symptom | Real cause | Evidence |
| --- | --- | --- |
| Suit sleeves/back/legs read as speckled camouflage with bright flecks | The suit base colour (Meshy retexture `01a0fe25…`, `meshy/tutorial-set-20261002`) is a patchwork of unrelated fragments: high-contrast knit/moiré weaves, white cross-stitches and pink skin-coloured pieces placed at random over the atlas. Not mips, not compression, not lighting. The fold normal map (baked from the 595k source) is fine. | `inspect/suit_crops.jpg`, `inspect/helm_suit_maps.jpg` |
| Chest rig: notch/holes in the back plate, one-sided ragged rims at armholes and hem | `fitlib.strip_inner` deleted 10,052 of the vest's 30,402 faces (the inner wall of a double-walled shell), opening holes such as the saw-tooth notch under the back plate | `renders/diag_var.jpg` (variants A/C vs B/D) |
| Chest rig, carrier, helmet: flaky jagged borders along straps and edges | `fitlib.decimate` (Blender COLLAPSE 40 %) ran on meshes still split at every UV seam (glTF import), so every seam collapsed on its own and tore | `renders/diag_var.jpg` (A/B vs C/D) |
| Long smeared "flaps" either side of the back plate (the dark blotches/torn look at the armholes) | Skin weights: the vest took LeftArm/RightArm and Left/RightShoulder weights from the body. In the idle clip the arms and clavicles move from the A-pose rest, dragging the side panels out into wings with stretched texture. Clean in the rest pose. Also the push-out against the full body used the inside of the upper arm as "nearest surface" under the armpits. | `renders/restidle.jpg`, `renders/flank.jpg` |
| Back plate looks tan with dark blotches in game | Not a fault: the back plate is rusty scrap steel (metallic) reflecting the sandy surroundings; the blotches were the holes/flaps above | Unity before frame below |
| Helmet: dense noisy pattern | Mostly the design (a riveted, banded Meshy shell), made worse by the 40 % decimation and single-texel speckle in its albedo/metal maps | `renders/r6_helm.jpg` |
| Suit poking through armour | Not found on the vest after the re-fit (push-out is against body + suit); minor on the carrier liner (inside, not visible) | `renders/diag/vest_pokethrough.png` |

Worn backpack: **none exists.** The Field Supply packs are inventory items and shop props only (`FieldSupplyShopPass.Packs`);
`PlayerArmourVisuals` has seven pieces (helmet, vest, arm guards, gloves, leggings, boots, plate carrier) and no pack.

## What changed, per file (all four keep path, GUID, 54-joint order, inverse bind matrices, mesh and material names)

| File | Change | Triangles | Textures |
| --- | --- | --- | --- |
| `Art/Imported/Meshy/colonist.glb` | Only two embedded images swapped (`patch_glb.py`; every accessor, skin, node, mesh and animation byte-identical, checked by the script): `suit_base` = new synthesised olive twill, `player_normal_4k` = the old fold map + seams, patch hems and stitches. Face/hair (3 Oct), collar, matte fabric, belt and gait (5 Oct) are untouched. | 76,043 (unchanged) | same sizes (4k BC7); 97.75 MB for the whole body set, unchanged |
| `Art/Armour/TutorialSet/TS_FieldVest.glb` | Re-fitted from the full Meshy source: no strip_inner, seams merged, flanks pushed out against an arm-less torso proxy, pymeshlab texture-aware quadric decimation with boundary preservation, torso-only weights with clavicle weight faded out below the armpits; albedo speckle median-filtered, metal flecks removed, roughness +0.05, normal scale 0.75 | 8,080 → 14,000 | 2k set, 16 MB (unchanged) |
| `TS_WardenCarrier.glb` | Same re-fit (keeps the hem cut at hips + 4 cm) | 5,764 → 8,993 | unchanged |
| `TS_Helmet.glb` | Same decimation (rigid on Head as before); albedo calmed (70 % 5 px median, high-frequency contrast ×0.6), metal median 9 px, roughness +0.08, normal scale 0.6 | 7,990 → 11,999 | unchanged |

Suit texture (`make_suit.py`, numpy from Cycles bakes of the suit in its own UVs): olive `(84,81,57)` sRGB twill (2.2 mm
diagonal, ±2 % in colour only; as relief it moiréd), panel-scale tone drift, sun bleach on upward and upper-back
surfaces, AO at 30 % as cavity dirt only (no lighting baked), wear on convex creases, elbows and knees, sand on knees,
seat and shins, sweat at the collar, a shallow-V back yoke and centre-back seam with stitch rows, and the concept's crash
repairs: tan canvas patches on the left shoulder (back and front), right seat and left thigh, grey canvas on the right
knee and left calf, all with folded hems and coarse stitching, plus a re-stitched tear on the right upper sleeve. Values
and patch placements are the tables at the top of `make_suit.py`.

**Cost.** Player body unchanged. Armour +5.9k skinned triangles for the default worn kit (vest + boots), +9.9k with the
helmet, +3.2k with the carrier instead of the vest; texture memory unchanged. Not measured natively. The 40 % versions are
the rollback files; to trade detail back, change `FACES` in `fit_all.sh` and rebuild (it is a rebuild switch, not a
runtime toggle).

## Rebuild, install, rollback

- Rebuild everything in `out/`: `art/colonist_back_20261120/build.sh` (bake → `make_suit.py` → `patch_glb.py` →
  `fit_all.sh` → `clean_tex.py` + `patch_glb.py` → `check_rig.py`). Scripts: `blender/bake_suit.py`, `blender/fit_piece.py`
  (stages `fit`, `skin`), `decimate.py` (pymeshlab via `uv run --with pymeshlab`), `blender/cblib.py` + `blender/compare.py`
  (review renders), `blender/diag*.py`, `blender/fitvar.py` (the diagnosis).
- Install: `P2/seq.sh install colonist_back-N AthenHill.Editor.ColonistBackPass20261120.RunBatch install,verify`
  (`Assets/AthenHill/Editor/ColonistBackPass20261120.cs`). It copies `out/*.glb` over the assets (first install keeps the
  shipped files in `rollback/` with `sha256.json`), reimports, adds the `cam_cb_*` cameras under the root
  **Colonist back review cameras**, saves the scene and writes `install.json`/`verify.json`. Idempotent: it copies only
  when hashes differ and rebuilds the camera root. No older installer is run.
- Verify (`-nographics`): files installed, body 54 bones / 7 materials / clips present, every armour piece bound by
  name with bind max diff < 1e-4 and materials present, ViewModelArmourMirror sources/mirrors intact, first-person arms
  renderers present (TS_FPArms not touched), six review cameras, no missing scripts under the player; triangle and
  texture-memory report per renderer.
- Rollback: `--steps rollback` copies `rollback/*.glb` back (sha256 there match the 5 Oct polish colonist
  `88a3b9a0…` and the 3 Oct pieces), reimports and removes the camera root.
- Capture (graphics mode, NOT yet run successfully): `DISPLAY=:0 WAYLAND_DISPLAY=wayland-1 ~/.local/state/ward-programme/unity.sh LOG
  AthenHill.Editor.ColonistBackPass20261120.RunBatch --steps capture --shots kit|light|carrier|suit --state before|after`
  (≤ 6 cameras each, at the rifle review stand; kit = conv/follow/back/quarter/helmet/vest in sun; light = shade
  conv/back/helmet + 20:30 conv/back/vest; carrier and suit = sun and shade). Output
  `unity/evidence/showcase_phase2/20261120/colonist_back/captures/<state>/`. "Before" now needs `--steps rollback` first
  (or skip it: the Blender before renders and the one Unity before frame exist).

## Verification status

- **Installed and verified** (`-nographics`, 19 Nov ~20:27, log `unity/evidence/showcase_phase2/20261120/install-colonist_back-1.log`):
  verify PASS, all bind diffs 0.00000, joint order and inverse bind matrices identical (also `check_rig.py`).
- **Looked at with my own eyes (Blender EEVEE, idle pose, sun):** before/after sheets in
  `unity/evidence/showcase_phase2/20261120/colonist_back/blender/` (`conv_before_after.jpg`, `kit_before_after.jpg`,
  `suit_before_after.jpg`, `carrier_before_after.jpg`, plus the diagnosis sheets). Iteration renders `renders/r1` (before)
  … `renders/r6` (final).
- **Unity Editor:** one before frame only (`captures/before/kit_sun_conv_13.0.png`, in-engine confirmation of the notch,
  flaps, torn hem and patchwork trousers); the rest of that run was killed by the watchdog (machine-wide swap). No after
  Editor capture, no shade/20:30 Unity frames, no Edit Mode run, no native run.


## Fix round (19 Nov evening, after the orchestrator's review and the first native frames)

Points from the orchestrator (20:50, 21:27) and what was done. Everything stays inside the four files; same rig,
joint order, inverse bind matrices, mesh and material names (`check_rig.py`).

| # | Point | Done |
| --- | --- | --- |
| 1 | Back-plate shard and flaky hem | The crumpled canvas skirt of the Meshy rig (present in the undecimated fit too) is cut off by a plane tilted front-to-back 1 cm up into each plate's lowest point (`fit_piece.hem_cut`), so the vest ends in the plates' own straight bottom edges. The lighter facet on the plate was a push-out dent: plate interiors are now smoothed along the normal only (`smooth_plates`; a plain Laplacian smeared the texture, seen and rejected in r7). |
| 2 | Shoulder pad | Drawn 12 % in towards the shoulder joint and re-weighted LeftShoulder 0.6 / LeftArm 0.4 (`pad_cap`), so it sits as a cap; its steel texels (metallic or painted, not the straps) recoloured dark blued steel (46/46/44 sRGB with 30 % of the original low-frequency value), rust and paint kept only within ~2 cm of the pad's 3D edge, metallic 0.6, roughness 0.62 (`clean_tex.py`, mask from `fit_piece.pad_mask`). |
| 3 | Collar notch and jagged neckline | `edit_suit_mesh.py` (positions only): the collar rim (open edge plus the folded rim's outer layer) goes onto a smooth ring (median profile, 28° low-pass); the neck skin's own jagged hole edge is pushed 12 mm down under the collar so no gap can open; the collar's under-layer is not dragged through the outer layer. Texture: a 28 mm collar band with a stitch row. |
| 4 | Saw-tooth sleeve ends | Same tool: sleeve rims onto a smooth ring (30° low-pass), frayed spikes collapsed onto it, forearm skin edge tucked 12 mm under the cuff. Texture: a 35 mm rolled cuff (inside tone, fold lines, darker hem edge, raised in the normal map). Weights untouched (each vertex keeps its own; moves are ≤ 6 cm along the forearm, smooth per sector). |
| 5 | Suit reads as olive plastic | `make_suit.py` v2: olive-brown (86/79/56), plain weave 1.6 mm in the normal map (15 µm relief) and colour, top-stitched seams added (set-in sleeves, torso side seams, leg outseams, shoulder seams, with the yoke and centre back), lighter yoke / darker side panels, wear along seams, stronger shoulder sun-fade, two more repair patches (upper back right, left sleeve back), cargo pockets with flaps on both thighs, a pen pocket on the left sleeve. Material: roughness 0.84 → 0.95, normal scale 0.42 → 0.55 (folds read more). |
| 6 | Helmet noise | `group_helmet.py`: texels classed (smoothed, no class speckle) into painted shell (dark olive-grey 60/62/56, metallic 0.55), bands and rivets (worn steel 104/98/88, metallic 0.88) and canvas straps/liner (116/101/76, non-metal, roughness 0.9); each class tone × gentle low-frequency variation + 15 % of fine detail. Normal scale 0.6. |
| 7 | cam_cb_conv framing | No change needed, and none would be right: the game's own solve (`ConversationFraming.Solve`, Shot.Default) cannot reach playerViewportX 0.27 at talking distances, because the wanted 0.50 rad head separation needs a shoulder offset beyond maxShoulder 0.75 m (0.31 rad), so the head lands at ~0.43 of the width (0.42 at 2.2 m). cam_cb_conv reproduces exactly that, as the phase 1 native conversation frames do. 0.27 is a ConversationFraming tuning question for the camera item. Comment added in the installer. |
| 8 | Hair stipple from behind (no helmet) | The shell and scalp colours are already dark; the dots were sun highlights on the alpha-clipped strand bits and the skin specular showing through. `hair_tex.py`: shells denser (alpha ×1.2 + 0.04: 11.9 % → 14.8 % of texels pass the cutoff), strand contrast halved; PlayerHairShell roughness 0.55 → 0.85; skin roughness ≥ 0.88 under the painted hair. Skin colour untouched (front look as on 3 Oct). |


Collar crease (part of point 3): once the patchwork texture stopped hiding it, the band 1-7 cm under the collar showed
the crumpled crease left by the 5 Oct collar lowering (dark slivers, `renders/hemF/collar.png`). `edit_suit_mesh.py`
now Taubin-smooths that band (326 welded vertices, at most 24 mm, rim and skin untouched; env `CB_SMOOTH`, default 15
iterations). **This last step has not been rendered**: Carl's game held the Blender slot. Check it with
`P2/blender.sh art/colonist_back_20261120/blender/hemview.py -- hemH art/colonist_back_20261120/out/colonist.glb`
(writes `renders/hemH/collar.png`). If it looks worse than `renders/hemF/collar.png`, rebuild without it:
`CB_SMOOTH=0 uv run --with numpy python edit_suit_mesh.py rollback/colonist.glb work/colonist_mesh.glb work/hem_report.json`
then the `patch_glb.py` line of `build.sh`, and reinstall.

Fix-round evidence (Blender Cycles CPU, idle pose, sun): `unity/evidence/showcase_phase2/20261120/colonist_back/blender_fix/`
(`conv_`, `kit_`, `suit_`, `carrier_`, `hems_before_after.jpg`, `native_b1_head_before.png`). Output hashes:
colonist.glb `267568c3…`, TS_FieldVest.glb `fffdf07f…`, TS_Helmet.glb `b5322215…`, TS_WardenCarrier.glb `d7f790a6…`
(unchanged since the first round).

Cost after the fix round: vest 14.0k triangles (unchanged from the first round), hair shells and body unchanged
(76,043), texture sizes unchanged.

## Open defects (be hard on these)

- Helmet: only marginally better. The speckle is gone, but the Meshy design itself is a dense set of riveted bands;
  shell, cover and straps still do not separate clearly. A real fix is a remodel or a hand-painted retexture (no Meshy
  credits this round).
- Suit: rolled sleeve hems and the collar edge are still jagged geometry (pre-existing cut from the 2 Oct jumpsuit fit,
  visible at the elbow in the conversation shot). The new texture is clean but a little plain/CG at close range, and in
  Blender's AgX it reads greener than the concept's olive-brown; judge in Unity before changing `OLIVE`.
- Plate carrier: torn hem and holes fixed, but its own Meshy texture is flat and cartoon-like with a smeared dark band at
  the lower back. Arm guards, gloves, boots and leg armour were not re-fitted (same strip/decimate recipe; they are
  small in this shot).
- Vest shoulder pad (left) now rides the spine (its weights were arm-only); in poses with the arm raised it may
  intersect the deltoid. Check in the rifle quest captures.
- The capture step's conversation shot uses `ConversationFraming.Solve` with a stand-in NPC 1.9 m ahead; in the one
  Unity frame the colonist sits near the centre rather than at 0.27 of the width. The distance is right; the framing of
  that camera may need checking against a real dialogue frame.

## Proposed text for the orchestrator

**unity/EDITING.md**, after "Player shoulder and clothing polish (5 October 2026)":

> ### Player seen from behind: suit texture and armour re-fit (20 November 2026)
>
> `art/colonist_back_20261120/README.md`. The suit's base colour is synthesised in its own UVs by `make_suit.py` from
> Cycles bakes (`blender/bake_suit.py`); colours, wear and patch placements are the tables at the top of the script.
> It is written into `colonist.glb` by `patch_glb.py`, which swaps embedded images only (rig, bind matrices, clips and
> the 3 Oct/5 Oct work stay byte-identical). The chest rig, plate carrier and helmet are re-fitted by
> `blender/fit_piece.py` + `decimate.py` (no `strip_inner`, seams merged, texture-aware decimation, torso-only weights,
> clavicle weight faded below the armpits); do not re-export them with `tutorial_set_20261002/blender/rebuild_armour.sh`,
> which brings back the holes, torn borders and side flaps. Rebuild with `build.sh`; install/verify/rollback with
> `ColonistBackPass20261120.RunBatch --steps install,verify|rollback` (no MainCharacterInstall needed); review cameras
> `cam_cb_conv`, `cam_cb_follow`, `cam_cb_back`, `cam_cb_quarter`, `cam_cb_helmet`, `cam_cb_vest` (root
> **Colonist back review cameras**).

**AGENTS.md section 3, "Player" row**, append:

> **20 Nov 2026 back pass** (`art/colonist_back_20261120`, `Editor/ColonistBackPass20261120.cs`): the suit's Meshy
> patchwork albedo (speckled camouflage from the conversation camera) replaced by a synthesised olive twill with seams,
> wear and the concept's canvas repair patches (same UVs; fold normals kept); vest, plate carrier and helmet re-fitted
> from the full Meshy sources without the strip/decimate damage and arm-driven side flaps (vest 14k, carrier 9k, helmet
> 12k triangles, was 8.1k/5.8k/8.0k); same GUIDs, rig and bind matrices. Verify PASS (-nographics); Editor and native
> captures pending; helmet still busy, sleeve/collar hems still jagged. Rollback `--steps rollback`. Not yet accepted by Carl.

## Provenance

All new texture content is procedural (numpy, this folder). Sources reused: the Meshy pieces already recorded in
`meshy/tutorial-set-20261002/README.md` (helmet `01a0fe21…`, chest rig `01a0fe8b-9adf…`), the Warden plate carrier
(`Art/Armour/WardenPlateCarrier.glb`, Meshy `01a0fc9d…`), the colonist's fold normal map. pymeshlab (GPL, tool only, not
shipped). No Meshy credits, no image generation used.
