# Character arms, 20 November 2026 (showcase phase 2)

Carl after playing `Builds/batch-playtest1119`: "All the character have their arms in very strange positions", narrowed
to "more the main character and not bad bad just in-natural and kinda camp", plus "the way he holds the pistol looks a
little janky too". This pass measures every character's arms in every clip, and adds a small runtime corrector that
pulls the arms into a natural envelope after the clips sample. The player colonist and his third-person pistol got most
of the work; the other characters get the same corrector with a shared profile.

Status: authored, installed into the saved scene with `-nographics`, `verify` run (see the end). Not natively tested and
not seen by Carl. Every visual judgement below comes from a CPU point-splat render of the posed skinned meshes
(`splat_sheets.py`), not from the game's renderer.

## What was wrong (measured, before)

Measured by `CharacterArmsPass20261120 --steps survey` (24 samples per clip, both arms, in the chest's bind frame).
Full tables: `unity/evidence/showcase_phase2/20261120/character_arms/r2/survey.md` (`survey.json` for numbers).
Definitions: *arm out* = upper arm lean out of the body's sagittal plane; *elbow out* = how far the forearm bends across
the body (0 = it bends toward the front of the upper arm; +-180 = backward); *palm* = 0 palm to the thigh, + palm turned
back; *wrist* = total wrist bend; *shoulder lift* = shoulder joint height over its bind height, relative to the chest;
*hand out* = the hand's lateral distance outside the hip joint.

Player colonist (MPFB body, clips baked into `colonist.glb`):

- Idle: arms held 10-14 degrees out with the elbows locked straight (flex 0-11; slight hyperextension, the bend direction
  points backward), wrists bent 21-30 degrees, hands 19-21 cm outside the hip joints, fingers flat and spread (index to
  pinky 29 degrees, held there by `PlayerHandGrip` resetting the fingers to the rest pose every frame). This is the
  mannequin look.
- Walk: arms out 12-27 degrees, elbows turned out (+17..50), palms turned back (18..51), wrists up to 42 degrees.
  Swing is in phase with the opposite leg (correlation 0.90) with a 46-47 degree range: the timing is fine.
- Run: arms out up to 35 degrees, wrists up to 51 degrees.
- Shoulders: 4-6 cm above the bind height in every clip (a mild shrug).
- Talking: the player plays idle while a dialogue is open (no talk clip), so it is the idle above, seen from behind in
  every conversation shot.
- Jumps: arms 11-33 out, elbows bending backward in several frames (old metric; see r2 for the corrected metric).

Player pistol, third person (`PlayerWeaponPose`, `PlayerHandGrip` on the body):

- Lowered carry: the pistol is turned 49-101 degrees *inside the hand* away from its gripped mount to point 60 degrees
  down (`carryPitch`), so the grip leaves the palm and the gun hangs beside the fist. The support (left) hand closes into
  the pistol's support-grip shape round nothing while the pistol is lowered (it was blended in whenever armed).
- Raised: the "Walk Forward While Shooting" hold brings the pistol up to the face with both forearms near vertical
  (hand height 155-160 cm, upper arm 66 degrees forward, elbow 48), and the support hand's curled fingers stand up beside
  the gun instead of round the grip: it reads like holding binoculars.
- Transitions: `PlayerWeaponPose` eases the hold weight (SmoothDamp, 0.06 s up, 0.125 s down) and the grips blend over
  0.15 s; no snapping found in code. The carry turn is weighted by (1 - raise), so the pistol turns in the hand while it
  rises: with the old 60-88 degree in-hand turn that is a visible spin.

Meshy NPCs and walkers (24-bone Meshy rigs, library clips; Brann and the three residents have finger bones):

- Idle: arms 12-27 degrees out (Brann 27, Tamsin and the walkers up to 24), straight elbows (several with the bend
  pointing backward: Linn -127, Mira up to 176), palms turned back 22-38 degrees, wrists 12-23, shoulders 6-12 cm over
  bind (Torr 12).
- Talk: Torr arms out to 38, palms back up to 128; Linn arms out 33 and palms up to 156 (palm out, a shrug); Brann arms
  out 26-40 with a reach (forward 33, elbow nearly straight) toward the listener; Vex's elbows turned out up to 48 (the
  "gunslinger"); Mira arms out to 40 with wrists 40.
- Walk/run: swing timing in phase (correlation 0.85-0.98); arms out 12-27 while walking.
- The yard mechanic (Humanoid Animator) and Wardens Ossa/Rell (two instances each, the gate post and the Berms copy) are
  in the same range.

