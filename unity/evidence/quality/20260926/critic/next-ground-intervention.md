# Next focused geometry/material intervention — 26 September 2026

**Recommend one representative paving-and-threshold patch at West Gate.** Bring the surface immediately inside one existing gate opening, its two pier contacts and the adjacent wall foot to a believable player-height stone/dust standard. Measure its exact bounds in the saved scene before authoring. Preserve the current opening, walking surface heights, gate assets and collider clearances. Keep the first audition localized; district rollout follows an accepted patch.

This recommendation follows inspection of the full-viewport native `cam_avenue`, `cam_grid`, `cam_gate`, `cam_whompah`, `cam_hill` and `cam_p1_tree_roots` 96 m/four-cascade frames and the official ARK courtyard reference. These shadow-profile images are useful visual evidence but the parent has separately reported that profile's failed frame-time target; this proposal does not endorse its performance. Their old pale leaves are also superseded by the later foliage audition.

## Visible reason for this priority

- In `cam_gate`, the slab field is a broad, almost uniformly cream surface. Slab edges share similar grooves and roughness. The heavy worn gate piers meet comparatively clean, regular paving, with little visible accumulation or material transition at their feet.
- In `cam_grid` and `cam_whompah`, the same coarse stone grain and regular seam language cover large uninterrupted areas. The grain is strong at close range, while convincing larger-scale variation, worn traffic zones and dust collecting in protected edges are weak. More normal-map contrast alone would intensify the existing problem.
- `cam_p1_tree_roots` makes the surface response especially clear: the foreground has coarse, evenly distributed pebbled relief and very similar slab tones. The straight soil boundary, stiff triangular grass and soft bark are separate visible rejection defects; this proposed gate patch does not claim to repair them.
- Avenue/hill views show why the paving matters at distance too: it occupies much of the open district and currently reads as a repeated material field. Shadows improve its depth, but do not supply the missing surface history.

In the [official ARK courtyard image](https://clan.fastly.steamstatic.com/images/44719856/41798a1b8cae10f220da4e4c94becd5384c83a92.jpg), irregular worn step lips, changes between firm stone and loose granular ground, and localized debris help join the architecture to the terrain. This is the relevant reference property. Its Egyptian forms, statues and exact assets are not a design prescription for Ward. Reference quality settings and promotional processing are unknown.

## One patch, ordered work

1. **Correct the material at pedestrian distance.** Audit the existing UV scale, normal-map strength/orientation and roughness response. Establish believable sandstone grain with quieter worn slab tops, distinct joints and restrained per-slab mineral variation. Keep non-directional base color; material depth should respond to the actual sun and shade. Retain the original assets and use an authored candidate material rather than globally editing the shared district material.
2. **Join the threshold to its surroundings.** Add an editable local dust/sand mask that collects beside the pier/wall feet and in selected joints, thinning along the walked route. Give the loose material its own normal/roughness response. Avoid uniform brown dirt, repeated black contact outlines, or decals covering every slab equally.
3. **Spend geometry only where it changes the close silhouette/contact.** On the localized surface, use restrained worn bevels and a few unique chips at exposed slab/threshold edges. Add tiny grounded mineral fragments only where protected from foot traffic. The aim is construction/wear continuity, with a clear usable route. Keep the underlying collision/traversal contract stable; do not scatter obstacles to manufacture density.

This is a bounded asset/material patch with an observable result. It does not require replacing a whole shop, inventing new lore or redesigning a district. It also offers a reusable material standard if successful. No estimate of its final GPU cost is assumed.

## Acceptance evidence to prepare after active timing work

Use the existing `cam_gate` as the wide context and add one fixed player-height view aimed across the new threshold, one downward close-up and one view of the shaded pier foot. Record the same material settings and lighting for before/after. The closer views must show quieter, correctly scaled stone detail; distinct stone/joint/dust response; and grounded base contacts without smear, z-fighting or floating chips. The improvement must survive the wider gate view without obvious texture repetition or patch borders.

Then test the actual gate walk/jump route and camera proximity, inspect moving specular/normal stability and include the patch in the qualified native performance profile. Rebuild saved render chunks through the existing workflow. The patch remains rejected if it looks plausible only in a still or damages access.

## Scope of the visual diagnosis

The shop silhouettes in these wide images still have repeated rectangular construction and broad planar areas, but these shots do not expose enough doorway/facade close detail to prescribe a responsible replacement. The visible actors are small or partly obscured by HUD/foreground, so this set cannot substantiate a specific anatomy, hand, face or deformation repair. Those require their own close native evidence. Ground material/threshold integration is the strongest next bounded intervention supported by the images actually inspected.
