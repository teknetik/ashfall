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

**Batched verification (since 1 October 2026, [AGENTS.md §7](../AGENTS.md)).** Each pass
installs into the saved scene, runs its own `-nographics` *verify* step (installed, prefab
links, no missing materials, chunk fingerprint, retired objects inactive), validates its
placements against colliders, routes, doors and NPC points, and adds `cam_<pass>_*` review
cameras at player height. It does not build the player or run native tests. One combined
native test per batch then makes a development build, captures every review camera at 13:00
and 20:30, alternates frame-time runs against the previous batch's build, and runs the city
loop and the range tutorial check. Results for 1 October:
[batch 1](evidence/combined/20261001/batch1/README.md) (perimeter walls, hydroponics,
training range, night life, basin mountains, city paving) and
[batch 2](evidence/combined/20261001/batch2/README.md) (West Gate arches, rooftops, Berms
road, first texture-memory changes). The per-pass build and capture commands in older
sections below predate this process. Pass run orders call the memory-capped programme
wrappers (`$O/unity.sh`, `blender.sh`, `heavy.sh`, with `$O` =
`~/.local/state/ward-programme`) that the AGENTS.md §8 machine limits require.

## Assets available now

Open `unity/AthenHill` in Unity 6000.6.0f1, then open
`Assets/AthenHill/Scenes/AthenHill.unity`.

- Expand **AuthoredWorld** to select individual meshes and collision proxies.
  Imported prefabs support scene overrides; use prefab variants for reusable changes.
- **Paving** is editable scene geometry and a render-chunk source; since 1 October 2026 it
  uses the flag material described in "City paving" below. **Paving Joints** is inactive.
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
  Since 1 October 2026 the rebuild also records each chunk mesh's UV distribution metric,
  which mipmap streaming uses to choose mips (see "Texture compression and streaming").

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

## Texture compression and streaming (1 October 2026)

The texture-memory pass (`Editor/TextureMemoryPass.cs`, sources `art/texture_memory_20261001`) compressed 434 scene
textures without downsampling any source or changing a material, prefab, scene reference or GUID. The city paving pass
set the streaming budget and the render-chunk UV metrics. Numbers: `evidence/texture-memory/20261001/README.md`.

