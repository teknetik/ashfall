# Shade sails — progress (1 Oct 2026)

## Done
- 17:05 read brief/BRIEF/AGENTS/EDITING; fresh audit `unity/evidence/shade-sails/20261001/audit-before.json` (after wall-foot drifts install).
- Maps of the four areas (`review/map-*.png`), contact sheets of the current batch-2 lookbook (`review/before-*.jpg`).

## Next
- Survey step (lights, cameras, sun, mesh probes: retrofit service poles, tree canopy, bunting) → layout (`sails.py`).
- Blender authoring (form-found sails, hardware, poles, festoons) → textures → review renders.
- Unity pass build/install/verify/cameras; editor captures (<= 6 close cams).
- 17:20 survey step (ShadeSailsPass.cs survey, -nographics) -> evidence/survey.json (158 lights, cameras, sun, probes).
- 17:35 layout (sails.py): Courtyard quad, Market quad (two retrofit service poles), Apron quad, Lattice tri; 0 problems,
  1 accepted warning (barrel smoke end cap under the market sail). formfind.py (force density).
- 17:45 author_sails.py (Blender) all four sites; make_textures.py; review renders review/r1 (form OK, hardware OK).
- 18:00 ShadeSailsPass.cs full (build/install/verify/cams/capture/toggle) compiled offline, copied to Assets.
- 18:00 build + install + verify OK (-nographics). Editor captures r1 (13:00, 6 cams).
- 18:04 fix: canvas self-shadowing killed the transmission -> ShadowsOnly canvas proxies 4 cm below (per LOD); transmission
  up; build,reinstall,verify OK; captures r2 (13:00 + 20:30).
- 18:07 bulbs warmer/dimmer (materials step); survey after (circuit 136->143 / 82->89, bulb on the emissive list);
  audit-after-install + sails.py --installed: 0 problems. Captures r3.
- 18:15 fix: retrofit service poles are I-beams (0.20 x 0.26 m), not round: strops round the beam, fixings on the flange
  faces; pole paint VH_Paint (grooved) -> SS_Pole* (tinted VH_Steel); captures r4/r5 OK.
- 18:25 plain build,verify keeps the instances' clock bindings (checked). README, DOCS_SNIPPET, evidence README written.

## Next (only if the orchestrator's combined test reports defects)
- Canvas underside brightness at noon (SS_Sail_* _WardTranslucency), shadow cost of the canopies, smoke vs market canvas.