Nothing here was a regression: the clips and rest poses are unchanged since early October (the brief's comparison holds).

## Causes

- Meshy library clips retargeted onto bulky clothed meshes hold the arms clear of the body (arm out 12-27 degrees idle).
- The MPFB rest-match (`finish_body.py`) matched limb directions to the Meshy rig, so the player inherited the same
  held-out arms; the retargeted gait keeps straight elbows and turned-out forearms.
- No finger animation reaches the player's hand: `PlayerHandGrip` writes the relaxed rest pose (flat, 29 degree spread)
  every frame when unarmed.
- The pistol carry turns the gun inside the hand instead of the wrist taking part of the turn; the hold clip is a
  close-to-the-face hold; the support hand's solved grip only fits that hold.
- Brann's "reach" and Linn's shrug are the talk clips themselves, not something freezing during dialogue (`NpcAgent`
  plays the talk clip on loop; `ActorAnimation` gives it a per-actor phase and rate; nothing stops it).

## Method and why

A runtime corrector, not baked clips:

- One mechanism covers 18 actors on four kinds of rig (MPFB player, Meshy 24-bone, Meshy with fingers, Humanoid
  Animator) and new residents by re-running `install`, with no new assets; `colonist.glb` stays untouched (another agent
  owns it tonight).
- The player's arms must work with the pistol in the hand, the conversation look-at and the face-speaker turn, which are
  all runtime layers; a corrector in the same frame composes with them by execution order.
- Cost: a few dozen transform reads/writes per visible actor per frame, skipped off-screen and beyond 45 m.

`Scripts/ArmPose/ArmPoseCorrector.cs` (order -20, after the Animation samples, before `PlayerWeaponPose`,
`PlayerHandGrip`, `ActorLookAt` at 0, `ViewModelArmsRig` 450 and `SupportHandIK` 500):

1. Collarbone: the shoulder joint is lowered to `shoulderLiftMax` over its bind height.
2. Upper arm: lean out of the body pulled toward `abductionTarget` by `abductionPull` (never closer than
   `abductionMin`, never pushed out), forward reach soft-limited at `forwardMax`.
3. Elbow turn-out: the upper arm twists about its own axis toward `elbowOutTarget` (only once the elbow is bent 10-30
   degrees, where it shows).
4. Elbow bend clamped to `elbowFlexMin..elbowFlexMax`, always toward the front of the arm (a backward-bending elbow is
   measured from straight). 4b: a hand more than `handReachMax` ahead of the shoulder swings down about the shoulder.
5. Forearm twist toward `palmTarget` (palm to the thigh), split between the forearm and the hand by `twistOnForearm`
   (no twist bones).
6. Wrist bend scaled by `wristKeep` and capped at `wristMaxBend`.

`ArmPoseFingerPass` (added at runtime, order 20, after `PlayerHandGrip`): a relaxed curl toward the palm
(`fingerCurl`, `thumbCurl`) and the finger spread drawn in toward the middle finger (`spreadPull`), weighted by
(1 - the grip weight on that hand); then, for the player with the pistol raised, the two-handed aim (below).

Five state profiles (idle, walk, run, talk, air) blend by the actor's current clip over `blendSeconds`. An
accumulation guard puts back any bone that nobody re-posed since the corrector's last write (clips without finger
curves cannot make the curl creep).

Player weapon behaviour:

- Pistol lowered: the arm correction stays on (both arms), so the carry swings like the unarmed walk; the support hand
  stays relaxed (`PlayerHandGrip.weaponPose` + `relaxSupportWhenLowered`, new, additive) and closes as the pistol rises.
- Pistol carry: `PlayerWeaponPose.carryPitch` 60 -> 40, and the wrist now takes up to 30 degrees of the carry turn
  (`carryWristShare` 0.8, `carryWristMax` 30, new fields; 0 = the old behaviour), so less of the turn happens inside the
  hand.
- Pistol raised: the arm correction hands over to the hold clip by `PlayerWeaponPose.Weight`; then a two-bone IK
  (`pistolAimWeight` 1, `pistolAimReach` 0.44 m, `pistolAimHeight` 0.08 m, `pistolAimSide` 0.02 m, `aimElbowPole`)
  extends both arms so the pistol sits ahead of the shoulders on the aim line (barrel rotation from `PlayerWeaponPose`
  kept), the support hand cupping the shooting hand (`supportOffset`). The body's `PlayerHandGrip.pistolLeft` was
  already empty (procedural curl), so `playerGrip` in the json changes nothing today; the support fingers are still the
  procedural curl, now closing round the shooting hand instead of standing beside the gun at the face.