- **Embedded glTF/glb images are compressed at import.** `Editor/GltfTextureCompression.cs` is a glTFast import add-on
  that compresses power-of-two embedded PNG/JPEG images to BC7. It keeps the channels, sRGB/linear flag, mips and
  sub-asset IDs, so references don't change. It acts whenever a .glb is (re)imported and is on by default
  (`GltfTextureCompression.DefaultOn`); `ATHEN_GLTF_COMPRESS=0` turns it off for one Unity run. Don't switch it off
  permanently: a reimport would bring back about 2.6 GB of uncompressed textures. Embedded textures are **not**
  mipmap-streamed (flagging them for streaming during import crashed Unity's streaming manager), and NPOT embedded
  images stay uncompressed, so export power-of-two maps from Blender.
- **TextureImporter textures must be power-of-two to compress.** Unity 6000.6 leaves a non-power-of-two texture with
  mipmaps uncompressed (RGBA32) even with CompressedHQ or an explicit BC7 override. Either author power-of-two maps, or
  set `npotScale = ToLarger` together with a Standalone BC7 (colour and masks) or BC5 (normals) override, as
  `TextureMemoryPass.ApplyImporters` does for the 20 maps it changed (also streamed). Don't use ToLarger on normals
  created from a height map ("Create from Grayscale"): it weakens the bumps.
- **UV distribution metrics.** `StaticRenderChunksEditor.Rebuild` calls `Mesh.RecalculateUVDistributionMetrics()` on
  every chunk mesh. Before 1 October every chunk kept the default metric 1, so streaming chose far too coarse mips for
  chunked materials (the old paving was held at mip 2). glTFast never computes the metric, so .glb meshes (masonry kit,
  shops, hall) still report 1; a fix in the add-on was tested but is not enabled, because it changes every pass's
  streaming and needs its own A/B.
- **Streaming budget.** PC quality `streamingMipmapsMemoryBudget` is **5,632 MB** (max level reduction 2), raised from
  4,096 by the paving pass when about 4.4 GB of non-streamed textures left every streamed texture pinned at its initial
  two-mip reduction. After compression, non-streamed textures are about 1.6 GB and resident textures about 2.2 GB at the
  three measured views; the texture-memory evidence recommends 3,584 MB. Carl decides; the setting is unchanged.
- **Check memory:** `TextureMemoryPass.RunBatch --steps inventory:<tag> -nographics` writes every texture the scene
  loads (inactive objects included), with format, mips, streaming flag and MB, to
  `evidence/texture-memory/20261001/inventory-<tag>.{json,md}`. It is heavy (about 12 GB plus 3 GB swap). In a
  development player started with `--athen-qa`, `ATHEN_TEXSTREAM_PROBE=1` logs the streaming counters
  (`texture-streaming.jsonl` and `-full.json` in the QA folder; `art/texture_memory_20261001/native_probe.sh`), and
  `ATHEN_TEXSTREAM_BUDGET=<MB>` or `ATHEN_TEXSTREAM_OFF=1` override the budget for an A/B in one build
  (`Scripts/TextureStreamingProbe.cs`). The probe hitches every 8 s, so never profile frame times with it.
- **Rollback:** `--steps revert -nographics` restores the original importer `.meta` files (copies in
  `evidence/texture-memory/20261001/rollback/meta`). For glTF, set `DefaultOn = false` (or run with
  `ATHEN_GLTF_COMPRESS=0`) and `--steps gltfplain:all:restore`. Review cameras `cam_tm_*` (**Texture memory review
  cameras**) show close-ups of compressed assets.

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

*1 Oct 2026: the eight `Desert Landscape` sectors described here are inactive (kept for rollback) and replaced by
**Basin mountains**; see "Basin mountains" at the end of this section.*

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

Do not run **Apply desert landscape** on the current scene: it deletes and re-creates the `Desert Landscape` root as
active objects with the 8 Sep material, and adds a second, active copy of **Hill weathered stones** (retired by the
hill pass).

### Basin mountains (1 October 2026)

The backdrop ring outside the walls is now the scene root **Basin mountains**: a prefab instance of
`Art/Terrain/BasinMountains/BasinMountains.glb` with eight chunks `BasinMountains_00…07` (the old sector split, 185,257
triangles in all) on `Materials/Terrain/SandstoneBasinV3.mat` (shader *Ward Desert Terrain V2*). The old
`Desert Landscape/DesertBasin_00…07` chunks stay in the scene inactive with `SandstoneBasinV2.mat`. The basin is
render-only (no colliders) and is not a render-chunk source.

- **Sources** in `art/basin_mountains_20261001` (`run_all.sh`: numpy heightfield with stream-power erosion, strata
  benches and talus → adaptive RTIN mesh → Blender glb, about 2 min through the capped wrappers). The layout is the
  8 Sep generator's (front escarpment, crest ring, distant ring). Re-export rather than editing the glb; chunk borders
  are shared vertices, so never edit one chunk alone.
- **Outer Berms edge**: inside the Berms ground footprint (X −104…−60, Z −54…48) and 0.75 m round it the new surface
  equals the old basin exactly (the Berms ground mesh was built as that surface + 4 cm), so the toe is untouched; the new
  terrain blends in by 7 m. The Berms ground mesh itself still carries the old basin's facets on its west and south
  slopes (up to about 11 m); rebuilding it from the new basin is a separate Berms ground task.
- **Haze** (V3 material Inspector; values in `art/basin_mountains_20261001/material.json`): the V2 shader has five new
  haze-shape properties whose defaults reproduce the old haze, so SandstoneBasinV2 and the Berms ground are unchanged:
  *Far haze starts* / *Density beyond the far start* (V3: 100 m / 0.28, so the haze matches the Berms ground out to
  138 m and thins beyond), *Haze height falloff* / *Height falloff base* (32 m above 6 m, so ridge tops keep their form
  at noon) and *High-sun haze tint* (a linear multiplier used only under a high, strong sun). `_RockSlope` 0.06 (V2:
  0.075) exposes more rock on the new slopes.
- **Rebuild / reinstall**: `BasinMountainsPass.RunBatch --steps material` (menu **Athen Hill → Basin mountains**)
  re-applies `material.json` and overwrites Inspector edits on V3; `--steps verify` checks the saved scene; `install`
  refuses to run twice. Rollback: deactivate **Basin mountains** and reactivate the eight `Desert Landscape` children,
  or restore `evidence/basin-mountains/20261001/rollback/`.
- **Review cameras** `cam_bm_*` (**Basin mountains review cameras**, player height on the Berms ground, rebuilt by
  `--steps addcams` from `art/basin_mountains_20261001/review_cameras.json`); skyline views use `cam_hill`,
  `cam_avenue`, `cam_courtyard`, `cam_westgate_mouth`, `cam_berms_road` and `cam_berms_overview`. Evidence and
  remaining defects (pale far massifs at noon, some serrated crests): `evidence/basin-mountains/20261001/README.md`.

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

## West Gate arches: sealed gates at the spawn (1 October 2026)

The two `District gate` arches at the +X spawn (the Meshy instances under **District rebuild**, still drawn by their
render chunks and untouched) now carry sealed working gates set 1.6 m back in each arch passage. Scene root **Ward west
gate arches** holds one prefab instance per arch, both at x 48 with identity rotation and scale:
`Prefabs/WestGateArches/WGA_GateA.prefab` (spawn arch, centred on z 0, wicket door in the south leaf) and `WGA_GateB`
(z 12, repair plate on the north leaf). These are not the −X **West Gate outpost** in the Outer Berms.

- Each prefab is a LODGroup (LOD0 bevelled and bolted within about 15 m, LOD1 to about 45 m, plain LOD2 beyond) over the
  groups *Leaves* (timber leaves, steel skin, transom, head grille; cast shadows), *Iron* (hardware; no shadows),
  *Stone* (guard stones on Athen Hill/Masonry Lit; cast), *StoneBand* and *Lamp* (no shadows), plus `Colliders` (one box
  sealing the opening at the leaves, one per guard stone), `Bulkhead light` (warm unshadowed spot on the **Ward lighting
  clock**, practical + night-only) and `Decals` (URP projectors: cart ruts, scuffs, sand, grime skirt, jamb scrapes, a
  painted KEEP CLEAR stencil and the gate number on the transom).
- Move a gate only together with its arch: the leaves are fitted to the Meshy opening (jambs ±2.465 m about the arch
  centre), measured from the saved chunk meshes. Decals are children of each prefab.
- Collision: the leaves' box seals each arch, so the strip behind the rampart is no longer reachable and the city stays
  enclosed. No saved collider changed and nothing was retired.
- Sources: `art/west_gate_arches_20261001` (`author_gate_arches.py` → `Art/WestGateArches/Models/WGA_Gate{A,B}.glb`;
  `layout.py` → `layout.json` with placements, decals, light and cameras, validated against a scene audit;
  `make_decals.py` → rut and jamb-scrape textures; `extract_gate_mesh.py` and `measure_opening.py` measure the arch).
  Rebuild: **Athen Hill → West Gate arches → Build assets** (batch `WestGateArchesPass.RunBatch --steps build,verify`).
  **Install (one time)** refuses to run twice; `reinstall` (authoring) unhooks the lights from the clock and re-adds them.
- Materials are shared, not copied: `TR_Timber*` (training range), `WG_*` steel, rubber and decals (West Gate kit) and
  `VH_*` (Vanguard Hall). Only the decal materials `WGA_DecalCartRuts`, `WGA_DecalJambScrape` and `WGA_DecalStencil` are
  new (copies of the weathering decal template).
- The night facade tune (below) re-set the bulkhead lens to `NF_BulkheadLens` and moved and widened the bulkhead spot.
  A prefab rebuild puts `VH_LampLens` and the original 125° spot back, so re-run `NightFacadePass` `apply` afterwards.
- Review cameras `cam_wga_*` (6, **West gate arch review cameras**). The scene before the install is in
  `evidence/west-gate-arches/20261001/rollback/`; evidence: `evidence/west-gate-arches/20261001/README.md`.
- Naming: these +X arches still carry the Meshy "WEST GATE" sign, which duplicates the −X Berms gantry's sign and
  contradicts the compass. Renaming is Carl's decision.

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

## City paving (1 October 2026)

The city floor **Paving** (a 120 × 90 m render-chunk source; its collider `COL_Ground` is separate) and the three
visible `AuthoredWorld/AAA Environment Dressing/Plaza inset *` bands use the shader **Athen Hill/Ward Paving Lit**
(`Art/CityPaving/Shaders/`) with `Art/CityPaving/Materials/PV_CityFlags.mat` (courses east–west) and
`PV_CityFlags_Band.mat` (courses north–south, slightly cooler and darker). The flags are mapped in **world XZ** (4 m
tile, eight 0.5 m courses); every world course gets a random shift and source course, and every flag instance its own
tone. Mesh UVs are used only by the depth and meta passes. The textures (`Art/CityPaving/Textures/PV_Flags_{BaseMap,
Normal,Mask}.png` at 2k, `PV_Grain_Normal.png` at 1k) are **not streamed**, because the floor is always under the
camera (17 MB resident).

- **Edit the look:** change `art/city_paving_20261001/tuning.json` or `tuning-band.json` and run
  `CityPavingPass.RunBatch --steps assets,bandmat` (no chunk rebuild: the chunks reference the material assets). In a
  development player, `ATHEN_MATERIAL_TUNE=<file from tune_runtime.py>` applies the values at start-up without a rebuild
  (`MaterialTuneProbe` in `Scripts/TextureStreamingProbe.cs`).
- **Edit the texture:** `author_paving.py` (through `$O/heavy.sh`; about 3.6 GB peak), then `--steps assets`.
- **Retired:** `Paving Joints` (already not drawn) and the four gunmetal `Avenue service band` strips are inactive.
- **Rollback:** point **Paving** back to `Art/Weathering/Paving Local wear.mat` and the insets to `PlazaPaving Local
  wear.mat`, reactivate `Paving Joints` and the service bands if wanted, then **Show Sources for Editing** → **Rebuild
  Render Chunks**. A pre-install scene copy is in `evidence/city-paving/20261001/rollback/`.
- The pass also raised the texture streaming budget and made render chunks record UV distribution metrics; see "Texture
  compression and streaming".
- Review cameras `cam_pv_*` (**City paving review cameras**); evidence and remaining defects:
  `evidence/city-paving/20261001/README.md`.

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
  *Since 1 Oct 2026 the Berms ground itself uses `BermsGroundV2.mat` (see "Berms road ground V2"); this material stays
  on the training range's earth bank and for rollback.*
- **Lights**: West Gate practicals are registered with City Light Circuit as practical *and* night-only lights.
  City Light Circuit now also drops practical shadows while its strength is below *Shadow Strength Threshold*.
- **Rebuilding**: *West Gate: build assets* rebuilds prefabs but never overwrites existing materials.
  *West Gate: install outpost* refuses to run over an installed outpost. The wreck gantry beside the gate is chunked
  AuthoredWorld content: its new visuals are under Gate/Wreck gantry, the originals are inactive sources; use
  Show Sources / Rebuild Render Chunks as usual if you change them.

## Berms road ground V2 (1 October 2026)

**Outer Berms → Berms ground** now uses `Art/BermsRoad/Ground/BermsGroundV2.mat` (shader *Athen Hill/Berms Ground V2*):
the basin's V2 ground model (scree, sand with wind ripples, rock with strata on slopes; the natural-ground values are
copied from `SandstoneBasinV3.mat` by the build step, so the toe matches the basin) plus painted features from two
splats over x −104…−60, z −54…48. `BermsRoadSplat.png` holds R road gravel, G sand, B crust and A 1 − compaction (the
channels the footstep map reads); `BermsRoadSplat2.png` holds R loose gravel, G relief height, B varnished-lag share and
A smoothed slope. The road from the outpost to the depot has two compacted wheel paths with ruts, a loose-gravel crown,
graded gravel windrows on both shoulders, sand-filled potholes and pull-off tracks; the outer 7 m of the floor fade to
the basin look. The ground mesh and its collider are unchanged.

