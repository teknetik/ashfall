# Tree shadow geometry review — source records only

The current supplied hero tree has three separately editable renderers/material slots per LOD: trunk, branches and leaves. Full source FBXs, Blender sources, 4k maps and records remain retained. This review did not open/import/render the source model during native timing.

| Part | Repaired LOD0 triangles | Source LOD1 triangles |
| --- | ---: | ---: |
| Leaves | 2,402,434 | 1,201,217 |
| Branches | 1,231,286 | 615,642 |
| Trunk | 115,056 | 28,744 |
| Total | 3,748,776 | 1,845,603 |

The older export manifest records 3,863,832 LOD0 triangles; its duplicate trunk was explicitly repaired to the current 3,748,776. Use `art/quality_20260908/tree/duplicate-repair.json` and `unity/evidence/quality/20260908/tree/prepared.json` when reconciling counts. Unity imported vertex counts (3,632,500 and 2,162,878) exceed Blender export vertices because of split vertex attributes; do not confuse vertices with triangles.

The saved prefab has two LODs at relative heights 0.50 and 0.015, crossfade width 0.12, and PC lodBias 2. Leaves cast TwoSided with alpha-tested Cull0 material; trunk/branches cast normally. Existing LOD1 trunk collision is an independent object outside both visual source containers. The installed tree was uniformly scaled 0.88; historical world bounds were 21.487 × 17.135 × 16.856 m. Preserve current scene transforms rather than replaying those historical values. User-added trees are separate content.

## Bounded candidate

Reuse the existing Source LOD1 container solely for shadows in a temporary, non-saving development audition. Original visible source meshes, materials, LOD membership, enabled flags and collision remain unchanged; only their casting flags are temporarily Off. The clone's three renderers are ShadowsOnly. Its inherited local hierarchy, material alpha/clip and world-space wind must match. Restoration recovers every original casting flag and removes only the owned clone. Validate before cloning that the source contains only transforms, mesh filters and mesh renderers: no scripts or collision may briefly execute or enter physics.

Compared with a full LOD0 caster draw, source LOD1 saves 1,903,173 submitted triangles (50.8%). If the full source is submitted into four cascades, that can save 7,612,692 triangles before additional lights. This is an estimate conditional on actual submissions, not a prediction that the measured 41.9M total falls by that amount or reaches 60 FPS. Other trees/buildings, crossfade duplication, depth/color passes and local shadow passes also contribute. If the source already selects LOD1, replacing its caster with LOD1 gives no geometry reduction for that draw.

## Editable profile and next evidence

Keep a recoverable full-source casting reference and a separate shadow-source candidate under the same hero prefab/variant, outside its visible LODGroup and outside disposable city chunks. The native helper is diagnostic only; permanent integration should save ordinary authored child renderers and explicit profile selection after review. Never use a camera Renderer's enabled=false to hide proxy geometry, because it disables its shadows too; use ShadowsOnly and keep alpha-tested Cull0 for leaves.

If LOD1 remains too costly, derive separate shadow-only meshes in Blender from preserved sources. Allocate geometry by projected shadow error, branch silhouette and leaf coverage at the actual cascade resolutions, not an arbitrary polygon cap or visible hero reduction. Installed URP ShadowUtils computes directional world texel size as (2/projectionMatrix.m00)/sliceResolution. A 4096 atlas with four cascade tiles uses 2048-per-tile resolution; cascade world extents still need actual matrices. Measure full-source vs proxy silhouette/coverage and self-shadow at that projection, in noon and low sun. Subtexel branch detail may be simplified while retaining trunk contact, large branches, leaf cluster gaps and opacity coverage. Preserve UVs and alpha; a solid blob or single canopy hull will change dappled shadows and interior lighting substantially.

A standard independent LODGroup still follows camera screen size, not automatically each shadow cascade's texel size. Per-cascade custom geometry selection would require a separate rendering design/verification pass; do not imply the simple clone implements it. The existing importers have generateMeshLods=0 and the PC profile has GPU Resident Drawer disabled, so newer mesh-LOD features are not already solving this source's shadow cost.

Reject proxy candidates with detached/shifted self-shadows, lost dappled coverage, bright leaf leaks, canopy density changes, low-sun silhouettes that no longer match, visible LOD seams, incorrect wind phase, extra collision or worse frame tails. Keep matched fixed-camera performance tests separate from the required warmed real-input route.
