# First-person rifle hands (20 November 2026, showcase phase 2)

> **Fix round (20 Nov, 21:33 to 22:55; see "Fix round" below): the hip framing changed.** The rifle now sits further
> out, lower right, pointing at the crosshair, with the support forearm and hand and the top of the shooting hand in
> frame. Old hip values: `hipOffset (0.13, -0.19, 0.40)`, `hipEuler (2, -4, -5)`. `--steps rollback` restores them,
> together with the rest of the clip-driven rifle. To keep the new hands but get the old hip framing back, set
> `HipFromAim = false` and re-run `install`. The sections below the fix round describe the first install and are kept
> for the record.

Status: installed in the saved scene, `verify` passes (`-nographics`). Not natively tested. No graphics-mode Unity
frames of the final state yet (two capture runs were killed by the watchdog, then the orchestrator stopped graphics
jobs). The review evidence for the final state is **Blender renders of the posed view-model geometry** dumped from Unity
(shape, contact and framing only, grey materials). Not yet accepted by Carl.

## What was wrong

- The rifle view model was **clip-driven**: the rifle hung under the hold clip's right hand, and the hand-to-rifle mount
  came from `RifleArmourInstall` (`GripFromButt 0.35`, `GripFromBottom 0.38`). Measured on `FieldRifle.glb`
  (`rifle_profile.py`): 0.35 of the length from the butt is the **magazine** (0.32 to 0.45 from the butt). The pistol
  grip is at about 0.20 from the butt (0.795 from the muzzle), 5 to 35 % of the rifle's height, 4.9 cm deep, 3.4 cm
  wide, raked 11°. So the shooting hand sat on the magazine well.
- The support hand was placed by the clip's hand orientation with a contact search. Its fingers were not solved
  against the rifle in a useful pose.
- ADS: the eye was 5 cm **below** the top rail (`aimOffset.y −0.118`; rail top is 0.170 above the weapon origin, the
  front sight tip 0.172). So the sights sat well above the crosshair, and the butt plate was 2.5 cm in front of the eye
  and filled the lower view.
- Found on the way, not part of the brief: the **pistol's** glove/arm-guard copies (`ViewModelArmourMirror`) were
  skinned to the pistol's `Weapon mount` (all 54 bones), not to the arms. `PlayerFace20261003.ArmourMirror` built them
  under `vm.rig`, which is the mount once the pistol is weapon-driven. With field gloves or arm guards worn, first
  person showed a rigid bind-pose shell on the pistol (`review/iter10/pistol_hip_fp_armour.png`).

## What changed

Editor pass `unity/AthenHill/Assets/AthenHill/Editor/RifleHandsPass20261120.cs`. It builds the rifle the way the
pistol was built:

- **Weapon-driven**: the view-model rifle is moved onto its own `RH weapon mount` under `Visuals`, which
  `FirstPersonViewModel` now places. The rifle sits exactly where it sat on screen before at the hip, because the hip
  offsets are unchanged.
- **Arms anchors**: `ViewModelArmsRig` on the rifle view model, with a hip anchor and an aim anchor. Shoulders sit under
  and behind the eye, with the torso bladed 40° (left shoulder forward). The arms follow 60 % of the weapon's
  sway/bob/recoil/draw (`followWeapon 0.6`), and the IK takes up the rest.
- **IK**: a new `RH right arm IK` (`SupportHandIK` on `RightArm/RightForeArm/RightHand`) and the existing left-arm IK
  hold the two new grip points under the view-model rifle.
  - Elbow poles in camera space: right (0.3, −0.95, −0.1), left (−0.35, −0.93, 0).
  - `twistShare 0.6`: 60 % of the wrist twist is moved into the forearm, because the rig has no twist bones.