- **Tune** colours, contrast, relief and the inner rock threshold on the material, or edit
  `art/berms_road_20261001/material.json` and re-run `--steps build` (the README lists the properties). Natural-ground
  values come from the basin material: change them on `SandstoneBasinV3.mat`, then re-run `build`.
- **Road features** (widths, ruts, windrows, potholes, spurs) are in `make_splat.py`, which reproduces the West Gate
  painting exactly off the road (`--check` proves it). If the splat changes, rebake the footstep map: `install` does it
  once and `toggle:new` re-applies it.
- **Berms road edge stones** (under Outer Berms) are ordinary `PH_Rock` prefab instances (no collider, no shadow) plus two
  cairns (one box collider each); move or delete them freely, keeping them off the road and spurs.
- `Editor/BermsRoadPass.cs` steps: `survey`, `build`, `install` (one time), `cameras`, `tune`, `verify`,
  `toggle:old|new`, `capture`. **Rollback:** `--steps toggle:old -nographics` restores the old material and footstep map
  and hides the stones; the pre-install scene is `evidence/berms-road/20261001/rollback/before-berms-road.unity`. The
  old `BermsGround.mat` stays on the range's earth bank.
- Review cameras `cam_br_*` (**Berms road review cameras**); evidence: `evidence/berms-road/20261001/README.md`.

