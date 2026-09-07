# Unity NPC import and rebuild — 7 September 2026

## Current result: Unity only, travelers and relaxed guards

Unity is now the sole active game/build target. Browser development, builds and
tests are retired. The browser sources and shared authoring inputs have not been
deleted because they contain earlier uncommitted work; the project instructions
and main README explicitly mark them historical. Temporary browser conversion
code from this change was removed, and its development/preview servers stopped.

The saved `unity/AthenHill/Assets/AthenHill/Scenes/AthenHill.unity` now has:

- **Mira, Torr, Vex and Linn:** `WardGuard.prefab`, with the existing arm and forearm
  bones posed down at the sides. No new generation, mesh or rig is needed. Names,
  dialogue, shop behavior, gameplay roots and placements are retained.
- **npc_walker_01–03:** `Traveler.prefab`, imported directly by Unity from the
  supplied weathered-traveler walking FBX. Their existing waypoint references,
  speeds, phases and non-interactive behavior are retained.
- **Player:** existing `MeshyPlayer`, unchanged.

The traveler retains all **10,177 source triangles** and its **24-bone rig**; no
lossy geometry reduction is applied. Its original albedo, roughness and metallic
maps are imported at a maximum 2048px. A generated URP map packs metallic into R
and `1 - roughness` into alpha. The visual root is normalized to 1.8m; skin/bind
matrices were checked across 16 walk poses (height 1.734–1.800m, sole Y within
about 16mm of ground). The imported walking take is 1.033 seconds. Idle/talk use
its first pose; the unused run reference aliases walk, not a new running animation.

The guard retains its 5,999-triangle delivery mesh, texture and skin weights.
Its idle/talk states are static relaxed poses, not authored gesturing animations.
The native screenshot confirms the lowered arms, intact shoulders and hands.

Source identity checks:

- Traveler source FBX and Unity FBX both SHA-256
  `766192d8a8fb89490593df1ccd585e2645fef49ca17471b18def7076bec77a8e`.
- Relaxed guard staging GLB and Unity GLB both SHA-256
  `8640d10bc7dd8018bc825a1aa6281f75f442467bd9230a4579656605e96f7f9b`.

Reproduce from repository root:

```sh
npm run prepare:guard # Asset processing only; no browser game/build.
/home/teknetik/Unity/Hub/Editor/6000.6.0f1/Editor/Unity \
  -batchmode -nographics -quit -projectPath "$PWD/unity/AthenHill" \
  -executeMethod AthenHill.Editor.ImportTraveler.ImportAndBuild \
  -logFile /tmp/ao2-traveler-build.log
uv run --with python-xlib python unity/tools/check_npc_import.py
uv run --with python-xlib --with pillow python unity/tools/check_release_smoke.py
```

`ImportTraveler.ImportAndBuild` installs both current models into the existing
scene and rebuilds native Linux development and release players. Both builds
succeeded with zero errors and one reported warning each. Outputs:

- `unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64`
- `unity/AthenHill/Builds/Linux/AthenHill.x86_64`

Native evidence: `unity/evidence/ward-guard/20260907T194714Z/`. The rebuilt player
passed grounded walking/running, all six fixed cameras and the full city-loop
suite (four dialogues, buy/sell, Lattice, modal input, pause, inventory, notes,
credits and reset). Screenshots include the arms-down guard and roaming traveler.
Sampled 1080p camera FPS ranged from 321 to 856 on this RTX 3060 workstation.
The rebuilt release passed startup, keyboard input, visible pause UI and runtime
log checks, and correctly ignored the development QA option. Release evidence:
`unity/evidence/ward-guard/20260907T194959Z-release/`.
The draw recorder still reports invalid zeroes, so this is **not** certification
of the draw-call budget, a medium laptop, or final art-reference likeness.

## Historical initial guard import (superseded)

The following records the earlier browser/native import before the user switched
to Unity only and assigned the traveler. Its browser commands and asset assignment
are historical, not the current workflow.

