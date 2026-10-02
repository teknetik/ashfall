# Brann, salvage dealer (1 Oct 2026)

Carl asked for the Salvage shop on the north avenue to become walkable with "an npc to trade with". This folder turns
the unused roster model `meshy/npc-roster-20260927/salvage_hauler` (burly bearded man, grey work shirt, cargo trousers
with knee pads, tool belt and holsters; text-to-3D preview `01a0e309-1690-7453-a61b-8b153dc030da`, refine
`01a0e30a-5208-7521-afd7-37a730a8537e`, 2k PBR) into a rigged, animated shopkeeper for Unity
(`unity/AthenHill/Assets/AthenHill/Prefabs/SalvageDealer.prefab`, built by `Editor/ImportSalvageDealer.cs`).

## Meshy tasks (`rig_dealer.py`, `record.json`)

The API key is read from `MESHY_API_KEY` in the environment only.

| Step | Task | Request | Credits | Outcome |
| --- | --- | --- | --- | --- |
| Old rig lookup | `01a0e30c-8256-72b3-b5fc-403481bc6b6d` (27 Sep) | GET v1/rigging | 0 | 404 "Rigging task not found" |
| Rig from refine task | – | POST v1/rigging `input_task_id` refine, 1.82 m | 0 | 400 "Input task not found" (expired) |
| Rig | `01a0f911-a342-77b2-8a5e-c1b68c294d8d` | POST v1/rigging `model_url` = data URI of `salvage_hauler/textured.glb`, `height_meters` 1.82 | 5 | `rigged.glb` (24 bones incl. `Head`, `neck`, `headfront`), `basic_walk.glb` |
| Idle 6 | `01a0f912-1b88-7368-b940-bac35b74682a` | v1/animations action 246, change_fps 30 | 3 | `idle_246.glb`, 7.4 s. **Installed idle.** |
| Idle 12 | `01a0f912-1e44-716f-8663-12ab660236fb` | action 252, change_fps 30 | 3 | `idle_252.glb`, alternate |
| Talk with Left Hand on Hip | `01a0f912-2435-7087-b3bf-8e5f6bdf7a9c` | action 309, change_fps 30 | 3 | `talk_309.glb`. **Installed talk.** |
| Talk with Hands Open | `01a0f912-20e4-7441-be7a-5fdefbdfd0a6` | action 313, change_fps 30 | 3 | `talk_313.glb`, alternate |
| Talk with Right Hand Open | `01a0f912-26a6-7171-bfc0-79f59a144f1d` | action 314, change_fps 30 | 3 | `talk_314.glb`, alternate |

Total: **20 credits** (pre-approved routine rigging/animation, AGENTS.md §5). Other library clips considered from their
previews (`previews/sheet_*.png`): 34 Checkout Gesture (a hand-to-chest bow, not an idle), 56 Stand and Chat, 315 Hand
on Hip Gesture, 47 Listening Gesture; the scanning/guard idles were avoided.

`strip_clip.py` writes `anim_only/<clip>.glb`: the same file without the duplicate mesh, skin and textures
(node hierarchy, scenes and animation accessors byte-identical, verified in the script; every clip's skeleton rest
transforms equal `rigged.glb` exactly). These ~130–230 kB files are what Unity imports as `Source/*.glb`; the full Meshy
downloads stay here.

## Inspection (headless Blender 5.2, Cycles CPU)

Scripts: `inspect_blender.py` (rest views, face, hands, feet, mid frames, `inspect.json`), `inspect_stretch.py`
(skin stretch per bone, shoulder/hip close-ups, `stretch.json`), `inspect_counter.py` (customer's view over a 0.95 m
counter at three phases per clip, hand reach, `counter.json`). Renders are in `renders/` (untracked).

Model: 41,416 triangles, 46,622 vertices, one material, three 2048² JPEG maps (base colour sRGB; metallic-roughness
with metallic B mean 0.003 / p95 0.012, so no accidental metal; roughness G mean 0.65; normal map). Rest A-pose height
1.82 m; the standing library poses are taller (about 1.89 m) and stand 9–12 cm below the rest-pose origin, because the
rest pose has the legs spread wide. Unity scales the standing idle to 1.82 m uniformly and lifts each clip.

