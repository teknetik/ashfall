# Ranged Outer Berms enemies: feral gunner droid and feral lancer drone (2 Oct 2026)

Carl asked to "use meshy to create 2 more enemies a bit further out that use ranged weapons for more of a challenge"
in the Outer Berms (desert scrub outside the West Gate; feral industrial droids are the enemy). The Berms are being
expanded to about 500 m across, so these enemies engage at 20–35 m: the gunner's shot and the lancer's silhouette and
amber eye were judged at game distance (renders `*_game25m*`, `*_game35m*`: 60° vertical FOV at 1080p, 1:1 pixels).

This folder holds the concepts, Meshy task records, Blender/numpy processing scripts, inspection renders (untracked)
and the hand-off for the gameplay prefabs. Unity side: `unity/AthenHill/Assets/AthenHill/Editor/OuterBermsRangedEnemies.cs`
(steps import / prefab / verify) builds the two **visual** prefabs, with no gameplay components:

- `Assets/AthenHill/Prefabs/OuterBerms/Visuals/FeralGunnerVisual.prefab`
- `Assets/AthenHill/Prefabs/OuterBerms/Visuals/FeralLancerVisual.prefab`

`handoff.json` lists what the gameplay prefab needs (paths, clip names and lengths, muzzle and optic, toe bones, rotors,
sizes, triangle counts, recommended FeralDroid wiring). Evidence: `unity/evidence/ranged-enemies/20261002/`
(`import.json`, `verify.json`).

## Design (house style)

Original designs for Tir: salvaged industrial machines gone feral, amber-red optics, sun-faded paint, rust, sand grime,
wear at joints and edges, realistic hard-surface sci-fi, no text or logos.

- **Feral gunner droid** (biped, ground ranged): a lean, upright 2.0 m former security/survey droid in faded
  olive-drab and slate-grey armour over a gunmetal frame, a narrow head with one amber-red optic, a whip antenna on the
  left shoulder, and a salvaged long rivet/arc gun strapped along its RIGHT forearm, the barrel reaching about 0.5 m past
  the claws. Clearly distinct from the bone-white/rust-orange cargo-lifter worker droid.
- **Feral lancer drone** (hover, aerial ranged): 1.8 m wide (2.15 m long with the lance), an armoured wedge hull in
  faded oxide-red over dull steel, four ducted fans at the corners (larger at the rear), an underslung long "arc lance"
  with copper coils and a slotted muzzle shroud, and one large amber-red eye in an armoured socket on the nose.

## Concepts (Codex image tool, free on Carl's plan)

`concepts/` (images untracked; prompts and provenance in `record.json` → `concepts`). Front views first, then side/back
views generated from the front view as a reference (`run_codex.sh NAME ref.png`):

| Concept | Outcome |
| --- | --- |
| `gunner_front/side/back.png` | Accepted (A-pose, separated limbs, gun on the right forearm). |
| `lancer_front.png`, `lancer_back.png` | Accepted. |
| `lancer_side_rejected_v1.png` | Rejected: the four ducts were drawn stacked and offset in profile; regenerated as `lancer_side.png` with an explicit layout. |
| `gun_side/top/quarter.png` | The gunner's forearm gun on its own (Meshy dropped the gun from the full-body model, below). |

## Meshy tasks (`gen_model.py`, `rig_gunner.py`, `record.json`)

The API key is read from `MESHY_API_KEY` in the environment only. Multi-image-to-3D: `ai_model latest`, PBR, 2k
textures, quad remesh, `save_pre_remeshed_model`, texture prompt per enemy, `image_enhancement`, `remove_lighting`.

