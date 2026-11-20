# Hero base: the player body (20 Nov 2026)

Carl, 20 Nov 2026: "can you recreate our main character as burley sci-fi action hero. he look a bit weak and the rigg
is so broken. I want a base character we can add armour etc on later. try with fal maybe rodin?" After seeing the first
candidate: "Yes, go ahead".

The player is now a Rodin 2.5 mesh made from a new concept, on a Meshy rig, with a repainted face and the tutorial
armour set re-fitted to it. It replaces the MPFB2 body of 2 Oct (`art/tutorial_set_20261002`), which is kept for
rollback. Working log: `PROGRESS.md`. Results of the native checks: section **Checks** below.

## What the player is now

| | |
| --- | --- |
| Look | The same man as the 3 Oct face concept (about 45, swept-back dark brown hair, trimmed beard with grey at the chin), heavily built. A fitted short-sleeved undershirt, fitted trousers and plain ankle boots are part of the body; forearms and hands are bare; a slim band with a cyan light on the left wrist. Armour goes over this. |
| File | `unity/AthenHill/Assets/AthenHill/Art/Imported/Meshy/colonist.glb` (same path and GUID): mesh `char1`, 80,000 triangles, one material `PlayerSkin` (4096 colour and normal, 2048 roughness), armature `Armature`, 54 joints, legacy clips `idle`, `walk`, `run`. |
| Height | 1.88 m in the file; `MainCharacterInstall` scales the rig to the project's 1.80 m actor height (scale 0.9585). |
| Skeleton | The Meshy "SmartRig" body bones as Meshy made them (24 game bones), so Meshy library clips play on it with no rest-pose matching. The 30 finger bones carry the previous rig's names (`index_01_l` ...) and are rolled so a positive rotation about local X closes the finger, which is what the grip code assumes. Finger tips, toe ends and six face bones were removed (face weights folded into `Head`). The left `Hand` joint was moved 20 mm to the real wrist. |
| Clips | The 12 source clips in `Art/CharacterMotion/Source/Player/` were fetched from Meshy on this rig, so `CharacterFeelPass.Retarget` is a straight transfer (hip scale 1.000, 24 bones). idle/walk/run in the file come from the same rig: in place, collarbones anchored to the idle pose, loops closed. |
| Armour | All seven `TS_*.glb` pieces re-fitted to this body from the Meshy sources (`armour/`), same materials and triangle counts, bind poses identical to the body's. |
| First person | `TS_FPArms.glb` is cut from this body (21.8k triangles). Grip solver finger radii were raised to the new hands' size. |

## Decisions made by the agent (Carl has not reviewed them one by one)

- **The base is dressed.** Shirt, trousers and boots are fused into the body mesh. Changing them means a retexture or a
  new generation, not a layer swap. This differs from the 2 Oct idea of a near-naked body with separate clothes; a fused
  fitted layer avoids the suit-fit defects of October.
- **1.80 m in the game**, the project's actor standard (controller capsule, cameras and conversation framing assume
  it). The burly read comes from width. Raising him means changing `MainCharacterInstall.Height` and those constants.
- **Native Meshy rig, shaped to the old contract** instead of re-posing the mesh onto the previous rig's rest pose: the
  October body needed a rest-pose match, a collarbone drop and later an arm corrector to hide the mismatch.
