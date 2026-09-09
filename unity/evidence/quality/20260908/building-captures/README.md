# Placed-building capture preparation and tree-platform targets

Prepared from the **20:07:39 UTC frozen scene audit** on 8 September 2026. This folder contains tooling and proposed cameras, **not newly captured native evidence or visual acceptance**. The shared Unity scene was not changed by the audit agent.

## Scope and numerical closure

The [capture plan](building-capture-plan.json) retains **all ten primary building placements individually**: Air + Water, Basic General, Field Supply, Finery, Relay Works, Repairs, Salvage, Thread + Hide, Tool Exchange and Vanguard Hall. Each has front, doorway, left side, right side, back and roof cameras: **60 proposals**. Every current mesh in each visual root plus its associated active shop signs/porch/threshold is identified from the frozen inventory. Mesh reuse never merges placement review.

The seven earlier proposals in [capture-requests.json](../audit/capture-requests.json) remain embedded as provenance. Side cameras were changed to pedestrian corner obliques: the old broadside positions could fall inside neighboring shops. These obliques still require assessment of occluded side regions. Add detail views when the rear of a wall, its supports or a threshold is hidden; a thumbnail of a corner is not full facade coverage.

The plan separately lists **122 active boundary/gate architecture instances** outside the ten-building set, including the two accepted west-gate arch placements and Ring Gate. This is not an all-mesh or whole-city visual pass. Hidden/rejected shop alternatives still need their separate source review. Architecture, wireframes, moving approaches and unresolved unique assets remain open in [the Phase 0 cross-reference](../../../../../docs/mesh-audit.md).

## Root-run sequence

1. With the intended AthenHill scene open outside Play Mode, run `AthenHill.Editor.BuildingAuditCapturePass.Prepare()` or **Athen Hill → Quality audit → Prepare building capture cameras**. The method prevalidates source selectors and camera-name collisions, then adds only missing disabled cameras under `Quality building audit cameras`. It does not move existing cameras, edit world geometry, show/hide sources, rebuild chunks, capture, save or build.
2. Inspect proposed cameras for framing and obstruction. Adjust the new diagnostic cameras in the Inspector as needed. Side/back views may reveal surrounding geometry or insufficient viewing clearance; keep these failures visible in the review rather than counting them as accepted views. Finish any coordinated source work and normal chunk workflow, then **save the scene**.
3. Run `AthenHill.Editor.BuildingAuditCapturePass.ExportSavedManifest()` or **Export saved building capture manifest**. It refuses a dirty scene. `saved-camera-manifest.json` records the actual serialized scene hash, current mesh/material paths and hashes, mesh GUID/local file IDs, placed-renderer global IDs/transforms/bounds, and each camera's exact position, Euler angles, quaternion, forward vector and lens. Collider overlaps and sight-line hits are diagnostic evidence, not an automated framing verdict. If source paths changed intentionally, update the affected plan selectors before running.
4. Root builds and launches that saved scene using the normal native Linux workflow. Keep the actual build identity/scene hash in a JSON build record. Leave the game in Play state with modals closed at native 1920×1080, render scale 1 and all nine actors.
5. Run the capture driver against the explicitly enabled native QA folder. Use a **new output directory for each lighting/build pass**. Example from repository root:

```bash
ATHEN_NATIVE_DIR=/absolute/path/to/running-native-qa \
/home/teknetik/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  unity/tools/capture_building_audit.py \
  --manifest unity/evidence/quality/20260908/building-captures/saved-camera-manifest.json \
  --build-record /absolute/path/to/actual-build-record.json \
  --output /absolute/path/to/new-building-native-noon \
  --hour 12
```

`--hour` is optional and requires the integrated native day/night diagnostics. It pauses the clock at that hour, waits for reflection refresh, and restores the previous hour/speed/pause state afterward. Repeat at the chosen shade/late-light hour with the same camera manifest. Without this option the current authored lighting is captured and time is not claimed to be fixed. The tool retains HUD and all actor/effect settings, returns the camera to normal follow afterward, and leaves the player open.

Each capture verifies native resolution, render scale, actor count, Play state and camera position. The existing native snapshot does not expose rotation/FOV, so the report explicitly states that those come from the saved camera and `AthenDebugBridge.View`, not an independent runtime counter. A supplied build record remains provenance supplied by the root; camera matching alone does not verify all shipped source files.