- **`RH shooting grip`**: the palm sits on the pistol grip's right panel, at 18 % of the rifle's height, with the
  fingers forward round the front strap. The installer searched hand pitch (0 to 30°) and roll (0 to 45°) for the
  smallest wrist bend and twist at hip and ADS, with no finger starting inside the gun. Chosen: pitch 10°, roll 15°.
  Verify measures the palm at 0.806 of the length from the muzzle (grip 0.795; the magazine is 0.55 to 0.68).
- **`RH support grip`**: the palm is under the front of the receiver/handguard, 28 cm ahead of the grip. The palm faces
  up and to the right, the fingers wrap the right side, and the thumb lies over the top. The installer searched
  station, yaw and roll (220 candidates, `support_candidates.txt`).
- **Joint search**: the arms configuration (blade 20/30/40°, shoulder depth, three right-elbow directions; 27 configs,
  `config_candidates.txt`) was searched together with both grips. Elbows on screen were penalised.
- **Fingers**: contact-solved against the rifle (temporary mesh colliders) into the view-model arms'
  `PlayerHandGrip.rifleRight/rifleLeft`. The finger radius includes a 2 mm glove allowance.
- **ADS from the sights**: `aimOffset` (0, −0.118, 0.34) → (0.011, −0.1723, 0.33); `aimEuler` (0, 0, 0) →
  (−3.27, 0, 0). The rail is levelled with the line of sight, the front sight tip sits on the crosshair, and the butt is
  1.5 cm behind the eye. Hip offsets, holster pose, sway, bob, recoil, draw/aim times, the muzzle point and the flash
  are unchanged; the install checks this (see Verification).
- **Pistol armour mirror** re-skinned onto the pistol arms' bones (same set-up as the rifle's copies). The broken state
  is recorded in `previous_pistol_mirror.json`.

Runtime changes (small, defaults keep old behaviour):

- `Scripts/Combat/ViewModelArmsRig.cs`: adds `aimAnchor`, `aimAnchorPosition/Rotation` and `followWeapon`, plus the
  pure static `Pose(...)`. With `aimAnchor` off and `followWeapon 0` (the pistol), it gives the same single
  camera-space anchor as before.
- `Scripts/Combat/SupportHandIK.cs`: adds `twistShare` (default 0), `restHandLocal` and `TwistDegrees`. The body's IK
  and the pistol's IKs keep 0. In the saved scene they gained the two default fields when the scene was re-serialised.
- `Scripts/Combat/RifleHandsQa.cs` (new): QA read-out.
- `Scripts/NativeQa.cs` (**shared file, one additive token**): `rifleHands=RifleHandsQa.State(combat),` added after
  `feel=...` in the snapshot.
- `unity/tools/check_rifle_quest.py` (additive): in first person with the rifle it asserts weapon-driven hands on
  `RH shooting grip` / `RH support grip`, and each hand within 2 cm of its grip point at hip and aiming. The check is
  skipped with a note when the build has no read-out.
- Tests: `Tests/Editor/RifleHandsTests.cs` (anchor blend, follow, twist decomposition, twist share).
  **Not run yet**: the Edit Mode run was killed by the watchdog.

## Where to tune

All tunables are `public static` fields at the top of `RifleHandsPass20261120`; re-run `install` after changing one:

| Field | Value |
| --- | --- |
| `GripFromMuzzle`, `GripBand` | grip location |
| `PalmHeight`, `PalmBack` | palm on the grip |
| `ShootPitches`, `ShootRolls` | shooting-hand search |
| `SupportFrom/To`, `SupportYaws`, `SupportRolls`, `SupportForwardBias` | support-hand search |
| `HipShoulders`, `AimShoulders`, `BladeYaws`, `HipMidZs`, `RightPoles`, `LeftPole` | arms configuration |
| `FollowWeapon` | 0.6 |
| `TwistShare` | 0.6 |
| `AimButtBehindEye` | 0.015 |
| `PostFrom/To`, `RailFrom/To` | sights |
| `FingerRadius`, `ThumbRadius` | finger solve radii |