## Warden training range (1 October 2026)

Scene root **Outer Berms/Warden training range** (groups *Firing point*, *Range officer*, *Range orders*, *Range flags*,
*Distance posts*, *Night lighting*, *Machine lane*, *Service apron*, *Backstop*, *Decals*). `TrainingRangePass` builds the
textures, URP materials and prefabs in `Prefabs/TrainingRange/` (including `TR_TrainingDrone` and the baked
`TR_WorkerDroidShell`; menu **Athen Hill → Outer Berms → Training range: build assets**); `TrainingRangeInstall` does
the one-time install, verify and editor captures. Batch:
`TrainingRangePass.RunBatch --steps build|install|verify|toggle:on|off` with `-nographics`, or
`capture:<dir>:cam_a+cam_b` with graphics and at most six cameras per run. Sources and run order:
`art/training_range_20261001/README.md`.

- Move, add or delete kit instances in the Scene view; none is a render-chunk source. Keep anything with a collider out
  of the tutorial's lines of fire (the eye at the firing line, `cam_checkpoint_plate1-3`, to each plate's aim point)
  and out of the plates' 1 m fall zone; `verify` reports `shotsBlocked`.
- The earth bank (`Backstop/Backstop earth bank`, mesh `Art/TrainingRange/Structures/TR_BermEarth.asset`) is generated
  on the Berms ground by the install from `layout.json` (`berm`); it uses the old Berms Ground material and has its own
  mesh collider. The timber revetment and the cable runs are world-space assets placed at their recorded origin
  (`authored-assets.json`); re-author them in Blender rather than moving them.
