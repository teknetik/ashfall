# Ward / Athen Hill — Unity production guide

Updated 28 September 2026. This replaces the historical browser MVP guide.

## Kanban board for Ashfall

For all future Kanban tasks concerning this project (the Ashfall game, including
Ward / Athen Hill), use the dedicated **Ashfall** Kanban board. Pass
`board="Ashfall"` explicitly when creating each task, including delegated,
review, QA and follow-up cards; do not rely on the default/current board.
Use the same board for task lookups, comments, links, blockers and completion
so the full task history stays together. Include this board instruction in any
handoff that may create further Ashfall tasks.

## 1. Direction and authority

Build and test **only the native Linux Unity game** in `unity/AthenHill`.
The user wants visual quality on par with **GTA6**. Treat that as an ambitious
reference for believable real-time environments, materials, lighting, characters,
animation and presentation. The immediate deliverable is a polished, playable
Ward district. GTA6-level quality is not established by an engine choice, a Meshy
export, a successful build, a high frame rate or this document. It requires
sustained asset production, art direction and in-game review; do not promise
whole-game parity, production scale or a schedule without evidence and planning.

Authority for future work:

1. The user's latest explicit instructions and accepted reference feedback.
2. This guide for production rules, and [lore.md](lore.md) for setting canon.
3. The actual saved Unity scene, serialized data and current source records for
   implementation status; dated evidence applies only to the build it tested.
4. [unity/EDITING.md](unity/EDITING.md) for editing operations,
   [unity/DESIGN.md](unity/DESIGN.md) for the accepted interface, and the linked
   asset manifests for provenance and recovery instructions.
5. Older handovers, phase reports and numbered concept frames are historical
   references where they conflict with the direction above.

Do not develop, rebuild or browser-test the retired TypeScript/Vite game.
Historical web files and shared art/audio production inputs may be read or reused;
asset-only processing is allowed. Preserve unrelated and uncommitted work.
Do not restart the port, regenerate the city or follow old browser build prompts.

## 2. Setting and product scope

**Tir** is the planet; **Ward** is the surviving oasis city. The Fall, Great Rebuild,
Quantum Tube network, Karaveen, Wardens and Outer Berms come from `lore.md`.
The unknown reason for Tir's isolation remains unknown. Do not invent a definitive
answer, new faction history, or a civil-war origin for the Fall.

Use that setting for new concepts and writing. Athen Hill remains the repository,
scene and current build label. Free Column, Lattice Jack, Ring Gate, Vanguard Hall
and the old NPC dialogue still exist in the implementation. Reconcile player-facing
names in a deliberate content pass; keep stable asset GUIDs, scene identifiers,
dialogue IDs, routes and save/data references. Do not automatically equate the
Free Column with the Wardens or turn goods-only Tube lore into confirmed passenger
transport. Names left in the current build are not additional setting canon.

The long-term game vision includes survival, settlement rebuilding/expansion,
nanotech-and-scrap weapons and FPS combat. These are future production milestones,
not permanently forbidden features and not already implemented. This guide update
does not authorize starting all those systems at once. Establish the district's
visual standard and preserve its working loop before expanding its scope.
Multiplayer, accounts, vehicles and extra playable regions are not current tasks.

The existing city loop must continue to work:

- Spawn at West Gate; walk the avenue, hill stairs, porches and gate openings.
- Talk to Mira, Torr, Vex and Linn; retain dialogue branches and objectives.
- Trade at Basic General, including flask purchase and scrap sale with atomic
  inventory/credit changes. Prices and starting inventory live in CityCatalog.
- Use the Lattice transition and sector overlay. Ring Gate retains its offline
  response until an explicit gameplay task changes it.
- Preserve movement, jumping, left-drag camera look, wheel zoom into first person,
  interactions, modal input blocking, inventory, notes, pause, audio, reduced motion
  and keyboard access. [unity/README.md](unity/README.md) records current controls.

## 3. Current Unity and asset baseline

Versions recorded in the project: **Unity 6000.6.0f1**, **URP 17.6.0**,
**glTFast 6.20.0**, Unity MCP **v10.2.0**. Inspect ProjectVersion, package manifest
and lockfile before changing dependencies. Keep Linux x86-64 working; existing
native evidence uses OpenGL. Do not silently change the graphics API or pipeline.

