# Ward next-level push — progress log (from 29 September 2026)

Goal from Carl (29 Sep 2026): push the game forward on the crafting/loot/upgrade loop and bring the visuals up
towards the AAA target in AGENTS.md. This log records what was done, where, and what is still open, so any session can
resume. Newest entries at the bottom of each section.

## Branches and worktrees

| Where | Branch | Purpose |
| --- | --- | --- |
| `/home/teknetik/code/ao2` | `ward/next-level` | Integration branch: rendering, lighting, art, native QA. Starts at `f17733c4` (checkpoint of the Hermes 29 Sep passes). |
| `/home/teknetik/code/ao2-gameplay` | `ward/gameplay-v2` | Gameplay systems (loot v2, fabrication, field orders, save/load). Scene changes only through `GameplayV2Installer`, re-run on the integration branch at merge. Library reflinked from the main checkout. |

`main` is untouched (3 local commits ahead of origin, not pushed). The old `ao2-crafting` / `ao2-devui` worktrees are
left as they were (committed evidence scripts still reference `ao2-crafting` by absolute path).

## Baseline (29 Sep, before any change)

Native lookbook `unity/evidence/rendering/20260929/baseline/` (11 review cameras × 09:00/13:00/17:30/21:00,
1920×1080 OpenGLCore, RTX 3060 / i9-10850K, High preset):

- 65–76 FPS average at `cam_hill`, p99 14.7–16.4 ms, **16–23 M triangles** submitted.
- Day: shadows stop ~18 m from the camera (High preset hard-coded 18 m, 1 cascade); linear orange fog from 12 m to
  118 m flattens everything past a street into beige; low sun/shade contrast.
- Night: nearly black; 61 practical lamps averaged intensity 1.4 / range 4.5 m and were culled beyond 42 m; forward
  rendering limited lights per object.
- Scene cost audit `unity/evidence/rendering/20260929/scene-cost-audit.json`: Karaveen truck 3.09 M tris (no LOD),
  hero tree LOD0 3.75 M, render chunks 3.3 M in effectively two 64×128 m cells (no culling), 14.9 M tris cast shadows.

## Work log

- Checkpoint commit `f17733c4` on `ward/next-level`: Hermes's uncommitted passes, restored overwritten inventory
  evidence, stopped tracking QA `pid`/`prefs` files.
- `unity/tools/lookbook.py`: native capture tool (named cameras × hours, frame-time profile, contact sheets).
- `Editor/SceneCostAudit.cs`: read-only per-renderer triangle/LOD/shadow report.
- `Editor/RenderingUpgradePass.cs` + `Editor/WardLightingPassV2.cs` (lighting v2): 150 m / 4-cascade sun shadows,
  Forward+, HDR grading, stronger SSAO, new day/night palette (whiter noon sun, cooler shade, moonlit night), fog
  38–420 m, lamps ×2.4 intensity / ×1.6 range reaching 150 m, render chunks at 24 m cells with flat ground not casting
  shadows. `GameSettings` shadow presets now 45/90/150 m with 2/3/4 cascades. Change log with before values:
  `unity/evidence/rendering/20260929/lighting-v2.json`, `rendering-upgrade.json`.

## Delegated work in flight

- Gameplay v2 (worktree `ao2-gameplay`): weapon stats/slots, Mk I/II mods, refined components, loot v2 with bad-luck
  protection, physical salvage caches, scrap heaps, Depot Foreman elite, Ossa field orders, salvage selling,
  fabricator UI v2, save/load.
- Truck and hero-tree LODs + shadow proxies (Blender, `art/optimization_20260929/`).
- Procedural sky v2 shader (`Shaders/WardSkyV2.shader`).

## Open items

- Judge lighting v2 natively (day/dusk/night) and iterate.
- Integrate truck/tree LODs, sky v2, gameplay v2; full native QA of the city loop and the Berms cycle.
