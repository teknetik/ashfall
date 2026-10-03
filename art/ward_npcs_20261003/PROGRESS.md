# Ward NPC replacement (started 2–3 Oct 2026, overnight)

Carl (verbatim): "Might be worth replacing the npc ward guards too and rebuilding their armour."
Extra (via the coordinator): "make sure the weapons work with the new models" — re-mount NPC weapons on the new bones
with a measured position, show them in the review captures.

## Scope (investigated, not assumed)
`Prefabs/WardGuard.prefab` (supplied `Art/Imported/Meshy/ward-guard.glb`, 26.9k tris, arms at sides) has exactly
**six** instances in `Scenes/AthenHill.unity` (scan of `m_SourcePrefab` guid 5af8cccb…):

| Character | Scene object | NpcDefinition | Role (dialogue) | Voice (AUDIO.md) | Structure |
| --- | --- | --- | --- | --- | --- |
| Mira | `npc_mira/WardGuard` | npc_mira | Basic General shopkeeper | Clara, British F | NpcAgent on `npc_mira`, guard is a child |
| Torr | `npc_torr/WardGuard` | npc_torr | Local fixer, terminal court | Chris, American M | same |
| Vex | `npc_vex/WardGuard` | npc_vex | Free Column guard, West Gate | Charlie, Australian M | same |
| Linn | `npc_linn/WardGuard` | npc_linn | Hill regular | Amelia, British F | same |
| Warden Ossa | `Outer Berms/Warden post/Warden Ossa` | npc_ossa | West Gate watch (field orders) | Victoria, British F | NpcAgent + ActorAnimation ON the guard prefab instance root |
| Warden Rell | `.../West Gate checkpoint/Warden Rell` | npc_rell | Checkpoint sentry | Roger, American M | same as Ossa |

No prefab nests WardGuard. The training-range "Wardens" in AGENTS.md are these two. Brann (SalvageDealer) is a
different model (holstered pistol is part of his mesh; out of scope).

Weapon/prop mounts on these NPCs: Ossa and Rell each carry an added child `Warden secured sidearm` (ScrapPistol.glb,
0.34 m) parented to the old rig's `RightHand`, hanging muzzle-down from an open hand (WestGateCheckpointPass.Arm).
The four colonists carry nothing.

## Plan
- Route (b) Meshy: Codex concept turnaround sheets (front/side/back A-pose) -> Meshy multi-image-to-3D (PBR, 60k) ->
  Meshy rig (24 bones, same names as every other actor) -> per-rig library idle + talk clips. Reason: six distinct,
  fully dressed characters overnight; Meshy is Carl's preferred source and the Brann pipeline (ImportSalvageDealer)
  is proven for idle/talk on legacy Animation. MPFB would need per-character garment/armour fitting (the player's
  armour pieces alone took a day and are still partly blocked).