| Area | Current state to preserve |
| --- | --- |
| Player | Supplied MeshyPlayer from `meshy/mpc`, walk/run and controller-driven movement. Static source idle/talk are known quality limitations. See [player record](unity/MESHY_PLAYER.md). |
| Four talking NPCs | Currently the supplied Ward Guard with arms at its sides on all four interaction roots. Distinct, role-appropriate characters may replace it (see §4 Characters); keep the interaction roots, dialogue IDs and routes. |
| Three original ambient walkers | `meshy/Meshy_AI_weathered_traveler_ri_biped`, supplied walking animation, existing roots/routes. |
| Additional ambient actor | Yard mechanic, Humanoid Animator and its separate four-point service-yard loop. The current roster is one player, four talking NPCs and four ambient walkers. |
| South Ring Gate | Accepted 12,009-triangle Meshy model, open aperture, console, approach step and current interaction/hum. The 6,263-triangle remesh was rejected. |
| Mission terminals | Three saved Meshy terminal instances and the MissionTerminal prefab. Preserve the mission slab, nearby interaction access and `cam_terminal`; task records are in `meshy/mission-terminal-v1`. Since 1 Oct 2026 the three renderers use the emissive variant `MissionTerminal_Lit` (night lighting row below); `MissionTerminal.mat` is unchanged for rollback. |
| Shops and salvage | Restored Relay-based shops, Basic General and the community board. The 8 Sep salvage scatter (trash, crates, scrap, generators) is retired and replaced by the street dressing kit (below). |
| Vanguard Hall | Rebuilt 30 Sep 2026 from the accepted concept (`art/vanguard_hall_20260930`): authored ashlar hall with LODs, own colliders, lamps on the city light clock, weathering and old battle damage from the shared `art/ward_masonry_kit`. The two facade uplights are Carl's Meshy tripod floodlights (`Prefabs/WardHill/WardFloodlight`, 30 Sep) in place of the modelled boxes. The Meshy hall stays in the scene inactive for rollback. See [EDITING](unity/EDITING.md). |
| Hall district shops | 30 Sep 2026: Relay Works, Air + Water, Tool Exchange (sci-fi display, Meshy props), Finery and Field Supply rebuilt in modelled stone (`art/hall_district_20260930`) with door recesses, clock-driven lamps and a new sign family (incl. Basic General). Old layers inactive; porch colliders, filter bank and routes kept. Not yet accepted by Carl. |
| North avenue shops | 30 Sep 2026: Salvage (hoist, rubble-patched breach), Repairs (braced canopy, flue, roof container), Thread + Hide (balcony with cloth and hides, lit display) and the Basic General booth (stone walls and piers, red lintel carrying its family sign) rebuilt on the same masonry kit, signs and weathering (`art/north_avenue_20260930`). Mira, counter dressing, stock, colliders and routes kept; old layers inactive. Not yet accepted by Carl. |
| Rooftops and service lines | 1 Oct 2026 (`art/rooftops_20261001`, scene root **Ward rooftops**): 44 instances that break the shop cornices seen from the avenue: water tanks (Finery, Thread + Hide), dew/condensate nets (Air + Water), PV panels (Tool Exchange), HF whip (Relay Works), dish (Repairs), ridge vents (Field Supply), a shaded terrace (Salvage), guard rails and cowls; service lines on pin-insulator masts across both cross streets and the alleys, conduit drops into junction boxes, two caged ladders. LOD0 67k / LOD1 28k triangles, shadows on the two tanks only, no lights, clear of the night-life smoke columns; nothing retired. Not yet accepted by Carl. |
| District replacements | Two active west-gate arches (closed by gates since 1 Oct; see the next row) and the mechanic remain. Seven rejected shop candidates under `District rebuild` stay inactive until revised and reviewed. |
| West Gate arches | 1 Oct 2026 (`art/west_gate_arches_20261001`, scene root **Ward west gate arches**): the two Meshy `District gate` arches at the +X spawn closed with steel-faced timber gates set 1.6 m back in the passage: braced leaves on strap hinges and jamb pintles, a wicket door (arch A), drop bar in stirrups, transom and head grille, worn steel threshold, guard stones, cart-rut, scuff, sand, grime and KEEP CLEAR decals, a bulkhead lamp per arch on the light clock (retuned by the night facade tune). LOD0–2; one box collider seals each opening. Meshy arches, their render chunks and saved colliders unchanged; nothing retired. Not yet accepted by Carl. |
| Hill and hero tree | 30 Sep 2026 (`art/hill_20260930`, scene root **Ward hill**): the plinth, stairs, tree ring, paving, beds, soil and roots rebuilt on the Ward masonry kit (same stone as the hall and shops), Poly Haven planting on a wind shader, Carl's Meshy "Reclaim & Save Point" kiosks on the three terminal slots (decorative, as before), tree uplights on the light clock. The hero tree mesh itself is unchanged. Saved hill/stair colliders kept; old visuals inactive. Not yet accepted by Carl. |
| Courtyard trees | 30 Sep 2026 (`art/courtyard_trees_20260930`, scene root **Courtyard tree beds**): `birch 3` and `birch 4b` moved north (1.2 m / 1.8 m) into stone beds built like the hero ring (seat coping, litter, roots, drip line, apron, uplights on the light clock). Trees keep their prefab links and trunk capsules. 1 Oct 2026 (`art/birch_canopy_20261001`, `BirchCanopyPass`): both birches on baked canopy mesh copies (crown occlusion, per-card yellow-green season mix and brightness jitter, crown-volume leaf normals; same triangles) and the *Ward Canopy* shader (wind, leaf transmission, no metallic); each bed's two uplights split into a trunk wash and a crown beam, with their own dimmer lens `BC_UplightLens`. LODGroups, draw calls and light count unchanged. Not yet accepted by Carl. |
| Street dressing | 30 Sep 2026 (`art/street_dressing_20260930`, scene root **Ward street dressing**): 145 instances of a 68-prop kit (CC0 Poly Haven scans, four Meshy pieces, Blender sacks/tarp/skip/litter) in 30 purposeful vignettes along walls, porch ends, lanes and yards, grime/scuff decals, NPC sit points on seats; old scatter and cube dressing inactive. Lanes, doors, stairs and routes kept clear (`layout.py`). Not yet accepted by Carl. |
| Shade sails | 1 Oct 2026 (`art/shade_sails_20261001`, scene root **Ward shade sails**): four form-found canvas sails (madder, indigo, natural and natural/indigo cloths with patches, seams and stencils) over the terminal court, the market rest spot, the West Gate apron and the Lattice approach, on raked steel poles with stone footings or guyed sandbag bases (two tied to the retrofit service poles), with festoon strings and 7 unshadowed festoon lights on the light clock (practical + night-only). Canvas shadows come from offset ShadowsOnly proxies; camera-only canvas colliders keep the follow camera under the sails. 98.5k / 28.8k triangles at LOD0 / LOD1; routes, doors, NPC points and the Lattice and terminal sightlines kept clear; nothing retired. Not yet accepted by Carl. |
| Wall-foot sand | 1 Oct 2026 (`art/wall_foot_drifts_20261001`, scene root **Ward wall-foot drifts**): 334 wind-laid sand banks (eight-piece kit, LOD0–2, no shadows or colliders) at the measured feet of the eight shops, Basic General, Vanguard Hall, the hill plinth and stair cheeks, inside corners, step ends, posts and the shop alleys, heavier on faces into the west-south-west wind, plus 320 decals (sand film, wall dust and grime skirt, post collars, alley sheets) on an angle-fading copy of the Ward decal graph. Doors, step middles, props, routes and NPC points kept clear; nothing retired. Not yet accepted by Carl. |
| Perimeter walls | 1 Oct 2026 (`art/perimeter_walls_20261001`, scene root **Ward perimeter walls**): 87 instances of a 32-module kit on the Ward masonry: north/south curtain walls with merlons and piers, the +X rampart with buttresses and wall walk either side of the District gate arches, the strip wall, the −X Berms walls. Weathered, repaired, broken-parapet and shell-damaged bays, collapsed sections in the north and south walls, and the old siege breach by the West Gate portal closed with HESCO and welded sheet. LOD0–2 plus an inset shadow-only massing mesh; saved wall colliders unchanged; old wall visuals inactive. Not yet accepted by Carl. |
| Hydroponics greenhouses | 1 Oct 2026 (`art/hydroponics_20261001`, scene root **Ward hydroponics**): both retrofit quonsets fitted out (racks, NFT channels, feed lines, LED bars on the light clock, vine gutters) and planted in 12 crop sections with LODs (lettuces, chard, herbs, seedlings, tomatoes, runner beans); polycarbonate skin on a filmed copy with no shadow pass; a working yard of 58 props in 12 vignettes (harvest crates, potting bench, nursery shade with drying herbs, rest bench with sit points, market handcart, nutrient totes, dosing trolley, compost); four night-only grow-glow lights. Retrofit Detail (succulents) and Glow inactive; the quonsets are still solid, not enterable. Not yet accepted by Carl. |
| Night lighting and ambient life | 1 Oct 2026 (`art/night_life_20261001`, scene root **Ward night life**): 8 merged-part Ward utility posts and 3 wall brackets in the dark pockets (courtyard and terminals, Lattice court, hall corner, hill benches, gate apron, both wall collapses, south lane, rampart foot) with warm unshadowed night-only spots on the light clock; the three Meshy mission terminals on an emissive material variant with cool night fills; a barrel fire with embers and flicker light, two flue smokes, Air + Water steam puffs and generator haze driven by `AmbientLife` (stopped by Reduced Motion). Not yet accepted by Carl. |
| World | Editable terrain basin, stone/soil detail, cloud/dust atmosphere, landmarks and collision sources. Existing assets are a baseline, not a permanent quality ceiling. 1 Oct 2026: **Basin mountains** (`art/basin_mountains_20261001`, scene root **Basin mountains**) replace the backdrop ring with an eroded heightfield on the original layout (stream-power valleys and gullies, strata benches aligned with the shader's beds, talus, outcrops; 185k triangles in the eight original sectors with shared borders), the Berms ground toe kept exact, on `SandstoneBasinV3` with new haze-shape controls; the old `DesertBasin` chunks are inactive. **Berms road ground** (`art/berms_road_20261001`): `Outer Berms/Berms ground` on *Berms Ground V2* (the basin's scree/sand/rock model plus a repainted road with wheel paths, ruts, crown, gravel windrows and potholes, blending to the basin over 7 m), 24 edge stones and 2 cairns, footstep map rebaked; ground mesh, collider, routes, encounters and range unchanged. **City paving** (`art/city_paving_20261001`): the city floor and the plaza bands round the hill on world-mapped dressed-sandstone flags (*Ward Paving Lit*: 4 m tile, 0.5 m courses shuffled per course, per-flag tone, sanded joints, 2k textures, not streamed); `Paving Joints` and the four `Avenue service band` strips inactive, `COL_Ground` unchanged. Old materials kept for rollback. Not yet accepted by Carl. |
| Interface | Accepted worn bronze/metal UI Toolkit art, open center view, corner HUD, ten visible hotbar slots with six working actions and four empty reserves. |
| Sound | Existing ElevenLabs music, ambience, spatial hums, footsteps and interaction cues; retain mixer, mute and reduced-motion behavior. |
| Outer Berms loop | Scrap pistol with grip/barrel/cell mods, refined components, seeded loot with bad-luck protection, salvage caches, scrap heaps, Depot Foreman elite, Ossa's five field orders, Basic General Supplies / Buy parts / Sell salvage, versioned save with Continue. Content lives in `Data/Crafting/WardCrafting.asset`, `CityCatalog.asset` and the field-order set; see [unity/EDITING.md](unity/EDITING.md). |
| Warden training range | 1 Oct 2026 (`art/training_range_20261001`, scene root **Outer Berms/Warden training range**): the range beyond the West Gate rebuilt as a working Warden range: three timber firing bays at the tutorial's firing line, range officer's table and RANGE ORDERS board, distance posts, a timber-revetted earth backstop with impact scars and a crest flag, a machine lane (tyre run, cover barricades, tethered training drone, stripped worker droid in a target frame) and a drone service apron (charge docks under a shade shelter, repair bench, compressor, welding cart, generator), lights on the light clock. Plates, reset station, Wardens, locker, encounters, respawn and landmarks unchanged; replaced clutter inactive. Range tutorial check 10/10 and city loop passed in the pass's own test and in combined batches 1 and 2. Not yet accepted by Carl. |
| Rendering baseline | Forward+, 150 m / 4-cascade sun shadows, HDR grading, TAA on High, procedural sky v2, interior-mapped windows, terrain v2, combat FX, truck/tree LODs. Measure changes with `unity/tools/lookbook.py` and `profile_scene.py`; the player is GPU-bound on the reference machine. **Light limit** (found by the birch canopy pass, 1 Oct 2026): on the Linux OpenGL Core player URP draws at most 32 lights per camera (sun, fill and the 30 nearest local lights). Courtyard views see 68–85 lights, so lamps beyond about 26–36 m are culled. Vulkan (a graphics-API change) or a light-budget pass are Carl's decision. **Texture memory** (1 Oct 2026, `art/texture_memory_20261001`): 434 scene textures compressed with no source downsampled and no reference changed: 414 glTF-embedded images to BC7 by the glTFast import add-on `GltfTextureCompression` (on by default, so every .glb import compresses), 20 non-power-of-two TextureImporter maps to BC7/BC5, scaled up to a power of two and streamed. Native at three views: non-streamed textures 4.0 → 1.6 GB, resident 4.7 → 2.2 GB, player VRAM 8.0 → 4.5 GB. glTF textures are not streamed and glTF meshes keep UV distribution metric 1 (open). Render-chunk meshes record UV distribution metrics since the paving pass. The PC texture streaming budget is 5,632 MB (raised from 4,096 by the paving pass, pending Carl); after compression the texture-memory pass recommends 3,584 MB (Carl decides). **Night facade tune** (1 Oct 2026, `art/night_facade_20261001`, `NightFacadePass`): the 34 caged wall lamps of the nine shops and Vanguard Hall are down-and-out cookie spots with dimmer bulbs and glowing globes, the two West Gate arch bulkheads retuned, shop windows on per-street *Ward Window Interior* materials (less room light, more blinds, a third lamp colour), Ward masonry normal scale 0.65, the orphaned Finery porch decals and the floating jib-hoist remnant (the 13:00 hill-bench shadow) retired; values in `facade-tune.json`, originals recorded for rollback. Not yet accepted by Carl. |

