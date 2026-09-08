# Ward — visual quality and RTX 3060 TODO

Updated 8 September 2026. Production direction: [AGENTS.md](AGENTS.md).
Setting: [lore.md](lore.md). Target: native Linux, RTX 3060 12 GB, 1920×1080,
60 FPS with measured frame times. This list distinguishes recoverable import losses
from assets that need new authoring. Completed changes require in-game evidence.

## Current pass — recover Meshy source fidelity

- [x] Audit retained source meshes, textures and Unity reduction steps. See
  [source audit](unity/evidence/fidelity/20260908/source-audit.json).
- [x] Remove the Ward Guard processor's forced 6,000-triangle simplification;
  preserve all 38,071 source triangles and the requested relaxed arm pose.
- [ ] Integrate and inspect the restored guards; verify all four talking roots,
  proportions, arm pose, skinning and interactions.
- [ ] Restore original mission-terminal geometry (25,656 triangles, currently
  reduced to 7,696), calculate missing tangents and enable its supplied PBR maps.
- [ ] Restore original-resolution materials/UVs for active Meshy salvage and gate
  assets where shared atlas packing reduced detail. Keep measured batching/culling.
- [ ] Remove destructive import defaults so future imports do not repeat the losses.
- [ ] Capture matched native close-ups and representative city views before/after.
- [ ] Verify native traversal, conversations, trades, travel and RTX 3060 timings.
- [ ] Record exact accepted settings, memory use, remaining visual issues and builds.

## Next art priorities

- [ ] Correct remaining anisotropic fitting in existing salvage buildings through
  individual placement reviews. The hall's depth was stretched over twice as much
  as its width; restoring shape also requires checking foundations and thresholds.
- [ ] Replace/rework the seven rejected district shop candidates. Uniform scale
  alone cannot recover roof/facade detail missing from the generated source.
  Inspect doors, roof thickness and material detail at pedestrian height.
- [ ] Establish one complete street frontage at the visual target before repeating
  it across the district. Break up repeated rooflines and identical shop shells.
- [ ] Rework the hero tree's roots, branching, canopy structure and close bark/leaf
  detail; test foliage shimmer and wind in motion.
- [ ] Improve player and NPC skin/hair/material response from actual source maps.
  Avoid treating emissive or shaded base-color exports as a complete PBR material.
- [ ] Replace static idle/talk poses with suitable animation; tune turns, foot
  contact and locomotion. Keep the approved guard/traveler/mechanic assignments.
- [ ] Add reviewed distance LODs where profiling shows a benefit. Preserve detailed
  near meshes; reductions must not replace the only retained runtime/source version.
- [ ] Review localized bounce, reflections and contact shadows after source fidelity
  is restored. Keep readable shade and a coherent sun/sky relationship.
- [ ] Review terrain/ground transitions and street density against the new standard.

## Work being handled in other active tasks

Check their latest saved changes and evidence before duplicating or reverting work.

- [ ] Integrate final localized dirt/wear, weeds and lore signage work.
- [ ] Integrate final grounding/foundations and Ring Gate placement fixes.
- [ ] Verify updated draggable HUD and settings/audio work with the restored assets.

## Qualification and longer-term scope

- [ ] Use current RTX 3060 frame-time criteria in new QA; retain geometry/draw/memory
  measurements but retire the obsolete universal 250k-triangle and 80-draw limits.
- [ ] Inspect LOD/mip transitions, antialiasing, shadow stability and first-person
  proximity in recorded gameplay, beyond fixed-camera stills.
- [ ] Qualify named quality presets on the RTX 3060, including real render scale,
  resident texture memory and hitches. Do not infer headroom from capped FPS.
- [ ] Reconcile Athen Hill/Free Column/Lattice labels with Tir/Ward lore in a
  coordinated content pass, preserving stable IDs and existing game behavior.
- [ ] Define a bounded survival/FPS/settlement prototype when requested. The lore
  describes future scope; these systems are not implemented by this art pass.

GTA6 is the visual ambition. A successful fidelity recovery or high frame rate does
not establish that the district has reached that quality level.
