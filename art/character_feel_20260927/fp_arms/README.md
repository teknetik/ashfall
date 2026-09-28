# First-person arms — provenance

## v2: `PlayerFPHands_v2` (27 Sep 2026 pm, request #6) — installed

A two-hand cup grip ("thumbs forward") authored procedurally in Blender 5.2 around the actual view-model scrap pistol.
Written by the Claude lane (task t_6c931016). No Meshy credits used.

Why not reuse the old arms: the player skeleton has 24 bones and none are finger bones (`...LeftForeArm, LeftHand,
...RightForeArm, RightHand`), so the colonist-cut arms can't close a grip. The hold is static, so v2 is a static mesh
parented to the view-model pistol. `FirstPersonViewModel` still places the rig so the pistol lands on the hip/ADS pose, so
sway, bob, recoil and draw/holster move the hands unchanged. There's no code change in the runtime script.

Files:
- `build_fp_hands_v2.py`: the generator. Run `blender -b -P build_fp_hands_v2.py -- <out.glb> [render_dir]`. Use a clean
  environment: `env -i HOME=$HOME PATH=/usr/bin:/bin blender ...`, because the agent's Python on PATH breaks the glTF add-on.
  It needs `render_views.py` on `sys.path` for previews.
- `render_views.py`: Blender preview renders from the in-game hip/ADS eye positions and orthographic sides.
- `pistol_frame.obj` / `pistol_frame.json`: the view-model pistol and the old arms, in the pistol's own frame (Unity
  axes, metres), plus the camera poses at hip and ADS. Written by `FPGripPass.Dump()` (Unity, Editor).
- `PlayerFPHands_v2.glb` / `.blend`: the output. The installed copy is
  `unity/AthenHill/Assets/AthenHill/Art/CharacterMotion/FirstPerson/PlayerFPHands_v2.glb`.
- `build_checks.json`: triangle counts and intersection diagnostics from the last build.

How it's built:
- The grip is sliced perpendicular to its measured axis (~20° rake, from the front and back straps). Each slice's convex
  hull is offset by the finger radius.
- Firing fingers (middle, ring, little) are tubes swept along that contour from the MCP knuckles on the right panel,
  across the front strap, to the left panel. The middle finger sits under the trigger guard.
- Support fingers (index to little) wrap the other way around a contour offset by one firing-finger thickness plus a
  2.4 mm crease, so they lie over the firing fingers. The support index presses up under the guard.
- Trigger finger: **on the trigger**. The proximal phalanx runs along the right of the frame above the guard, the finger
  enters the guard, and the pad rests on the trigger face.
- Thumbs forward: the firing thumb runs from the web over the backstrap and forward along the left of the frame, riding
  above the support thumb. The support thumb points forward along the frame above the grip panel.
- Palms are convex hulls of spheres on the grip contour. The support palm steps out over the firing fingertips.
- Wrists are straight. Forearms, bracers and sleeves run 56 cm back toward the elbows, so no cut end shows at hip, ADS,
  recoil, sway or mid-draw (see the Editor renders).
- Each hand is voxel-remeshed (1.1 mm) into one surface (finger creases ≥ 2 mm stay open), smoothed, material-tagged and
  decimated. Glove hems, bracer lips, nails and the wrist status tab are small separate pieces.

Dimensions (from the layout parameters):
- Hand length (wrist crease to middle fingertip) is about 18.5 cm: palm about 9.5 cm plus a middle finger 8.9 cm
  measured along the grip.
- Knuckle span, index to little, is about 8 cm across the grip. Palm hull thickness is 2.6 cm.
- Finger radii at the base are 8.0–9.8 mm, tapering to 6.4–8.0 mm at the tip.
- The pistol grip is about 4.5 cm wide and 6–7 cm front to back. The pistol is 26 cm long and 17 cm tall. The rear sight
  is 8.5 cm above the pistol origin, which puts it on the eye line at ADS.

Triangles: 26,064 in total.
- Right hand 11,000, left hand 10,000.
- Nails, hems, bracer lips and tabs about 5,000.
- The old arms were 1,373.

Materials: six URP Lit materials created by `FPGripPass`, in `Art/CharacterMotion/FirstPerson/FPHands/`. The albedo is
flat and was sampled from the colonist texture. No lighting is baked in.

| Material | sRGB albedo | Smoothness | Other |
| --- | --- | --- | --- |
| Skin | .63/.44/.37 | .46 | |
| Glove | .26/.255/.235 | .42 | |
| Bracer (olive) | .27/.27/.19 | .5 | metallic .15 |
| Sleeve | .14/.145/.14 | .15 | |
| Nail | | | |
| Glow | | | cyan emission ×0.8 |

Known limitations:
- Flat materials: no normal or detail maps.
- The fingers are smooth tubes. Knuckles are simple bumps and there are no tendons or creases.
- The static hold doesn't animate the trigger.
- Hidden overlaps remain where the firing fingertips tuck under the support palm, and where the palm hulls touch the grip
  panels. These overlaps are inside the other surface. Ray-parity counts in `build_checks.json` are approximate because
  the Meshy pistol isn't watertight.

Install and rollback (Unity, Editor):
- `FPGripPass.Install()`, or the menu Athen Hill → Combat → Install first-person hands v2. `WeaponFeelPass.Install()`
  also calls `FPGripPass.Attach()` after it rebuilds the view model.
- Rollback: `FPGripPass.UseOldArms(vm, true)` re-enables the old arms' renderers and hides "FP hands v2". The old arms
  are still in the rig with their renderers disabled.

## v1: `PlayerFPArms.glb` (27 Sep 2026 am) — kept for rollback

`extract_arms.py` cuts the forearms and hands from the 20k-triangle player colonist, giving 1,373 triangles with the
player's own materials. They're posed by `pistol_hold.anim`. The fingers can't grip because the rig has no finger bones.