Read the relevant source records before replacing assets:
[character imports](docs/model-import.md),
[Ring Gate](meshy/ring-gate-v1/README.md),
[mission terminal manifest](meshy/mission-terminal-v1/model/meshy-manifest.json),
[salvage](meshy/salvage-20260908/README.md),
[district/rejected shops](meshy/district-20260908/README.md),
[audio](unity/AUDIO.md).

## 4. Visual direction: contemporary fidelity on Tir

Keep the desert colony identity: sun-warmed mineral surfaces, salvaged industrial
metal, patched cloth, restrained cyan technology, an oasis tree, layered desert
terrain and a settlement with visible work and history. Early MMO city references
inform atmosphere and social readability. They do **not** prescribe 2001 rendering,
low polygon counts, muddy textures, primitive anatomy or crude animation.

Build visual storytelling from the lore: aquifer infrastructure, hydroponics,
food stalls, nanofabrication workshops, adapted industrial droids, caravan repairs
and defensive works are useful motifs. They should explain how Ward survives.
Art motifs do not imply working simulation systems. Place wear at joints, handles,
drainage paths and repair sites; avoid uniform grunge across every surface.

Use warm sandstone, varied weathered metals, restrained cloth accents, localized
vegetation and cool sky/shade. The old hex palette is reference, not a rule that
all materials must share one tint. Keep distinguishable stone, painted metal,
bare metal, rubber, fabric, soil, bark and skin under the same lighting.