| Step | Task | Options | Credits | Outcome |
| --- | --- | --- | --- | --- |
| Gunner model a1 | `01a0fbb0-537d-7542-9a0a-3b2cf6f4b5b6` | front/side/back concepts, `pose_mode a-pose`, 40k polycount | 30 | **Used.** Body, head, optic, antenna and plates match the concept; clean A-pose. The forearm gun was **not** generated (only a slim forearm), so the gun was made separately. 86,644 tris (40k quads). |
| Lancer model a1 | `01a0fbb2-cd35-73cd-bddd-06972c5abe81` | front/side/back concepts, 40k | 30 | **Used** after processing (below). Faces glTF −X; the four ducted fans have fused, warped blades. 80,741 tris. |
| Forearm gun a1 | `01a0fbbc-1025-7497-8e38-543d4cc100c5` | side/top/three-quarter gun concepts, 20k | 30 | **Used.** Clean receiver, copper coils, ribbed barrel, slotted muzzle shroud with an open bore; its two hanging D-ring handles were replaced (below). 41,553 tris. |
| Gunner rig | `01a0fbb8-d409-77d6-953a-3104a1472087` | `model_url` = data URI of `gunner/a1/model.glb`, `height_meters` 2.0 | 5 | `gunner/rig/rigged.glb`: 24-bone Meshy humanoid (incl. `Head`, `headfront`, `LeftToeBase`, `RightToeBase`), armature scale 0.01 (cm), plus basic walk/run. |
| 20 library clips | `01a0fbb9-…` (ids in `record.json` → `gunner_rig.animation_tasks`) | `change_fps` 30 | 60 | Candidates chosen from the preview GIFs (`previews/sheet_*.png`), judged on the gunner itself (`renders/gunner_rig/*_p0..p3.png`). |

**Total: 155 credits** (pre-approved routine generation/rigging/animation, AGENTS.md §5). Balance 597 → 272 over the
same window; the difference beyond 155 was spent by other sessions.

### Library clip choices (gunner)

The library has no one-armed arm-cannon shot: the shooting clips are two-handed rifle/pistol holds (95 Gun Hold Left Turn,
98 Run and Shoot, 234 Walk Forward While Shooting, 232/236 quick-draw pistol), and 528 "Walk Left with Gun" turns the
body sideways. So the ranged clips are **procedural layers on library bases** (`make_gunner.py`):

| Clip | Source | Notes |
| --- | --- | --- |
| `idle` | 2 Alert | Alert, slightly hunched; gun arm low and forward. Alternates: 11 Idle 1, 89 Combat Idle (hips offset 36 cm). |
| `walk` | rig basic walk | In place, 1.07 s. Alternates: 30 Casual Walk (3.3 s), 21 Walk Fight Forward. |
| `run` | rig basic run | In place, 0.67 s. Alternates: 14 Run 2, 511 Rifle Charge (root motion 2.8 m). |
| `aim` | 2 Alert + aim layer | Right arm locked on the target: upper arm forward 12° down / 6° out, forearm and gun level, back of the forearm up and rolled 15° outward, torso bladed 10° (right shoulder forward). Loops. |
| `fire` | aim + recoil | One shot from the aim pose: shot at 0.05 s; arm pitches up 12° plus 6° muzzle climb, right shoulder kicks back 5°, torso leans back 3.5°, head 3°, hips back 2.5 cm; settled by 0.6 s; starts and ends in the aim pose (FeralDroid `attack` with `fireClipPerShot`). |
| `fire_raise` | 2 Alert + aim + recoil | Raise from the idle arm (0–0.30 s), hold, the same shot at 0.55 s, settled in the aim pose by 1.2 s (for a flow without a separate aim wind-up). |
| `strafe_left` / `strafe_right` | 525 / 526 Cautious Crouch Walk Left / Right + aim layer | Made in place (hips drift removed; native sideways speed 1.15 / 0.98 m/s), gun arm aimed forward. |
| `hit` | 177 Gunshot Reaction | First 1.0 s, eased back to its first frame over the last 0.35 s. Alternates: 172 Electrocution Reaction (3.7 s), 178 Hit Reaction (steps 0.94 m sideways). |
| `death` | 183 Shot and Fall Backward | Falls about 1.1 m back, lands at 2.5 s, 3.5 s. Alternates: 181 Electrocuted Fall (5 s), 184 Shot and Fall Forward. |

