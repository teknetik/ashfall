# Ward talking NPCs and Wardens (3 Oct 2026)

Replaces the shared supplied Ward Guard on the six actors that used it (Mira, Torr, Vex, Linn; Wardens Ossa and Rell)
with six distinct Meshy characters. Concepts, prompts and the progress log: `art/ward_npcs_20261003/`. Unity installer:
`unity/AthenHill/Assets/AthenHill/Editor/WardNpcInstall.cs`. Pre-approved Meshy use (AGENTS.md section 5).

## Pipeline (`npc_meshy.py NAME`, resumable; key from `MESHY_API_KEY`, never written to records)
1. Codex concept turnaround sheet (`art/ward_npcs_20261003/concept/<name>_sheet_v1.png`, prompt `p_<name>.txt`),
   cropped into `panel_front/side/back.png`.
2. `POST v1/multi-image-to-3d`: ai_model latest, triangle topology, target_polycount 60000, should_remesh, PBR textures,
   symmetry auto, pose_mode a-pose (30 credits). Output `model.glb`, `thumb.png`.
3. `POST v1/rigging` with `input_task_id` = the model task and the character's height (5 credits): `rigged.glb`
   (24 Meshy bones, the same names as every other actor in the game), `basic_walking/running.glb`.
4. `POST v1/animations` on that rig, change_fps 30 (3 credits each): one idle and one talk from the library
   (ids from `meshy/character-feel-20260927/animation-library.json`).
5. `strip_clip.py` (copied from `salvage-dealer-20261001`) writes `anim_only/<clip>.glb` (animation-only copies that
   Unity imports).
6. `inspect_npc.py` (headless Blender, Cycles CPU): `renders/rigged_*.png`, `renders/sheet_all.png`,
   `inspect_rigged.json`.
7. `prepare_unity.sh` builds `<npc>/rigged_fixed.glb`, the file Unity imports: Meshy ships near-flat vertex normals with a
   normal map that compensates them per triangle (Blender renders it correctly: `vex/renders/face_nm_on/off.png`), but in
   Unity the faces came out faceted with every tangent-sign / green-channel combination tried. So: `smooth_normals.py`
   (smooth vertex normals, 60 degree crease) -> `rebake_normals.py` (Blender bakes the original shading normal onto the
   smooth mesh, tangent space, 2048, `normal_smooth.png`) -> `replace_normal.py` + `add_tangents.py` (MikkTSpace tangents
   of the smooth mesh). Facets gone in the Unity captures; UVs, skin, base colour and metal-roughness unchanged.
   (`fix_tangents.py`, `invert_green.py`, `tangents_blender.py`, `face_nm_test.py` are the diagnostic steps, kept for the record.)
   Also found: editor captures that render `SkinnedMeshRenderer.BakeMesh` copies have no tangents, which disables
   normal maps in the capture; `WardNpcInstall.Capture` renders the live skinned mesh instead.

## Tasks
| NPC | Multi-image-to-3D | Rig | Clips | Credits |
| --- | --- | --- | --- | ---: |
| mira | `01a0fe94-9734-716c-83c7-79e8968c00f6` | `01a0fe98-b373-73a9-9c4b-afc614fae87d` (1.68 m) | idle_244 `01a0fe99-6ecc-717a-94a1-257861900da0`, talk_313 `01a0fe99-7236-773b-9df8-01cfcdccdb04` | 41 |
| torr | `01a0fe94-979a-7070-ad41-9a0d13417aec` | `01a0fe98-656d-740e-a8aa-d9b29ae7f08b` (1.76 m) | idle_246 `01a0fe98-cdcc-76d7-bcee-d616b0a7a430`, talk_309 `01a0fe98-d0da-72c0-a002-7d454df59541` | 41 |
| vex | `01a0fe94-97a9-72c5-a2dd-3df68e107d79` | `01a0fe99-537c-722c-a9ee-7faa2448ee10` (1.8 m) | idle_243 `01a0fe9a-1e99-73ce-bf37-656bfe4eac00`, talk_314 `01a0fe9a-21c6-7594-b67b-d4f1c56e6e67` | 41 |
| linn | `01a0fe94-9730-70dd-a890-ec443841835d` | `01a0fe99-5256-7257-9469-c848d7b75cf0` (1.62 m) | idle_252 `01a0fe9a-593b-77bd-8b3c-5620b8e20c8f`, talk_310 `01a0fe9a-5c6d-7510-8198-726ffa454196` | 41 |
| ossa | `01a0fe94-97de-7553-9314-b96ce2257e7d` | `01a0fe98-b5bc-7794-a56d-f2a7ddd7ea20` (1.74 m) | idle_243 `01a0fe99-705b-76d3-a38a-3ea0cc4767e8`, talk_313 `01a0fe99-73dc-73a8-854b-db859c6688ab` | 41 |
| rell | `01a0fe94-97f3-7165-b846-c5f23173651b` | `01a0fe99-54c7-735f-8d94-e2c77d64251a` (1.88 m) | idle_252 `01a0fe9a-1f61-770b-a1cf-7c979049a9c4`, talk_314 `01a0fe9a-2343-71cb-8209-94d298fa70c9` | 41 |

Total: **246 credits**.

## Notes and defects
- All six: Meshy sculpted hands, no finger bones (open/mitt hands); faces read well at dialogue distance.
- Linn: the rigging output dropped the PBR set (base colour also wired as full emissive, no normal or
  metallic-roughness, so metallic would default to 1). UVs/base colour match `model.glb` (RMSE 0.6 %), so
  `linn_material.py` puts `model.glb`'s PBR set on the rigged file before `prepare_unity.sh`.
- Linn's idle 252 tilts the head back at mid-loop; `ActorLookAt` levels 70 % at rest.
- Rell's helmet came out as a riveted head band (as in the concept).
- Ossa's drop-leg holster is empty in the mesh: Unity mounts `ScrapPistol.glb` in it. Rell's sling is part of the
  mesh: Unity mounts `FieldRifle.glb` on his back. Vex's holstered sidearm is part of his mesh.

## Recovery
The old Ward Guard objects stay in the scene, inactive. `WardNpcInstall.RunBatch --steps rollback` reactivates them and
repoints each `NpcAgent.actor`; the new prefabs stay in the project.

## Runtime LODs (3 Oct 2026, after the native bisect)
`prepare_unity.sh` now also runs `lod_blender.py` (Decimate collapse on the position-welded mesh, head/neck protected,
LOD0 ~20k, LOD1 6–9k) and `glb_lod.py` (splices both into the rigged GLB as `char1` and `char1_lod1` on the same skin,
with MikkTSpace tangents and `normal_smooth.png`). `lod.json` per NPC records the counts.