Requirements for the visual target:

- **Architecture:** believable construction and human scale, coherent rooflines,
  doors, recesses, supports, trims and functional thresholds. Build depth where the
  player can see it. Repeated modules need meaningful structural/material variants.
- **Street composition:** intentional foreground/middle/background, readable
  landmarks, shade, working spaces and localized clutter. Preserve clear paths;
  density means purposeful activity and construction, not random prop counts.
- **Hero tree and terrain:** convincing roots, branching, canopy mass, bark scale,
  leaf clusters, ground transitions and layered geology. Judge silhouettes at
  distance and surfaces/foliage at player height, including motion.
- **Characters:** convincing anatomy, face/hair, fabric and armour construction,
  hands/feet, deformation and ground contact. Natural idle, turn and locomotion
  transitions are quality work; source static poses are not final animation.
  Supplied models are a starting point, not a fixed assignment: replace them when a better character serves the role
  (e.g. give Mira, Torr, Vex and Linn distinct faces, clothing and silhouettes instead of one armoured guard).
  Use Meshy (generation, texturing, remeshing, rigging, animation — pre-approved in §5) or other licensed sources,
  keep the gameplay roots, dialogue IDs, routes and save/data references, and keep the previous model recoverable.
- **Materials:** correct scale and UVs; distinct albedo, normals, roughness and
  metallic response; controlled dirt and edge wear. Keep shading readable in shade.
  Do not bake strong directional light or shiny highlights into base color.
