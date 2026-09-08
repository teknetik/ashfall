# Ward — visual quality and RTX 3060 TODO

Updated 8 September 2026 after the user's latest visual review. Production guide:
[AGENTS.md](AGENTS.md). Setting: [lore.md](lore.md).

**Highest priority: audit every mesh and its polygon count. The game still looks
below the requested standard.** Earlier source recovery is completed technical
work, not acceptance of Vex, the buildings, stones or the overall visuals.

Keep native Linux playable on the **RTX 3060 12 GB at native 1920×1080 / 60 FPS**.
Use measured headroom to improve silhouettes, construction and surface detail.
More triangles alone do not fix poor geometry, UVs, textures, shading or animation;
do not add subdivision merely to raise a count, or impose an arbitrary low-poly cap.

| Phase | Importance | Outcome |
| --- | --- | --- |
| 0 — Complete mesh audit | **P0: do first** | Every asset has counts, visual evidence and a repair decision; buildings and Vex receive first review. |
| 1 — Buildings, Vex and hero tree | **P1: highest visual impact** | Improve the weakest major meshes and establish one convincing street frontage. |
| 2 — Landmark props and ground detail | **P1: required replacements** | Lattice model, save/reclaim terminals, real stones or removal, benches, visible dirt/graffiti. |
| 3 — Character movement | **P1: gameplay presentation** | Jump animation and convincing locomotion/idle transitions. |
| 4 — Lamps, developer controls and day/night | **P2: lighting systems** | Lit fixtures, a development time-control menu, and a tested day/night cycle. |
| 5 — District rollout and qualification | **P2: production acceptance** | Extend accepted improvements and qualify the district on the RTX 3060. |
| 6 — Later content and gameplay | **P3: subsequent scope** | Lore naming and bounded future gameplay work. |

Work in this order, moving individual audited assets into repair as findings are
ready. Validate visuals and performance after each meaningful integration;
qualification is not postponed until phase 5. Check current saved work and other
task records before duplicating or reverting it.

## Phase 0 — P0: audit every mesh before further broad replacement

- [ ] Inventory **all active scene meshes**, including Meshy imports, Blender
  models, primitive/placeholder geometry, characters, buildings, portals, tree,
  rocks, benches, lamps, terminals, foliage and terrain. Map every instance to its
  source mesh/prefab; distinguish unique assets from repeated placements. Record
  inactive/rejected candidates separately so they cannot be mistaken for the game.
- [ ] Record **source and actual Unity runtime triangle/vertex counts**, every
  available LOD, reduction percentage, active LOD at normal viewing distances,
  submeshes/material slots and instance counts. Use triangulated counts for
  comparison; Meshy's polygon/quad labels are not necessarily Unity triangles.
  Inspect both editable source renderers and derived render chunks. Keep visible
  geometry separate from triangles submitted across shadow/depth/color passes.
- [ ] Record source versus imported texture dimensions, texel density, UV stretch,
  atlas/mip losses, normal/tangent validity, shader/map bindings, roughness/metallic
  channels and scaling. Check that the intended detailed mesh is actually rendered.
- [ ] **Inspect every building mesh and every placed building.** Check front,
  side/back, roof, doorway, supports and threshold at player height; detect warped
  construction, stretched proportions, thin roofs, fused details and repetition.
  Review inactive alternatives against their original Meshy sources as well.
- [ ] **Inspect Vex first among the characters.** Verify the live mesh/prefab and
  LOD, then compare source, Unity material and native close-up. The previous recovery
  recorded 38,071 triangles per guard; that does not resolve the user's continued
  low-quality result. Check silhouette, armour, hands, UVs, normals, texture detail,
  shading, deformation and static poses before selecting the fix.
- [ ] Capture matched native overview, wireframe/debug evidence and player-height
  close-ups. Identify whether each defect comes from the source model, import,
  scale, material, lighting, animation or placement. Include current floor decals
  so missing/ineffective dirt is diagnosed rather than assumed to be installed.
- [ ] Produce an audit report in docs/mesh-audit.md with one row per unique asset,
  linked scene instances/evidence, counts, defects, importance and a decision:
  **keep, restore, repair, regenerate, replace or remove**. Rank by visible impact,
  starting with buildings and Vex; give each failed asset a concrete follow-up task.

**Exit:** every active mesh is accounted for, source/runtime losses are explicit,
and the highest-impact repairs have close-up evidence and a chosen approach.
The earlier [source audit](unity/evidence/fidelity/20260908/source-audit.json) is
input to this work; it is not completion of this broader scene and visual audit.