In the Inspector:

- Rifle view model › `ViewModelArmsRig`: anchors, follow.
- `Player arms rig` › `SupportHandIK`: left pole and twist.
- `RH right arm IK`: right pole and twist.
- `FirstPersonViewModel.aimOffset/aimEuler`: ADS.

A re-run of `install` resets all of these.

## Commands

```
P2=~/.local/state/ward-programme/showcase-phase2-20261120
$P2/seq.sh install rifle_hands-N AthenHill.Editor.RifleHandsPass20261120.RunBatch install,verify   # idempotent; undoes the previous install from previous.json first
$P2/seq.sh install rifle_hands-N AthenHill.Editor.RifleHandsPass20261120.RunBatch rollback         # clip-driven rifle and the old pistol mirror back
$P2/seq.sh install rifle_hands-N AthenHill.Editor.RifleHandsPass20261120.RunBatch dump --tag NAME  # OBJ per state (nographics)
$P2/blender.sh $PWD/art/rifle_hands_20261120/render_dump.py -- <evidence>/dump/NAME <evidence>/review/NAME [states]
DISPLAY=:0 WAYLAND_DISPLAY=wayland-1 ~/.local/state/ward-programme/unity.sh <log> AthenHill.Editor.RifleHandsPass20261120.RunBatch --steps capture --shots rifle|rifle_armour|pistol|pistol_armour|orbit --tag after
```

Rollback was tested (`rifle_hands-rollback1`, then reinstalled as `rifle_hands-12`). Against the pristine scene
(`before-rifle_hands-5`), all 23 YAML documents the pass touches are restored (`rollback_exactness.txt`), with three
exceptions. Each one is functionally equal, not byte-equal:

- The two new default fields on four SupportHandIKs.
- Redundant prefab overrides holding the source values on the rifle arms' bones.
- Explicit local bounds on the two pistol mirror copies, where the scene had empty dirty bounds before.

**Do not re-run `MainCharacterInstall` / `TutorialSetInstall` (→ `PlayerFace20261003.FirstPersonHands`) with this pass
installed.** Its `Unmount` only knows its own `Weapon mount`; run this pass's `rollback` first and `install` afterwards.

## Verification

- `verify.json` (install 12): pass.
  - Hands within 0.4 cm of their grip points in every state (hip, ADS, burst, ADS burst, walk, sprint); lowered is
    mid-draw and not asserted.
  - Wrist bend/twist in degrees, rifle: shooting hand 50/1 at the hip and 32/2 at ADS; support hand 29/19 at the hip
    and 22/21 at ADS. For comparison, the pistol's support hand twists 114 to 134.
  - Both right-elbow positions are behind the camera; the left elbow is below the frame.
  - Mirror copies are on the arms bones (rifle and pistol). No temporary colliders are left.
  - Reference values are unchanged since install (`reference.json`, 44 keys): pistol view model offsets/motion/IK/grips;
    rifle hip/holster offsets, motion, muzzle and pivot in the weapon frame, flash; held rifle/pistol mounts and
    muzzles; the held rifle's support grip; the body's grips, IK and `PlayerWeaponPose` settings.
- Scene YAML diff for each install (`scene_diff_install5.txt`, `scene_diff_install12.txt`): only the rifle view-model
  objects, the pistol mirror copies, and the default fields above.

## Evidence

All under `unity/evidence/showcase_phase2/20261120/rifle_hands/`:

- Review renders of the final geometry (Blender, `review/iter11/`):
  - FP frames per state: `rifle_{hip,ads,burst,ads_burst,walk,sprint,lowered}_fp[_armour].png` and the same for the pistol.
  - Orbit views of the hands: `rifle_hip_orbit_{shoot_right,shoot_front,shoot_left,support_left,support_under,support_right}.png`.
  - Sheets with rifle beside pistol: `review/rifle_vs_pistol_iter11.png`, `review/rifle_vs_pistol_armour_iter11.png`,
    `review/rifle_orbits_iter11.png`.