- Never move the plates, the range reset station, the briefing board, Ossa and Rell, the arms locker, encounters,
  respawn or the `checkpoint_*` landmarks. The retired range clutter (old firing bench and sandbags, the flag in front
  of the line, the plates' floating "PLATE 0n" text, rocks and shrubs on the range floor) is inactive in place;
  `evidence/training-range/20261001/install.json` lists every object.
- Night lights are on the **Ward lighting clock** (practical + night-only); the red "range live" lamp is practical only.
- Rollback: deactivate the root (the retired objects can be reactivated from the install record) or restore
  `evidence/training-range/20261001/rollback/scene-before-training-range.unity`.
- Review cameras `cam_range_*` (**Training range review cameras**). The pass's own native A/B measured +0.7 ms at the
  range's wide view, +0.17 ms looking out of the West Gate and nothing at `cam_hill`; evidence and the tutorial check:
  `evidence/training-range/20261001/README.md`.

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
  re-creates its lights, so rerun the install (authoring: `VanguardHallPass.Reinstall()`) to re-bind them to the clock,
  then re-run `NightFacadePass` `apply` to restore the wall-lamp tune (see "Night facade tune").
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
  After *Build assets* or *Refresh models and materials*, re-run `NightFacadePass` `apply` (see "Night facade tune"):
  *Build assets* re-creates the wall lamps as point lights with `VH_LampLens` bulbs, and *Refresh* puts `WS_Glass` back
  on every shop's windows.
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
  Then re-run `NightFacadePass` `apply`, as for the hall-district shops.
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

## Ward rooftops and service lines (1 October 2026)

**Ward rooftops** (scene root) breaks the shop cornices where the avenue sees them. It has one child per shop roof
(*Relay Works roof*, *Air + Water roof*, … *Thread + Hide roof*) whose transform equals that shop's root, so the pieces
under it are in the shop's own frame (origin = facade centre at paving level, +Z towards the avenue), and **Service
lines** in world space: two conductors across each cross street between roof masts, short lines across the two narrow
alleys, and four conduit drops from the masts down the side walls into junction boxes. Pieces are prefab instances of
`Prefabs/Rooftops/RT_<id>.prefab` (tanks, dew/condensate nets, PV frame, cowls, turbine vents, whip, dish, service-line
masts, guard rails, shade frame, caged ladders, wall hooks, junction boxes; LOD0/LOD1, shadows only on the two tanks)
plus three street-kit props on the Salvage terrace (shadows off as instance overrides). Nothing was retired, no
render-chunk source changed and there are no lights.

- Move, add or delete deck pieces in the Scene view; keep them inside the parapets and 1.8 m from the Repairs flue and
  Salvage stovepipe smoke. The **spans and drops are meshes generated from the layout**, so moving a mast or junction
  box means editing `art/rooftops_20261001/layout.py` (which validates decks, roof furniture, smoke, windows and doors,
  routes and roof clearance), then `author_cables.py` (Blender) and **Athen Hill → Rooftops → Build assets**; rebuilt
  prefabs update the instances. Kit geometry: `author_roof_kit.py`; maps: `make_textures.py`.
- Materials: the shops' `VH_*` and `WS_*` and the street kit's `SD_Sack` and `SD_Rope` (shared, so their Inspector edits
  apply here too), plus `Art/Rooftops/Materials/RT_DewNet` (alpha-clipped, double-sided net; *Base Map* tiling 4 =
  0.25 m tiles), `RT_SolarCell` and `RT_Ceramic`.
- Ladders carry a box collider over their bottom 2.2 m; on the roofs only the three street-kit props keep their own
  boxes.
- **Install (one time)** refuses to run twice (authoring: `RooftopsPass.Reinstall()` replaces the root from
  `layout.json`); **Verify saved scene** writes `evidence/rooftops/20261001/verify-saved-scene.json`. Review cameras
  `cam_rt_*` (**Rooftops review cameras**): four along the avenue rows and two into the cross streets, all at 1.62 m.
  Evidence, rollback scene and remaining defects: `evidence/rooftops/20261001/README.md`.

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

### Birch canopy and bed uplights (1 October 2026)

`birch 3` and `birch 4b` stay TreesBundleB prefab instances (prefab links, LODGroups and trunk capsules unchanged). Their
five LOD renderers use baked mesh copies (`Art/BirchCanopy/Meshes/BC_*`: crown occlusion, per-card season, brightness
and dryness in vertex colour, crown-volume leaf normals; positions and triangles identical) and six materials in
`Art/BirchCanopy/Materials` on **Athen Hill/Ward Canopy** (`Shaders/WardCanopy`, a fork of the Ward Tree shader): the
green leaf map blended per card to the turned-leaf map, *Albedo saturation*, *Crown occlusion on ambient/direct*, leaf
transmission with *Sun transmission through the crown*, wind *bend start/end heights*, *Crown sway* and *Leaf flutter*.
Never static-batch the birch LOD renderers (wind).

- Change the look on the materials, or in `art/birch_canopy_20261001/canopy-tune.json` followed by
  `BirchCanopyPass.RunBatch --steps apply,verify -nographics`. Changing the bake (occlusion, season distribution,
  normals) needs `--steps build,apply,verify`.
- **Bed uplights** (`TreeBed_Birch3/4b.prefab`, the same light objects on the **Ward lighting clock**): an avenue-side
  trunk wash and an opposite crown beam per bed, with the lens `BC_UplightLens` (not the shared `VH_LampLens`). Values
  live in `canopy-tune.json`; `apply` recomputes the aim from the recorded positions. **Athen Hill → Courtyard trees →
  Build assets** or **Retune uplights** puts the old 70 / 14 m lights and `VH_LampLens` back, so re-run
  `BirchCanopyPass --steps apply` after either.
- From wider views the bed uplights can be culled by the visible-light cap (see "Night lighting and ambient life");
  judge a fixture from a camera near it.
- Review cameras `cam_bc_*` (**Birch canopy review cameras**). `--steps rollback` restores the vendor meshes and
  materials, bed lights and lens slots; the pre-install scene is `evidence/birch-canopy/20261001/rollback/`. Evidence:
  `evidence/birch-canopy/20261001/README.md`.

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

## Shade sails (1 October 2026)

**Ward shade sails** (scene root) holds four prefab instances (`Prefabs/ShadeSails/SS_Courtyard/Market/Apron/Lattice.prefab`):
tensioned canvas sails over the mission-terminal court, the market rest spot behind Air + Water, the caravan goods on the
West Gate apron and the approach to the Lattice step. Each prefab has three LODGroups: **Sail** (canvas, rolled hem,
corner plates, turnbuckles or lashings), **Rig** (raked steel poles on stone footings or sandbagged base plates, guys to
sandbagged anchors, and wire-rope strops on the two retrofit service poles by the market) and **Festoons** (cable,
lampholders, bulbs). It also has **Festoon lights** (unshadowed points on the **Ward lighting clock**, practical +
night-only; the bulb material `SS_FestoonBulb` is on the clock's emissive list) and **Colliders** (pole capsules,
footing, ballast and guy-anchor boxes, and one camera-only mesh collider per canvas, at least 3.67 m up, so the follow
camera stays under the sail). Nothing was retired and no render-chunk source changed.

- **Shadows:** the canvas renderers never cast. A ShadowsOnly copy of the coarse canvas 4 cm below each sail (one per
  LOD) casts the sail's shadow, so the cloth never shadows itself and its underside keeps the sun transmitted through it.
  Keep that arrangement if you replace a canvas. Poles and stone footings cast at LOD0 only.
- **Materials:** the canvases `Art/ShadeSails/Materials/SS_Sail_<Site>` use **Athen Hill/Ward Ground Cover** with its
  wind at 0: *Leaf light transmission* (0.18–0.32) is how much sun glows through the cloth, *ambient transmission* the
  shade side, and alpha clip opens the worn-through holes. Pole paints `SS_PoleGrey/Red/Olive` are tinted copies of
  `VH_Steel`.
- **Rebuild:** geometry, layout and textures are generated in `art/shade_sails_20261001` (`sails.py` for layout and
  validation, `author_sails.py` in Blender, `make_textures.py`), then **Athen Hill → Shade sails → Build assets** (batch
  `ShadeSailsPass.RunBatch --steps build,verify`). This re-saves the prefabs in place, and the installed instances keep
  their clock bindings. Only if the number of sails or lights changes, use `--steps build,reinstall,verify`, which
  re-creates the instances, re-binds the lights and keeps the first rollback copy. For material values only, use
  `--steps materials,verify`.
- **Moving a sail** means moving its poles: change `sails.py` and re-run the chain; don't move an instance by hand. The
  validator checks routes, doors, stairs, NPC points, sightlines to the Lattice ring and the terminals, and head
  clearance (lowest canvas 3.67 m, lowest festoon cable 2.92 m).
- The pass's `toggle:off|on` step saves the scene; for A/B builds use scene copies instead.
- Review cameras `cam_ss_*` (**Shade sail review cameras**). Evidence, the rollback scene and the light-circuit change:
  `evidence/shade-sails/20261001/README.md`.

## Wall-foot sand and grounding (1 October 2026)

**Ward wall-foot drifts** holds 334 prefab instances of an eight-piece sand kit (`Prefabs/WallFootDrifts/WFD_Run_L/M/S`,
`Run_Low`, `Corner_L/S`, `Post`, `Sheet`; LOD0–2, culled past about 60 m, no shadows or colliders) and 320 URP decal
projectors, grouped per building (`Relay Works` … `Thread + Hide`, `Basic General`, `Vanguard Hall`, `Hill plinth and
stairs`, `Posts`, `Shop alleys`), each group with a `Decals` child. Banks sit on the measured wall-foot lines, heavier on
faces into the west-south-west wind and in inside corners; step middles, doors, bays, props, routes and NPC points stay
clear. The drifts are not a render-chunk source: move, duplicate or delete instances directly, with uniform scale only,
and keep each bank's sand on its own level (not hanging off a porch edge). Characters walk through the banks by design.

- **Look:** sand material `Art/WallFootDrifts/Materials/WFD_Sand` (URP Lit; tint `_BaseColor`, 1.5 m tile). Decal
  materials `WFD_DecalFootBand` (ground film along the banks), `WFD_DecalWallSkirt` (contact grime and dust coat on
  walls), `WFD_DecalPost` and `WFD_DecalSheet`; per projector edit Fade Factor, Size and position (draw distance 40 m).
  They use `Art/WallFootDrifts/Shaders/WFD_Decal.shadergraph`, a copy of the Ward weathering decal graph with **angle
  fade on**; the shared graph has it off, which paints ground decals onto risers and props.
- **Geometry or layout:** `art/wall_foot_drifts_20261001` (`author_drift_kit.py`, `faces.py`, `probe_faces.py`,
  `layout.py`, `make_textures.py`), then **Athen Hill → Wall-foot drifts → Build assets** (prefabs and materials update in
  place). Re-placing everything needs `reinstall` (authoring only). `layout.py --check --audit <audit>` re-validates the
  installed placements against a fresh scene audit. The pass's `toggle:on|off` step saves the scene; for A/B builds use
  scene snapshots instead.
- **Rollback:** deactivate the root (or delete it and its review-camera root); the pre-install scene is
  `evidence/wall-foot-drifts/20261001/rollback/before-wall-foot-drifts.unity`. Nothing was retired.
- Review cameras `cam_wfd_*` (**Wall-foot drift review cameras**). Night and native views had not been reviewed by the
  pass; evidence and known limits (little sand on porch decks, post collars that can read as discs):
  `evidence/wall-foot-drifts/20261001/README.md`.

## Perimeter walls (1 October 2026)

**Ward perimeter walls** (scene root, one child per wall) holds 87 instances of a 32-module kit on the Ward masonry
(`Prefabs/PerimeterWalls/PW_<kind>_<variant>_<length>.prefab`): the north and south curtain walls, the +X rampart either
side of the District gate arches (and the slot between them), the strip wall beyond it and the −X Outer Berms walls.
Each prefab is a LODGroup (LOD0 bevelled and chipped ashlar within about 16 m, LOD1 to about 45 m, flat-block LOD2
beyond) plus one ShadowsOnly massing mesh used at every LOD, inset 9 cm behind the lit faces so the stone never
self-shadows and shadows never pop between LODs. Fittings, field repairs and rubble cones cast their own shadows. The
walls are not render-chunk sources.

- Move, swap or delete module instances in the Scene view, with uniform transforms only (modules run along local +X,
  city face +Z, origin on the wall centreline at paving level). To swap a bay, drag another `PW_*` prefab of the same
  length into its place.
- Collision is unchanged: the saved boxes `AuthoredWorld/COL_BLD_boundary_wall*`, `COL_BLD_west_wall*`,
  `COL_BLD_berms_gate_wall_*` and `COL_BLD_boundary_side` still enclose the city, so the visual collapses and the siege
  breach stay blocked. Nine low convex colliders sit on the rubble cones.
- Story beats: shell craters, soot, a broken merlon and stitched cracks on the District gate flanks; the south wall
  collapse at x 7–14; the north wall collapse at x −42…−49 behind the Quantum Tube; and on the Berms wall by the West
  Gate portal, shell damage, a collapse and the old siege breach closed with HESCO, sandbags and a welded sheet screen.
- Geometry changes go through `art/perimeter_walls_20261001` (`pw_layout.py` → `layout.json`;
  `author_perimeter_walls.py` → `Art/PerimeterWalls/Models`, about a minute for all kinds; `pw_validate.py` checks every
  module footprint against a scene audit), then **Athen Hill → Perimeter walls → Build assets** (batch
  `PerimeterWallsPass.RunBatch --steps build,verify`). **Install (one time)** refuses to run twice; `reinstall` replaces
  the root during authoring.
- Retired (inactive, kept for rollback): the old `AuthoredWorld/BLD_boundary_*`, `BLD_west_wall*`, `BLD_wall_buttress*`,
  `BLD_wall_inset*`, `BLD_wall_signal*` and `BLD_berms_gate_wall_*` visuals and the `Wall shadow proxy` objects, listed in
  `evidence/perimeter-walls/20261001/install.json`. The scene before the install is in
  `evidence/perimeter-walls/20261001/rollback/`.
- Gotcha: a shadow-only proxy that coincides with the lit stone faces puts the whole wall in its own shadow (URP biases
  do not cover it); keep proxies inset behind the faces.
- Review cameras `cam_pw_*` (22, **Perimeter wall review cameras**); evidence and remaining defects:
  `evidence/perimeter-walls/20261001/README.md`.

## Hydroponics greenhouses (1 October 2026)

**Ward hydroponics** fills the two retrofit quonsets (`Ward district retrofit/Hydroponics bays`) and the ground round
them:

- **Interior**: 14 prefab instances at their authored pivots: `Prefabs/Hydroponics/Interior/HY_Fitout_A/B` and twelve
  `HY_Crops_<bay>_<side>_<third>` crop sections, each a three-level LODGroup (full plants within about 9 m, reduced heads
  to about 25 m, one cross card per plant beyond). The racks, NFT channels, feed lines, LED bars, vine gutters, fans and
  floor are in the fit-out; lettuces, chard, herbs, seedlings, microgreens, cordon tomatoes and runner beans are in the
  sections. The crop-bar LEDs (`HY_LED`) are on the **Ward lighting clock**; the propagation-tier LEDs (`HY_LEDProp`)
  stay on. Crop sections cast shadows only within their LOD0 range, through a shadow-only copy of the LOD1 heads.
- **Yard**: 58 prefab instances in 12 vignette groups (*harvest by the A door*, *potting bench*, *nursery under shade*,
  *growers' rest bench*, *cart loaded for the market*, *nutrient totes*, *dosing* …), each group's origin at its centre,
  with ground grime and scuff decal projectors. `HY_crate_*`, `HY_basket_*` and `HY_pot_*` nest the street kit's scanned
  crate, basket or pot (`Prefabs/StreetDressing`) with a produce fill. Stools and the bench carry **NPC sit point**
  markers. Nothing in the yard is a render-chunk source: move, duplicate or delete instances directly.
- **Grow glow lights**: four night-only point lights inside the bays on the light clock (practical and night-only).
- **Retrofit planters and tank fittings**: a filtered copy of the retrofit's `Hydroponics bays Detail` mesh
  (`Art/Hydroponics/Retrofit/Hydroponics_bays_Detail_kept.asset`) without its 93k triangles of desert succulents.

The one-time **Install** retired `Hydroponics bays Detail` and `Hydroponics bays Glow` (inactive, kept for rollback). The
`Hydroponics bays Structure` renderer's polycarbonate slot is a prefab-instance override to `HY_Polycarbonate` (dust and
condensation film, double-sided, **no shadow pass** so sun reaches the crops); revert that override to restore the
retrofit skin. The quonsets keep their solid colliders; they are not enterable.

Change geometry through `art/hydroponics_20261001` (Blender `author_hydroponics.py --only interior|props`; textures
`prepare_textures.py`; layout `layout.py`, which checks colliders, door thresholds and walking lines), then **Athen Hill →
Hydroponics → Build assets** (re-imports, rebuilds materials and prefabs; scene instances update). After an install,
`--steps build,reinstall,verify` is for authoring only. Materials are in `Art/Hydroponics/Materials`; crops use **Athen
Hill/Ward Ground Cover** with no wind and leaf transmission. For a timing A/B, `HydroponicsPass abbuild:on|off` builds
both arms from one snapshot without changing the saved scene. Review cameras `cam_hy_*` (**Hydroponics review
cameras**); the pass's own A/B (+0.73 ms day and +0.98 ms night at the yard's wide view, +0.14 ms at `cam_hill`), the
rollback scene copy and remaining defects are in `evidence/hydroponics/20261001/README.md`.

