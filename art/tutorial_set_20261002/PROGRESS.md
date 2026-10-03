# Tutorial set and MPFB2 player body (started 2 Oct 2026)

Carl's request (2 Oct, evening):
> "create the jumpsuit we talked about and retrofit the armour and create a full set. this will be the tutorial set.
> I am not sure I [like] wood though this is a sci-fi. it can be basic but not minecraft basic. scrap salvaged metal will do."

Clarification: "I wanted you to use mpfb2". The player becomes an MPFB2 base human, a near-naked body with the
jumpsuit and armour layered on one skeleton. Downloads approved: MPFB 2.0.17 and makehuman_system_assets (CC0).
Rig choice: **MPFB game rig with fingers**.

## Decisions
- **Skeleton:** MPFB `game_engine` rig (53 bones, fingers). The 22 body bones are renamed to the game's existing
  Meshy names (pelvis→Hips, spine_01→Spine02, spine_02→Spine01, spine_03→Spine, neck_01→neck, head→Head,
  clavicle→Left/RightShoulder, upperarm→Arm, lowerarm→ForeArm, hand→Hand, thigh→UpLeg, calf→Leg, foot→Foot,
  ball→ToeBase), and the `head_end`/`headfront` leaf bones are added. `Root` is dropped, so clip paths stay
  `Armature/Hips/...`. The finger bones keep their MPFB names (`index_01_r` …). Result: the Unity bind-pose-delta
  retarget (`CharacterFeelPass.RetargetPlayerClips`), weapon mounts, footsteps and installers work unchanged, and
  fingers become available for grips.
- **Tutorial set = the existing Field items**, which have stats but no models: field_vest (chest),
  field_helmet, field_armguards, field_gloves, field_leggings, field_boots. All of it is salvaged scrap metal, no wood.
  The jumpsuit is the body's base clothing, not an item.
- Warden plate carrier (quest reward) refitted to the new body.
- Armour pieces are skinned meshes on the same skeleton, shown by `PlayerArmourVisuals` per slot.

## Status (2 Oct 2026, 22:00)
- [x] Concept: `concept/tutorial_set_concept_v1.png`, with the jumpsuit-only sheet in `jumpsuit/suit_concept_v1.png`.
- [x] Piece reference images (Codex image_gen): `pieces/*.png`.
- [x] MPFB 2.0.17 and the CC0 system assets and beard pack installed; headless via `blender/blender_mpfb.sh`.
- [x] MPFB body (`blender/mpfb_build.py`, tag v3): phenotype, skin, eyes, brows, lashes, short02 hair, Sigmund beard,
  game_engine rig renamed, 1.80 m.
- [x] Jumpsuit (`blender/jumpsuit_fit.py`, v7): the colonist suit refitted and cut, shrink-fitted with the collar
  lowered ("he has no neck" fixed), skinned from the full body, hidden body removed.
- [x] Finish (`blender/finish_body.py`, v7): glTF materials, one `char1` mesh (67,247 tris, 7 materials, 54 bones),
  idle/walk/run retargeted, giving `blender/out/colonist_mpfb.glb` (installed as `Art/Imported/Meshy/colonist.glb`).
