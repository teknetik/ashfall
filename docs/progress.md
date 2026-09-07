# Athen Hill completion progress

Active goal: continue from Phase 2 through the playable MVP, preserving the
project's phase, Blender, fixed-camera and performance gates. One banked usage
reset is authorized if quota exhaustion prevents progress; none used so far.

## Starting evidence

- Phase 1 committed at `812f6e6`; fresh build passed 2026-09-07.
- Prior route/physics QA passed. Prior M4 Max greybox performance was about
  120 FPS; final world/NPC and medium-laptop performance are still unqualified.
- Blender MCP connected; entry scene was the accepted Phase 0 probe. Current authored city is saved through `10_cliff_silhouettes.blend`.
- User-added `concept_art/` images are source inspiration, not frozen targets.
  Retain worn bevels/panels and male colonist cues; written brief governs dry
  daylight, compact low-rise scale, original names and practical starting kit.

## Phase ledger

- Phase 2: complete. Built-in Codex image generation; eight immutable refs.
- Phase 3: complete for authored-world integration. See `phase-3.md`; final beauty scores remain Phase 6.
- Phase 4: technical integration verified, visual acceptance reopened by the user. Replace the primitive-looking character with an externally sourced realistic base and detailed armour. See `art-direction-update.md`.
- Phase 5: complete and committed at `d5132e6`. Production dialogue, trading, travel and desktop/mobile QA passed; see `phase-5.md`.
- Phase 6: active. Imported character replacement, lighting comparison, audio and measured performance.
- Phase 7: pending. Loading/pause, production QA and static release packaging.

## Integration constraints

- Three coordinates: metres, Y up, north -Z; landmark positions are feet.
- World collider extraction must finish before World.load resolves.
- Preserve halfspace ground, 0.25 m stairs, 0.5 m porches, 1.5 m hill plaza.
- World import validates eight landmark groups, globally batches render
  materials and owns shared textures plus pending-load cleanup.
- Character art faces +Z; controller currently faces -Z. Rotate visual root.
- Renderer statistics include shadow passes; budget NPC geometry accordingly.
- Retain Phase 1 evidence; add later-phase verification rather than relabeling it.

## Skill/source ledger

Director plus gameplay, graphics, UI, debug/profile, QA, 3D/image/audio generator
skill files loaded from `/Users/carl.draper/.agents/skills/`; built-in imagegen
skill loaded from `/Users/carl.draper/.codex/skills/.system/imagegen/`.
Built-in imagegen is the requested concept/texture source; Blender MCP is the
required mesh source. Tripo/Gemini marketplace alternatives are not selected
because the project explicitly requires original Blender meshes and Codex art.
ElevenLabs is the requested future audio source. No credentials belong in the
runtime, committed code, manifests, or reports.

Independent Phase 1 audit and source-reference critic completed. Their findings
inform the integration constraints and Phase 2 direction above.

## Phase 3 follow-up QA

Final geometry capture report: `tools/phase3-support/runs/2026-09-07T10-05-42.477Z-16797/report.json`.
119.87 fps, 28 draws, 126,268 rendered triangles, zero browser errors.
`collider-equivalence.json` proves all 263 runtime static definitions, controller
configuration and six named camera transforms exactly match the full-route
baseline. No duplicate route was necessary for visual-only changes.

Gameplay references loaded: `gameplay-workflows.md`,
`physics-engine-selection.md`, `checklists/new-game-definition-of-done.md`
under the gameplay-systems skill. All three read successfully.