## Night lighting and ambient life (1 October 2026)

**Ward night life** (scene root, not a render-chunk source) lights the pockets that fell to moonlight at night and adds
small working effects:

- **Street lamps** and **Wall lamps**: prefab instances of `Prefabs/NightLife/NL_StreetLampPost` and `NL_StreetLampWall`,
  merged-part versions of the authored Ward utility post and wall fixture (`Art/Quality/Lamps`; the five avenue lamps
  still use the 103-part originals as chunk sources). Three LODs (post 35.7k / 19.6k / 4.1k triangles, switching at
  about 33 m and 66 m); the masses cast sun shadows through a ShadowsOnly LOD2 copy; the post has a mast capsule and a
  footing box collider. Each instance carries a scene-added warm spot (*Lamp warm street light*: straight down, 150°,
  intensity 6, range 15 m; *Lamp warm wall light*: tilted 25° out from the wall, 130°, intensity 4, range 10 m),
  unshadowed and listed on the **Ward lighting clock** as practical and night-only. Move a lamp by moving its instance;
  tune its light directly. Pockets: the courtyard behind the mission terminals, Vanguard Hall's east corner, the Lattice
  court, the hill-foot benches, both sides of the District gate apron, the south-wall collapse, the south lane (two wall
  brackets), the north collapse behind the Quantum Tube and the east rampart foot by the nanofab yard.
