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

## Meshy source fidelity recovery

The 8 September recovery preserves the full 38,071-triangle guard and
25,656-triangle terminal. The terminal uses a derived tangent mesh and Lit PBR
material. Active salvage families and west arches use original mesh UVs and
full source maps through **Art/Imported/Meshy/Fidelity**. Original exports,
previous runtime assets, native before/after views and RTX 3060 measurements are
recorded in [the recovery report](evidence/fidelity/20260908/README.md).

**Athen Hill/Fidelity** contains the scoped migration and review commands. The
migration is already applied; use saved prefabs/materials and render-chunk controls
for normal edits. Do not repeatedly run the migration to overwrite later tuning.
Retain detailed near meshes and source maps when authoring reviewed LODs. The
old 6k guard cap and district-wide texture atlas are not current quality rules.

## Post-war salvage

*30 Sep 2026: the trash, crate, scrap and generator instances here are retired (inactive, kept for rollback) and replaced by
the kit under **Ward street dressing** — see "Street dressing" below.*

**Post-war salvage** contains 98 editable prefab instances: repaired shop fronts,
Basic General, Vanguard Hall, the community board, crates, generators, litter and
industrial scrap. **Prefabs/Salvage** has the eight reusable assets. Their imported
FBX models and original PBR maps live in **Art/Imported/Meshy/Salvage**; the older
packed textures and UV-remapped mesh copies remain in its **Atlas** subfolder
as recovery sources. Active restored visuals use **Meshy/Fidelity** materials.
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