Rejected as primary clips: 89 Combat Idle (shield-guard pose, hips off origin), 192 Right Jab (punch), the spell casts.

## Processing

### Gunner (`prep_gun.py`, `make_gunner.py`, `make_textures.py`, `strip_images.py`)

- **Gun** (`prep_gun.py`, Blender): uniform scale to 0.85 m, muzzle to glTF +Z, the two hanging D-ring handles (holes run
  sideways, so they cannot hold a forearm laid along the gun) removed and replaced by two authored rounded steel strap
  bands around the forearm and receiver (UVs from the removed handle texels: same material). A child empty `Muzzle`
  sits 1 cm ahead of the bore. 33,446 tris. Renders `gunner/renders/gun_*.png`.
- **Mount** (`make_gunner.py`, numpy, no Blender round trip): the gun is added to the Meshy rig GLB as a rigid child node
  of `RightForeArm` (origin on the bone axis 0.26 m from the elbow, barrel along the bone, top on the back of the forearm
  opposite the claws, measured from the rest mesh), so the rig's own nodes, skin and mesh stay byte-identical and every
  Meshy clip still applies. The gun's rear end sits 5 cm behind the elbow; the muzzle is 0.5 m past the wrist.
- **Clips**: rotations + Hips translation at 30 fps written as GLB animations on the merged rig (`gunner/build/clips`,
  full, for review) and animation-only copies (`gunner/build/anim`, imported by Unity).
- **Textures** (`make_textures.py`): URP Lit sets (BaseMap sRGB, Normal, Mask = metallic R / occlusion G / smoothness A
  = (1 − roughness) × 0.85) for the body and the gun. The Meshy emission maps are black, so `FeralGunner_Emission.png`
  is an optics-only map: the head optic's 17 forward-facing red-orange triangles rasterised into UV space at 2k, gated by
  texel redness and averaged down to 1024 (`renders/gunner_optic_emission.png`).
- `strip_images.py` writes the Unity copy of the merged rig without embedded images (the maps come in once, as PNGs).

### Lancer (`process_lancer.py`, `make_textures.py`)