- Rifle drawn: the corrector fades out for both arms (the rifle carry/hold clips and `SupportHandIK` own them); the rifle
  hold is in the survey only.

## Values and where to tune them

All values live in `art/character_arms_20261120/characters.json` and are written into the components by `install`
(re-running `install` overwrites Inspector edits, so tune the json, or tune in the Inspector and copy back):

- `profiles.meshy` (every NPC, walker, resident and the mechanic) and `profiles.player`: `all` then per state.
- `characters[]`: regex on the actor key (`player`, the NpcAgent / AmbientWalker object name) -> `label`, `profile`,
  `overrides` (same shape as a profile, plus `weight` and `corrector` for component fields such as the aim IK).
- `playerWeapon`: fields on the player's `PlayerWeaponPose`; `playerGrip`: fields on the body's `PlayerHandGrip`.
  The originals are kept in `player_weapon_original.json` on the first install, for rollback.

In the Inspector: the `Arm Pose Corrector` on each actor (the ActorAnimation object): `weight` (0 turns it off for that
actor), the five profiles, the pistol aim block on the player.

## Adding a character

Put the actor in the scene with an `ActorAnimation` (legacy Animation or Humanoid Animator) and run `install` again. Bones
are found by name (`LeftShoulder/LeftArm/LeftForeArm/LeftHand` and `clavicle_l/upperarm_l/lowerarm_l/hand_l`; fingers
`index_01_l` or `LeftHandIndex1` / `mixamorig:` names) or through the Humanoid avatar. It gets `profiles.meshy` unless a
`characters[]` entry says otherwise. Check it with `survey` and `dump` (both read-only). The three residents (Nadje,
Pell, Oren) were already in the scene when this pass ran and are covered.

## Commands

    P2=~/.local/state/ward-programme/showcase-phase2-20261120
    $P2/run.sh ca $P2/seq.sh install character_arms-N AthenHill.Editor.CharacterArmsPass20261120.RunBatch install,verify; $P2/wait.sh ca
    # read-only: survey (tables) and dump (OBJ per actor/pose/before-after), --only <regex on the key>, --tag <folder>
    ... RunBatch survey,dump --tag r2 [--only '^player$']
    # rollback: removes the correctors and the review cameras, restores PlayerWeaponPose / PlayerHandGrip values
    ... RunBatch rollback,verify     (verify then reports FAIL: no correctors)
    # review sheets without the GPU (numpy point splats; front/threequarter/back/side views, crops)
    ~/.local/state/ward-programme/heavy.sh python3 art/character_arms_20261120/splat_sheets.py DUMP OUT [actor_regex] [views] [px_per_m]
    ~/.local/state/ward-programme/heavy.sh python3 art/character_arms_20261120/splat_sheets.py --crop DUMP OUT actor pose_regex view cx,cy size px
    python3 art/character_arms_20261120/summary_table.py unity/evidence/showcase_phase2/20261120/character_arms/r2/survey.json

`render_sheets.py` is the Blender (Cycles CPU) version of the sheets; it waits on the shared Blender slot, which is held
while Carl's game runs, so the point-splat renderer was used tonight.

Review cameras (root **Character arms review cameras**; positions in `review_cameras.json`): `cam_arms_<label>` full
body, front three-quarter, 3.4 m out, 1.6 m high, for every actor (walkers at their saved start point);
`cam_arms_talk_<label>` a conversation-like framing 2 m in front of each talking colonist. Riding review rigs
`Arms review rig [front|right|left|frontright|frontleft|behind|backright]` (inactive; `Scripts/ArmPose/ArmsReviewRig.cs`,
development builds only): switched on with NativeQa `setActive`, the main camera rides with the colonist at 3.4 m with a
40 degree lens (full body about 70 % of 1080p), while movement, facing and the aim line follow a steering proxy fixed at
the follow camera's heading, so W still walks straight and aiming does not turn him toward the review camera.

Native capture script (the orchestrator runs it): `unity/tools/capture_character_arms_native.py`. Conversations: the
real conversation camera, a frame every 0.5 s for 6 s (8 colonists + residents via landmarks `res_<name>`). Player, HUD
hidden, open apron at `west_gate` heading west: idle front / front-right / right / behind; walk and run from the right,
front-right and behind; a turn from the front. Pistol at `checkpoint_firingline`: draw (right), carry idle (right,
front-right, front, behind), carry walk and run (right, front-right), aim (right, front-right, front), aim walking
(right), fire and lower after the shot (right, front-right), holster (right), plus one gameplay over-the-shoulder aim
frame with the HUD. Walkers: frames while each is within 7 m of its review camera's target.

## Evidence

