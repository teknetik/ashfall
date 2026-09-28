# West Gate checkpoint — 26 September 2026

Requested scope: clarify Ossa and the arms locker, establish two visibly armed Wardens with a booth and defensive barriers, add local foliage, and replace the disc-shaped target with pillow feet. Preserve the three robot models accepted by the user and the working city/Outer Berms loops.

## Saved content

- Warden booth: 3.8 × 4.6 m footprint, 2.9 m roof, open front, counter/radio, solar panel, wiring, bench and practical light.
- Dedicated cyan-lit ARMS LOCKER, 1.22 × 1.7 × 0.66 m, preserves the existing interaction root and single pistol issue.
- Ossa and Rell: named NPC dialogue roots, existing Ward Guard model and existing scrap pistol attached to the hand. Secured sidearms are visual equipment; guard combat AI is not introduced.
- Four tapered barriers, ten existing drought shrubs fitted to ground and 180 localized grass tufts, clear main route.
- Three Meshy steel target plates on authored hinged, braced stands, separate numbered bullseye decals; preserved health, collision and tutorial callbacks.
- Inspectable briefing board and a range reset station. Reset is available during the target lesson or after completion; it cannot bypass the encounter/reward sequence.

`author_checkpoint.py`, `author_target_stand.py` and `prepare_target.py` were run through live Blender MCP. `.blend` files retain geometry/material sources, GLBs feed saved Unity content. Source box collision proxies remain separate. Uniform scale only. Existing CC0 Ward retrofit materials and textures are reused; see `art/ward_retrofit_20260926/README.md` and its source manifests. Groundcover uses the existing HillGrass material. Target decal lettering is rasterized Liberation Sans Bold; no font binary is redistributed by this pass. Unity signs use the engine’s built-in LegacyRuntime font; this pass does not redistribute a font binary. A dedicated depth-tested URP lettering shader prevents signs showing through other objects.

`WestGateCheckpointPass` and `CheckpointRangePass` are narrowly scoped Editor-only installation helpers. They preserve original models and interaction roots, refuse duplicate installation, and save editable scene content. Rejected robot candidates remain outside shipping Assets as provenance. The original target is retained inactive in the prefab for recovery. `unity/evidence/checkpoint/20260926/scene-before-checkpoint.unity` is the scene backup before this pass.

Source/runtime audits: `geometry.json`, `target-runtime.json`, `ground.json`. Candidate drone source audits are historical unused production work, not evidence of an installed replacement. Final native verification and remaining defects are recorded under `unity/evidence/checkpoint/20260926/`.
