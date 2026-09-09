# Hill-platform save/reclaim terminal family — 8 September 2026

This source-production task replaces only the three decorative `PROP_hill_market_00/01/02` visual families beneath `AuthoredWorld`. It does not replace the accepted mission terminals or either travel landmark. The exact frozen source/part/collider inventory is [tree-platform-targets.json](../../unity/evidence/quality/20260908/building-captures/tree-platform-targets.json).

## Brief

The existing 214-triangle props each occupy a 0.86 × 1.34 × 0.785 m envelope. The new family is designed as a believable 1.65 m service terminal with a slim body, recessed screen, physical controls, card/palm reader, retrieval slot, service-door hinges, panel seams, vents and a grounded base. It uses warm grey enamel, dark structural steel, restrained teal accents, brass fittings and localized contact/base wear. Readable lettering is authored separately after generation. The height increase is deliberate; the horizontal footprint must remain within the existing footprint and the local Linn route must remain clear.

| Existing visual prefix | Base position (Unity metres) | Front | Intended visual variant |
| --- | --- | --- | --- |
| `AuthoredWorld/PROP_hill_market_00_` | (5, 1.50, -4) | +Z | SAVE |
| `AuthoredWorld/PROP_hill_market_01_` | (-5, 1.50, -4) | +Z | RECLAIM |
| `AuthoredWorld/PROP_hill_market_02_` | (-5, 1.50, 1) | +Z | RECLAIM |

The eight existing source parts and both named collider objects per slot are retained. The installer hides only the eight retired renderers after new visuals are present and refits the existing collider components without changing their identifiers. No broad prefix matching of mission or Lattice content is permitted.

## Gameplay boundary

The saved props have no save/reclaim interaction IDs or components. `GameSession.Prompt`/`Interact` handles NPCs, Lattice and Ring interactions; `hillPoint` tracks visitation only. This task produces decorative terminal models. Authored screens must visibly report `OFFLINE` until a separately scoped gameplay implementation exists. No successful save, respawn binding, reclamation inventory or credit transfer is implied by the models.

## Source and acceptance

Original concept reference and prompt live in `refs/quality_20260908/platform-terminals`. Meshy source, full delivered PBR maps, task options, actual credits and checksums are retained in this folder. Any cleanup/export is a derivative; originals remain untouched. No source topology is destructively reduced, and no nonuniform scaling is allowed for fitting.

Meshy 7 ultra task `01a082f4-ec1a-7558-92e4-07c0a5b403cf` succeeded for 35 credits. It returned 3,015,022 triangles, 4K albedo and normal maps, and 2K metallic/roughness maps. The full source is preserved. The deliberately smaller runtime derivatives are measured separately against that source; see [integration handoff](../../art/quality_20260908/platform-terminals/INSTALL.md). Initial source inspection found an invalid screen patch, and independent review caught poor seating of the first display insert. Both the rejected images and correction details are retained; no native acceptance is inferred from generation.

Source inspection and a successful import only qualify a candidate. Root integration must capture front, side, back, screen close-up, sun/shade and first-person native approaches, verify Linn clearance and all three original mission terminals, and obtain independent critical review before marking the TODO complete.
