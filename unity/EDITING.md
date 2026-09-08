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

## Meshy ring gate

**Meshy Ring Gate** in the south court is a saved instance of
**Prefabs/RingGate.prefab**, generated from the user's front/back/right reference
through Meshy MCP. Its model and editable URP material are under
**Art/Imported/Meshy/RingGate**. The ring, sandstone clamps, platform, four lights
and control console share one atlas. The runtime model has 12,009 triangles; the
original generation, FBX/GLB downloads and task records are retained in
**meshy/ring-gate-v1** at the repository root.

The prefab uses a static concave MeshCollider so the aperture remains open.
**Approach step** reuses the city's authored stone step with a box collider,
giving the player capsule a tread before the generated platform's narrow riser.
The **Ring interaction** marker and its hum retain their original positions and
offline behavior. Only the **Landmarks/ring_gate** debug arrival moved to the
platform in front of the console. NPC roots and waypoint routes are unchanged.

Tune the material's base color, metallic/smoothness, normal strength and emission
in the Inspector. The original arches and their collision proxies remain
inactive under **AuthoredWorld** and are excluded from the rebuilt render chunks.
Use **cam_whompah** for the unchanged comparison angle and **cam_ring_front** for
the frontal inspection. Do not rerun the installer to edit an existing gate;
it refuses to overwrite the installed prefab instance.

## Post-war salvage

**Post-war salvage** contains 98 editable prefab instances: repaired shop fronts,
Basic General, Vanguard Hall, the community board, crates, generators, litter and
industrial scrap. **Prefabs/Salvage** has the eight reusable assets. Their imported
FBX models and original PBR maps live in **Art/Imported/Meshy/Salvage**; the packed
runtime textures and UV-remapped mesh copies are in its **Atlas** subfolder.
The original Blender objects remain in **AuthoredWorld** with the replaced parts
inactive. Original shop lettering is reused on seven shop variants.

Select **City Render Chunks → Show Sources for Editing** before moving props or
editing materials; click **Rebuild Render Chunks** afterwards. Source prefabs and
colliders stay editable. Small material families of at most 5,000 triangles are
combined across cells, while large buildings retain spatial batches. Set **Small
Material Triangle Limit** to zero to disable that optimization.

Trash has no collision. Crates and industrial props use simple boxes; the shop
and hall shells use static mesh colliders. Basic General deliberately reuses its
original box collision and walkable porch so the counter can be approached.
Keep the clear avenue, stair approaches, doors, NPC routes and Lattice exclusion
area when editing the scatter.

The saved **cam_salvage_shop**, **cam_salvage_general**, **cam_salvage_hall**,
**cam_salvage_board**, **cam_salvage_yard** and **cam_salvage_wreck** cameras support
repeatable inspection. **SalvageCityPass.Capture** refreshes editor screenshots;
**SalvageCityPass.Build** builds both Linux players from the saved scene.

**ImportSalvageAssets.Prepare** is a source import operation: it recreates the
individual-material prefabs and now fits new imports uniformly. The fidelity
recovery uses original mesh UVs and full source materials in **Meshy/Fidelity**.
Do not follow a reimport with **SalvageAtlas.Build**: the legacy packing reduced
source detail, and the command refuses to overwrite restored fidelity materials.
Review each updated prefab in place and rebuild render chunks. Do not rerun
**SalvageCityPass.Install** on the installed scene; it refuses to overwrite it.
Normal edits use the Inspector and render-chunk rebuild controls above.

Source views, Meshy task records, and native verification are linked from
[meshy/salvage-20260908/README.md](../meshy/salvage-20260908/README.md).

## Reference-style field interface

The September 8 UI pass remains editable in **UI/CityHUD.uxml** and **CityHUD.uss**.
Identity, vitals, compass, field notes, utility strip, local log and ten square
hotbar slots (six illustrated actions and four reserves) share original bevelled frame artwork. Dialogue, shop, field pack,
notes, sector lattice, pause and credits inherit the same skin. Element names
remain the binding contract for **CityHud**.

**UI/Art** contains the item PNGs, original interface symbols, three nine-slice
frames and the bundled font/licence. **HudArtImporter** keeps UI textures sharp,
without mipmaps or compression; the UI panel allows them in its dynamic atlas.
The frame SVG sources are retained in **refs/ui_20260908/chrome**. Regenerate them
with `uv run --with cairosvg python unity/tools/create_ui_chrome.py` from the repo
root. Item generation sources and prompts are under **refs/ui_20260908/items**.

The compass follows the rendered camera (north is world +Z). Conversation diamonds,
credits, item counts and notes use live session data. The log scrolls through local
events; it is not a multiplayer message box. Scrollable modal content preserves
its header/footer, and inactive HUD controls cannot take focus behind a modal.
Small windows increase HUD type size and narrow the peripheral panels.