## Phase 1 — P1: improve buildings, Vex and the hero tree

- [ ] **Improve every failed building from the audit.** Start with one complete
  frontage—facade, roof, entrance, ground transition and props—then apply the
  accepted construction/material standard to the remaining buildings. Track each
  building individually; one improved prefab does not accept the whole district.
- [ ] Correct existing non-uniform building fitting. The hall's depth was stretched
  over twice as much as its width; restore proportions while refitting foundations,
  thresholds and collision. Preserve routes, gameplay roots and asset references.
- [ ] Rework/regenerate the seven rejected district shop candidates where useful.
  Uniform scaling or larger textures cannot restore missing facade/roof geometry.
  Keep them inactive until revised and reviewed. Reduce identical rooflines and
  shop-shell repetition in the active district.
- [ ] **Raise Vex's visible quality** using the audit findings: repair geometry,
  materials/UVs or obtain a better source as needed. Preserve Vex's identity,
  dialogue, interaction root and role. Review the result in conversation and at
  arm's length before propagating shared guard changes to other NPCs.
- [ ] Review the player and remaining NPCs for similar surface/anatomy problems.
  Improve supplied skin/hair/armour/fabric maps and material response; preserve
  current character assignments and rig compatibility during improvements.
- [ ] Rework the **hero tree**: close gaps at the root/trunk joins, improve root
  volume, branching and canopy mass, and correct stretched bark/leaf detail.
  Judge first-person proximity, distant silhouette and foliage in motion.

**Exit:** the representative frontage, Vex and tree improve in actual gameplay;
remaining building defects have specific tasks and reviewed references.

## Phase 2 — P1: replace landmark props and finish visible ground detail

- [ ] **Replace the requested “south Lattice Jack” model.** Identify the intended
  object by saved scene path, position and native capture first: current records
  identify the **north Lattice Jack** and a separate accepted **south Ring Gate**.
  Resolve that naming/direction mismatch before changing a portal. Replace the
  intended Lattice visual while preserving travel interaction, arrival/access,
  collision and audio; do not substitute the wrong landmark.
- [ ] **Replace the tree-platform terminals with Meshy-generated save/reclaim
  terminals.** Locate those platform props separately from the three restored
  mission terminals. Create coherent references, retain detailed source geometry
  and PBR maps, then fit readable controls and usable approaches at human scale.
  Preserve existing interaction IDs; record whether save/reclaim behavior exists
  and scope any missing gameplay separately from the model replacement.
- [ ] **Build convincing volumetric 3D stones/rocks, or remove the bad decorative
  stones.** Replace flat discs, crude shapes and floating/intersecting pieces with
  reviewed stone assets; remove pieces that do not improve the scene. Check varied
  silhouettes, grounding, texture scale and contact shadows. Preserve functional
  stone stairs, paving, foundations and required traversal/collision.
- [ ] **Replace the benches.** Use believable seat/back/support construction,
  proportions, material detail and grounded feet. Check player-height views,
  collision and clear paths around the tree and plaza.
- [ ] **Make floor dirt and graffiti visibly present in the native game.** The
  user still considers this unresolved. Review existing wear/decals, repair any
  binding, layer, depth, opacity or placement failures, then add readable localized
  grime, sand, foot scuffs, stains and ground markings/graffiti where appropriate.
  Capture before/after in sun and shade; asset files or Editor-only previews are
  not acceptance. Coordinate with existing weathering/signage work.
- [ ] Improve close grass/foliage shapes and soil/paving transitions; replace
  obvious flat spikes and excessively repeated paving where they dominate views.

**Exit:** each requested prop has a reviewed replacement or a recorded removal;
save/reclaim and Lattice targets are correctly identified, and floor dressing is
visible without obstructing routes or making every surface uniformly dirty.

## Phase 3 — P1: jump animation and character movement

- [ ] **Add a jump animation** with takeoff, airborne and landing states blended
  into idle/walk/run. Drive transitions from actual movement/grounding; handle
  standing and running jumps, walking off edges and repeated jumps without
  accidentally changing the controller's jump height, speed or collision.
- [ ] Verify jump and landing using real input in third person and first person,
  on level ground and stairs. Check feet, ground contact, clipping, camera behavior
  and return to locomotion.
