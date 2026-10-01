# West Gate arches — progress log (1 Oct 2026, batch 2)

Workstream brief: /home/teknetik/.local/state/ward-programme/prompts/08-west-gate-arches.md (review item 4).

**15:10 go-ahead received from the orchestrator (batch-1 build taken): install into the saved scene is now allowed**
(one-time install with rollback copy, verify -nographics; no player builds or native runs of our own).

## Done
- 15:00 Read brief, BRIEF.md (memory safety, revised DoD), AGENTS §1–8, perimeter walls README/layout.json.
  Gate = two Meshy `District gate` instances (prefab `Prefabs/District/gate.prefab`, chunk-rendered as
  `Chunk_9/10_District_gate_2_*`), rampart line x 46.3–49.7, arches centred z 0 and z 12. Through the arches: the
  enclosed strip (x 49.7–58) and the 3 m strip wall at x 59 (`COL_BLD_boundary_side`).

- 15:05 Arch geometry measured from the saved render chunks (`extract_gate_mesh.py` -> `gate_world.obj`,
  `gate_profile.json`, `review/gate_slices.png`): each Meshy instance = two piers (x 46.4-49.6) + a 2.1 m arch wall
  (x 46.95-49.05) with a 4.94 m opening (z ±2.47 about the arch centre), jambs vertical to ~y 5.0, basket head,
  crown y 6.74. Arch centres z 0 (spawn arch) and z 12. Strip beyond holds only the perimeter strip wall.

- 15:10 Fresh scene audit -> unity/evidence/west-gate-arches/20261001/audit-before.json.
- 15:15-15:40 author_gate_arches.py (Blender, masonry kit for the guard stones) -> Art/WestGateArches/Models/WGA_Gate{A,B}.glb
  (LOD0 25.4k/24.2k, LOD1 11.3k/10.1k, LOD2 1.5k/1.4k tris); review_gate.py Cycles renders review/r1 (fit in the real
  arch geometry, wicket, hinge/pintle, head grille, guard stone, LODs): reads as a sealed working gate; fixes applied
  (bar moved above the lock rail clear of the middle pintles, cover strip/stirrup z-fights, guard-stone batter side,
  outer skin seams, lighter LOD2).
- make_decals.py -> Textures/WGA_DecalCartRuts.png, WGA_DecalJambScrape.png. layout.py -> layout.json (gates, 12 decals,
  light spec, 6 cam_wga_* cameras); validation vs the fresh audit: 0 problems (spawn 4.1 m from the nearest new collider).
- Editor/WestGateArchesPass.cs written; compile-checked outside Unity (night_life check_compile.py): OK.

- 15:29 Unity `build` OK (prefabs WGA_GateA/B, 0 unmapped materials, 3 colliders, 1 light, 8 decals each;
  build-assets.json). First capture failed on a fake-null `??` camera lookup (fixed, compile-checked); capture requeued.
- Stencil decal atlas (KEEP CLEAR on the leaves, gate numbers 1/2 on the transoms) added to make_decals.py/layout.py.

- 15:31 Editor captures (in memory, scene not saved): unity/evidence/west-gate-arches/20261001/editor-pre1 (6 cams).
  Reads as a sealed working gate in the real lighting (spawn, front, close, wicket, head, threshold). Fixes: guard
  stones came out blue-grey (kit macro hue drift on two small stones; now warm tint, macro 0), KEEP CLEAR stencil too
  worn to read (wear lowered), gate numbers enlarged, ruts a little stronger.
- 15:36 Queued build,install,verify (-nographics) into the saved scene.

- 15:36 INSTALLED into the saved scene (install.json, rollback/before-west-gate-arches.unity); verify OK.
- 15:40 Editor captures of the installed gates (editor-after): KEEP CLEAR printed only on frame members (projector box
  5 mm short of the boards) -> stencil and grime decals moved; 15:41 build,reinstall,verify -nographics OK (lights
  re-hooked); editor-after2 confirms the stencil.
- Evidence README, art README, DOCS_SNIPPET.md written.

## State: DONE (15:50), pending the orchestrator's combined test (frame time, 20:30 look, city loop)

## Next (only if the combined test reports defects)
- Night tune of the bulkhead (intensity/range/lens), larger gate numbers, stronger ruts if they vanish natively.
