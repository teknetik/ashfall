# Mining droid — Meshy text-to-3D, 26 September 2026

Hero asset for the aquifer pump station (lore: repurposed industrial mining droids).
Generated with `art/ward_retrofit_20260926/meshy_text_to_3d.py` (preview → PBR refine,
realistic, triangle remesh, 60k target). Prompt, negative prompt and task IDs are in
`task.json`; `model.glb` (60,706 tris, one material, 2k base/metal-rough/normal maps) and
`thumbnail.png` are the unmodified Meshy output. The key came from the environment only.

Outcome: accepted as a **standing four-legged walker** rather than the requested kneeling
droid with a drill boom (Meshy ignored those parts). Inspected before use: no floaters,
fused parts or holes seen at front/side/back views; lens faces source −Y.

Runtime: rigged by hand in Blender (`rig_droid.py`) — Meshy auto-rigging is humanoid-only.
Rigid hard-surface skinning (body + swing and foot bones per leg), `walk` and `idle` actions,
uniform scale to 3.4 m. Unity: `Art/WardRetrofit/MiningDroid.glb` (legacy clips),
`Prefabs/WardMiningDroid.prefab`, installed by `AthenHill.Editor.WardMiningDroidPass`.