- [x] Helmet and Warden carrier refitted to the MPFB body; installed skinned through `Editor/TutorialSetInstall.cs`
  (bind poses identical to the body's, max diff 0.00000).
- [x] Unity: `MainCharacterInstall.InstallBatch` OK, `CheckBatch` OK. Fixed along the way:
  - `CharacterFeelPass.Retarget` read the Meshy bind hip height about 100× too low. Meshy→Meshy cancelled out;
    Meshy→MPFB put the hips at 94 m. It now reads rest positions from fresh model instances.
  - The Check step now accepts 54 bones and skinned armour pieces.
- [x] Editor captures: `unity/captures/`, sheet `unity/unity_capture_v1.png`.
- [x] Native batch ts1 (`unity/evidence/next-level/20261002/ts1`, 22:24): build OK; city loop PASS; range tutorial
  10/10; expansion 8/8; gunner separation 8/8; rifle quest 32/33 (the carrier model shows on the colonist; the failure
  is the HUD depot marker, which also failed in nl3); enemies 40/41 (`post_relay` salvage cache had no E prompt, with
  the pack full in the same run, so probably inventory capacity and not the character); A/B against nl3 within drift
  (+0.1 ms p50 at hill/avenue/gate). The native character cameras show only the empty review stand, because the player
  spawns at the gate; the editor captures are the visual evidence.
- [ ] Remaining pieces (chest rig, bracers, knee/shin, boot plates, gloves): **blocked, Meshy balance 13 credits**.
- [ ] Data, once the pieces exist: start equipped with vest + boots; primer completion grants helmet, arm guards,
  gloves and leg armour.
- [ ] Known gaps: the suit reads dark in sun; fingers are flat at rest (no grip curl yet); the beard is a card shell; the
  `MainCharacterInstall.Capture` "vest" shots now show pieces[0], which is the helmet.

## Night of 2–3 Oct 2026 (after Carl topped up Meshy with 1000 credits)
- All five remaining pieces generated (Meshy image-to-3D, 30 credits each): chest rig, bracer, knee+shin, boot plates,
  glove. The glove is a 2.8 mm shell over the player's own hand (palm + finger joints 01–02 + wrist, so fingerless) that
  keeps the finger skinning. Meshy retexture from `pieces/glove.png` (10 credits). Fits: `blender/fit_vest.py`,
  `blender/fit_limbs.py` (aligned to the bone segment, length/radius sized, mirrored, rigid per loose part,
  `ensure_weighted` so straps never fall to a glTF neutral_bone), `blender/fit_gloves.py`. One-shot rebuild:
  `blender/rebuild_all.sh`.
- Neck (Carl: "still issues with the lack of neck", then "now he looks like a human giraffe", then "second row looks
  fine"): body v5 = measure-neck-height +0.3, neck-scale-vert +0.1; jumpsuit tag m0.25 = collar compressed to 25 %.
  Comparison sheet `neck_options.png`. `fitlib.BODY_TAG = 'm0.25'`.
- **Rest pose matched to the Meshy rig** (`finish_body.py`): clips transfer as rotations relative to the rest pose, so
  the MPFB A-pose differences (arms 19°, forearms 29°, feet 27°) carried into every clip, and the weapon holds came out
  overhead. Every bone segment is now re-posed onto the colonist's rest direction before export. Holds, idle and
  walk now match the source clips.
- Relaxed finger curl baked into the rest (8/14/10°); suit base colour lifted (`blender/tex/suit_base.png`).
- Weapons (Carl: "make sure the weapons work with the new models"): `MainCharacterInstall` now measures the palm on the
  installed hand (MPFB 0.062 m along the bone) and sets the pistol/rifle grip 0.011 m short of it (0.051 m; the fixed
  0.11 m would have put the guns at the fingertips). New runtime `Scripts/Combat/PlayerHandGrip.cs` curls the right
  hand round the grip whenever a weapon is drawn (trigger finger part-open) and the left hand on the rifle; it is wired
  by `TutorialSetInstall`. Captures: `unity/captures/{pistol,rifle}_{side,shoulder}.png`.
- Data (`apply_data.py`, idempotent): he starts wearing field_vest + field_boots (boots no longer start in the pack);
  the Field set descriptions now describe the scrap pieces. `BermsTutorial.kitItems` equips helmet, arm guards, gloves
  and leg armour when the primer completes (into the pack if a slot is taken), with the notice "Warden kit issued".
- Unity: all seven pieces installed, bind max diff 0.00000; Edit Mode 253/255 (the two failures are guard-model tests,
  NPC agent's area, reported to it). Captures `unity/unity_capture_v3.png`, `unity/tutorial_set_full_v1.png`.
- Pending: combined native batch after the NPC and building agents finish.

## Tools
- `blender/fitlib.py`: import, push-out (vertex / field / liner strip), skinning, mirror, skinned GLB export, renders.
- `meshy_job.py`: resumable Meshy image-to-3D / retexture with manifest records.

## Combined native batch on1 (3 Oct, 00:18–00:52) and cost bisection
- on1 (`unity/evidence/overnight/20261003/on1`): rifle quest 34/34, city loop PASS, range tutorial 10/10, expansion 8/8;
  gunner separation 7/8 (two gunners at 1.29 m < 1.5 m; nothing tonight touched droids); enemies 40/41 (the post_relay
  drop-cache E prompt, same failure as ts1, probably inventory merge). **A/B vs ts1: +5 to +7.5 ms p50** (cam_hill 59→41 fps).
- Bisection (`bisect/`, new dev-only NativeQa action `setActive` + `lookbook.py --set "prefix=0"`): the six new NPCs
  cost ~8.6 ms at cam_hill and ~4.4 ms at cam_gate (60k-tri skinned meshes, updateWhenOffscreen); the buildings ~0.6 ms;
  the player's worn armour ~2.3 ms at the gate (full-detail Meshy pieces). With the NPCs off the hill view is 15.6 ms,
  faster than ts1.
- Fixes: armour decimated to 40 % at export (`fitlib.DECIMATE`; helmet 20k→8k, vest 22k→8.9k, bracers 18k→7.3k,
  legs 21k→8.4k, boots 18.7k→7.5k, carrier 14.5k→5.8k; gloves unchanged at 4.2k), re-installed. NPC optimisation
  (18–22k LOD0, off-screen skinning/animation culling) handed back to the NPC agent. Re-measure in batch on2.

## Weapons pass, part 2 (3 Oct, 02:15–04:15)
- **First-person view models rebuilt on the MPFB arms** (`TutorialSetInstall.ViewModels`): the pistol view model still
  used the previous colonist's arms (`PlayerFPArms.glb`, Meshy rig) with a hold clip now retargeted to the MPFB rest, and
  the rifle never had one. `blender/fp_arms.py` cuts the player's arms (upper arm to fingertips, suit + skin, 17.8k tris)
  into `TS_FPArms.glb`; each view model gets that rig at the colonist's scale, the player's own materials (no second
  texture set), the weapon copied from the third-person hand pose, its muzzle and flash, finger grip (`PlayerHandGrip`)
  and support-hand IK. `FirstPersonViewModel.rifle` picks the weapon; the overlay camera is shared;
  `PlayerCombat.rifleViewModel` gives first-person rifle shots their muzzle. An earlier "true first person" attempt
  (body arms + lens at the eye) was removed: the hold puts the rifle beside the head and the lens ended up inside the
  stock.
- **Support-hand IK** (`Scripts/Combat/SupportHandIK.cs`, two-bone, after animation/aim/view-model placement): left
  hand onto a "Support grip" point on the rifle handguard (0.30 m ahead of the grip, hand orientation taken from the
  hold clip). On the colonist it is scaled by the aim-pose weight, so the lowered carry keeps the hand free.
  `PlayerHandGrip` now curls the support hand for both weapons.
- QA: `check_rifle_quest.py` adds first-person pistol hip/aim captures and checks, and rifle view-model hip/aim checks.
  NativeQa snapshot has `rifleViewModelVisible`. Quest **37/37** (`unity/evidence/overnight/20261003/fpvm3`);
  sheet `unity/native_fp_views_v3.png`.
- Open: the first-person pistol hands look unconvincing (support-hand fingers pinch, the right hand sits loosely on the
  grip); the first-person rifle support hand sits just under the handguard rather than on it. Needs a hand-pose pass
  with close-up captures (or authored grip poses) rather than procedural curl only.

## Final overnight state (3 Oct, 04:45): batch on3, everything together
`unity/evidence/overnight/20261003/on3` (build copied to `unity/AthenHill/Builds/batch-on3`; `Builds/LinuxDevelopment` is
the same build): rifle quest 37/37, gunner separation 8/8, city loop PASS, range tutorial 10/10, expansion 8/8 (Berms walks
166–179 fps), enemies 39/42 (southern_cache loot prompts; intermittent, a different site each run; follow-up chip).
A/B vs ts1 (last night): cam_hill 57.9→60.6 fps, avenue 54.6→52.0 (noon) / level (night), gate 114→97 (noon), 108→88 (night).
Lookbook of 74 review cameras at 13:00 and 20:30. Edit Mode 255/255. Pistol view model restored to the authored FP hands v2
grip (`FPHandsV2Tests` updated to pick the pistol view model now that a rifle one exists).
Next candidates: gabion bastions look like tiled boxes up close; first-person rifle support hand sits just under the
handguard; NPC/walker hands are fingerless mitts; the native character cameras don't show the player (he spawns at the gate).

## 3 Oct 2026: the kit is no longer granted by the primer
Carl's playtest: finishing the robot tutorial handed over a full armour set, which should be a crafting mission. The primer's
`BermsTutorial.kitItems` is now empty (code default and scene) and the helmet, arm guards, gloves and leg armour are built at
Brann's bench through Ossa's four Warden Kit orders from Berms salvage (`art/armour_mission_20261003/README.md`). The models,
installers and equipment data from this set are unchanged; the vest and boots are still worn from the start.