- Unity editor frames of the **old clip-driven** rifle (13:00, before): `captures/before/fp_rifle_*.png`.
  `captures/after_install5_superseded/` shows an early state (hand on the grip, old ADS); it is superseded.
- Logs: `install-trace.txt`, `config_candidates.txt`, `support_candidates.txt`, `verify.json`, `reference.json`,
  `report-result.txt`, `../install-rifle_hands-*.log`.

## Honest state and open defects

- **No game-shaded frames of the final state.** The Blender renders show placement and contact, not materials, light
  or TAA. The pending capture runs are listed in the report to the orchestrator.
- **The rifle is not yet "as good as the pistol" in frame.** The pistol is held up and centre-right, with both hands
  in full view. The rifle keeps its old hip framing (low right, `hipOffset` unchanged), so at the hip you see the left
  forearm and part of the support hand behind the receiver. The shooting hand is out of frame in every state: its grip
  is 47° below the view centre at ADS. The hands are now correct where they are; making them read in frame needs a hip
  re-framing (rifle higher and more centred, handguard visible), which changes the look of the hip pose and should be
  judged with Carl.
- Thumbs: both thumbs still overlap the rifle by a few millimetres (verify lists `thumb_02/03_r`, `thumb_01/02_l`).
  The right thumb lies along the right side pointing forward instead of wrapping over the top; the curl solver only
  bends about the joint's X axis, with no opposition. The right thumb is never in frame; the left thumb is on top of
  the barrel and visible at ADS.
- Support-hand ring and pinky close fully (270°) without touching the handguard: they hang under the barrel as a loose
  fist. They are hidden at the hip and visible from below only.
- The shooting wrist is bent about 50° at the hip; hand and forearm still line up from the camera's view.
- Lowered (mid-draw) poses bend the wrists up to 66°: the rifle drops away faster than the arms follow.
- The upper-arm cut of the arms mesh shows in orbit views only, never in first person.
- ADS change: the front sight now sits on the crosshair. Needs Carl's eye in play (it frames the rifle lower than before).

## Proposed text

### unity/EDITING.md, after the "Face, hair and first-person hands" paragraph

**First-person rifle hands (20 Nov 2026, `art/rifle_hands_20261120/README.md`).** The field rifle's view model is
weapon-driven like the pistol's.

- **Mount and anchors.** The rifle sits on `RH weapon mount`. The arms are at camera-space hip and aim anchors
  (`ViewModelArmsRig`: `aimAnchor`, `followWeapon 0.6`).
- **IK and grip points.** `RH right arm IK` and the arms' `SupportHandIK` (elbow `poleHint`, `twistShare 0.6`) hold
  `RH shooting grip` (palm on the pistol grip, 0.795 of the length from the muzzle) and `RH support grip` (under the
  front receiver, 28 cm ahead).
- **Fingers.** Solved against the rifle into the arms' `PlayerHandGrip.rifleRight/rifleLeft`.
- **ADS.** `aimOffset/aimEuler` come from the rifle's sights: rail level, front sight tip on the crosshair, butt
  1.5 cm behind the eye.
- **Pistol mirror fix.** The pass also re-skins the pistol's glove/arm-guard copies onto the pistol arms; they had been
  bound to its weapon mount.
- **Tuning and commands.** Tune with the static fields of `RifleHandsPass20261120` and re-run
  `RunBatch --steps install,verify`. `--steps rollback` restores the clip-driven rifle. `--steps dump` plus
  `art/rifle_hands_20261120/render_dump.py` gives Blender review renders without graphics-mode Unity.
- **Before re-running older installers.** Run `rollback` before re-running `MainCharacterInstall`/`TutorialSetInstall`,
  and `install` afterwards.

### AGENTS.md "Player" row, append

