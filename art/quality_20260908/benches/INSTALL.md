# Bench integration handoff

Prepared source candidate; root owns Unity integration and native review.

1. Wait for compilation, save the authored AthenHill scene and run `AthenHill.Editor.WardBenchPass.Install()` through Unity MCP, or **Athen Hill → Quality → Install authored plaza benches**.
2. The helper checks the exact six old primitive renderers, two placements and absence of pre-existing bench colliders. It refuses to overwrite a previous installation. It creates ordinary mesh/material/prefab assets, disables only the two old plaza bench sets, and adds two prefab instances at their original centres. Original primitive objects remain recoverable.
3. Save assets, explicitly rebuild render chunks, save and reopen the scene. The helper does not build, rebuild chunks or certify visuals.
4. Build native Linux and capture front, side, rear, seat/support joints and underneath each bench at player height, with the existing 1.8 m actor. Inspect source metal/wood distinction, grain direction, edge quality, fixings, source shadows and all foot contacts in sun and shade. The source studio renders are not game evidence.
5. Walk around both ends of both benches with real input. Check the hill approach, avenue path, camera clipping and the new mass-following collision proxies; no sitting behavior is added. Record cost in the changed native scene.

Original sources, retained CC0 maps, material packing code, explicit mesh JSON and Blender document are in this directory or the linked provenance directories in `BRIEF.md`. `geometry-report.json` and `buffer-validation.json` are authoritative for the exported revision. Retained `revision-01` is the rejected source audition, not the installation target.

No TODO checkbox or AAA acceptance follows from the installer or these source views. Independent native review is still required, and the four separate perimeter benches remain outside this bounded replacement.
