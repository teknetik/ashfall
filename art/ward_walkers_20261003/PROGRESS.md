# Ward ambient walkers (3 Oct 2026, overnight from ~02:15)

Brief: AGENTS.md section 3 lists "Three original ambient walkers: meshy/Meshy_AI_weathered_traveler_ri_biped" - the
same model three times. Make them distinct, role-appropriate Ward residents from lore.md; keep every route, root,
AmbientWalker setting and save/data reference; previous model recoverable. Inspect the yard mechanic; replace only if
clearly weak. Performance: LOD0 <= 20k, LODs, culled skinning. Budget ~200 Meshy credits.

## Survey (`unity/evidence/ward-walkers/20261003/survey.json`, read-only `Editor/WardWalkerSurvey.cs`)
Five AmbientWalkers in the scene: the three travelers (`Colonists/npc_walker_01..03`, child `Traveler` prefab instance,
10,177 tris, `updateWhenOffscreen` on, walkStrideSpeed 1.35 for every speed), the yard mechanic (Humanoid Animator,
5.6k) and the Ward mining droid. Walkers never stop (constant speed), so only a walk loop matters.

| Walker | Route | Speed | Role chosen |
| --- | --- | ---: | --- |
| npc_walker_01 | (16..38, -3.5..-2.5): the long east avenue lane from the West Gate, 46 m | 0.95 | Karaveen caravan porter (goods from the gate caravans to the market) |
| npc_walker_02 | (-4..3, 22..28): north loop beside the Quantum Tube gate, 26 m | 1.05 | nanofabrication technician (Tube goods node <-> workshops) |
| npc_walker_03 | (5..11, -23..-19): south loop in the hall district, 20 m | 1.15 | hydroponics grower taking harvest to market and food stalls |

Yard mechanic: rendered in Blender (`meshy/ward-walkers-20261003/review_mechanic/renders/sheet.png`): coveralls,
hi-vis vest, goggles; low-poly face facets at close range but readable at yard distance. Not clearly weak: left as is.

## Log
- 02:10 concept prompts (`concept/p_porter.txt`, `p_nanotech.txt`, `p_grower.txt`; Codex `gen.sh`), three sheets in ~1 min.
- 02:12 Meshy multi-image-to-3D x3 (`meshy/ward-walkers-20261003/walker_meshy.py`).
- 02:18 rigs + walks. Blender inspection: porter and Sel accepted. **Grower v1 rejected**: broken face texture and
  T-pose; its carry clip (551) is a shoulder carry with an arm out, 552 includes a bucket pick-up: no crate carry.
- 02:24 grower v2 concept (`p_grower_v2.txt`: straw hat, harvest satchel of greens in the mesh); re-generated; face OK.
- `Editor/WardWalkerInstall.cs`: import, prefab (in-place walk: hips drift removed, soles on 0, small loop seams
  closed; stride speed = root-motion speed or planted-foot speed; LODGroup LOD0 20k / LOD1 6k; bounds sampled over the
  walk; `updateWhenOffscreen=false`; `Animation.cullingType=BasedOnRenderers`), install (Traveler child inactive,
  new prefab instance beside it, `AmbientWalker.actor` repointed), verify, rollback, capture, diagnostics.
- Clip auditions to avoid foot sliding (rate = route speed / clip ground speed): Casual Walk 1.30 (porter), Walking Woman
  0.80 (Sel), basic walk 0.63-0.78, Walking 2 1.00 (porter) / 1.16 (Sel), Quick Walk 0.91 (grower). Kept the last three.
  Other agents' in-progress compile errors (FirstPersonRifleView/TutorialSetInstall) blocked two runs for a few minutes.
- 02:50 install + verify OK (`unity/evidence/ward-walkers/20261003/verify.json`): links, materials, no colliders on the
  moving visuals, LOD/culling settings, walk paths, soles, stride vs walkStrideSpeed, playback rates 0.91-1.16, walker
  snapshot (roots, routes, speeds, phases, turn settings, colliders) identical to `before.json`, mechanic untouched.
- Editor captures (`captures/`, 13:00): bodies read well. Face close-ups (1.15 m, low sun) show faceted/patchy shading.
  Investigated: same with LOD forced to 0, without the normal map, without received shadows, plain URP Lit, mip bias -4;
  Blender renders of the same LOD0 (rest and walk pose) and of Unity's own baked mesh are clean; the face follows the
  Head bone rigidly during the walk (spread p95 <= 1.2 cm, like Vex/Mira idles: `install-log.json` facecheck). So the
  geometry, UVs and skin are right; the remaining difference is Unity's shading of the 20k decimated face in grazing
  sun. Left for the native batch to judge at real viewing distance (ambient walkers are seen at >= 3 m).
- Edit Mode 255/255 (`editmode.xml`), no test changes.

## Status: installed, awaiting the combined native batch and Carl's review

## Recovery
The three `Traveler` children stay under each walker, inactive. `WardWalkerInstall.RunBatch --steps rollback`
reactivates them and repoints `AmbientWalker.actor`; the new prefabs (`Prefabs/WardWalkers/`) stay in the project.
Note: the old `ImportTraveler.Install` menu would destroy whatever `AmbientWalker.actor` points at; run rollback first.

## Cost notes (for the native A/B)
Before: three 10.2k-triangle travelers skinned every frame (`updateWhenOffscreen` on), one shared 2k texture set.
After: LOD0 20k inside ~11 m, LOD1 6k to ~120 m, culled beyond; skinning and animation stop off-screen.
Textures: 3 x (base colour, metal-roughness, normal) 2048 BC7 with mips ~= 50 MB (glTF textures, not streamed).