- [ ] Replace static idle/talk poses and improve turn/locomotion transitions.
  Retain the four talking NPCs and traveler/mechanic routes; inspect foot sliding
  and deformation in moving gameplay, not just a paused animation pose.

## Phase 4 — P2: lamps, developer menu and day/night cycle

- [ ] **Create new lamp models with actual lighting.** Establish an appropriate
  fixture family and useful placements; pair emissive bulbs with measured local
  illumination, appropriate shadows, falloff and color. Check bases, scale and
  wiring/construction in daylight, plus street visibility at dusk and night.
- [ ] **Add a debug/developer menu**, with a small time-control interface available
  before day/night qualification: set time of day, sunrise/noon/sunset/night
  presets, pause/resume the clock, cycle speed and reset to the authored default.
  Useful follow-ups include current mesh/LOD statistics and rendering settings.
  Keep it gated to Editor/development builds, preserve release bridge restrictions,
  and prevent gameplay input leaking through the open menu.
- [ ] **Implement a day/night cycle** with a configurable game clock, sun/moon or
  night-light direction as appropriate, sky, ambient light, exposure, reflections
  and lamp switching. Keep coherent art direction across transitions; avoid
  noon-baked shadows/reflections persisting into night. Treat timing as tunable
  gameplay configuration rather than inventing new planetary lore.
- [ ] Review bounce, contact shadows and shaded facade readability. Profile dynamic
  lighting, shadows and reflection updates before district-wide rollout; use
  distance/culling strategies where needed instead of flattening all lighting.
- [ ] Use the developer controls to inspect dawn, noon, dusk and night with all
  actors and UI active. Check smooth transitions, readable routes/characters,
  lamp timing and RTX 3060 frame times in the most expensive lighting state.

## Phase 5 — P2: district rollout and qualification

- [ ] Extend accepted asset/material standards through the district, checking
  repetition, purposeful working spaces, clutter, first-person detail and routes.
- [ ] Add reviewed distance LODs where measured cost warrants them. Preserve the
  detailed near meshes and originals; inspect silhouettes, transitions and shadows.
- [ ] Inspect mip selection, antialiasing, foliage shimmer, shadow stability and
  clipping in recorded gameplay after each pass. Keep matched native comparisons.
- [ ] Qualify named RTX 3060 quality presets at native 1080p with real render scale,
  CPU/GPU frame times, p50/p95/p99/max, hitches and resident memory. Target average
  FPS >= 60 and p99 <= 16.67 ms; separate uncapped measurements from capped play.
  Preserve unavailable counters as unavailable and retain old evidence honestly.
- [ ] Recheck movement/jump, four dialogues, atomic trades, travel, modal input,
  HUD/settings/audio and reduced motion. Build/reopen the saved scene and qualify
  native Linux development and release players after meaningful integration.
- [ ] Clean up deprecated Unity object-search overloads when touching relevant
  tooling. Preserve measurements while removing obsolete budget assumptions.

## Phase 6 — P3: later content and gameplay

- [ ] Reconcile Athen Hill/Free Column/Lattice labels with Tir/Ward lore while
  preserving stable IDs and behavior.
- [ ] Define a bounded survival/FPS/settlement prototype when requested. These
  systems remain future scope, separate from the current visual priorities.

## Completed recovery baseline — historical evidence, not visual sign-off

- [x] Audit retained exports and remove the guard's forced 6k simplification;
  preserve all 38,071 source triangles and relaxed arm pose.
- [x] Restore the mission terminals from 7,696 to 25,656 triangles, generate
  tangents and enable their supplied PBR maps.
- [x] Restore active salvage/west-arch source UVs and full material textures;
  prevent legacy atlas commands from overwriting recovered source fidelity.
- [x] Repair stone weathering's texture bindings and future uniform-scale import
  defaults; preserve current grounding, foundations and the remade Ring Gate.
- [x] Remove four empty retired terrain references while keeping the eight
  connected terrain renderers, routes and collision.
- [x] Capture native comparisons and a first-person walkthrough; pass the existing
  route, city-loop and release checks, including HUD/mute/reduced motion.
- [x] Record the recovery build at native 1080p: view averages 203–439 FPS,
  5.15 ms p99 during moving samples and 1,035 MiB player GPU allocation. Both Linux
  builds had zero errors (development 3 warnings, release 5). These measurements
  apply only to that build; see [evidence](unity/evidence/fidelity/20260908/README.md).

GTA6 remains the visual ambition. Counts, restored source files and high frame rates
support production decisions; acceptance requires convincing native gameplay views.