- **Lighting:** a coherent sun/sky/exposure relationship, plausible bounce and
  shadow contact, local practical lights and reflections where justified.
  Atmosphere should establish distance without flattening all depth into beige.
- **Presentation:** stable antialiasing, clean contact/shadow edges, readable UI,
  spatial audio and responsive camera/movement. Inspect shimmering, ghosting,
  popping, clipping, sliding feet and animation stiffness in moving gameplay.

Author scale in metres; Unity ground plane is X/Z and +Y is up. Use the existing
1.8 m actor and controller clearance as measuring references. Typical human doors
should read around 2–2.4 m unless an industrial opening is intentionally larger.
Preserve existing layout and routes during asset replacements. Retire the old
hard-coded browser coordinate diagram as an editing authority; inspect the saved
scene. Layout or playable-area expansion is a separate design task.

Preserve accepted concept images and prompts. Save new targets as dated versions
and explicitly record what they supersede. Older low-fidelity frames cannot veto
improvements requested by the user. Use matched reference angles and close-ups;
a concept image or Meshy thumbnail is never evidence of the game's final render.

## 5. Meshy and asset production

**Meshy credit approval, 8 September 2026:** routine Meshy generation, texturing,
remeshing, rigging and exports needed for requested asset work are preapproved.
Proceed without asking again about those costs. Record task IDs, options, usage
and outcomes. This is not blanket approval for unrelated asset purchases.
Free/licensed external resources are allowed with provenance and appropriate
usage rights. Keep original work; do not ship extracted Funcom/Rockstar content,
copied logos, UI chrome, music or game models.

Use Meshy for generation, Blender for authoring/cleanup/baking where appropriate,
and Unity for assembly and final verification. There is no Blender-only sourcing
rule. Use the live Blender MCP for Blender authoring and the working Unity MCP
for Editor operations. Inspect connection/instance state before mutations; report
an actual unavailable tool without treating it as a failure of unrelated tools.

For each replacement:

1. **Brief:** choose the accepted reference, real dimensions, closest player view,
   material regions, functional openings and placement. Include consistent
   front/side/back views when helpful. Distinguish source quality from runtime LOD.