20 Nov 2026 (`art/rifle_hands_20261120`, `Editor/RifleHandsPass20261120.cs`): the first-person rifle view model is
weapon-driven like the pistol's.

- The shooting hand is on the pistol grip, not the magazine well (the old mount at 0.35 of the length from the butt
  was the magazine). The support hand is under the front receiver.
- Fingers are contact-solved, and 60 % of the wrist twist is spread into the forearm.
- ADS is taken from the rifle's sights: front sight tip on the crosshair, butt behind the eye.
- The pistol's glove/arm-guard copies are re-skinned onto its arms; they had been bound to its weapon mount.
- `verify` passes. Review is so far Blender renders of the posed geometry. Not natively tested and not accepted by Carl.
- Open: the rifle's hip framing still shows little of the hands; thumbs do not oppose.

## Provenance

No Meshy credits, no new assets. `FieldRifle.glb` and the MPFB arms (`TS_FPArms.glb`) are unchanged.

## Fix round (20 Nov 2026, 21:33 to 22:55)

Asked by the orchestrator after reviewing `rifle_vs_pistol_iter11.png`:

- The rifle was huge in the lower right and angled about 30° to the left of the view.
- The hands were barely in frame.
- The support hand was a fist beside the barrel.
- Lowered wrists bent up to 66°.
- Natives were needed. Editor graphics captures do not fit in memory.

Installed as `rifle_hands-25`; `verify` passes; scene diff `scene_diff_install25.txt` shows only this pass's objects.

**Hip re-framing** (`HipFromAim`, `HipWeapon`, `HipConverge`, `HipCant`)
- The weapon origin is at camera-space (0.17, −0.15, 0.56).
- The bore converges on the crosshair 12 m ahead; verify measures the bore crossing the view axis about 19 m out
  (`boreAtCrosshairM`).
- 6° cant.
- `hipOffset (0.13, −0.19, 0.40)` → `(0.17, −0.15, 0.56)`; `hipEuler (2, −4, −5)` → `(−3.83, −0.53, −6.01)`.
- The rifle points into the view instead of across it.
- The shooting hand's index knuckle is now on screen at hip: viewport (0.46, −0.82), and (0.50, −0.91) mid-burst.
  The support hand is at (0.35, −0.38).
- The nearest weapon point is 24 cm from the eye at the hip and 20 cm mid-burst.
- At ADS the butt is behind the eye, as before; ADS is unchanged from the first install.
- Muzzle point, flash, tracer origin and ballistics are untouched: they are child transforms of the weapon. The
  reference check (44 values) is unchanged, minus the hip key, which is now intended to change.
- Recoil and sway values are unchanged. The arms follow 60 % of the weapon's motion, so recoil still moves the arms.

**Arms** (searched jointly with both grips over 48 configurations: blade, shoulder x/y/z, aim depth, left elbow
direction)
- Chosen: blade 40°, mid-shoulder (0.07, −0.25, 0.06) at the hip and z −0.17 at ADS.
- Elbows below the frame are rewarded; an upper arm near the frame is penalised.

**Support hand**
- Station 0.53 of the length from the muzzle, at the front of the receiver/handguard just ahead of the magazine,
  24 cm ahead of the grip.
- Palm up, rolled 15° to the right; fingers forward-right round the right side.
- The search is now limited to palm-up grips: yaw 45–90°, roll 0–30°.
- Thumb along the left side: a new thumb opposition axis. The thumb's joints turn about whichever of the six local
  axes brings the tip towards a target point fastest (left side of the handguard for the support thumb; over the top
  of the grip for the shooting thumb).

**Lowered**
- `ViewModelArmsRig.drawFollow` (1.0): while the weapon is in the draw slide, the arms follow it rigidly, easing to
  `followWeapon` 0.6 as it comes up. Curve: smoothstep², via the new `FirstPersonViewModel.DrawBlend`.
- Lowered wrists are now 51° (shooting) and 43°/41 twist (support), down from 66° and 57°.

