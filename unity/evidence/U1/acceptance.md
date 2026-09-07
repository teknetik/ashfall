# U1 import baseline — 7 September 2026

Technical baseline accepted with open visual/performance work. Actual MCP scene
assembly and captures completed in Unity 6000.6.0f1, URP 17.6.0, glTFast 6.20.0.

- Saved `Assets/AthenHill/Scenes/AthenHill.unity`; six fixed cameras and character/portrait review cameras.
- Asymmetric GLB: source +X=3 becomes Unity X=-3; source +Z=5 stays Z=5. The data conversion is (-x,y,z), once, with no negative root scale.
- 262 authored collision proxies plus ground = 263. Box bounds retain local transforms. Cylinders use their simple convex imported mesh; shadow proxy is excluded from collision.
- Candidate: 9 meshes, 35,029 total source triangles, four imported legacy clips. COLOR_0, both UV channels, UV-selection keywords, hair/beard/eyebrow cutout and eyes clearcoat retained. Review report records every mesh and material.
- Candidate shadow proxy stays enabled as ShadowsOnly; visible meshes receive shadows without duplicate shadow casting.
- Actual Play mode snapshot confirms both imported actors running idle, all clips registered. Detailed locomotion transitions are U2 work.
- Actor prefab variants expose clips and stride calibration. Paving and its joints are ordinary editable scene objects; raw world remains a modular imported prefab instance.
- Final Console error query: zero entries.

Open issues: initial lighting is darker than the browser baseline, foliage needs the browser's cutout adaptation, no finished material/visual scorecard. Initial unbatched view recorded 441 draws, so the 80-draw performance gate is NOT passed. Geometry remains editable; batching will retain source modules. Player camera/ground contacts are not yet traversal-qualified.
