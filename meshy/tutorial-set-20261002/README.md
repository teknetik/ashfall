# Tutorial set and MPFB2 player: asset provenance (2 Oct 2026)

Carl's request: a crash-repaired pilot jumpsuit, the existing armour refitted, and a full basic armour set in salvaged
scrap metal (no wood) as the tutorial set. The player is built on an **MPFB2** base human ("I wanted you to use mpfb2").
Working files and the pipeline are in `art/tutorial_set_20261002/` (see its `PROGRESS.md`).

## Player body (MPFB2)
- **MPFB 2.0.17** (GPL-3, extensions.blender.org, sha256 `4f0a879d…a87`) installed as a Blender 5.2 user extension.
  The archive is kept in `~/.local/share/mpfb-downloads/`.
- **makehuman_system_assets_cc0.zip** (CC0, files.makehumancommunity.org, 267 MB): skin `middleage_caucasian_male`,
  eyes `high-poly` with `brown_eye.png` (clear cornea shells removed), eyebrows `eyebrow007`, eyelashes `eyelashes02`,
  hair `short02`.
- **bodyparts05_cc0.zip** (CC0, 6 MB): beard `grinsegold_beard_sigmund_wip` by grinsegold. Its grey hair texture is
  tinted dark brown and keeps its own alpha (`art/tutorial_set_20261002/blender/tex/beard_rgba.png`).
- Phenotype: male, age 0.62, muscle 1.0, weight 0.7, proportions 0.85, height 0.6, caucasian. Targets: head-square
  0.45, chin-width +0.35, chin-prominent +0.25, head-age +0.25, neck-scale-horiz +0.3. Scaled to 1.80 m.
- Rig: MPFB `game_engine` (fingers). The 22 body bones are renamed to the game's Meshy names (`Hips`, `Spine02`,
  `Spine01`, `Spine`, `neck`, `Head`, `Left/RightShoulder|Arm|ForeArm|Hand|UpLeg|Leg|Foot|ToeBase`) and
  `head_end`/`headfront` are added, giving 54 bones. `Root` is dropped, and the finger bones keep their MPFB names.

## Jumpsuit
- Geometry: the flight suit of Carl's `main_char_OK` colonist (`meshy/main-char-20261002/rigged.glb`). Its skeleton
  was posed onto the MPFB joints (spine as one chain, boots flat, collar lowered and snugged), and the colonist's head,
  hands and bare forearm skin were cut out by bone dominance and texture colour. The suit was shrink-fitted and pushed
  out to clear the body, then re-skinned from the full MPFB body before the hidden body faces were deleted.
- Texture: **Meshy retexture** `01a0fe25-8ac9-729a-9898-75ea7fadd6f8` (meshy-7, multiview style from
  `art/tutorial_set_20261002/jumpsuit/suit_front.png` + `suit_back.png`, original UVs, 4k PBR, **10 credits**). The
  base colour is used as delivered; roughness is lifted by +30 % (`blender/tex/suit_roughness.png`). The normal map is
  the colonist's 4k map baked from the 595k source.

## Armour
| Piece | Item | Source | State |
| --- | --- | --- | --- |
| Scrap helmet | `field_helmet` | Meshy image-to-3D `01a0fe21-f20b-72db-a7c7-1c7d4f7ee794` from `pieces/helmet.png` (latest, 20k tris, PBR 2k, **30 credits**) | Fitted (`blender/fit_helmet.py`), rigid on `Head`, installed |
| Warden plate carrier (refit) | `warden_plate_carrier` | existing `Art/Armour/WardenPlateCarrier.glb` (Meshy `01a0fc9d…`) | Refitted (`blender/fit_carrier.py`): uniform scale 0.294, hem trimmed at hips + 4 cm, liner stripped, smooth push-out, torso weights; installed skinned (the rigid chest-bone copy is removed by the installer) |
| Scrap chest rig | `field_vest` | Meshy image-to-3D `01a0fe8b-9adf-726d-9043-59e76461afeb` (30 credits) from `pieces/chest.png` | Fitted (`blender/fit_vest.py`), torso weights, installed |
| Bracers | `field_armguards` | Meshy image-to-3D `01a0fe8b-d6a6-7106-8924-bad591ad811b` (30 credits) | Fitted (`blender/fit_limbs.py bracer`), rigid on the forearms, mirrored, installed |
| Knee + shin plates | `field_leggings` | Meshy image-to-3D `01a0fe8c-12fc-7008-aaae-6804e3f3f4ee` (30 credits) | Fitted (`fit_limbs.py kneeshin`), rigid on the shins, mirrored, installed |
| Boot plates | `field_boots` | Meshy image-to-3D `01a0fe8c-4f3b-7603-acce-7b28135db43a` (30 credits) | Fitted (`fit_limbs.py bootplates`), on the foot and toe bones, mirrored, installed |
| Fingerless gloves | `field_gloves` | shell over the player's hands + Meshy retexture `01a0fe99-4b52-7765-9165-a5d2283026d3` (10 credits) (the image-to-3D glove `01a0fe8c-8b85-719c-bb1f-f34c4b87edb8` (30 credits) is kept as a reference only) | `fit_gloves.py`, finger skinning kept, installed |

Piece references and the concept are Codex image_gen (ChatGPT plan); prompts are beside the images in
`art/tutorial_set_20261002/{concept,pieces,jumpsuit}/`. Carl topped up Meshy with 1000 credits on 2 Oct (evening); all pieces are generated.

## Previous player (recoverable)
`previous/` holds the installed `main_char_OK` colonist GLB, `MeshyPlayer.prefab` and the city scene as they were
before this pass (sha256 in `previous/sha256.txt`; none of them was committed yet). To roll back, copy
`colonist_main_char_OK.glb` over `Art/Imported/Meshy/colonist.glb` and run `MainCharacterInstall.InstallBatch`.