- **Skin tone** graded to the repainted face (about 30 % darker than Rodin's pale albedo).
- **Finger radii** in the grip solvers: 12.5 mm fingers, 14.5 mm thumb (`PlayerFace20261003`), 14.5 / 16.5 mm with the
  glove allowance (`RifleHandsPass20261120`); the MPFB hands were 8.2 / 9.5 mm.
- **First-person rifle support elbow** pushed outward (`RifleHandsPass20261120.LeftPoles`), because the thicker forearm
  filled the lower centre of the view.

## How it was built

| Step | Tool | Script / record | Cost |
| --- | --- | --- | --- |
| Concept sheet, three views, 5504 x 3072 | fal `fal-ai/nano-banana-pro/edit` with the face concept as reference | `concept/p_hero_sheet_v1.txt`, request `01a1f866-c87e-7592-9890-26d317219519` | listed $0.15 (4K may bill more) |
| Mesh | fal `fal-ai/hyper3d/rodin/v2.5`: Gen-2.5-High, 150K Triangle, PBR, TAPose, HighPack, seed 20261 | request `01a1f868-f14b-7c83-a4f7-39103f756923`, `rodin/model.glb` | $1.20 listed |
| Rig and clips | Meshy rigging (`model_url`, height 1.88, `include_fingers`) and 13 library clips | `rig/hero_rig.py`, `rig/record.json`, `rig/ledger.json`; rig task `01a1f86e-8961-7749-8e9c-d02892e1d449` | 44 credits |
| Face repaint | Three orthographic flat-colour views of the head repainted by Meshy image-to-image (nano-banana-pro), projected back with visibility rays; rest of the skin and hair graded to match | `face/face_views.py`, `face/face_project.py`; tasks `01a1f87d-0e0b-74d8-8abf-5084c838aefb`, `01a1f880-2ae3-722c-9163-9516eedd0c10`, `01a1f880-364b-77b9-9dc1-5a0262f8687f` | 27 credits |
| Textures | Hem tag painted out; normal map flattened 75 % on the face and 35 % on skin; skin roughness x 0.82 | `build/finish_textures.py` -> `build/tex/` | |
| Player file | Decimate to 80k (head and hands protected), wrist fix, bone contract, hand weight smoothing, clips, export | `build/build_hero.py` -> `build/hero.blend`, `build/out/colonist.glb`, `build/out/TS_FPArms.glb`; checks `build/check_hero.py`, `build/measure_fingers.py`, `build/measure_wrist.py` | |
| Source clips | Slim copies (proxy mesh, no textures; bind matrices and keys byte-identical) | `build/slim_clip.py` -> `build/out/source/` (7.4 MB for 12; the previous set was 43 MB) | |
| Armour | Re-fit of the seven pieces | `armour/README.md`, `armour/out/`, `armour/check.json` | |
| Unity | File swap with rollback copies, review cameras, audit; the existing installers do the rest | `unity/HeroBasePass20261120.cs` (installed in `Assets/AthenHill/Editor`), `unity/apply.py`, `unity/install.sh` | |

fal ran out of credit after the Rodin run (uploads refused from about 10:25), which is why the face repaint went
through Meshy. fal charges were not read back from the account.

## Rebuilding and installing

Blender jobs go through `~/.local/state/ward-programme/showcase-phase2-20261120/blender.sh` (one at a time, CPU).

```
B=~/.local/state/ward-programme/showcase-phase2-20261120/blender.sh; H=$PWD/art/hero_base_20261120
$B $H/face/face_project.py -- $H/rodin/model.glb $H/face/tight $H/face/out v1   # only after changing the repaint
$B $H/build/finish_textures.py
$B $H/build/build_hero.py -- tris=80000        # hero.blend, colonist.glb, TS_FPArms.glb
$B $H/build/check_hero.py -- $H/build/out/colonist.glb $H/build/renders
art/hero_base_20261120/unity/install.sh all    # code rh-rollback files main check arms rh rh-base verify
art/hero_base_20261120/unity/install.sh tests
```

- A new `hero.blend` changes the armature only if the bone edits change. If it does, every armour piece must be
  exported again from it (the installer refuses a piece whose bind poses differ from the body's by more than 0.01).
- `install.sh` runs one Unity job per step. `main` is `MainCharacterInstall.InstallBatch`; it must be preceded by the
  rifle-hands rollback and followed by the arms and rifle-hands installs, as before.
- `RifleHandsPass20261120 verify` compares against reference values; they were re-baselined for this body (`rh-base`).

## Rollback

`art/hero_base_20261120/unity/install.sh rollback` restores the 21 replaced files from `rollback/assets/` (kept on the
first install; hashes in `rollback/sha256.json`) and re-runs the installers, which rebuilds the previous body's prefab,
clips and grips. Then `python3 art/hero_base_20261120/unity/apply.py --revert` removes the pass file, the guards and
the finger-radius edits, and restore `LeftPoles` in `RifleHandsPass20261120.cs` from git. Not run.

While the hero base is installed (`rollback/installed.json` exists), `ColonistBackPass20261120` install and rollback
and `PlayerFace20261003` rollback refuse to run: they would copy the previous body's files back over it.

## Checks

[[CHECKS]]

## Known defects and open points

[[OPEN]]
