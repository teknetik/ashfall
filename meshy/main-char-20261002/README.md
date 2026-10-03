# Main character (player colonist), 2 October 2026

Carl's request (2 Oct 15:50): "swap out the main character for char_main_OK. NOK is to be used later but put that
asset in the right place for now."

Delivered files (kept unchanged in `meshy/incoming-20261002/`, SHA-256 in `incoming-sha256.txt`):

| File | Content | Use |
| --- | --- | --- |
| `main_char_OK.glb` | 595,052 triangles, 317,310 vertices, unrigged, 1.90 m, centred on the origin, faces glTF +Z; 3 × 2048 px JPEG (base colour, metallic/roughness, normal); pygltflib export | **Installed** as the player (this record) |
| `main_char_NOK.glb` | 11,913 triangles, same shape, own unwrap with 2048 px baked base/normal and a 4096 px metallic/roughness PNG; Blender glTF export | **Held for later** in `nok-held-for-later/` (copied, not installed, nothing references it) |

## Pipeline

1. `blender/prep_player.py` (Blender 5.2 headless via `~/.local/state/ward-programme/blender.sh`, 25 s):
   LOD0 = Decimate (collapse, ratio 0.1008, source UVs kept, no normal recalculation) → **59,999 triangles /
   46,510 vertices**; tangent-space normal **baked 4096 px** from the 595k source with its own normal texture applied
   (Cycles CPU, 1 sample, cage 4 mm, ray 12 mm: longer rays hit the shells under the collar and beard); LOD1 =
   15,000 triangles (`player_lod1.glb`, record only, not installed); rig upload copy with 1024 px JPEGs
   (`player_rig_input.glb`, 2.1 MB). Previews in `blender/previews/` (hi Workbench vs lo Eevee with the baked map).
   Record: `blender/prep.json`.
2. `rig_main_char.py` (Meshy API, pre-approved, record `rig.json`): rigging task `01a0fd2b-d937-7338-b11d-5afbd92fa01c`
   on the rig-input GLB at `height_meters` 1.8 → `rigged.glb` (same 59,999 triangles, 48,075 vertices after Meshy's
   re-export with tangents; 24 joints, the usual Meshy names Hips/Spine02/Spine01/Spine/neck/Head/…/RightHand/…
   RightToeBase, `Armature` node at 0.01 scale, 1.8 m with the soles at y = 0) plus the rig's basic walking/running
   GLBs. Animation tasks (30 fps): idle_252 (Idle 13, the accepted calm breathing idle), aim_95 (Gun Hold Left Turn),
   rifleturn_573 (Rifle Turn Left), lower_334 (Lower Weapon, Look, Raise), aimturn_585, left_528, back_233, fwd_234.
   **Credits: 5 (rig) + 8 × 3 (animations) = 29.** Meshy accepted the 60k mesh directly, so no further decimation or
   weight transfer was needed.
3. `prepare_player.py` → `unity/AthenHill/Assets/AthenHill/Art/Imported/Meshy/colonist.glb` (same path/GUID as the
   mpc colonist): rigged mesh + `idle` (idle_252, 6.03 s) + `walk` (Meshy walking, 1.07 s) + `run` (Meshy running,
   0.67 s); the 1k rig textures replaced by the 2048 px source base colour and metallic/roughness JPEGs and the 4096 px
   baked normal PNG (24.2 MB GLB; glTFast + `GltfTextureCompression` compress to BC7 on import). It also copies the
   eight clips to `Art/CharacterMotion/Source/Player/Player_<name>.glb` for the retarget. Record: `prepare.json`.
4. Unity (batch, `AthenHill.Editor.MainCharacterInstall.InstallBatch`): see
   `art/next_level_20261002/character/REPORT.md`.

## Previous player (recoverable)

The mpc colonist (`meshy/mpc`, 10,391 triangles, 4096 px texture): regenerate `colonist.glb` with
`unity/tools/prepare_meshy.py` (or `git show <HEAD-before-this-pass>:unity/AthenHill/Assets/AthenHill/Art/Imported/Meshy/colonist.glb`,
blob hash in `prepare.json`), restore `previous/MeshyPlayer.prefab.before` over `Prefabs/MeshyPlayer.prefab`, then run
`MainCharacterInstall.InstallBatch` again (the same chain re-attaches the pistol, rifle, vest, clips and footsteps to
whichever colonist.glb is present). The 27 Sep rig's clip sources stay in `meshy/character-feel-20260927/player*/`.