**Wrist and elbow, final state** (`verify.json`; swing/twist in degrees)

| State | Shooting hand | Support hand |
| --- | --- | --- |
| Hip | 47/2 | 37/40 |
| ADS | 42/3 | 46/47 |
| Burst | 48/2 | 40/40 |
| Walk / sprint | 46–47/2 | 36–38/40 |
| Lowered | 51/2 | 43/41 |

Hands are within 0.01 cm of their grips in every state.

**Runtime changes in this round**
- `ViewModelArmsRig.drawFollow` and `FollowFor`.
- `FirstPersonViewModel.DrawBlend`: a read-only getter.
- New test `DrawFollowHoldsTheArmsWhileLowered` in `RifleHandsTests.cs`.
- The pistol is unaffected: its `followWeapon` is 0.

**Review tooling**
- `render_soft.py` is a CPU z-buffer renderer of the OBJ dumps, with no GPU or Blender slot. It was used while the
  Blender slot waited for a running player.

Final sheets, grey shapes only, under `unity/evidence/showcase_phase2/20261120/rifle_hands/review/`:
- `rifle_vs_pistol_fix1.png`
- `rifle_vs_pistol_armour_fix1.png`
- frames in `review/fix1/*_soft.png`

**Native frames.** `unity/tools/capture_rifle_hands_native.py` (showcase_qa style, `ATHEN_EXE`/`ATHEN_OUT`):

- Continues the kit save twice: bare hands (gloves and arm guards moved to the pack) and wearing them.
- Stands at `rifle_stand` at 13:00 with the HUD hidden (`reviewHud`), in first person.
- Captures rifle and pistol hip, ADS (RMB held), burst (F held), walk (W), sprint (W + Shift_L) and lowered (shortly
  after the draw key).
- 24 PNGs at 1920×1080, with the `combat.rifleHands` read-out logged per frame.
- It has not been run by me: no build or native runs in this round.

**Still open after the fix round**
- At the hip the left elbow sits just below the frame (viewport y −1.15). The sleeve fabric around it shows at the
  bottom edge as a ragged shape in the grey renders. The search could not put the elbow lower without losing the
  support hand or bending the wrist more.
- The rifle still fills more of the frame than the pistol (it is a 0.9 m rifle) and the pistol shows both hands more
  fully. In the grey renders the rifle now reads as held: rifle into the view, support arm along the handguard, shooting
  knuckles at the bottom.
- The shooting thumb's base still overlaps the grip by a few mm (`thumb_01/02_r`), and so does the support thumb
  (`thumb_01/02_l`). It is not visible in first person.
- Support wrist twist is 40–47° with 60 % moved into the forearm.
- No game-shaded or native frames of the fix round yet; run `capture_rifle_hands_native.py` on the next build.

## Rebaseline step (20 Nov 2026, 01:00)

`--steps rebaseline [--keys k1,k2]` re-reads the reference values (the 44 values `verify` compares) from the saved
scene and writes them to `reference.json`.

- With `--keys`, only the named keys are taken over. Every other key that differs is logged as "KEPT (still differs)"
  and `verify` keeps failing on it.
- Log: `rebaseline.txt`. The old file is kept as `reference-before-rebaseline-*.json`.
- It saves nothing: the scene and prefabs are untouched.

Run on 20 Nov 01:03 (`rifle_hands-rebase`, `rebaseline,verify --keys body.pose`):

- **Only key that differed:** `body.pose`. The pistol carry pitch went 60 → 40, set deliberately by the character arms
  pass (`art/character_arms_20261120`).
- **Verify:** passes.
- **Scene:** the scene file is byte-identical before and after (`scene_diff_rebaseline.txt`).

A later pass that deliberately changes `PlayerWeaponPose` (or any other referenced value) needs
`RifleHandsPass20261120 --steps rebaseline --keys <key>` afterwards.
