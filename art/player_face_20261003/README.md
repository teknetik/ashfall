# Player face, hair, beard and first-person hands (3 October 2026)

Carl's 3 Oct playtest: "NPC looks ok why not MPC … Why do other NPC look so good even in the face." The NPCs are Meshy
multi-image models with a painted, sculpted face texture; the player was the MPFB2 body with the dated MakeHuman CC0
skin, card hair and a card beard that glTF exported as alpha **BLEND** (so Unity drew them as solid sorted slabs). The
second open item was "first-person hands still not convincing". Not yet accepted by Carl.

## What changed

**Face and skin** (the body, rig, proportions, neck/collar m0.25, clips and armour bind poses are unchanged; all seven
armour pieces still bind with max bind-pose difference 0.00000).
- The MPFB skin mesh (head, neck, hands; original MPFB UVs) was retextured by Meshy from a three-view face concept painted
  over renders of this exact head (Codex image_gen, `concept/face_concept_v1.png`, prompt `concept/prompt_face_v1.txt`):
  rugged 45-year-old, short dark swept-back hair, full dark beard with grey at the chin, weathered skin. Three candidates
  were compared under the NPC inspection light (text prompt, single image, multi-view): the multi-view one won
  (`renders/cand_*`). `blender/make_tex.py` makes the runtime set: 4k base colour (+10 % saturation, slightly warmer,
  no relighting), 4k tangent-space normal, 2k roughness (Meshy's x0.92), metallic 0.
- Hair, beard and brows are painted into that texture (as on the NPCs). The MakeHuman `short02` hair, Sigmund beard and
  eyebrow cards are gone; `blender/shells.py` adds four alpha-clipped shell layers over the painted hair/beard (copies of
  the skin faces under `tex/hair_mask.png`, offset up to 8 mm scalp / 10 mm beard, combed back/down, skinned with the
  head; eyes excluded) on one material `PlayerHairShell` (`tex/hair_shell.png`: painted colour, alpha from the painted
  strand contrast). A vertex-colour alpha per layer (1.0 → 0.55, fading to the mask edge) thins the outer layers.
- Eyelashes are now alpha **MASK** (cutoff 0.5) instead of BLEND; the shells too (`Round` node → glTF MASK).
- Eyes: MPFB `brown_eye.png` had a red iris (read as bloodshot in sun); `tex/eye_brown.png` keeps its fibre detail
  re-tinted dark brown, sclera slightly less white.
- Export now carries MikkTSpace tangents and one `COLOR_0` (white except the shells).

| | before | after |
| --- | --- | --- |
| Player triangles | 67,249 | 71,867 (cards −4.4k, shells +9.0k) |
| Materials | 7 (skin, eyes, lashes, brows, hair, beard, suit) | 5 (skin, eyes, lashes, suit, hair shell) |
| Skin maps | 2k MakeHuman diffuse only | 4k base + 4k normal + 2k roughness (Meshy) |
| Hair/beard | 2 alpha-BLEND card sets (2k + 1k) | 1 alpha-MASK shell material (2k RGBA) |
| colonist.glb | 50.5 MB | 70.5 MB (BC7-compressed on import by GltfTextureCompression) |

**First-person hands** (`unity/AthenHill/Assets/AthenHill/Editor/PlayerFace20261003.cs`, `FirstPersonHands`, run by
`TutorialSetInstall.Attach` at the end of every `MainCharacterInstall` run).
- The pistol view model shows the player's own MPFB arms (same `PlayerSkin`, sleeves) instead of the authored
  "FP hands v2" grip mesh (v5 file, 110k triangles, flat colours): 17.8k triangles. v2 stays attached, inactive.
- Pistol is **weapon-driven**: `FirstPersonViewModel` places the pistol on a `Weapon mount`; the arms rig sits at a
  camera-space anchor (shoulders centred under/just behind the eye, `ShoulderAnchor`) via the new runtime
  `ViewModelArmsRig` (order 450); both arms are two-bone IK'd (`SupportHandIK`, which now honours `poleHint`: elbows
  down and out) onto a `Shooting grip` (palm on the grip's right panel, knuckles up the raked grip, found by palm contact)
  and a `Support grip` (cup under the shooting hand). ADS distance 0.46 m (`PistolAimDistance`; was 0.30) so the wrists
  stay below the sights.
- Fingers: `PlayerHandGrip` takes solved per-bone grip poses per weapon/hand (`pistolRight/Left`, `rifleRight/Left`);
  `SolveFingers` curls each finger joint by joint until it touches the weapon (temporary mesh colliders) or, for the
  pistol support hand, the shooting hand's finger capsules. The body's shooting-hand grips are solved on the held
  pistol/rifle in their hold clips; the rifle support hand is shared with the view model. Empty arrays = old curl.
- Rifle view model: still clip-driven (a weapon-driven trial put the hand on the receiver; `WeaponDrivenRifle=false`);
  its support grip is now found by palm contact under the barrel (18 cm ahead of the grip) and copied to the held rifle.
- Worn field gloves / arm guards are mirrored onto both view-model rigs (`ViewModelArmourMirror`, shown exactly while
  the body's piece is shown).

## Files
- Blender: `blender/inspect_skin.py`, `prep_meshy.py` (Meshy input `meshy_input/skin_head.glb`, eyes' UVs packed into an
  empty corner), `face_lookdev.py` (same light/framing as `meshy/ward-npcs-20261003/inspect_npc.py`), `make_tex.py`,
  `shells.py`. The chain itself: `art/tutorial_set_20261002/blender/finish_body.py -- m0.25` (new default; `face=old`
  rebuilds the MakeHuman look) and `fp_arms.py` (no vertex colours on the arms).
- Textures: `tex/skin_base.png`, `skin_normal.png`, `skin_rough.png`, `hair_mask.png`, `hair_shell.png`, `eye_brown.png`.
- Unity: `Editor/PlayerFace20261003.cs` (steps install, cameras, hands, verify, capture `--shots face|fp|tp`, rollback),
  runtime `Scripts/Combat/ViewModelArmsRig.cs`, `ViewModelArmourMirror.cs`; changed `PlayerHandGrip.cs`,
  `SupportHandIK.cs` (pole), `TutorialSetInstall.cs` (calls FirstPersonHands), `MainCharacterInstall.cs` (check accepts
  player arms), `PistolModsInstall.cs` + `FPGripPass.cs` (pick the pistol view model, not "any" of the two),
  `Tests/Editor/FPHandsV2Tests.cs` (asserts the new set-up when v2 is inactive).

## Evidence
- Blender, NPC light: `renders/compare_before_after_torr_blender.png` (rows: before, after, Torr; front, ¾, side, shade);
  candidates `renders/cand_{text,img,mv}_*.png`, shells `renders/shells_v{1,2}_*.png`, hands `renders/*hand*`.
- Unity editor (13:00 profile, live skinned meshes with tangents): `unity/face_after_vs_torr_unity.png`
  (sun front, sun ¾, shade, Torr), `unity/fp_after_sheet.png` (pistol hip/ADS/orbit, rifle hip/ADS/orbit),
  `unity/body_after_unity.png`, single frames in `unity/captures/`. Before: `art/tutorial_set_20261002/unity/captures/armour_face.png`,
  `art/tutorial_set_20261002/unity/native_fp_views_v3.png`.
- Logs: `unity/install3.log` + `unity/main_character_install.json` (full chain), `unity/verify.json` (pass, incl.
  `MainCharacterInstall.Check`), `unity/editmode.xml` (Edit Mode 268/268).
- Review cameras for the native lookbook (player at his West Gate spawn, facing +Z): `cam_player_face_20261003_face_front`,
  `_face_quarter`, `_face_side`, `_body_front`, `_follow_back` (root "Player face 20261003 cameras").

## Provenance and licences
- Meshy retexture (pre-approved, AGENTS.md §5), records in `meshy/player-face-20261003/`: `skin_mv_v1` (used)
  `01a101b8-df9c-714f-9f0e-f888716dd885`, `skin_img_v1` `01a101b8-df96-73e0-862c-db0c6b880d2a`, `skin_text_v1`
  `01a101b8-0693-70c1-b062-d52b3ead2800`; 10 credits each, **30 credits**. Input: the MPFB skin mesh (CC0 MakeHuman base).
- Concept: Codex image_gen (ChatGPT plan), our own renders + `art/tutorial_set_20261002/concept/ref_player_face.png` as references.
- MakeHuman/MPFB assets (eyes, eyelashes02, base mesh): CC0 (MakeHuman project, 2020 release). The brows, short02 hair and
  Sigmund beard are no longer used.

## Rollback
Previous outputs: `art/tutorial_set_20261002/blender/previous_face_20261003/` (colonist_mpfb.glb, TS_FPArms.glb, final
blend + renders, the old finish_body.py/fp_arms.py; `sha256.txt`). `-executeMethod AthenHill.Editor.PlayerFace20261003.RunBatch
--steps rollback` copies them back over `colonist.glb`/`TS_FPArms.glb`, reinstalls with the authored FP hands v2 and the
procedural finger curl, and removes the review cameras. To rebuild the old look from source: `finish_body.py -- m0.25 face=old`.

## Remaining defects
- Alpha-tested shells: a speckled fringe at the hair/beard silhouette in editor captures (SMAA); judge natively with TAA
  for crawl/shimmer in motion. The painted hairline shows a few light comb strokes.
- Face skin reads slightly glossy on the nose in noon sun; shade is darker than the NPCs (who are lit differently).
- Rifle: the shooting hand sits on the magazine well, not the pistol grip (third-person mount from RifleArmourInstall,
  copied by the view model); rifle ADS still puts the stock end in the lower view. Pistol support hand is a cup under the
  grip, not thumbs-forward. No wrist twist distribution (the pistol hand turns 30° from the clip).
- The jagged cut edge of the jumpsuit collar (pre-existing) and the upper-arm cut of the first-person arms (not in view).
- Not natively tested (round rule): needs the combined batch lookbook of the cameras above at 13:00/20:30, the rifle
  quest first-person checks and an A/B (shells +9k tris on the player; pistol view model −92k tris).
