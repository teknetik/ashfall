# Ward Guard — Unity handoff

This is an original white-armoured perimeter guard generated from the included front, side, and back concept views. Meshy generated the model and added a humanoid armature.

## Import

1. Copy `model/character-rigged.fbx` into the Unity project's `Assets/Characters/WardGuard/` folder.
2. In the Model Importer, set **Rig → Animation Type** to **Humanoid**, then use **Configure** to inspect and correct the Avatar mapping before use.
3. Import `model/character-walk.fbx` and `model/character-run.fbx` as animation clips. Configure their Avatar source to the rigged character if Unity does not associate it automatically.

`model/character-rigged.glb` is included for inspection or non-Unity tooling. `model/meshy-manifest.json` records the source views, task IDs, scale (1.8 m), target topology budget, and hashes can be generated from the files if required.

The `references/` images are the source turnarounds and should be retained with the model.