Good: readable face and beard (`renders/face.png`), boots and laces, shirt pockets, belt and holsters, clean silhouette
from front, side and back (`rest_*.png`). Talk 309 reads as offering or explaining across a counter
(`talk_309_mid_threequarter.png`, `strip_counter_talk_309.png`).

Known defects (Meshy auto-rig on a wide A-pose source; none blocks a counter placement):

- Hands are sculpted mitts with no finger bones; fingers are partly fused at close range (`hand_left.png`).
- Shoulders bulge when the arms come down from the A-pose (`idle_246_shoulders.png`, `idle_252_shoulders.png`).
- The right forearm/hand passes through the hip holsters in both idles (`idle_252_hips.png`, `idle_246_hips.png`),
  and the crotch stretches in the weight-shift idle (stretch dominated by Hips/UpLeg, `stretch.json`). Both sit below
  a 0.95–1.0 m counter top.
- Talk 309 stretches the back strap behind the raised right arm (`talk_309_hips.png`); visible only from behind or the
  far side.
- Talk 313 drops both hands to counter-top height in front of the body (`strip_counter_talk_313.png`); it would clip
  a counter placed close to him, so it is kept as an alternate only.
- Idle 246 tilts the head; `ActorLookAt` levels 70 % of it at rest and turns it to the player in focus.

`inspect.json`'s `bone_motion_deg` values near 360° are quaternion sign flips in that Blender measure (read them as
360 minus the value); the Unity verify below measures bone motion with `Quaternion.Angle`.

## Unity (assets only; the city scene is not opened or saved)

`unity/AthenHill/Assets/AthenHill/Editor/ImportSalvageDealer.cs`, run with
`~/.local/state/ward-programme/unity.sh <log> AthenHill.Editor.ImportSalvageDealer.RunBatch -nographics --steps import,prefab,verify`.
Results: `unity/evidence/salvage-shop/20261001/dealer-import.json` and `dealer-verify.json`.

- `Art/Imported/Meshy/SalvageDealer/SalvageDealer.glb` (= `rigged.glb`, glTFast, animation method Legacy; its three
  2048² maps compressed to BC7 by `GltfTextureCompression`: base colour sRGB, normal and metallic-roughness linear).
- `Source/*.glb`: the animation-only clips (Legacy). `Clips/dealer_<clip>.anim`: bone rotations plus Hips translation,
  each lifted so the lowest sole is at y = 0 over its loop (idle 246 +0.118 m, idle 252 +0.105, talk 309 +0.110,
  talk 313 +0.097, talk 314 +0.089 at prefab scale), loop seam eased over 0.3 s (largest seam 0.02, talk 314).
- `SalvageDealer.mat`: editable copy of the imported material on `Shader Graphs/glTF-pbrMetallicRoughness` (the Ward
  Guard's shader family), double-sided as Meshy authored it, metallic/roughness from the texture (factors 1).
- `Prefabs/SalvageDealer.prefab`: root `SalvageDealer` (ActorAnimation idle `dealer_idle_246`, talk `dealer_talk_309`,
  walk = run = idle; ActorLookAt with `Head` / `neck`) > `Visual` (uniform scale 0.9649: standing idle 1.8862 m -> 1.82 m)
  > glTFast instance `SalvageDealer` (Animation, clip paths `Armature/Hips/...` resolve here) > `Armature` / `char1`
  (SkinnedMeshRenderer, shadows on, update when off-screen). Faces +Z, feet at y = 0. No colliders.
- Verify: 41,416 triangles, 46,622 vertices, 24 bones, 4 bones per vertex, no blend shapes; idle and talk resolve every
  bone path, 20 bones move more than 1° in each, sole at frame 0 is 0.001 m (idle) / 0.000 m (talk), idle height 1.82 m.