- **Mission terminal glow**: one cool point fill (0.75, 3 m, night-only on the clock) in front of each Meshy mission
  terminal screen. The three terminals use `Art/NightLife/Terminal/MissionTerminal_Lit.mat` (the Meshy material plus an
  emission map of the MISSIONS display, the badge and the status button derived from the albedo; constant emission, like
  the hill kiosks). The original `MissionTerminal.mat` is unchanged; put it back on the three renderers to revert.
- **Ambient life**: *Barrel fire* (flames and embers on the HDR additive `Art/NightLife/FX/NL_BarrelFlame`, smoke and a
  flickering fire light in the market rest-spot barrel), *Repairs flue smoke*, *Salvage stovepipe smoke*, *Air + Water
  relief steam* (intermittent puffs) and *Generator exhaust haze*. These are ordinary ParticleSystems (cookfire
  materials, `Art/NightLife/FX/NL_Steam`, `NL_ExhaustHaze`) driven by **AmbientLife** (`Scripts/AmbientLife.cs`):
  Reduced Motion stops and clears them, *Day/Night Tint* scales the particle colour with the clock, and *Puff Seconds*
  and *Min/Max Gap* make intermittent puffs. The fire light flickers at night and is off by day; it is deliberately not
  on the light clock, which would overwrite the flicker.

