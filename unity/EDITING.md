# Editing Athen Hill in Unity

Engine editability is a project requirement, added by the user on 7 September 2026.

The port must save an ordinary Unity scene, modular prefab instances, materials,
animation assets and editable UI assets. Gameplay scripts expose tuning in the
Inspector. Dialogue, prices, NPC placement and routes belong in serialized data.
The city must not be recreated by a runtime scene-generation script.

Import/assembly helpers are Editor-only conveniences. Once a scene exists,
assembly must refuse to overwrite it. Subsequent changes use normal scene/prefab
editing or narrowly scoped operations. Original imported GLBs remain intact;
make prefab/material variants for adaptations. Generated render batches, if
needed, retain their editable source objects and have an explicit rebuild action.
Do not silently overwrite user edits or replace the city with one mega-mesh.

Current checkpoint: the imported city and player controls are verified. City-loop
assets below are saved and verified with keyboard input.

## Assets available now

Open `unity/AthenHill` in Unity 6000.6.0f1, then open
`Assets/AthenHill/Scenes/AthenHill.unity`.

- Expand **AuthoredWorld** to select individual meshes and collision proxies.
  Imported prefabs support scene overrides; use prefab variants for reusable changes.
- **Paving** and **Paving Joints** are editable scene geometry with separate materials.
- **PlayerCandidate** and **NpcImportAudition** prefab variants live in
  `Assets/AthenHill/Prefabs`. ActorAnimation exposes all four clip references,
  walk/run stride speeds and crossfade duration.
- **Player** has a CharacterController and PlayerMotor. Change capsule dimensions,
  walking/running speed, gravity, step height, ground snap and turning in the Inspector.
- **MainCamera / FollowCamera** exposes boom distance, target height, sweep radius,
  mouse sensitivity, pitch and yaw. Fixed camera objects are normal Unity Cameras.
- **Controls.inputactions** opens in Unity's Input Actions editor. Gameplay and UI
  are separate maps, ready for modal UI behavior.
- **Landmarks** holds editable world-space marker objects. Moving a marker changes
  the debug destination; it does not move the city geometry automatically.

Save scene and prefab edits outside Play mode. Imported GLBs are preserved source
assets; changing a material on a variant is safer than editing importer sub-assets.

## Dialogue, trading and HUD

- Select **CitySession** for interaction range, player/input/camera references,
  reduced motion and mute defaults. **CityCatalog.asset** holds starting credits,
  starting inventory, item descriptions/prices, destination names and transition time.
- Each **Data/npc_*.asset** holds that colonist's name, role, dialogue nodes and
  choices. Preserve IDs when changing wording so existing branches remain connected.
- Move NPC prefab instances under **Colonists** in Scene View. Their interaction
  position follows the object. Select a walker to adjust speed and its waypoint list;
  move the numbered objects in its route group to reshape the path.
- Open **UI/CityHUD.uxml** in UI Builder. Its **CityHUD.uss** controls colours,
  spacing, fonts and panels. Keep element names used by CityHud bindings when
  rearranging controls. **CityPanel.asset** controls reference resolution and scaling.
- Import/assembly commands create initial assets only; they refuse to recreate an
  existing city loop. Editing the scene does not require rerunning the scripts or
  changing the original TypeScript files.

**Hill visit area**, **Lattice interaction** and **Ring interaction** are editable
scene markers referenced by CitySession. Move the associated marker when relocating
its landmark; interaction ranges are also Inspector properties.