Outputs are 60 original PNGs, ten clearly labelled contact sheets, a linked HTML index, exact saved manifest copy, build-record copy, native environment/settings/snapshots and image SHA256 values. `review-ledger.json` starts every view **unreviewed/unaccepted**, including successful captures. Missing captures remain visible as gaps. The critic records actual coverage, defects, scores and decisions after inspecting the original images. The driver provides no wireframe, motion, gameplay or performance qualification.

## Tree-platform replacement production brief

[tree-platform-targets.json](tree-platform-targets.json) records the exact frozen source identities, eight mesh children and two collider proxies per prop. These are the small decorative terminals around the tree; their current identifiers say `hill_market`, not save/reclaim.

| Slot prefix under `AuthoredWorld` | Body center, metres | Ground/pivot for a new model | Front |
| --- | --- | --- | --- |
| `PROP_hill_market_00` | `(5, 2.15, -4)` | `(5, 1.50, -4)` | `+Z` |
| `PROP_hill_market_01` | `(-5, 2.15, -4)` | `(-5, 1.50, -4)` | `+Z` |
| `PROP_hill_market_02` | `(-5, 2.15, 1)` | `(-5, 1.50, 1)` | `+Z` |

Each prop is **214 triangles across eight parts**, with an overall `0.86 × 1.34 × 0.785 m` envelope. Its body is `0.75 × 1.30 × 0.65 m`; the base is `0.86 × 0.14 × 0.76 m`, with bottom at platform Y=1.50. Children use `_foot`, `_body`, `_screen_bezel`, `_interface`, `_lower_access`, `_vent`, `_vent.001` and `_button`. `_interface` geometry has world-coordinate vertices despite a zero transform position: use its recorded bounds, not the transform alone. The mesh source is `Assets/AthenHill/Art/Imported/world.glb`.

The two enabled non-trigger BoxColliders per slot are `COL_PROP_hill_market_XX_body` and `COL_PROP_hill_market_XX_foot`. Preserve them during audition; fit a deliberate new proxy if the accepted silhouette requires it. Keep the platform, tree traversal and nearby Linn access clear. Retain the complete existing prefix family recoverably when a replacement is installed, including all eight visual children and the matching collider proxies.

Model production can start against those measured slots: grounded industrial casing, a real recessed screen/bezel, service-panel thickness, separate controls, believable cable/service access and localized foot-contact dirt; author in metres with base pivot at zero and front +Z. Retain detailed source geometry and original maps; use separate readable text/screen art instead of generated baked lettering. Preserve the slot envelope during the first audition, use uniform scale, and inspect from 1.6–1.8 m eye height at the screen as well as all sides. Geometry and supplied texture/channel quality need source review before Unity installation.

**No existing save/reclaim gameplay binding was found.** `GameSession.Prompt` / `Interact` target NPC dialogue, Lattice or Ring; `hillPoint` only tracks hill visitation. The code path and inspected SHA256 are recorded in the JSON. The three props presently have no distinct interaction IDs or save/reclaim roles to preserve. A later explicit role/content decision and gameplay implementation are separate from preparing the replacement visual family; do not claim the decorative props already save or reclaim anything.

Do not touch the separate accepted mission terminals: `Mission Terminal Upgrade/Mission Terminal 01/02/03/Meshy Mission Terminal` at `(10, .25, -13.8)`, `(8, .25, -13.8)`, `(6, .25, -13.8)`. Their source is `Imported/Meshy/MissionTerminal/mission-terminal.glb`. The Lattice console at `(0, 1.2, -39)` is another separate target. All are explicitly excluded in the platform target manifest.

## Verification performed without Unity operations

`prepare_plan.py` reproduces JSON from the frozen audit and current inspected GameSession code; it does not read later mesh geometry as though it were the old snapshot. It produced 10 primary buildings, 60 uniquely named cameras, 122 additional architecture instances and three distinct tree-platform props. Python syntax and CLI help were checked with the bundled Python/Pillow runtime. The Editor helper compiled against installed Unity 6000.6 assemblies using [compile.rsp](compile.rsp); the standalone compiler emits the existing Newtonsoft/netstandard reference warning. Actual Unity installation, export, native capture and critic acceptance remain root-run work.