**HudWindowLayout** registers each movable HUD group and the shared modal frame.
Drag exposed frames/headers or the small bronze grips; Ctrl-drag works from a button
without activating it. Placement uses translations over the authored USS anchors,
persists through PlayerPrefs, and adapts to window size. Nameplates retain an offset
from their NPC. **Pause → Reset UI positions** restores defaults. The hotbar is
688 × 90 reference pixels with ten approximately 64-pixel square cells.
Native pointer, persistence and resize checks run with
`uv run --with python-xlib python unity/tools/check_draggable_ui.py` and save evidence
under **unity/evidence/ui/20260908/draggable**. Their QA preference namespace keeps
the player's saved layout intact.

Build via **HudArtImporter.BuildDevelopment** or **BuildRelease** in batch mode,
or the ordinary Linux build menu. Native UI verification is
`uv run --with python-xlib python unity/tools/check_ui_reference.py`; evidence is
saved under **unity/evidence/ui/20260908**. The test restores the previous display
resolution when finished. PRODUCT.md and DESIGN.md describe the current UI rules.


## District shops, gates and yard mechanic · 8 September 2026

**District rebuild** contains seven **inactive, rejected shop candidates** and two
active copies of the new west gate arch. Their editable prefabs are in **Prefabs/District**;
raw FBX sources and materials are in **Art/Imported/Meshy/District**. Replaced
shop instances have been restored under **Post-war salvage**. Relay Works and the
previous clutter pass remain active. The original walkable porch/step colliders
remain, supplemented by the restored shop meshes and open gate collision meshes.

The **District/Atlas** material packs eight new buildings beside the complete
previous salvage atlas, preserving its texels. The eight new types each have a
padded 1k tile. Shared UV meshes and static render chunks keep draw costs small.
After editing source transforms, rebuild the render chunks. **Field Supply
nameplate** reuses the original authored lettering over Meshy's distorted text.

**npc_yard_mechanic** uses **Prefabs/YardMechanic.prefab**, a validated Humanoid
Avatar, one skinned mesh, and the **YardMechanic** Animator controller. Its
**Yard mechanic route** is a separate four-point loop at the west service yard.
Edit that route and its AmbientWalker speed in the Inspector. The original
four talking NPCs and three roaming travelers retain their models and routes.
**ActorAnimation** supports this Animator as well as existing legacy Animation
actors. ImportTraveler excludes the mechanic when refreshing the three travelers.

For deliberate source reimport, **ImportDistrictAssets.Prepare** recreates
individual materials and prefabs. Preserve full source maps and review each
candidate in place. The legacy **DistrictAtlas.Apply** refuses to overwrite
restored fidelity materials; its 1k tiles are no longer the default. Field Supply's
source geometry faces +X, corrected to +Z by the importer before fitting it.
The importer now fits uniformly inside the maximum parcel envelope. Do not
re-enable the rejected 3.5k shop candidates based on that scale correction alone:
roof geometry, door scale and the 1k atlas allocation failed close-up review.
Use full source texture resolution and inspect at pedestrian height before
promoting a revised candidate. **DistrictShopRecovery.RestoreAndBuild** selectively
restores the previous shops and builds both Linux players, preserving other edits.
**DistrictCityPass.Install** and **ImportYardMechanic.Install** are one-time
installers and reject duplicate installation. Normal editing uses the saved
instances and prefabs. **DistrictCityPass.Build** captures all district cameras
and builds both Linux players from the current saved scene.

References and input crops: **refs/district_20260908**. Source models, task IDs
and credit ledger: **meshy/district-20260908**. Dated captures, collision traversal,
rig validation and runtime reports: **unity/evidence/district/20260908**.

## Prop grounding and complete foundations · 8 September 2026

The six **Hill root stone** objects now contact their local soil, coping or stair
surface. Both **Plaza bench** assemblies sit with both feet on their local surface.
The eight shop porches, Basic General porch and Vanguard Hall plinth extend under
the full building footprint and slightly below the paving. Their matching box
colliders follow the extended slabs; entrance step edges and heights are retained.
Covered interior-floor renderers are disabled to avoid overlapping top faces.

**CityGroundingPass.Apply** performs this focused repair on existing source objects
and rebuilds the editable render chunks. It checks that actor roots, routes and
interaction markers are unchanged. Normal tuning still uses source transforms and
the chunk rebuild control. **cam_grounding_*** cameras provide pedestrian-height
inspection of the stairs, benches and building sides/backs.

The accepted **RingGate.prefab** is installed at the **south Ring Gate**. The
**north Lattice Jack** is a separate travel landmark with its own original model.
Grounding evidence and native checks are in **evidence/grounding/20260908**.