2. **Generate/author:** retain detailed source geometry and full source textures.
   Do not default a hero building to a 3,500-triangle job or request low-poly art
   solely because the historical guide had a small scene budget.
3. **Inspect before installation:** compare the whole shape and pedestrian views.
   Check doors, roof thickness, railings, open apertures, fused parts, floaters,
   warped panels, holes, normals and baked text. Repair, split into modules,
   regenerate or reject failures. Extra texture resolution cannot repair geometry.
4. **Fit and shade:** normalize orientation, pivot and scale without changing
   proportions. Use uniform scale for whole buildings/characters; change geometry
   deliberately if a parcel needs another shape. Never stretch axes to fill an old
   bounding box. Give signs separately authored, readable lettering.
5. **Prepare runtime variants:** create materials, collider proxies, LODs and
   texture settings. Preserve originals and task records; no destructive remesh or
   source downsampling. Judge each reduced version against the detailed source.
6. **Audition in Unity:** inspect a saved prefab instance at its intended placement,
   in sun and shade, from orbit and first-person cameras, with a human scale marker.
   Check collision/access, animation and draw/texture cost before broad rollout.
7. **Integrate and verify:** replace only the intended visuals, preserve gameplay
   roots/data and rebuild derived render chunks. Capture native views and test the
   affected real-input route. Keep a recoverable previous version.

The rejected district shops are a recorded failure case: independent X/Y/Z scaling
stretched Field Supply's relative height about 2.6 times; low-detail source meshes
lost roof/facade structure; 2k maps became 1k atlas tiles. The later uniform-scale
fix did not repair those assets. Do not re-enable them on that fix alone. The
rejected Ring Gate remesh similarly lost console/platform detail. Preserve these
records so later work does not repeat the same optimization mistake.

## 6. Geometry, textures and rendering budgets

The **250k visible-triangle limit, 80-draw limit, fixed light count, blanket ban on
real-time GI, one-material-per-family rule and fixed 512/1k/2k texture ceilings are
retired**. They were prototype constraints, not universal measures of efficiency
or requirements for native Unity. Do not replace them with arbitrary giant budgets.

Allocate cost according to screen coverage, viewing distance, material needs and
measured CPU/GPU/memory limits. Spend detail on silhouettes and surfaces the player
can inspect. Use modular architecture, tiling materials, trim sheets and decals
where appropriate, plus dedicated hero materials when sharing would lose quality.
A single atlas for an entire district must not erase its facade detail.

- **Geometry:** retain a detailed near LOD and build lower LODs for distance.
  Inspect transitions, silhouettes, normals and shadows. Use instancing and spatial
  culling for repetitions; retain editable source objects behind render chunks.
- **Textures:** choose texel density from the closest intended view. 2k–4k sets
  are useful starting points for material regions, not guarantees or ceilings.
  Use higher resolution when justified; large facades often need tiling/trim detail
  instead of one stretched unique map. Verify mip selection, anisotropic filtering,
  compression and atlas padding in the native player. Record VRAM/resident texture
  use; use mip streaming when appropriate rather than discarding source detail.
- **Material import:** verify normal-map orientation, color spaces and packed-map
  channels. Convert roughness to smoothness where the Unity shader requires it.
  Confirm metallic masks do not turn stone, dust, rubber or cloth into metal.
- **UVs:** the normal Unity convention is UV0 (`Mesh.uv`) for material textures,
  with separate non-overlapping lightmap UVs in UV1 (`Mesh.uv2`) when needed.
  Check importer behavior and any custom shader assumptions. Do not follow the
  historical guide's reversed lightmap/tiling assignment.
- **Lighting:** use appropriate baked/mixed lighting, probes, local lights, shadows,
  ambient occlusion and reflections. Dynamic GI, volumetrics or ray tracing are
  options to evaluate if supported and beneficial, not required labels for quality.
  Do not use bloom, fog, grading or depth of field to conceal bad source assets.

The current **URP** implementation is the working baseline, not an untouchable
limit. Before a pipeline/API migration, compare the same representative scene,
assets and cameras and document the visual gain, Linux support, shader/material
conversion, performance and maintenance cost. Preserve the working scene during
that experiment. Do not assume HDRP or an upgrade automatically repairs art.