The browser and Unity Linux builds now use the supplied Ward Guard for Mira,
Torr, Vex and Linn. Their names, dialogue, shop behavior and authored positions
are retained. The three ambient walkers retain `npcs.glb` and their routes.
The Unity player remains `MeshyPlayer`; the browser player is unchanged.

## Source and runtime assets

`meshy/ward-guard/model/character-rigged.glb` is the original source. Its 38,071
triangles caused the browser's total submitted geometry to reach 487,068 triangles.
`npm run prepare:guard` derives a 5,999-triangle, 6,032-vertex delivery mesh using
meshoptimizer, weighting normals, UVs and all 24 bone influences during reduction.
Surviving vertices retain the supplied skin weights and texture coordinates.
The original 2048px texture and all source files are retained.

The same resulting GLB is used at:

- `public/assets/ward-guard.glb`
- `dist/assets/ward-guard.glb`
- `unity/AthenHill/Assets/AthenHill/Art/Imported/Meshy/ward-guard.glb`

All three were verified with SHA-256
`04080f51d60778736804d59a91fbbe300ab2614b4ed4b52b775c5b44fafa6126`.
The browser validates a six-thousand-triangle ceiling, one material and 24 bones.
The Unity import checks the actual bone/bind-matrix geometry, about 1.797m tall,
with soles about 0.6mm above the origin. Unity's default BakeMesh scale handling
is not used to measure this centimetre-armature export.

The source GLB contains only one standing-pose keyframe. `idle`, `talk`, `walk`
and `run` are explicitly marked static fallbacks in its delivery metadata and
browser diagnostics; these are not four animated clips. The separate walk/run
FBX files remain available but are not used by the stationary talking NPCs.
The traveler FBX has not been assigned to any runtime actor in this change.

## Builds and verification

Reinstalled the locked Node dependencies to repair copied `.bin` launchers.
`npm run build` now succeeds normally. The 29 existing character regression
checks pass. Added a reproducible real-browser check:

```sh
npm run build
npm run preview -- --port 4174 --strictPort
node tools/verify-model-import.mjs
```

The production browser test checked the exact delivered bytes, loaded texture,
rig/scale, separate talking and ambient model assignment, four real-keyboard
conversations, moving ambient actors, player walk/run and all six fixed cameras.
It completed without browser errors. The six 1920×1080 views measured roughly
59.94–59.96 FPS, 45–49 submitted draws and 205,900–230,492 submitted triangles.
Screenshots were inspected for guard silhouette, texture and placement.
Evidence: `tools/model-import/2026-09-07T16-06-27.526Z/`.

Unity's `Athen Hill → Characters → Use supplied Ward Guard for talking NPCs`
imports the asset and updates the existing scene. It preserves NpcAgent roots
and GameSession references, and checks that the ambient actors and player visual
retain their references. `ImportWardGuard.ImportAndBuild` is the batch entry point.
Both Linux development and release builds succeeded with zero errors and one
reported warning each. Outputs:

- `unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64`
- `unity/AthenHill/Builds/Linux/AthenHill.x86_64`

Run the native check with `uv run --with python-xlib python unity/tools/check_npc_import.py`.
It temporarily uses the supported 1080p display mode and restores the previous mode.
It passed grounded walking/running, six camera captures and the existing complete
city-loop suite: all four conversations, modal input, buying a flask, selling
scrap, Lattice travel, pause, inventory/notes, credits and reset. The rebuilt
release also remained running through keyboard input with no logged exceptions.
Native evidence: `unity/evidence/ward-guard/20260907T160949Z/`.

Native sampled FPS ranged from 344 to 841 on this RTX 3060 workstation. Its draw
recorder returned zero despite visible rendering, so those zeroes are invalid
and do not qualify the Unity draw-call gate. These workstation checks do not
certify a medium laptop or final art-reference likeness.