Blender: turned to face glTF +Z, uniform scale to a 1.8 m span; duct circles fitted (2 cm walls); everything inside each
duct's inner wall removed (17,507 faces of fused, curled and holed Meshy blades and shards, plus 20 vertices of loose
shard islands); per duct an authored static motor pod with three stator struts (body) and a spinning three-blade rotor
with spinner (`Rotor A` front-left, `B` front-right, `C` rear-left, `D` rear-right; diagonal pairs share a blade hand;
pivot on the hub, spin axis local Y); the authored parts use a small UV patch of dark steel on the body atlas. A torn
open hole in the hull top (found as a pit in a ray-cast height field) is covered by a bolted steel hatch plate. An
emissive `Lens cap` dome (5.8 cm radius) over the eye socket and a `Muzzle` empty 1 cm ahead of the lance tip.
Origin: centre of lift (rotor hubs' centroid) at the hull's mid-height. Exported without images.

## Inspection (headless Blender 5.2, Cycles CPU; renders untracked)

`inspect_static.py` (source models: views with a 1.8 m marker, close-ups, back-face check, loose parts, open edges),
`inspect_rig.py` (rest pose and every candidate clip, four phases each), `inspect_gunner.py` (merged gunner per clip: gun
clearance from the body, muzzle path, fire/aim views at 6 m and game views at 25/35 m), `process_lancer.py` renders.

Gunner (renders/gunner_a1, gunner_rig, gunner_build):

- Good: silhouette and proportions read as a lean security droid next to the 1.8 m marker; optic, antenna, plates and
  joints are clean; normals mostly front-facing; the arm-extended aim and the recoil kick read clearly at 25 m and 35 m
  (`fire_*_game25m.png`, `*_game35m_side.png`); the muzzle tracks the barrel (forward within 0.1° in the aim pose).
- Known defects: the hands are three-fingered claws with partly fused fingers (as concept, Meshy auto-rig has no finger
  bones); a few small inner shell faces are back-facing (single-sided URP materials show them as pin-holes at close range);
  in `run` the gun passes close to the thigh/torso for a few frames (80 sampled gun vertices within 1.5 cm at one frame);
  `aim`/`fire_raise` touch the torso armour lightly (32 vertices) when the alert idle leans; in `death` the barrel rests
  on the ground; the strap bands carry a stretched (stripy) patch of the handle texture; 86.6k (body) + 33.4k (gun) tris
  with no LOD yet.

Lancer (renders/lancer_a1, lancer/proc/renders):

- Good: bold silhouette (four large ducts, long lance), eye reads as a bright dot at 25–35 m with the lens cap lit,
  clean authored rotors and spinners, hatch covers the hull hole.
- Known defects: the lower inner lip of each duct keeps a ragged, toothed edge from the Meshy blades (visible from below
  at close range); the front pair of ducts is slightly smaller than the rear pair (as generated); rotor blades are simple
  twisted plates without their own texture detail; 64.6k body tris.

## Unity (assets only; the city scene is not opened or saved)

`OuterBermsRangedEnemies.RunBatch -nographics -quit --steps import,prefab,verify` via
`~/.local/state/ward-programme/unity.sh` (42 s, rc 0, 3.5 GB anon peak; verify: 0 failures). Assets:
`Art/OuterBerms/Ranged/` (`Models/FeralGunner.glb` = merged rig without images, `Models/FeralLancer.glb`,
`Source/gunner_*.glb` animation-only, `Clips/FeralGunner/<clip>.anim`, `Materials/FR_*.mat`, `Textures/*.png` BC7,
mip-streamed); prefabs in `Prefabs/OuterBerms/Visuals/`. Measured (`verify.json`, `handoff.json`):

- **FeralGunnerVisual**: root at the feet facing +Z > `Visual` (uniform scale 1.001; legacy `Animation`,
  playAutomatically off, culling BasedOnRenderers) > `Armature` (glTFast instance) > `char1` (SkinnedMeshRenderer,
  86,644 tris, 24 bones, root bone Hips, localBounds = all-clip envelope + 12 % per side, verified to cover every
  sampled frame) and `.../RightForeArm/ForearmGun` (33,446 tris) > `Muzzle`. Standing idle 2.00 m. Ten clips, every
  bone path resolves: idle 4.03 s, walk 1.07, run 0.67, aim 4.03, strafe_left 1.20, strafe_right 1.30 (loops); fire
  0.60 (shot at 0.05 s), fire_raise 1.20 (shot at 0.55 s), hit 1.00 (Once); death 3.53 (ClampForever). Lowest sole
  0.00 m over every clip except death (first frame 0.00). Muzzle in the aim pose: prefab (0.27, 1.65, 0.98), pointing
  +Z (level), 0.50 m ahead of the wrist; fire recoil peak 17.8° up. Native speeds: walk 1.65 m/s, run 5.85 m/s,
  strafes 1.15 / 0.98 m/s. Optic: the body renderer's material (`FR_FeralGunner`) has the optics-only emission map,
  `_EMISSION` on, RealtimeEmissive.
- **FeralLancerVisual**: root at the centre of lift facing +Z > `Visual` (glTFast instance) > `Body` (64,594 tris),
  `Rotor A..D` (448 tris each, local Y up, `Blur disc` child), `Lens cap` (`FR_FeralLancerLens`, emissive), `Muzzle`
  at (0.00, −0.24, 1.32) pointing +Z. Size 1.80 × 0.67 × 2.15 m. 66,694 tris total.
