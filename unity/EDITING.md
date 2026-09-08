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

The saved city, controls, dialogue, trading, travel and audio are verified.
Native keyboard checks exercise the same scene used in the Editor.

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
  walking/running speed, jump height, gravity, step height, ground snap and turning in the Inspector.
- **MainCamera / FollowCamera** exposes boom distance, target height, sweep radius,
  mouse sensitivity, pitch and yaw, wheel zoom step, maximum distance and first-person
  eye height. A boom of zero enters first person. Fixed camera objects are normal Unity Cameras.
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

## Sound and render optimization

- **Audio/City.mixer** opens Unity's Audio Mixer with Music, Ambience, SFX and UI groups.
  **City Audio** references ordinary AudioSources. Volumes, clips, looping and
  spatial falloff are editable on those sources. Footstep cadence is on CityAudio.
  Lattice/Ring hum sources are children of their interaction markers.
- **Audio/ElevenLabs** contains the current generated WAV assets. **City Audio**
  exposes three footstep variations, trade/offline/travel cues, music fade time and
  dialogue/travel music levels. The music source's Volume is its full gameplay
  level. **Market murmur** is a positional source near Mira. Long music streams
  from the build; short effects are decompressed for immediate playback.
- Select **City Render Chunks**, then **Show Sources for Editing** before changing
  city meshes. Select individual objects under AuthoredWorld as usual. Click
  **Rebuild Render Chunks** when finished. This saves grouped render meshes and
  disables only the source renderers, preserving their transforms and colliders.
  Do not edit meshes under **Generated material chunks**; they are disposable.
  The build check refuses stale chunks instead of silently baking over edits.

- **Materials/World** and **Materials/Actors** contain native editable material
  variants. Adjust their textures, colours and shader properties directly. The
  original GLB sub-assets are retained. Changes to material properties propagate
  to render chunks; assigning a different material requires rebuilding chunks.
- **Sun**, **Skylight Fill**, **City sky reflection** and **DesertSky.mat** expose
  lighting and sky controls. The reflection probe captures the sky; rebake it after
  changing the sky. PC_RPAsset controls shadows, MSAA and render scale.
- Character/portrait review cameras retain editable offsets and follow the actor
  when selected through the development bridge.

The source-edit round-trip check moved a crate, rebuilt, hid it, rebuilt, and
restored it. It preserved the imported mesh, prefab connection and 264 colliders.
This verifies the optimization workflow without requiring manual code changes.

## Sky, grass and drifting dust

The atmosphere pass is saved in the normal scene. **DesertSky.mat** now uses
**Athen Hill/Desert Atmosphere**: high/low sky colours, dust horizon, cloud coverage,
opacity, drift, sun size and distant ridge strength are editable material controls.
It reads the existing Sun direction. After a sky edit, use **Athen Hill → Atmosphere
→ Bake sky reflection**, then save the scene. The 128px reflection is baked once;
clouds do not trigger runtime probe updates.

- **Materials/World/MAT_grass** controls the olive, dry grass and exposed soil
  colours and world-space surface detail. Existing ground meshes stay intact.
- **City Atmosphere → Hill grass 1–4** are ordinary MeshRenderer objects with
  saved mesh assets. Each **GrassPatch** exposes its seed, tuft count, placement
  bounds, width/height and path/terminal exclusions. Click **Rebuild this grass
  patch** after tuning these inputs. Each patch is limited to 85 tufts; the four
  patches total 1,360 triangles and never cast another shadow pass. These objects
  are separate from the city's static render batches.
- **Materials/Atmosphere/HillGrass** controls blade colours and wind bend.
  **City Atmosphere** controls overall wind speed. Reduced Motion freezes cloud
  and grass movement and clears dust; toggling it off resumes them.
- **Drifting plaza dust** is a normal ParticleSystem with editable shape, emission,
  lifetime and velocity. It is capped at 64 particles and uses the **PlazaDust**
  material. The effect is deliberately subtle and fades near the camera.

The shared periodic noise is original numerical data in
**Art/Atmosphere/AtmosphereNoise.asset**. Sky, ground and blade detail use original
project shaders. No generated character or third-party environment asset is needed.
The add-atmosphere command refuses to overwrite an existing setup; subsequent
edits use the controls above.

## Mountains and terrain

**Desert Landscape** contains eight original Blender terrain sectors. They form a
continuous desert basin outside the city walls, with foothills, eroded escarpments,
low passes and rear ridgelines. The scene keeps their prefab link to
**Art/Terrain/DesertBasin.glb**. They are render-only and do not enter the playable
rectangle. Their shared edge normals match; each sector can be culled separately.
The full basin is 5,120 triangles. **Hill weathered stones** adds 26 small original
stones (520 triangles) in the planted quadrants, clear of the paths and terminals.

**Materials/Terrain/SandstoneBasin** exposes the sandstone texture, rock tint,
detail size, surface relief and haze density/colour. The shader blends projections
on all three axes and two texture scales to suppress stretching and repetition.
Baked vertex lighting adds valley occlusion and sky access for the fixed sun.
Re-export the Blender terrain after changing the sun direction.
The distant terrain supplies its own cavity shading and writes depth in the
forward pass; it does not repeat its geometry in the city's SSAO depth prepass.
The normal city fog and lighting remain unchanged. Camera far planes are 650 m.
The sky's old flat ridge layer is disabled because the backdrop is now geometry.

**Materials/World/MAT_grass** now blends the original **HillSoilAlbedo** and
**SandstoneAlbedo** images with slope and broad ground variation. Fine gravel,
soil, olive ground cover and exposed stone share world coordinates. The existing
ground geometry, grass, stairs and collision remain in place.

The original generation scripts are **blender/scripts/18_desert_terrain.py** and
**19_hill_stone_details.py**; execute them through the live Blender MCP connection.
The saved Blender sources are **18_desert_terrain.blend**, **19_hill_stones.blend**
and **20_terrain_city_review.blend**. The last contains the six named city cameras
for source mesh inspection; use the Unity screenshots for final materials.
**Athen Hill → Terrain → Apply desert landscape** reinstalls these generated
terrain objects and rebuilds render chunks. It preserves gameplay roots/colliders
and retains the old mesa sources with their renderers disabled. Use material and
prefab Inspector edits for normal tuning; reapplying resets the generated terrain.

Texture prompts and built-in ImageGen provenance are recorded in
**evidence/terrain/20260908/image-generation.json**. Scalar geology data can be
rebaked with **unity/tools/make_terrain_surface.py** (NumPy, SciPy, Pillow).