`unity/evidence/showcase_phase2/20261120/character_arms/`:

- `before/`, `r1/`, `r2/`: survey tables per run (`before` is the first, buggy corrector; its "before" rows are valid).
- `dump/<tag>/`: OBJ per actor, pose, before/after (git-ignored size: about 200 MB per full run).
- `sheets/<tag>/<actor>__<view>.png`: top row before, bottom row after; `sheets/<tag>/crops/`: close-ups.
- `verify.json`, `*-result.txt`.

## Proposed text

For `unity/EDITING.md` (after "Player shoulder and clothing polish"):

> ### Character arms (20 November 2026)
>
> `art/character_arms_20261120/README.md`. Every actor with an `ActorAnimation` carries an `Arm Pose Corrector`
> (`Scripts/ArmPose/`, LateUpdate order -20, fingers and the player's two-handed pistol aim at order 20 in
> `ArmPoseFingerPass`, added at runtime). It pulls the clip's arms into a natural envelope per state (idle, walk, run,
> talk, air): collarbone lift, arm lean out of the body, forward reach, elbow turn-out and bend, forearm twist, wrist
> bend, finger curl. Values come from `art/character_arms_20261120/characters.json` (profiles `meshy` and `player`,
> per-character overrides, the player's `PlayerWeaponPose`/`PlayerHandGrip` values) and are written by
> `CharacterArmsPass20261120.RunBatch --steps install,verify`; re-run it after adding a character (it overwrites
> Inspector edits: tune the json). `--steps survey,dump` measure and dump poses without saving; `rollback` removes it.
> `weight` 0 on a corrector turns it off for that actor; the clips themselves are unchanged.

For `AGENTS.md` section 3 (a new row):

> | Character arms | 20 Nov 2026 (`art/character_arms_20261120`, `Editor/CharacterArmsPass20261120.cs`, runtime
> `Scripts/ArmPose/`): Carl's playtest note (arms "in-natural and kinda camp", pistol hold "janky"). A runtime
> `ArmPoseCorrector` on all 18 humanoid actors (player, Mira, Torr, Vex, Linn, Brann, Tamsin, Ossa and Rell at both
> posts, the three walkers, the yard mechanic, Nadje, Pell, Oren) pulls the clip arms in (idle lean out 10-34 degrees
> down to about 5-8, straight locked elbows to a slight bend, palms to the thighs, wrists straighter, collarbones down,
> talk reaches limited), and relaxes the player's fingers. Pistol: carry pitch 60 -> 40 with the wrist taking up to 30
> degrees (the gun no longer turns 60-90 degrees inside the hand), support hand relaxed while lowered, a two-handed
> extended aim by IK instead of the hold clip's at-the-face pose. Values in `characters.json`; `--steps rollback`.
> Measured with -nographics surveys and point-splat renders; not natively tested or accepted by Carl. |

## Measurements after (final install, run r5)

Means with the maximum in brackets, before -> after, both arms pooled (degrees; cm for shoulder lift and hand out).
From `r5/survey.json` (`summary_table.py`); the Wardens' second rows are their Berms copies.

| character | clip | arm out | reach fwd | elbow bend | elbow out | palm | wrist | shoulder lift cm | hand out cm |
|---|---|---|---|---|---|---|---|---|---|
| linn | idle | 12 (14) → 8 (8) | -10 (-7) → -10 (-7) | 6 (14) → 10 (10) | -127 (-121) → -13 (0) | 26 (50) → 17 (28) | 6 (11) → 2 (4) | 6 (7) → 3 (3) | 17 (17) → 12 (14) |
| linn | talk | 18 (33) → 12 (16) | -33 (-4) → -33 (-4) | 94 (135) → 94 (135) | -23 (5) → -8 (18) | 70 (156) → 38 (91) | 20 (42) → 12 (25) | 6 (8) → 3 (3) | 18 (36) → 13 (24) |
| mira | idle | 12 (15) → 8 (8) | -1 (2) → -1 (2) | 4 (12) → 10 (12) | 119 (176) → 1 (14) | 22 (32) → 12 (15) | 23 (30) → 9 (12) | 9 (10) → 3 (3) | 17 (20) → 14 (17) |
| mira | talk | 14 (40) → 11 (17) | 16 (31) → 16 (27) | 26 (78) → 31 (78) | -4 (51) → 3 (35) | 6 (52) → -3 (30) | 26 (40) → 16 (24) | 4 (8) → 3 (3) | 18 (29) → 16 (20) |
| torr | idle | 14 (19) → 8 (9) | -7 (2) → -7 (2) | 2 (4) → 10 (10) | - | 30 (42) → 16 (18) | 22 (26) → 9 (10) | 12 (14) → 3 (3) | 22 (28) → 18 (21) |
| torr | talk | 28 (38) → 15 (17) | -10 (33) → -11 (27) | 74 (97) → 76 (97) | 11 (38) → 9 (23) | 87 (128) → 46 (67) | 27 (49) → 16 (30) | 8 (10) → 3 (3) | 21 (34) → 15 (26) |
| vex | idle | 15 (19) → 8 (9) | 2 (5) → 2 (5) | 3 (6) → 10 (10) | - | 38 (48) → 18 (21) | 12 (15) → 5 (6) | 9 (11) → 3 (3) | 22 (24) → 17 (18) |
| vex | talk | 15 (29) → 11 (15) | 17 (48) → 14 (31) | 19 (89) → 26 (89) | 23 (48) → 6 (26) | 5 (49) → -3 (27) | 20 (32) → 12 (20) | 2 (5) → 1 (3) | 19 (23) → 17 (19) |
| walker_01 | idle | 18 (24) → 9 (10) | 14 (30) → 14 (30) | 12 (23) → 16 (23) | 49 (49) → 26 (26) | 28 (40) → 12 (13) | 22 (26) → 9 (10) | 9 (9) → 3 (3) | 20 (22) → 15 (15) |
| walker_01 | walk | 17 (27) → 10 (13) | 13 (35) → 13 (35) | 6 (23) → 13 (23) | 42 (50) → 8 (41) | 25 (40) → 13 (20) | 15 (28) → 8 (14) | 9 (11) → 3 (3) | 21 (25) → 17 (22) |
| walker_02 | idle | 18 (24) → 9 (10) | 14 (30) → 14 (30) | 12 (23) → 16 (23) | 49 (49) → 12 (25) | 33 (46) → 14 (14) | 20 (27) → 8 (11) | 8 (8) → 3 (3) | 19 (21) → 14 (14) |
| walker_02 | walk | 17 (27) → 10 (13) | 13 (35) → 13 (35) | 6 (23) → 13 (23) | 42 (50) → 8 (40) | 30 (46) → 15 (22) | 13 (27) → 7 (14) | 8 (10) → 3 (3) | 20 (25) → 16 (21) |
| walker_03 | idle | 14 (16) → 8 (8) | 1 (17) → 1 (17) | 12 (18) → 14 (18) | 6 (6) → 4 (4) | 33 (33) → 15 (15) | 26 (29) → 10 (12) | 6 (6) → 3 (3) | 22 (24) → 17 (20) |
| walker_03 | walk | 13 (18) → 9 (10) | 3 (18) → 3 (18) | 7 (17) → 13 (17) | 6 (7) → 0 (4) | 30 (41) → 17 (18) | 24 (30) → 12 (15) | 6 (7) → 3 (3) | 22 (25) → 18 (22) |
| tamsin | idle | 34 (63) → 11 (16) | 5 (55) → 4 (22) | 37 (79) → 37 (79) | -24 (51) → -17 (10) | 39 (77) → 15 (23) | 28 (49) → 11 (18) | 12 (14) → 3 (3) | 41 (46) → 26 (33) |
| tamsin | talk | 29 (37) → 15 (17) | -6 (37) → -7 (28) | 74 (97) → 76 (97) | 12 (38) → 8 (22) | 57 (101) → 28 (52) | 15 (29) → 9 (17) | 9 (10) → 3 (3) | 22 (36) → 16 (27) |
| yard_mechanic | walk | 31 (43) → 14 (17) | -9 (15) → -9 (15) | 24 (60) → 25 (60) | -1 (32) → -4 (19) | 41 (61) → 19 (23) | 12 (22) → 6 (11) | -4 (-4) → -4 (-4) | 26 (31) → 15 (17) |
| yard_mechanic | run | 30 (44) → 19 (25) | -36 (15) → -36 (15) | 93 (124) → 93 (124) | -16 (-1) → -13 (0) | 22 (47) → 8 (22) | 18 (38) → 9 (19) | -1 (0) → -1 (0) | 22 (31) → 18 (27) |
| Ossa | idle | 19 (22) → 9 (9) | -14 (-9) → -14 (-9) | 18 (21) → 18 (21) | -17 (-1) → -4 (10) | 58 (88) → 28 (37) | 17 (21) → 7 (8) | 17 (19) → 2 (2) | 33 (35) → 19 (21) |
| Ossa | walk | 7 (7) → 7 (7) | 1 (1) → 1 (1) | 7 (7) → 12 (12) | - | 19 (20) → 14 (14) | 0 (0) → 0 (0) | 8 (9) → 3 (3) | 15 (15) → 12 (13) |
| Ossa | run | 7 (7) → 7 (7) | 1 (1) → 1 (1) | 7 (7) → 30 (30) | - | 19 (20) → 14 (14) | 0 (0) → 0 (0) | 8 (9) → 3 (3) | 15 (15) → 8 (8) |
| Ossa | talk | 15 (50) → 10 (20) | -0 (16) → -0 (16) | 45 (95) → 45 (95) | -16 (33) → -11 (20) | 20 (85) → 10 (48) | 11 (23) → 7 (14) | 8 (15) → 3 (3) | 30 (42) → 23 (29) |
| Ossa_2 | idle | 15 (19) → 8 (9) | 2 (5) → 2 (5) | 3 (6) → 10 (10) | - | 41 (52) → 20 (24) | 18 (22) → 7 (9) | 9 (11) → 3 (3) | 21 (22) → 16 (17) |
| Ossa_2 | talk | 14 (39) → 11 (17) | 16 (32) → 16 (27) | 26 (78) → 31 (78) | -4 (51) → 4 (35) | 4 (50) → -3 (30) | 20 (38) → 12 (23) | 2 (7) → 2 (3) | 19 (29) → 17 (21) |
| Rell | idle | 18 (21) → 9 (9) | -16 (-13) → -16 (-13) | 19 (24) → 19 (24) | -8 (0) → 6 (12) | 42 (65) → 23 (29) | 10 (13) → 4 (5) | 16 (17) → 2 (2) | 30 (31) → 17 (20) |
| Rell | walk | 7 (7) → 7 (7) | 1 (1) → 1 (1) | 7 (7) → 12 (12) | - | 19 (20) → 14 (14) | 0 (0) → 0 (0) | 8 (9) → 3 (3) | 15 (15) → 12 (13) |
| Rell | run | 7 (7) → 7 (7) | 1 (1) → 1 (1) | 7 (7) → 30 (30) | - | 19 (20) → 14 (14) | 0 (0) → 0 (0) | 8 (9) → 3 (3) | 15 (15) → 8 (8) |
| Rell | talk | 18 (41) → 12 (18) | -2 (32) → -4 (18) | 38 (105) → 38 (105) | -11 (32) → -10 (20) | 25 (87) → 13 (53) | 7 (27) → 4 (16) | 8 (12) → 3 (3) | 29 (35) → 23 (28) |
| Rell_2 | idle | 12 (14) → 8 (8) | 0 (3) → 0 (3) | 3 (11) → 10 (10) | -150 (-150) → 0 (0) | 23 (25) → 14 (16) | 22 (24) → 9 (10) | 9 (10) → 3 (3) | 22 (23) → 18 (21) |
| Rell_2 | talk | 15 (30) → 11 (15) | 16 (48) → 13 (29) | 19 (89) → 26 (89) | 24 (48) → 6 (26) | 9 (52) → -0 (29) | 20 (30) → 12 (18) | 2 (5) → 2 (3) | 21 (25) → 19 (22) |
| player | idle | 12 (14) → 6 (7) | -2 (1) → -2 (1) | 3 (11) → 12 (12) | -150 (-150) → 0 (0) | -2 (3) → 4 (10) | 26 (30) → 9 (11) | 5 (6) → 2 (2) | 20 (21) → 14 (15) |
| player | walk | 19 (27) → 10 (12) | 3 (25) → 3 (25) | 22 (58) → 24 (58) | 35 (50) → 22 (35) | 34 (51) → 14 (18) | 20 (42) → 8 (17) | 5 (6) → 2 (2) | 20 (24) → 13 (16) |
| player | run | 26 (35) → 17 (20) | -23 (34) → -23 (34) | 94 (119) → 94 (119) | 7 (24) → 10 (17) | 17 (41) → 8 (19) | 31 (51) → 12 (20) | 5 (6) → 2 (2) | 17 (28) → 12 (17) |
| brann | idle | 27 (28) → 10 (10) | -1 (1) → -1 (1) | 17 (18) → 17 (18) | 16 (17) → 15 (15) | 10 (11) → 3 (4) | 11 (12) → 4 (5) | 0 (0) → 0 (0) | 30 (31) → 16 (16) |
| brann | walk | 19 (28) → 11 (13) | 11 (34) → 11 (34) | 22 (58) → 23 (58) | 36 (50) → 24 (36) | 46 (62) → 21 (26) | 13 (24) → 6 (12) | -2 (-2) → -2 (-2) | 19 (24) → 14 (16) |
| brann | run | 27 (36) → 18 (22) | -16 (42) → -16 (42) | 93 (122) → 93 (122) | 7 (24) → 7 (19) | 27 (49) → 13 (25) | 17 (31) → 8 (16) | 1 (3) → 1 (3) | 19 (31) → 15 (23) |
| brann | talk | 30 (40) → 15 (18) | 7 (33) → 6 (27) | 28 (67) → 28 (67) | 6 (17) → 7 (16) | 12 (27) → 1 (4) | 15 (36) → 9 (22) | 0 (0) → 0 (0) | 32 (43) → 21 (28) |
| resident_nadje | idle | 24 (44) → 10 (12) | 15 (51) → 12 (36) | 49 (114) → 49 (114) | 11 (62) → 6 (45) | 28 (74) → 3 (25) | 19 (57) → 7 (18) | 2 (6) → 2 (3) | 16 (22) → 8 (14) |
| resident_nadje | walk | 21 (30) → 11 (14) | 6 (28) → 6 (28) | 18 (38) → 19 (38) | 29 (48) → 23 (38) | 29 (45) → 15 (20) | 13 (25) → 6 (12) | 1 (3) → 1 (3) | 17 (23) → 10 (12) |
| resident_nadje | talk | 16 (38) → 11 (17) | 37 (61) → 27 (34) | 23 (101) → 25 (101) | 16 (51) → 10 (36) | -40 (-1) → -42 (-4) | 13 (40) → 8 (24) | -3 (-1) → -3 (-1) | 12 (18) → 9 (16) |
| resident_oren | idle | 24 (47) → 10 (13) | -37 (34) → -37 (31) | 49 (114) → 49 (114) | 12 (66) → 8 (40) | 30 (74) → 4 (26) | 20 (59) → 8 (18) | -1 (2) → -1 (2) | 20 (27) → 12 (21) |
| resident_oren | walk | 21 (40) → 11 (16) | -27 (-4) → -27 (-4) | 18 (38) → 19 (38) | 29 (52) → 23 (42) | -19 (16) → -23 (3) | 12 (25) → 6 (12) | -1 (0) → -1 (0) | 21 (31) → 13 (25) |
| resident_oren | talk | 22 (36) → 13 (17) | 8 (56) → 5 (33) | 60 (130) → 61 (130) | 23 (39) → 16 (22) | -52 (-34) → -54 (-35) | 17 (33) → 10 (20) | 2 (3) → 2 (3) | 12 (20) → 10 (16) |
| resident_pell | idle | 24 (39) → 10 (12) | -4 (53) → -7 (28) | 49 (114) → 49 (114) | 9 (55) → 6 (25) | 22 (75) → 0 (25) | 21 (63) → 8 (18) | 2 (5) → 1 (3) | 24 (34) → 15 (26) |
| resident_pell | walk | 21 (32) → 11 (14) | 9 (30) → 9 (30) | 18 (38) → 19 (38) | 29 (48) → 22 (38) | -22 (0) → -27 (-8) | 12 (24) → 6 (12) | 2 (4) → 2 (3) | 24 (30) → 16 (19) |
| resident_pell | talk | 17 (34) → 12 (16) | 17 (53) → 14 (30) | 23 (101) → 25 (101) | 16 (45) → 11 (30) | -44 (-11) → -43 (-12) | 12 (34) → 8 (20) | -4 (-4) → -4 (-4) | 20 (28) → 16 (26) |


### Walk and run swing (orchestrator's question, 23:40)

The corrector moves the average pose and keeps the motion. Per cycle, before -> after (upper-arm fore-aft swing in the
sagittal plane, hand fore-aft travel relative to the shoulder, elbow bend range):

| character | clip | upper-arm swing L/R deg | hand fore-aft L/R cm | elbow bend L / R deg |
|---|---|---|---|---|
| player | walk | 47/46 -> 44/42 | 47/41 -> 47/41 | 4..58 / 9..34 -> 15..58 / 15..34 |
| player | run | 122/92 -> 99/83 | 52/44 -> 49/42 | 72..116 / 80..119 -> unchanged |
| Brann | walk | 48/46 -> 44/42 | 42/36 -> 41/37 | 4..58 / 9..35 -> 12..58 / 12..35 |
| Brann | run | 125/96 -> 105/87 | 47/42 -> 44/40 | 70..118 / 79..122 -> unchanged |
| Daro (walker 01) | walk | 45/42 -> 42/38 | 37/28 -> 31/25 | 1..23 / 0..19 -> 12..23 / 12..19 |
| Sel (walker 02) | walk | 45/42 -> 42/38 | 40/31 -> 34/26 | 1..23 / 0..19 -> 12..23 / 12..19 |
| Anso (walker 03) | walk | 37/37 -> 36/36 | 37/37 -> 32/32 | 0..17 / 1..17 -> 12..17 / 12..17 |
| yard mechanic | walk | 52/53 -> 47/45 | 43/36 -> 43/36 | 9..60 / 12..36 -> 12..60 / 12..36 |
| Nadje / Oren / Pell | walk | 47/42, 51/39, 47/41 -> 43/38, 46/39, 42/37 | 40/34, 39/34, 43/34 -> 40/34, 42/36, 42/35 | min 9 -> 12 |

So the walk keeps its swing (hand travel unchanged for the player, 47/41 cm) and the run keeps its pumping elbows
(72-119 degrees, untouched; the run profile's minimum is 45). The upper-arm angle range drops a little because the arm no
longer swings out sideways as it swings forward. Swing timing: in phase with the opposite leg (correlation 0.90 walk,
0.93 run for the player). From the front a 45 cm fore-aft swing is nearly invisible, which is why the b3 front frames
looked pinned; the capture script now films walk and run from the right and the front-right (riding rigs). Wardens
Ossa and Rell have no walk clip (their walk/run slots are the idle).

## What I looked at with my own eyes

Point-splat renders (shape only, no game shading) of the posed skinned meshes from the `dump` step:

- Player, all 13 poses (idle, walk 0/25/50 %, run 0/25 %, pistol carry idle/walk/run, half raise, aim idle/walk), front,
  three-quarter and back, before and after (`sheets/r3`, `sheets/r4`), plus close crops of idle (front, side, back),
  walk (front), pistol carry and pistol aim (front, three-quarter, side) in `sheets/p1/crops`, `p2/crops`, `r2/crops`.
  After: arms hang by the sides with a slight elbow bend, hands at the thighs with loosely curled fingers, shoulders
  lower; from behind (the conversation view) the arms no longer flare. The aim is now an extended two-handed hold at
  chest-to-chin height instead of the pistol at the face.
- Brann (three-quarter sheet and talk crops): the talk reach comes down and bends at the elbow (still a forward gesture).
- Linn, Vex (three-quarter sheets): idle closer; Linn's wide shrug (talk 45-75 %) is narrower but still a shrug.
- The other actors' sheets were rendered (`sheets/r4/*`) and glanced at, not studied pose by pose.
- The orchestrator's native frames from build b3 (character_arms-5) were described to me, not seen by me.

## Still wrong / not done

- Not natively verified on the final install (-8). Build b3 had install -5 (before the working-idle and forearm fixes).
- First-person pistol (not mine, the rifle agent's files): in the rifle agent's own review renders
  (`rifle_hands/review/fixL/pistol_ads_fp_soft.png`) the support hand's fingers stand flat and upright beside the grip
  instead of wrapping it, and the hip hold is canted with a bent wrist. It needs work by whoever owns the view models.
- Pistol carry: the gun still turns 30-60 degrees inside the hand (turnInHand idle 59, walk 19-72) because the gripped
  mount points well off the carry line in a hanging hand; the wrist takes 30 more degrees than before. A real fix is a
  carry hand pose (wrist and forearm) or a carry clip; the current one is better, not right.
- Aim: the support hand is placed by offset and orientation, with the generic procedural finger curl; there is no
  contact solve against the gun, so fingers may intersect or float by a centimetre or two. The aim walk keeps the hold
  clip's torso.
- Talk gestures keep their character: Linn still shrugs, Brann still gestures forward, Torr and Tamsin still lift their
  palms (palm up to 52-68 degrees back). These are now within the envelope rather than removed.
- Residents' and Tamsin's idles are working motions with raised arms (elbow up to 114); the corrector limits the lean but
  the raised-arm moments remain.
- Elbows that bent backward in near-straight idles (Linn -127, Mira up to 176, player jumps) now bend forward a little;
  nothing measured was past a joint's range otherwise (no wrist over 65 degrees after, palm-out only in Linn's talk).
- No Meshy credits used and no new clips; a natural relaxed idle, a male walk with looser arms, and a pistol low-ready
  carry clip for the player would be the next step if the corrected clips are still not right (ask before spending).
- The `before/` survey's "after" rows came from a buggy first corrector; use r4/r5.

## Verify

`verify.json` (install character_arms-8, 23:36): PASS, 19 actors (18 humanoid correctors bound, prefab links intact, no
missing scripts; the Berms mining droid has an ActorAnimation but no arm bones and is skipped), 29 review cameras,
7 riding rigs, all inactive; every idle sample's arm lean within 2 degrees of its profile.
