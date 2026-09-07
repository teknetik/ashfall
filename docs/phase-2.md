# Phase 2 — frozen concept references

2026-09-07. Eight original Codex imagegen references generated, displayed and
visually inspected. Phase 2 concept production is complete. This is concept
acceptance, not evidence that the current greybox matches final art.

## Frozen outputs

The exact eight PNGs live under `refs/`; `manifest.json` records dimensions,
sizes and SHA-256. `environment-prompts.json`, `characters-prompts.json` and
`ui-prompt.json` retain exact prompts, input roles and built-in output sources.
Accepted files are immutable. Revisions must use new filenames.

01: broad split-trunk olive tree on a raised grassy mound, visible stairs,
low shops, twin west arches, hall antenna and human scale.
02: clear dry avenue, deep storefronts, Basic General, repeated worn facades.
03: two thick standable pale arch tunnels with muted red banners.
04: Lattice Jack console, open technological hoop and stepped pad.
05: two massive facing stone Ring Gates, clear and translucent apertures.
06: full-body male colonist, workwear, beard, one salvaged shoulder assembly.
07: Mira in oxblood workwear/apron, shared kit, flask and medkit stall.
08: original dark thin-line HUD, six slots, vitality/nano, log and buy/sell.

Environment/UI images are 1672×941 (near 16:9), PC is 1024×1536 and vendor is
1536×1024. Runtime comparison captures will still use 1920×1080. No image was
stretched, cropped, or repainted with code.

## Design decisions and review

User-provided source images under `concept_art/` supplied weathered metal,
bevels, inset technology and male grooming cues. The written brief determines
dry golden afternoon, compact low-rise dimensions and practical recruit kit.
No source imagery is used as a runtime game asset. Meshes remain original
Blender work; no marketplace or extracted game content is selected.

The five environments share matte sandy stone, worn gunmetal, muted red cloth,
small teal signals, olive foliage and a blue-to-gold sky. The tree has clear
branch/canopy gaps and asymmetry; it remains legible at thumbnail viewing size.
Standing humans show scale in all five environment frames. The two travel
landmarks differ by both mass and material, not only their labels.

Generated background landmarks are composition guides, not literal survey
maps. Preserve the existing metre-based runtime layout and verified routes.
The primary matches are landmark silhouette, material language, palette,
western sunlight and density; avoid reproducing inconsistent distant map
placements between generated views. Capture camera transforms must be recorded
before the Blender integration and remain fixed during beauty comparisons.

## Gates and next phase

- Eight required references: pass; exact prompts and hashes saved.
- Original, coherent visual direction: pass by direct image review.
- Images displayed before proceeding: pass.
- Blender MCP live read: pass at Phase 2 entry and continuation.
- Runtime build: fresh TypeScript/Vite build passed at phase entry.
- Runtime visual/performance comparison: pending authored-world phases.

Phase 3 starts from the accepted Phase 1 route/controller. Preserve the stable
ground halfspace and simple separate collision proxies. Keep global material
batching after landmark replacement; count shadow passes in the 80-draw and
250k-triangle budget. No final premium/MVP claim is made at this milestone.