- Known limit of Meshy rigs: no finger bones -> no curled grips. So weapons are mounted where no grip is needed:
  Ossa = scrap pistol in the drop-leg holster on the right thigh (RightUpLeg), Rell = field rifle slung on his back
  (Spine), Vex = holster is part of his mesh (city guard; weapons are holstered inside Ward per Rell's dialogue).
- Unity: `Editor/WardNpcInstall.cs` (idempotent): builds `Prefabs/WardNpcs/<Name>.prefab` per NPC like
  SalvageDealer; in the scene, the old guard visual is deactivated (kept for rollback), the new prefab instance is
  added under the gameplay root and `NpcAgent.actor` repointed. Roots, colliders, definitions, dialogue, routes kept.

## Log
- 22:40 concept prompts written (`concept/p_*.txt`); Codex generating `concept/<name>_sheet_v1.png` (gen.sh).
- 22:45 six concept sheets done (`concept/<name>_sheet_v1.png`, prompts `concept/p_<name>.txt`, Codex logs). All six read
  as intended; Rell's "open-face helmet" came out as a riveted head band (kept).
- 22:47 Meshy multi-image-to-3D submitted for all six (`meshy/ward-npcs-20261003/npc_meshy.py`, pose_mode a-pose
  accepted, 60k triangles, PBR). Each NPC: model 30 + rig 5 + two clips 3+3 = 41 credits.
- 23:05 mira/torr/ossa rigged with clips; `Editor/WardNpcInstall.cs` written (import, prefab, install, verify,
  capture, rollback). Blender inspection running (`inspect_npc.py`, renders in `<npc>/renders/`).
- 23:30 all six rigged with clips (246 credits total; balance 863 -> 607 includes other agents). Blender inspection
  sheets `meshy/ward-npcs-20261003/<npc>/renders/sheet_all.png`: all six accepted for installation.
- Unity import/prefab: fixed holster/rifle side (Unity +X is the character's right). Linn's rig output lost its PBR
  set -> `linn_material.py`.
- Faceted faces in Unity: traced (normal map off/on, tangent w, green channel, live vs baked capture) to Meshy's
  near-flat normals + compensating normal map not reproducing in Unity; fixed by `prepare_unity.sh` (smooth normals,
  normal map re-baked in Blender, MikkTSpace tangents). Captures now use live skinning (BakeMesh copies lack tangents).
- Rell's rifle re-mounted flat against the back (flank on the back, magazine down-right); review cameras pulled in front
  of obstructions (the first back camera was inside a wall).
- Edit Mode 255/255 (`unity/evidence/ward-npcs/20261003/editmode.xml`). Two tests updated because they encoded the
  single-guard-model state: CharacterFeelTests.GuardModelCharactersDoNotShareOneScanningLoop now tests each NpcAgent's
  driven actor (old guard actors remain inactive for rollback, so a name scan found 12); CheckpointAssetTests accepts
  the new Warden weapon mounts (holstered sidearm / slung rifle) besides the old open-hand sidearm.
- Verify (-nographics) OK: links, materials, clip paths, heights, soles, talk motion, mounts (no collider overlaps),
  gameplay snapshot (roots, definitions, dialogue, voices, colliders) identical to before.json.

## Status: installed, awaiting the combined native batch and Carl's review

## 3 Oct 01:05–: performance fix round (native bisect: six NPCs = 8.6 ms p50 at cam_hill, 4.4 ms at cam_gate)
- `meshy/ward-npcs-20261003/lod_blender.py` + `glb_lod.py` (run by `prepare_unity.sh`): LOD0 ~20k triangles (Decimate
  collapse on the mesh welded by position; head/neck vertex-group factor 4 so the face keeps its density: without it the
  face UVs smeared), LOD1 6.0–9.0k (Mira 9.0k, Linn 9.0k, Vex 7.8k, others 6.0k: welded UV seams stop the collapse
  earlier). Skin weights by bone name, glTF skin/armature unchanged, MikkTSpace tangents, normal map = normal_smooth.png
  (a fresh selected-to-active bake onto the decimated mesh came out with inverted texels per UV chart; decimation keeps
  UVs so the 60k smooth-normal bake fits). Blender A/B renders: `vex/renders/rigged_face*.png` vs `rigged_lod_*`.
- Unity (`WardNpcInstall`): LODGroup on Visual (LOD0 above 0.14 screen height ≈ 11 m, LOD1 to 0.012 ≈ 120 m, culled
  beyond); `updateWhenOffscreen = false` with localBounds (root bone frame) covering 16 samples of idle and talk, +12 %;
  `Animation.cullingType = BasedOnRenderers`. Verify checks all three. ActorLookAt's correction converges (slerp toward
  the target, not accumulating) while the Animation is culled, and the clip overwrites the bones again on return.
- Verify OK (gameplay snapshot unchanged), Edit Mode 255/255 (`editmode-lod.xml`). Face captures held
  (`captures/` now; the 60k captures kept in `captures-60k/`).
- Textures unchanged: 3 × 2048² BC7 + mips per NPC ≈ 16.8 MB, ≈ 101 MB for six (not streamed: glTF textures).