The field pack (30 Sep 2026, after the user's Ark reference) is built by **PackPanel** from the `inventory-panel`
elements; its filters are **InventoryView.Categories** (catalog tags). The colonist view is the scene object
**Character preview** (**CharacterPreview**: framing, drag speed, resolution; child camera and Key/Fill/Rim studio
lights). During its own camera pass the player's renderers move to the **CharacterPreview** layer, the Sun and Sky fill
and any lamp reaching the colonist switch off, and the studio lights switch on; everything is restored after the pass,
and the camera only runs while the pack shows it. **Athen Hill → UI → Install field-pack colonist view** re-creates a
missing rig (it only re-wires an existing one).

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

## Localized Ward surface wear · 8 September 2026

**Ward surface wear** contains editable URP Decal Projectors for terminal-base
grime, standing scuffs, stair-edge sand, wall runoff and layered notices. Twelve
small clumps reuse the existing hill-grass geometry; green clumps are confined
to the aquifer service fitting. These objects add no gameplay collision.
Keep the stair centers, terminal standing spaces and service lane accessible.

**Art/Weathering** retains the original atlas, notice textures, three material
variants and editable shaders. The material variants preserve source albedo and
normals, adding a world-space scalar mask for broad variation. `CopyGltfSurface`
translates glTFast material properties before using URP Lit. Adjust **Broad dust
variation**, **Variation per metre** and **Sheltered wall base dirt** in the
Inspector; originals remain in their previous material folders.

**PC_Renderer → Ward weathering decals** uses Screen Space with Medium normal
reconstruction. Keep **Intermediate Texture = Always**: the installed URP 17.6
decal pass otherwise receives a missing color target in fixed-camera captures.
The existing OpenGL graphics API and URP pipeline remain in use.

Edit projector position, Size, Fade Factor and UV Scale/Bias directly. The
atlas's four quadrants are sand, foundation grime, scuffs and runoff. Notices
have separate exact-text SVG sources in `refs/weathering_20260908`; the source
atlas and generation prompt are there too. `prepare_weathering_assets.py`
recreates the original vector notices and pins its Lit derivative to URP 17.6.
It does not change the supplied atlas. Flat paper uses decals; curled paper
geometry is not included in this pass.

The one-time install command refuses duplicate installation. **Weathering →
Refresh and capture installed wear** captures the saved scene; **Build current
Linux players** builds both outputs. Rebuild render chunks after changing source
material assignments, as with other city edits. Projector-only placement edits
do not alter those source meshes. Evidence and remaining visual limitations are
recorded in [the weathering report](evidence/weathering/20260908/README.md).

## Phase 1 frontage, hall, Vex and roots · 8 September 2026

**Phase 1 Finery frontage** is a saved prefab with separate construction, windows,
door, roof, services and entrance-light groups. Mesh assets are in
**Art/Phase1/Finery**. The original Finery Meshy renderer/collider remain disabled
under **Post-war salvage/BLD_shop_w_01 repaired**. Its existing three sign objects
remain there; they have offset mesh pivots, so fit their renderer bounds rather
than assuming Transform.position is their visible centre. Porch, steps, canopy,
notices and prior courtyard props are preserved. The closed shop has one fitted
box proxy; opening an enterable interior is a separate gameplay/layout task.

The hall visual uses uniform scale 756.518. Its front edge stays at z−26.55 and
base y0.5; its source plinth and matching collider fit the reduced depth. The
previous transform and scene are preserved in the dated evidence.

Vex alone overrides the guard's mesh with **VexSurface/WardGuardTangents.asset**
and uses **OriginalPBR/VexOriginalPBR.mat**. The clone preserves skinning and UVs.
Do not assign **Candidate4K/VexCandidate4K.mat**: that audition introduced unwanted
markings and was rejected. The other guards retain their original assignments.

**Phase 1 tree roots** uses **Art/Phase1/Tree/TreeRoots.prefab**, with closed root
geometry and full 4K bark. The original trunk/roots remain hidden source objects;
existing collision and upper crown remain. Show sources before editing and rebuild
render chunks afterward. Do not revive disabled root renderers or shadow proxies
without reviewing overlaps. Saved Blender sources, exact import recipes, original
and final scene snapshots, and limitations are linked from
[the Phase 1 report](evidence/phase1/20260908/README.md).

## Dust-bowl grade and Karaveen caravan market (26 September 2026)

**Karaveen caravan market** is one prefab instance of **Art/KaraveenMarket/KaraveenMarket.glb**
at the origin. Each stall is a child (`Stall Produce`, `Stall Pottery Water`, `Stall Scrap Tools`,
`Stall Cloth Rugs`, `Stall Rations`, `Cookfire`, `Bunting`, `Caravan stock`); move a stall by
moving that child. `COL_*` children hold the box colliders (renderers disabled). `* Goods`
children cull by LODGroup. `LIGHT_*` children hold lantern lights, which are listed in the
*Ward lighting clock* CityLightCircuit so they follow day/night. `SMOKE_chow` holds the
cookfire flames, embers and smoke. The source and rebuild steps are in
`art/karaveen_market_20260926/README.md`; the old placeholder stalls remain disabled.

The lighting clock uses **Art/Atmosphere/Dustbowl/WardDustbowl.asset** (default 16:00) and the
global volume uses **WardDustbowlGrade.asset**. Point them back at WardAfternoonShade /
AthenHillBeautyVolume to compare. **Windborne dust** holds the dust-sheet and grit particle
systems; tune them there. Values and originals are recorded in
`evidence/dustbowl-market/20260926/pass.json`.

## West Gate exit and Warden outpost (26 September 2026)

Everything lives under **Outer Berms → West Gate outpost** (groups Gate, Outpost, Terrain dressing, Scatter,
Practical lights, Decals, West Gate review cameras). Pieces are ordinary prefab instances from
`Prefabs/WestGate`; move, rotate or delete them in the scene as usual. Gameplay roots were moved, not replaced:
Warden Ossa, Warden Rell, Warden arms locker (its cabinet visual is the child *Arms locker visual*), Checkpoint
field briefing, Range reset control and the respawn point. If you move one, move its **Landmarks** entry
(`checkpoint_*`) too. Colonists and Wardens win the E prompt within 2.4 m, so keep world interactables at least
that far from a Warden's stand point (the Edit Mode test `WestGateLandmarksResolveToTheIntendedInteraction` checks this).

- **Materials** are in `Art/WestGate/Materials` (URP Lit, editable; tiling = 1 / metres per repeat). WG_* paints,
  signs and papers come from `art/west_gate_20260926/make_textures.py`; PH_* are the Poly Haven props.
- **Berms ground** uses `Art/WestGate/Ground/BermsGround.mat` (shader *Athen Hill/Berms Ground*). Tints,
  saturation, layer sizes, height-blend depth, packed-ground darkening, macro variation, edge blend and haze are
  material controls. The splat (`BermsGroundSplat.png`: R road, G sand, B crust, A 1 − compaction) is regenerated
  by `make_ground_splat.py` from `layout.json`; the previous SandstoneBasin material is recorded in the evidence.
- **Lights**: West Gate practicals are registered with City Light Circuit as practical *and* night-only lights.
  City Light Circuit now also drops practical shadows while its strength is below *Shadow Strength Threshold*.
- **Rebuilding**: *West Gate: build assets* rebuilds prefabs but never overwrites existing materials.
  *West Gate: install outpost* refuses to run over an installed outpost. The wreck gantry beside the gate is chunked
  AuthoredWorld content: its new visuals are under Gate/Wreck gantry, the originals are inactive sources; use
  Show Sources / Rebuild Render Chunks as usual if you change them.

## Air + Water filter bank (29 September 2026)

**Air + Water filter fittings** (under *Ward shop architecture*, a render-chunk source root) is a saved instance of
`Art/Phase1/AirWater/Filters20260929/AirWaterFilters.prefab`: five parts (three vessel mounts, header with valve/gauge/ISOLATE plate, roof riser),
uniform scale 1, full-resolution maps, no colliders. The eight 9 Sep manifold/wall-mount/downfeed renderers are disabled, not deleted; canisters,
retainers, riser clamps/anchors and feed flanges remain. Use Show Sources, edit, then Rebuild Render Chunks. `AirWaterFilterPass` is a one-time
installer that refuses to run twice. Evidence, rollback scene/chunks and defects: `evidence/airwater-filters/20260929/README.md`.

## Vanguard Hall rebuild (30 September 2026)

**Vanguard Hall** (scene root) is a saved instance of `Prefabs/VanguardHall/VanguardHall.prefab` at world (−10, 0, −26.55),
uniform scale 1. It replaces the Meshy salvage hall, which stays in the scene inactive (*Post-war salvage/Vanguard Hall
repaired*), together with the retrofit *Hall banners* and the old *BLD_hall_plinth/step* and their colliders. The hall is
**not** a render-chunk source: it keeps its own LODGroup (LOD0 ~85k triangles to 26 % screen height, LOD1 ~42k) and
vertex-coloured masonry. Children: `LOD0`/`LOD1` (glTF models), `Colliders` (podium, front and rear steps, body, portal
recess, piers, entablature; boxes you can edit), `Fittings` (Poly Haven lamps, security light/camera, air conditioners,
power box; each wall lamp has a *Bulb*), `Practical lights` (portal, recess and rear lamps, two terrace uplights, mast
beacon), `Weathering decals` (runoff and wall-foot sediment on the accepted Ward atlases).

- Materials are in `Art/VanguardHall/Materials`. Stone uses **Athen Hill/Masonry Lit** (Weathered Lit + per-block
  vertex tint *_BlockTint* and occlusion *_BlockAO*); metals, bronze/brass, banner (alpha clip, linen detail normal)
  use URP Lit; glazing **VH_Glass** is Ward Window Interior with hall-sized rooms. VH_Glass and VH_LampLens are on the
  **Ward lighting clock** emissive list and the lamp/uplight lights are practical + night-only lights there.
- Geometry changes go through the source: `art/vanguard_hall_20260930/author_vanguard_hall.py` (Blender 5.2) writes
  the GLBs and `vanguard-hall.json` (colliders, fittings, uplights). Then **Athen Hill → Vanguard Hall → Build assets**
  rebuilds the prefab (existing materials keep Inspector edits; *rebuild materials* resets them). Rebuilding the prefab
  re-creates its lights, so rerun the install (authoring: `VanguardHallPass.Reinstall()`) to re-bind them to the clock.
  **Install rebuilt hall** is one-time and refuses to run over an installed hall; **Verify saved scene** writes a report.
- **Vanguard Hall review cameras** (`cam_vh_*`) are player-height views for `tools/lookbook.py`; real-input traversal:
  `tools/check_vanguard_hall_traversal.py`. Evidence, rollback scene and remaining defects:
  `evidence/vanguard-hall/20260930/README.md`.

## Hall district shops, signs and weathering (30 September 2026)

**Ward shops (hall district)** (scene root) holds five prefab instances from `Prefabs/WardShops`: Relay Works (−18.1, −18),
Air + Water (−18.1, −9), Tool Exchange (−18.1, 9) (all yaw 90), Finery (18.1, −18) and Field Supply (18.1, −9) (yaw −90).
Each has `LOD0`/`LOD1` (glTF), `Colliders` (body, front piers, over-door blocks and door leaves set back 0.4 m so the
recesses are walkable), `Fittings` (Poly Haven lamps with bulbs, AC, power box, security light), `Practical lights`
(on the **Ward lighting clock**, practical + night-only), `Sign mounts` (the sign prefab under each) and, for the Tool
Exchange, `Display` (Meshy props on named mounts plus the display light). The shops are not render-chunk sources.
The porch and step colliders are the original `AuthoredWorld/COL_BLD_shop_*` boxes; their renderers are retired.

- Geometry changes go through `art/hall_district_20260930/author_ward_shops.py` (and `author_ward_signs.py` for signs),
  both on the shared kit `art/ward_masonry_kit`. Then **Athen Hill → Ward shops → Refresh models and materials**
  (re-imports the GLBs into the existing prefabs, keeping light bindings). *Build assets* rebuilds prefabs from the JSON
  records (then re-run *Fit Tool Exchange display props* and *Install signs*, and re-bind lights by re-running the
  install on a fresh scene). *Install rebuilt shops* is one-time; *Dry-run install* lists what it would retire.
- Stone uses the hall's materials (`Art/VanguardHall/Materials/VH_*`, **Athen Hill/Masonry Lit**). Its weathering controls:
  *Runoff streaks* (map, tile, strength, tints), *Rust*, *Edge wear*, *Dust on upward faces*, *Old pitting*, *Battle
  damage*, *Shrapnel scars per metre*, *Grime packed on arrises*, *Occlusion darkens albedo*. The weights they scale are
  baked per vertex by the kit (see `art/ward_masonry_kit/README.md`); these meshes are probe-lit (UV1/UV2 hold wear data,
  not lightmap UVs). Shop-only materials (`WS_*`: glass, steel, paint, canvas, corrugated roof, sign parts, cyan LEDs) are
  in `Art/WardShops/Materials`.
- Retired layers stay in the scene inactive (`evidence/hall-district/20260930/shops-install.json`). The district
  retrofit's combined *Shop retrofits* meshes use filtered copies in `Art/WardShops/Retrofit`; point them back at the
  `WardRetrofit.glb` sub-meshes to restore. The accepted Air + Water filter bank is kept by prefab-instance overrides on
  `Ward shop architecture/air_water` (only *Front filter bank* and the riser anchors active).
- The Basic General sign is **Basic General sign (hall district family)**; the 29 Sep baked plate *Basic General neon
  sign* is inactive for rollback.
- Real-input QA: `tools/check_hall_district_city_loop.py` (walks Vex → Torr → Linn → Mira trade → shop porches and door
  recesses → Lattice link). Evidence and defects: `evidence/hall-district/20260930/README.md`.

## North avenue: Salvage, Repairs, Thread + Hide and Basic General (30 September 2026)

**Ward shops (north avenue)** (scene root) holds four prefab instances from `Prefabs/WardShops`: Salvage (−18.1, 18) (yaw 90),
Repairs (18.1, 9) and Thread + Hide (18.1, 18) (yaw −90), and the Basic General booth (8, 0, 15.1) (yaw 0). The shops have
the same children as the hall-district shops (`LOD0`/`LOD1`, `Colliders` with walkable door recesses, `Fittings`,
`Practical lights` on the Ward lighting clock, `Sign mounts`); Thread + Hide's `Display light` is warm and practical only.
The booth has `Colliders` for its two new front piers only: the rear, side, roof, porch and step collision is still the
six original `AuthoredWorld/COL_BLD_general_*` boxes. Mira, **Basic General counter dressing**, **Basic General back
panel**, **Basic General sign (hall district family)** and *Basic General authored frontage/Stock* are separate and
untouched; the frontage's structural groups are inactive.

- Sources: `art/north_avenue_20260930/author_north_shops.py` (the three shops, on the hall-district `Shop` class and the
  shared masonry kit), `author_basic_general.py` (the booth), signs through `art/hall_district_20260930/author_ward_signs.py
  -- salvage repairs thread_hide`. After re-running them use **Athen Hill → Ward shops → Refresh models and materials**: it
  re-imports every shop model and re-maps each prefab renderer's material slots from the model's material names (a model
  that gains or loses a material shifts its sub-mesh order; without the re-map the wrong materials land on surfaces).
- One-time: **North avenue: install (one-time)** (refuses to run twice; *North avenue: dry-run install* lists what it
  would retire), then **North avenue: install signs**. **North avenue: verify saved scene** checks the group, lamps on the
  clock, retired layers, kept colliders and the untouched Basic General pieces.
- Retired layers stay inactive (`evidence/north-avenue/20260930/north-install.json`). The *Shop retrofits* meshes now use
  `Art/WardShops/Retrofit/*_north_avenue.asset` (filtered again for these three parcels); the `_hall_district` copies stay.
- New materials in `Art/WardShops/Materials`: WS_PaintOlive/Ochre/Yellow, WS_ContainerRust, WS_Cloth{Indigo,Ochre,Madder,Bone},
  WS_Hide (double-sided cloth) and WS_LedWarm (emissive, on the lighting clock).
- Real-input QA: `tools/check_north_avenue_native.py` (the whole city loop plus every new porch and door recess, profiled
  north-avenue legs, first-person stills); frame-cost A/B: `tools/profile_north_walk.py`. Evidence and defects:
  `evidence/north-avenue/20260930/README.md`.

## Hill, tree ring, terminals and hall floodlights (30 September 2026)

**Ward hill** (scene root) is a saved instance of `Prefabs/WardHill/WardHill.prefab` at the origin. It replaces the hill's
visuals only: the plinth, surface and eighteen stair colliders (`AuthoredWorld/COL_ENV_hill_*`) are unchanged, and the
retired pieces (plinth/caps/mound/paths, the old stair stones, market boxes, root stones, the spiky Hill grass patches,
Hill weathered stones, stair sand decals, the hill bench) stay in the scene inactive (`evidence/hill/20260930/install.json`).
The hill is not a render-chunk source.

- Children: `LOD0`/`LOD1` (glTF: walls, stairs, ring, paving, metal, bed soil, ring soil, roots, sand; at LOD0 the walls,
  stairs and ring cast shadows through `Shadow proxy (LOD1 meshes)`), `Planting` (one LODGroup per bed zone and the ring; ground cover casts no shadow, boulders/shrubs/twigs do), `Colliders` (stair cheek boxes,
  `COL_TreeRing` mesh collider, convex `COL_TreeRingSoil`), `Terminals` (three `WardSaveTerminal` prefab instances facing
  the tree: Meshy kiosk LODs, *Screen front/back* overlays with `HP_TerminalScreen`, a night *Screen glow*), `Practical lights` (three tree uplights). Uplights and screen glows are
  practical + night-only lights on the **Ward lighting clock**.
- The saved terminal colliders `COL_PROP_hill_market_0x_body/foot` were moved/rotated onto the new kiosks and pads (same
  objects). The kiosks are decorative, as the old boxes were: no save or reclaim interaction exists.
- Stone uses the hall's `VH_*` materials (Athen Hill/Masonry Lit), so hall weathering edits apply here too. Soils, roots,
  plants and the kiosk/floodlight materials (`HP_*`, emissive with the RealtimeEmissive flag so URP keeps `_EMISSION`) are in
  `Art/WardHill/Materials`: `WH_BedSoil`, `WH_RingLitter`, `WH_RootBark` (URP Lit) and one material per
  Poly Haven species. Foliage uses **Athen Hill/Ward Ground Cover** (`Shaders/WardGroundCover`, the Ward Tree shader with
  the wind bending by height above each group's origin): *Sway*, *Full bend at this height*, *Blade flutter* and the
  transmission sliders are per material; wind stops with Reduced Motion. Never static-batch the planting.
- Geometry changes go through `art/hill_20260930` (`author_ward_hill.py`, `scatter_hill_plants.py`, shared `hill_layout.py`),
  then **Athen Hill → Ward hill → Build assets**. Rebuilding recreates the hill prefab and its lights, so re-bind them with
  `WardHillPass.Reinstall()` (authoring only; it keeps the retired objects retired). **Install rebuilt hill** is one-time;
  **Dry-run install** lists what it would retire; **Verify saved scene** writes `evidence/hill/20260930/verify-saved-scene.json`.
- **Vanguard Hall floodlights**: `Fittings/Facade floodlight west/east` are `WardFloodlight` prefab instances (Carl's Meshy
  model, head re-aimed 15°, three LODs); the existing `Practical lights/Facade uplight west/east` spots sit at their lenses
  (same light objects, so the clock bindings are kept). The hall GLBs no longer contain the box uplights. After a hall
  re-author, run **Athen Hill → Ward hill → Install Vanguard Hall floodlights** (re-imports the hall models and edits the
  prefab in place).
- Review cameras `cam_hill_*` (under *Ward hill review cameras*); real-input check `tools/check_hill_native.py`. Evidence,
  rollback scene and remaining defects: `evidence/hill/20260930/README.md`.

## Scavenger's Arc: fabrication, loot and field orders (29 September 2026)

Gameplay v2 content is serialized data; nothing is hard-coded in the scripts. Edit these assets in the Inspector:

- **Data/CityCatalog.asset** — every item. Keep the first three rows (Basic General's stock) and all IDs.
  `rarity` (Common/Uncommon/Rare) drives loot glow, toast and tile colours; `sellOnly` + `sellPrice` puts raw salvage
  in Basic General's *Sell salvage* list (Mira never stocks it); `excludeFromTrade` keeps rare parts, refined
  components and mods out of every trade; `icon` is the USS illustration class (`scrap-icon`, `pistol-icon`, …).
  `tags` feed tag ingredients (e.g. `nanite:tier1`, `component:capacitor`, `material:conductive`).
- **Data/Crafting/WardCrafting.asset** — the Scrap Pistol's base `stats`, clamp bounds `minStats`/`maxStats` and slots
  (grip, barrel, cell); `modifiers` (per mod: slot and effects — stat + `add` or `percent`); `recipes` (inputs by item
  or tag, `group` Component/MarkI/MarkII, `unlocks`: `acquireItem` or `orderStart`, `lockedHint`); `lootTables`
  (min/max quantity, chance, `pityAfter` bad-luck protection, `guaranteeUntilCollected` for the Foreman's core);
  presentation labels for slots, tag ingredients, recipe groups and the fabricator stats table.
  Effective stat = clamp((base + Σadd) × (1 + Σpercent / 100)). PlayerCombat reads every weapon stat from this; its own
  damage/range/nano fields are only a fallback. After editing, run `AthenHill.Editor.CraftingDataExporter.Export`
  to refresh the dev-UI export and validate references.
- **Data/Crafting/WardFieldOrders.asset** — Ossa's five orders (goal FitMod / CollectItem / CraftFromGroup, target,
  test-fire flag, encounter to activate, guidance key, brief, radio start/complete lines, credit/item/schematic
  rewards) and the Field Notes templates (`{brief} {item} {weapon} {recipe} {inputs} {count}`). Orders only move
  forward; rewards and completion lines fire once.
- **Prefabs/OuterBerms/SalvageCache.prefab** — the droid drop (glow colours, light intensity, prompt).
  **SalvageHeapNode.prefab** — search time, respawn time, cancel distance, prompts, marker light/motes.
  **FeralDepotForeman.prefab** — a prefab *variant* of FeralWorkerDroid: change its overrides (health, strike, wind-up,
  stagger immunity, optics) there; worker changes flow through.
- Scene (installed by `GameplayV2Installer`): **CitySession → FieldOrders** (data, guidance targets
  `fabricator`/`depot`/`foreman`, encounter binding `foreman`), **CitySession → CraftingSession.cachePrefab**,
  **Outer Berms/Encounters/Depot Foreman · processing hall** (move the spawn child to reposition; respawn 300 s),
  **Outer Berms/Salvage heaps** (one `Salvage node · …` per searchable prop; move a node with its prop, set its loot
  table and prompt range per node), Landmarks `berms_foreman_hall` and `berms_scrap_heap`.
- `GameplayV2Installer.InstallBatch` is one-time: it refuses to run over its own marker (*CitySession/Gameplay v2 ·
  installed*) or an unsaved scene. `GameplayV2Content.BuildData/BuildOrders/BuildPrefabs` authored the assets once and
  refuse to overwrite them unless `GAMEPLAY_V2_FORCE=1` (which discards Inspector edits).
- **CitySession → WardSaveGame**: save file name and (for tools/tests) a folder override. The format is
  `WardSaveData` version 1 (JsonUtility). When adding saved state, add fields with safe defaults; bump
  `CurrentVersion` only for incompatible changes (older builds then refuse the file and start a new game).
  **CraftingSession → Fresh Seed Per New Game** (on) seeds loot per new game; turn it off to always start from
  *Loot Seed* for repeatable QA. The start menu's Continue / New Game / confirmation live in **UI/StartupMenu.uxml**.
- UI: the fabricator window and *Sell salvage* list are laid out in **UI/CityHUD.uxml** (`fabricator-panel`,
  `salvage-list`) and styled in **CityHUD.uss** (sections "Gameplay v2 · …"); `FabricatorPanel` and
  `SalvageSalePanel` fill them from data. Keep the named elements.

## Courtyard tree beds (30 September 2026)

**Courtyard tree beds** holds two prefab instances (`Prefabs/CourtyardTrees/TreeBed_Birch3/Birch4b.prefab`) centred on
the birches `birch 3` (moved to −19.60, 25.55) and `birch 4b` (moved to −16.34, −1.85): the hero tree's ring at street
level in Ward stone (seat 0.49 m), leaf litter, roots, a drip line and riser, apron flags, planting, two uplights each on
the **Ward lighting clock**, an annulus collider (wall and coping) and a convex soil collider. To move a bed, move it
*with its tree* (the tree root keeps its prefab link, LODs and trunk capsule). Geometry changes go through
`art/courtyard_trees_20260930/author_tree_beds.py` (Blender) → **Athen Hill → Courtyard trees → Build assets**; the
install is one-time. Materials are the hall's stone/fittings and the hill's litter, root bark and plants (shared).
Review cameras `cam_tree_bed_*`; evidence `evidence/courtyard-trees/20260930`.

## Street dressing (30 September 2026)

**Ward street dressing** holds 145 prefab instances of the street kit (`Prefabs/StreetDressing/SD_<id>.prefab`: Poly
Haven scans, four Meshy pieces, Blender-made sacks, tarp, scrap skip and litter) in 30 vignette groups
(*Relay Works frontage: parts stock*, *East yard: generator and fuel*, *Windblown litter* …), each group's origin at its
centre so a vignette moves as one. Each group also carries its **Ground grime / Ground scuffs** URP decal projectors
(the weathering atlas; fade factor, size and UV bias are Inspector edits). The dressing is **not** a render-chunk source:
select, move, duplicate or delete instances directly; no chunk rebuild is needed.

- Props have LODGroups (switch heights tuned on the native A/B), box colliders where you could walk into them (litter
  and hand-sized pieces have none) and, on stools and benches, **NPC sit point** markers (+Z facing) for the crowd pass.
- Keep the avenue lanes, doors and bays (front, rear, side), stair approaches, walker/mechanic/droid routes and NPC
  stand points clear; `art/street_dressing_20260930/layout.py` checks all of these for the source layout.
- Materials: `Art/StreetDressing/Materials` (URP Lit, instancing on; `SD_Potted_*` are the hill plant materials with the
  wind bend starting higher). Change a prop's look on its material; change its geometry through the scripts in
  `art/street_dressing_20260930` and **Athen Hill → Street dressing → Build assets** (re-imports and rebuilds the prefabs;
  instances in the scene update).
- The old salvage scatter, the cube *Street cargo crate / Street bollard / Plaza bench* and four retrofit collider
  proxies that rendered as grey slabs (`Ward district retrofit/Shop retrofits/COL_*_bin`, renderer off, collider kept)
  were retired by the one-time **Install**. Review cameras `cam_sd_*` (**Street dressing review cameras**); evidence and
  A/B frame times in `evidence/street-dressing/20260930`.