Unity's [2026 pipeline strategy](https://unity.com/topics/render-pipelines-strategy-for-2026)
prioritizes URP development and HDRP maintenance. Roadmap features are not proof of
availability in installed URP 17.6.0. Verify actual package/API support; HDRP's
Linux support uses Vulkan in Unity's
[feature comparison](https://docs.unity3d.com/6000.0/Documentation/Manual/render-pipelines-feature-comparison.html).

Technical references:
[LOD](https://docs.unity3d.com/6000.0/Documentation/Manual/LevelOfDetail.html),
[mipmap streaming](https://docs.unity3d.com/6000.0/Documentation/Manual/TextureStreaming.html),
[lightmap UVs](https://docs.unity3d.com/6000.0/Documentation/Manual/LightingGiUvs.html).
Consult documentation matching installed versions before implementing a feature.

## 7. Performance and visual acceptance

The first playable performance target is an **average of 60 FPS at native
1920×1080 on the High preset** (render scale 100 %, no frame generation) on the
reference machine, the Linux **RTX 3060 12 GB / i9-10850K** host. Revised
30 September 2026: the 3060 is an older GPU, so occasional frame-time spikes are
accepted; a p99 or maximum above 16.67 ms is reported, not a failure on its own.
Record actual hardware/VRAM, driver, API, quality and render scale for each run.
A vague medium laptop is not a qualified platform. Establish additional named
hardware and quality profiles when that becomes a delivery task.
Optional high-quality screenshots must state their settings and cannot substitute
for the native gameplay target. Do not hide a lower render scale or frame generation.

Measure a warmed, representative standalone traversal with all nine current actors,
shadows, HUD and active effects, including shop/travel states. For new quality
qualification, target average FPS >= 60 on the recorded baseline; report duration,
p50/p95/p99/max, hitches, CPU/GPU time when available, memory and loading
separately. Judge cost with alternating before/after runs of the same walk (this
desktop drifts about ±1–1.5 ms between runs), once per batch of passes (below),
and state the change.
A pass that takes the average below 60 FPS, or adds repeated hitches during normal
walking, is a regression to fix or explain. Keep uncapped timing samples separate
from VSync-limited play. Report unavailable counters as unavailable, never zero cost.
Distinguish visible geometry from submitted triangles across shadow/depth/color
passes; draw calls, batches and SetPass counts are different measurements.

Historical reports and QA scripts may still assert 250k triangles, 80 draws or a
58 FPS threshold. Those are previous test contracts, not current art constraints.
When updating qualification tooling for a new visual pass, replace obsolete
budget assertions with explicit recorded profiles and the current frame-time
criteria. Keep old evidence intact; do not remove measurements, hide failures or
weaken checks merely to claim success. This documentation revision does not change
those scripts or retrospectively qualify any build.

For every significant visual pass:

1. Capture a baseline of the current saved native build. Use `cam_hill`,
   `cam_avenue`, `cam_gate`, `cam_grid`, `cam_whompah`, `cam_hero` and relevant
   asset cameras; keep position, lens, exposure and resolution matched.
2. Add **player-height close-ups**, character face/full-body views and a moving
   walkthrough. Inspect sun/shade, thresholds, foliage, LOD changes and first-person
   proximity. Wide skyline screenshots alone cannot accept a building.
3. Compare reference, before and after. Score composition/silhouette, scale,
   material detail, lighting/depth, density/storytelling, character/animation,
   temporal stability and UI/readability from 0–5, with specific defects.
   A score of 4 means strong at the intended viewing distance with minor remaining
   issues; 5 means the chosen reference target is met in that view.
4. Aim for at least 4 in every applicable category at hero views and close range.
   Broken anatomy, warped architecture, soft focal textures, clipping and blocked
   traversal are rejection reasons regardless of the average score. Scores support
   review; they do not certify whole-game AAA or GTA6 parity.
5. Exercise affected verbs with real input, inspect runtime logs and record
   performance. An image improvement with a broken route or excessive frame time
   remains unfinished. Preserve the user's rejection/acceptance decisions.

**Batched verification (1 October 2026).** Per-pass builds, native lookbooks, A/B
profiles and city loops were taking most of the working time. When several passes
run, steps 1–5 apply to the batch, not to each pass:

- **Each pass:** authors and reviews with Blender renders and a few small editor
  captures, then installs into the saved scene. It verifies the scene with
  `-nographics` (installed, prefab links, no missing materials, chunk fingerprint,
  retired objects inactive). It validates placements against colliders, routes,
  doors and NPC points, and adds `cam_<pass>_*` review cameras at player height.
  It does not build the player or run native tests of its own.
- **Each batch:** one combined native test, made of a development build, a
  lookbook of every review camera at 13:00 and 20:30, alternating frame-time runs
  against the previous batch's build, the city loop and the range tutorial check.
- **Afterwards:** defects and costs go back to the owning pass for a fix round. If
  a batch is over budget, toggle pass roots to find which pass is responsible.

Iterate a focused family of changes to keep comparisons useful. Coupled fixes
(such as geometry, UVs and its texture bake) may be developed together when they
solve one documented problem. Do not let a rigid one-family rule block necessary
work or turn every small document edit into a full game test run.

## 8. Editing, architecture and verification

The game must remain ordinary editable Unity content: saved scenes, modular
prefabs, materials, animation assets, Inspector controls, serialized gameplay data,
Input Actions and UI Builder assets. No runtime script may reconstruct the whole
city to hide missing authoring. Scene assembly/import helpers are Editor-only;
one-time installers must not overwrite an already edited city.

Use [unity/EDITING.md](unity/EDITING.md) for the source-edit/rebuild workflow.
Show source renderers before editing, then explicitly rebuild render chunks.
Keep source transforms, collider proxies and prefab links. Do not edit disposable
chunk meshes directly or bypass the stale-source build guard. Use narrowly scoped
operations and preserve GUIDs; do not rewrite the entire scene for a visual fix.

Current implementation map:

- `PlayerMotor`, `FollowCamera`, `GameInput`, `ActorAnimation`, `AmbientWalker`:
  movement, camera, controls and actors.
- `GameSession`, `CityCatalog`, `NpcDefinition`, `ShopModel`: interactions, data,
  objectives and trading. Keep tuning and content serialized.
- `CityHud`, `UI/CityHUD.uxml`, `UI/CityHUD.uss`, `unity/DESIGN.md`: interface,
  bindings and shared visual rules. Keep UI labels editable and reserves inactive.
- `CityAudio`, `CityAtmosphere`, materials and scene objects: ambience and atmosphere.
- `AthenDebugBridge`, `NativeQa`, `unity/tools`: named cameras, state, captures,
  native profiling and real keyboard verification. No browser globals are required.

Use relevant existing Edit/Play Mode checks for logic changes and real-input
native checks for traversal, animation and UI changes. Build and launch the Linux
player after meaningful runtime/asset integration; verify the saved/reopened scene
and shipping materials/shaders, not just Editor Play mode. Release builds must
retain the development-bridge restrictions. Documentation-only edits need link,
content and diff review, not a game rebuild.

**Machine limits.** The reference machine has 32 GB of RAM and a 12 GB RTX 3060,
both shared with the user's desktop. Swap is zram, which itself uses RAM, followed
by a btrfs swapfile. Parallel Unity, Blender and player jobs crashed it three times
between 29 September and 1 October 2026: an NVIDIA out-of-memory error took the
desktop down, systemd-oomd killed the whole Claude app, and swap thrashing froze
the machine until it was reset. These rules apply to every session and tool:

- Run one Unity or native-player job at a time.
- Use `-nographics` for player builds and every Unity step that does not render.
  A graphics-mode build alone took about 9 GB of VRAM.
- Run Unity, Blender and the player each in its own memory-capped
  `systemd-run --user --scope` with a small swap allowance, so a runaway job is
  killed alone. A killed Unity can leave its import workers and Unity.DataStore
  behind, so stop the whole scope.
- Keep batch editor captures to about six cameras per run.
- Close the Unity Editor before native runs.
- Keep run state and scripts out of `/tmp`, which a reboot clears.

Keep dated evidence under `unity/evidence/`, with the tested revision or working-tree
snapshot/build identity, references, settings, captures, logs and remaining defects.
Do not attribute old performance, route or image acceptance to a newly changed scene.
Keep credentials out of documentation, source and logs; use the configured local
secret mechanism. Retain asset/task provenance and distribution notices.

## 9. Production milestones from the current build

This is the working outline, not authorization to implement every phase at once.
Continue from the existing city instead of restarting historical phases 0–7.

| Milestone | Work and exit evidence |
| --- | --- |
| Quality baseline | Record the current native district, close-ups, moving route and performance; agree on versioned contemporary visual references and document the visible gaps. |
| Representative street | Bring one facade, its threshold/ground/props and lighting to the target together. Preserve source detail, correct proportions, readable materials and traversal; accept at player height before replicating the approach. |
| Hero landmarks | Improve the hill tree, gate, hall and skyline using the established material/detail standard. Preserve existing accepted Meshy gate/terminal work unless it is the subject of the pass. |
| Characters and life | Improve faces, hair, clothing, idle/turn/locomotion and purposeful ambient behavior without breaking current NPC roles/routes. Keep costs measured; density expands through explicit gameplay work. |
| District rollout | Extend accepted modules/material standards through the city; add lore-grounded working spaces and prop clusters. Recheck repetition, paths, first-person detail and performance. |
| Presentation and qualification | Finish light/shadow/reflection quality, temporal stability, audio mix and UI cohesion. Pass native route/verbs and frame-time criteria, with honest remaining art gaps. |
| Future gameplay slice | When requested, design one bounded survival/FPS/settlement loop from the lore, then prototype and qualify it before larger world/system expansion. |

Prioritize the weakest visible part of the actual gameplay frame. The current
[recovery screenshots](unity/evidence/district/20260908/recovery/native) still show
repetitive facades, broad empty paving, limited
tree/canopy structure and uneven close-up surface quality. These are starting
observations, not acceptance of those limitations as the game's style.
