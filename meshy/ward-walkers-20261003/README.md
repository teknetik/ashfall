# Ward ambient walkers (3 Oct 2026)

Replaces the supplied "weathered traveler" (`meshy/Meshy_AI_weathered_traveler_ri_biped`, `Prefabs/Traveler.prefab`),
which all three ambient walkers shared, with three distinct Ward residents. Concepts, prompts and the progress log:
`art/ward_walkers_20261003/`. Unity installer: `unity/AthenHill/Assets/AthenHill/Editor/WardWalkerInstall.cs`.
Pipeline copied from `meshy/ward-npcs-20261003/` (talking NPCs). Pre-approved Meshy use (AGENTS.md section 5).

| Walker | Route | Character | Height | Walk clip | Clip ground speed | Route speed | Playback |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: |
| `npc_walker_01` | east avenue lane from the West Gate (46 m loop) | **Daro**, Karaveen caravan porter, pack frame with trade cloth and a water can | 1.78 m | Walking 2 (566) | 0.954 m/s (root motion) | 0.95 | 1.00 |
| `npc_walker_02` | north loop by the Quantum Tube goods node (26 m) | **Sel**, nanofabrication technician, patched slate work coat, magnifier visor, cyan diagnostic wand | 1.68 m | Walking 2 (566) | 0.903 m/s (root motion) | 1.05 | 1.16 |
| `npc_walker_03` | south loop in the hall district (20 m) | **Anso**, hydroponics grower, straw hat, waxed apron, harvest satchel of greens | 1.80 m | Quick Walk (115) | 1.262 m/s (planted foot) | 1.15 | 0.91 |

`ActorAnimation` plays the walk at route speed / clip ground speed, so the playback rates above keep the planted foot
still (no foot sliding). The yard mechanic (`district-20260908/mechanic`, 5.6k triangles) was inspected
(`review_mechanic/renders/sheet.png`) and left unchanged: readable at its yard distance, faceted only at close range.

## Pipeline (resumable; key from `MESHY_API_KEY`, never written to records)
1. Codex concept sheet `art/ward_walkers_20261003/concept/<name>_sheet_v*.png` (prompt `p_<name>*.txt`), cropped to
   `panel_front/side/back.png` by `walker_meshy.py`.
2. `walker_meshy.py NAME [--stop-after model|rig]`: multi-image-to-3D (latest, triangle, 60k, PBR, a-pose, 30 credits),
   rigging at the character height (24 Meshy bones, 5), library walk clips at 30 fps (3 each).
3. `strip_clip.py` -> `<name>/anim_only/<clip>.glb` (what Unity imports).
4. `inspect_npc.py` (headless Blender): `<name>/renders/sheet_all.png`; `rigged_fixed --clips --faceclip` renders the
   runtime LOD0 driven by each walk (skinning check). `render_dump.py` renders Unity's baked mesh (diagnostic).
5. `prepare_unity.sh [names]` (shell script, kept locally; git keeps only py/md/json under meshy/):
   `smooth_normals.py` -> `rebake_normals.py` (normal_smooth.png) -> `lod_blender.py <dir> rigged.glb 20000 6000 pos 4`
   -> `glb_lod.py <name> rigged.glb rigged_fixed.glb normal_smooth.png lod.npz`. Result: `rigged_fixed.glb` with
   LOD0 20,000 and LOD1 6,000 triangles (`lod.json`).
6. Unity: `unity.sh LOG AthenHill.Editor.WardWalkerInstall.RunBatch -nographics --steps import,prefab,install,verify`
   (and `--steps capture` with graphics). Audition another clip with `--steps import,prefab --only porter --walk porter=walk_30`.

## Tasks and credits
| Character | Model task | Rig task | Clips | Credits |
| --- | --- | --- | --- | ---: |
| porter (Daro) | `01a0ff51-ad2b-76ab-9560-c881927dfe60` | `01a0ff55-cd14-7497-acb2-ce7099da8b48` | walk_30 `01a0ff56-8d74-7559-9d02-7cec83562bd9`, walk_566 `01a0ff67-c75e-7346-b369-b8e0b6ae42c7` | 41 |
| nanotech (Sel) | `01a0ff51-ad2c-7085-9a4f-2e9618aee460` | `01a0ff55-cd12-71ed-a620-70960c70eeda` | walk_1 `01a0ff56-38c0-763c-b083-e135fb171eed`, walk_566 `01a0ff67-c75d-7602-8763-c00edecb220f` | 41 |
| grower v2 (Anso) | `01a0ff5d-6914-75b9-98b0-bfc1d6028a52` | `01a0ff62-645c-70ec-af53-1b47bf1c7629` | walk_566 `01a0ff63-1ce6-7539-89d0-db12837c1a9b`, walk_115 `01a0ff63-1fc6-75a8-abba-3243a73247a2` | 41 |
| grower v1 (rejected) | `01a0ff51-ad82-7256-9b9e-cd5f4b340710` | `01a0ff56-baa9-7088-9a27-edbafad88850` | carry_551 `01a0ff57-73e5-7370-b3e5-9772c419a380`, walk_30 `01a0ff57-76e5-7007-8a15-b422bc6bcada` | 41 |

Total **164 credits** (budget ~200).

Clip auditions (stride measured by the installer on each rig): Casual Walk 30 = 0.73 m/s (porter rate 1.30),
Walking Woman 1 = 1.32 (Sel rate 0.80), basic_walking (free with the rig) = 1.35–1.51 (rates 0.63–0.78),
Walking 2 566 = 0.90–0.96, Quick Walk 115 = 1.26. The closest to 1.0 was kept.

## Rejected / notes
- **grower v1** (`grower_v1_rejected/`): broken face texture (eyes misaligned, a hole on the nose bridge) and a T-pose.
  Its "Carry Heavy Object Walk" (551) turned out to be a shoulder carry with one arm out, and "Carry Water Bucket Walk"
  (552) includes a bucket pick-up, so neither supports a carried crate; v2 carries its harvest in a satchel in the mesh.
- All three: Meshy sculpted hands, no finger bones. Walking 2 is a root-motion clip with small rotation seams (≤0.04)
  that the installer closes over the last 0.12 s; its drift is removed so the AmbientWalker moves the actor.