Layout and validation: `art/night_life_20261001/night_layout.py` (routes, doors, stairs, NPC points, props, colliders) →
`night-layout.json`. `NightLifePass.RunBatch` (batch only, `-nographics`) steps: `relayout` (adds, moves or removes
fixtures to match the layout, keeping the light objects and their clock bindings), `retune` (light values),
`rebuildfx` (recreates *Ambient life* and the review cameras), `fxmats` (particle materials only), `lodcuts` (lamp LOD
heights in place). **Do not re-run `build` after the install**: it re-saves the lamp prefabs under the installed
instances. The install is one-time. Compile-check C# changes outside Unity first with
`art/night_life_20261001/check_compile.py`. Review cameras `cam_nl_*` (**Night life review cameras**); evidence and
remaining defects: `evidence/night-life/20261001/README.md`.

**Visible-light cap (OpenGL Core).** The Linux player runs OpenGL Core, where URP draws at most 32 lights per camera:
the sun, the fill and the 30 local lights nearest the camera. When the birch canopy pass measured it, the saved scene had
140 enabled local lights and the lighting clock kept them at full strength within 90 m, so in the courtyard 68–85
lights were visible and lamps beyond about 26–36 m from the camera were not drawn (for example the Vanguard Hall portal
lamps and the market lanterns from the birch views). The shade sails, installed later, add 7 festoon lights to the
clock (practical lights 136 → 143, night-only 82 → 89), all competing for the same 32. Judge a fixture from a camera near it; a lamp missing in a wide view may be culled, not broken. Measured
by the birch canopy pass's `capture` probe (`lightcull-*.json`; `evidence/birch-canopy/20261001/README.md`). The fix
is district-wide: Vulkan for the Linux player (a graphics-API change) or a light-budget pass. Both are Carl's decision.

## Night facade tune (1 October 2026)

Material and light values only. All of them live in `art/night_facade_20261001/facade-tune.json` and are applied by
**NightFacadePass** (`Editor/NightFacadePass.cs`, batch steps `apply`, `verify`, `rollback`, `fixdefects`); the original
values are in `originals.json`, recorded before the first change.

- **Wall lamps** (the caged `PH_WallLamp` heads on the nine Ward shops and Vanguard Hall, 34 in all): each
  `<lamp> light` under the prefab's **Practical lights** is a **spot** placed 0.15 m further from the wall and 0.1 m
  below its original point, aimed down and 10° out, 140° / 95°, intensity ×1.3, with the cookie
  `Art/NightFacade/Textures/NF_WallLampCookie`, unshadowed, on the Ward lighting clock (practical + night-only). The
  bulbs use `NF_WallLampBulb` and the globes `NF_WallLampGlass` (both on the clock's emissive list). The edits are in the
  prefab assets (`Prefabs/WardShops/*.prefab`, `Prefabs/VanguardHall/VanguardHall.prefab`), so the scene instances
  carry no overrides. `VH_LampLens` (hill uplights; the tree beds now use `BC_UplightLens`) is unchanged. To retune, edit the `lamps` block and run
  `apply`: positions are always recomputed from the recorded originals.
- **West Gate arch bulkheads** (`Prefabs/WestGateArches/WGA_GateA/B`): lens slots on `NF_BulkheadLens` (on the clock's
  emissive list); the *Bulkhead light* sits 0.3 m further from the leaves and leans 8° toward them, 140° / 90°, intensity
  4.2, range 8.5 m, so the leaves and arch A's wicket are lit (block `bulkheads`).
- **Shop windows**: `WS_Glass` (Relay Works, Air + Water, Tool Exchange), `Art/NightFacade/Materials/NF_Glass_HallEast`
  (Finery, Field Supply) and `NF_Glass_North` (Salvage, Repairs, Thread + Hide) set the room-lamp intensity
  (`_EmissionColor`), lit fraction, blinds and the warm, neutral and cool lamp colours per street. **Athen Hill/Ward
  Window Interior** has a third lamp colour: *Neutral lamp tint* and *Neutral lamp fraction* (0 = the previous
  two-colour look). `VH_Glass` (the hall) is tuned the same way.
- **Ward masonry** `VH_Ashlar` and `VH_AshlarRough`: *Normal Map → Scale* 0.65 (was 1.0), so the worn-rock normal stops
  reading as pillows under grazing lamp light. It is the shared stone of every building on the masonry kit.
- **Re-run `apply`** after a shop *Build assets* (it re-creates point lights and `VH_LampLens` bulbs), a shop *Refresh
  models and materials* (it puts `WS_Glass` back on every shop), a Vanguard Hall prefab rebuild or a West Gate arch
  prefab rebuild. `rollback` restores every recorded light, bulb, glass slot and material value, the decals and the
  retrofit mesh; the window shader before the third colour is
  `art/night_facade_20261001/rollback/WardWindowInterior.shader.orig`.
- **Defects** (`fixdefects`): two orphaned 8 Sep wall-foot decals (*Field Supply and Finery weathering/…/Foundation
  grime 9, 10*) left at the old Finery facade line over the porch are inactive. The floating 13:00 shadow at the hill
  benches was the hoist of the old Tool Exchange jib crane, now stripped from *Ward district retrofit/Shop
  retrofits/Shop retrofits Structure* into `Art/NightFacade/Retrofit/Shop_retrofits_Structure_north_avenue_nf.asset`
  (original asset kept). The visible Finery porch streak is the moonlight shadow of *Avenue utility lamp 02*'s mast (the
  night key light; only the warm lamps fill it), not a decal; softening it needs a district-wide night key-light change,
  left to Carl.
- Review cameras `cam_nf_*` (**Night facade review cameras**). Evidence and remaining defects:
  `evidence/night-facade/20261001/README.md`.
