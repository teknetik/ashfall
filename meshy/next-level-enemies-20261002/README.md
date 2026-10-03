# Next-level Outer Berms enemies: Scrap Reaper, Ironclad Warden, Post Sentinel (2 October 2026)

Carl delivered three Meshy models (web app, staged in `meshy/incoming-20261002/`) for "3 more enemy droids for the outer
berms ... higher level droids". This folder holds their inspection, preparation and the records the Unity installer
(`unity/AthenHill/Assets/AthenHill/Editor/NextLevelEnemiesInstall.cs`) reads.

## Meshy manifest

**No Meshy API tasks were ordered by this pass (0 credits).** The models were rigged and animated by Carl in the Meshy
web app (UE/Mixamo-named skeletons, walking + running clips). Web-app rig tasks are not listed by the API
(`GET /openapi/v1/rigging` shows only the three API rigs of earlier passes), so library clips cannot be ordered against
these rigs; every clip beyond walk/run is procedural (below). Balance at the time: 82 credits; re-rigging both bipeds
through the API and ordering four library clips each would cost about 34 credits and is the recommended follow-up if the
procedural attack/death clips are judged too stiff.

| Delivered file | What it is | Measured |
| --- | --- | --- |
| `Meshy_AI_Ironclad_Warden_biped/*_Walking|Running_withSkin.glb` | **A bearded human in a tactical shirt, knee pads and a holstered pistol**: Carl's new model for the salvage NPC **Brann** (coordinator decision, 2 Oct evening), delivered under a droid-sounding name. 66 joints (`pelvis…head`, `mixamorig:*` end bones, fingers), 11,358 tris, 1.70 m, faces +Z, standing rest pose. The hostile "Ironclad Warden" droid built from it first is retired (`Prefabs/OuterBerms/Retired/`). | walk 1.042 s in place (1.36 m/s), run 0.667 s (4.52 m/s) |
| `Meshy_AI_Scrap_Reaper_biped/*` | Feral industrial droid: hunched biped, left claw, right-arm cylindrical weapon with a red lens, spiked plates. 43 joints, 8,573 tris, 1.70 m, faces +Z. | walk 1.042 s (1.29 m/s), run 0.667 s (4.44 m/s) |
| `Meshy_AI_Post_Sentinel_1002142607_texture.glb` | One-wheeled "POST" courier droid: parasol hat with two antennae, boxy torso, a rifle in the right hand pointing down. Static mesh, 8,608 tris in 4,478 loose parts, 1.894 m, faces +Z. | wheel radius 0.21 m (hub x 0.016, z −0.009), rifle tip at (−0.17, 0.54, 0.14) |

## Scripts (run order)

1. `inspect_models.py` (Blender 5.2 headless, `~/.local/state/ward-programme/blender.sh`): rest pose, walk/run frames and
   close-ups beside a 1.8 m marker, sentinel height bands and loose parts → `renders/`, `inspect.json`.
2. `prep_models.py` (`uv run --offline --with pillow --with numpy python prep_models.py`): per rig `<key>/build/<Name>_geo.glb`
   (Walking GLB without animations/images, WEIGHTS_0 renormalised, JOINTS_1/2 + WEIGHTS_1/2 dropped: glTFast skins four
   influences), `<key>/build/anim/*.glb` animation-only clips (walk, run from the delivered files; procedural idle, attack,
   hit, death), `<key>/build/clips/*.glb` with geometry for review, `<key>/textures/<Name>_{BaseMap,Normal,Mask}.png`
   (Mask: R metallic, G 1, B 0, A smoothness = (1 − roughness) × 0.85). Sentinel: `sentinel/build/PostSentinel_geo.glb` with
   the tyre split per triangle (every vertex inside a 0.216 m cylinder about the hub axis and within the 15 cm tyre band;
   582 triangles) into a `Wheel` mesh node pivoted on the hub under `Body`, plus `Muzzle`, `Head`, `Hat` nodes; origin at the
   wheel's contact point. → `handoff.json`.
3. `review_clips.py`, `review_side.py` (Blender): frames of the procedural clips and the wheel split → `renders/review_*`,
   `renders/sheet_review_*.png`.

### Procedural clips (30 fps, bone rotations about world axes applied in hierarchy order on the rest pose + pelvis translation)

| Clip | Warden | Reaper | Notes |
| --- | --- | --- | --- |
| idle | 3.0 s loop | 3.0 s loop | breathing sway: spine ±1.2°, head yaw ±3°, arms ±2°, pelvis −8 mm |
| talk (Brann only) | 4.0 s loop | – | counter talk: head nods and glances, the right hand rises in an explaining gesture (upper arm −38°, forearm −55°, wrist waves) and settles, a small weight shift |
| attack | 1.1 s, "hammer": right fist back and up, torso wound, overhand blow with the hips driving forward; blow at 0.52 | 0.8 s, "slash": both arms wind back, sweep forward and across; blow at 0.49 | FeralDroid plays it at a rate that lands the blow on the wind-up; `attackImpact` from `handoff.json` |
| hit | 0.6 s | 0.6 s | torso and head flinch back, arms up, pelvis back 7 cm; returns to the stance |
| death | 2.4 s | 2.0 s | stagger, drop to the knees, topple forward prone (ClampForever) |

Known limits: no finger motion; the Warden's "hammer" reads as a heavy punch (no weapon in hand); the kneel of the death
clip is quick; the Reaper's claw and weapon do not articulate beyond the arm chain. All of this is a first procedural pass
to be replaced by Meshy library clips if credits are approved.

## Brann (2 Oct, evening)

The Unity `brann` step (`NextLevelEnemiesInstall.Brann`) rebuilds `Prefabs/SalvageDealer.prefab` in place on this rig: uniform
scale 1.059 (standing idle 1.70 → 1.80 m at the soles), clips idle / talk (procedural) and walk / run (delivered), legacy
`Animation` driven by `ActorAnimation` (walk stride 1.36 m/s, run 4.52 m/s), `ActorLookAt` on `head` / `neck_01`, material
`NL_IroncladWarden` (URP Lit), rendering layer mask 129 (interior lighting). The previous Meshy hauler prefab is kept as
`Prefabs/Retired/SalvageDealer_hauler_20261001.prefab`.

## Outputs used by Unity

`handoff.json` (stride speeds, bone names, rest positions, clip lengths, sentinel wheel/muzzle/head), the geometry GLBs,
animation GLBs and texture sets. The installer copies them to `Assets/AthenHill/Art/OuterBerms/NextLevel/`.
