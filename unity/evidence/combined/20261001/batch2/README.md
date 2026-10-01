# Combined test, batch 2 (1 Oct 2026)

Batch 2 = West Gate arches, rooftops & service lines, Berms road ground (plus the first texture-memory changes, which
landed before the build: 22 NPOT TextureImporter textures → BC7/BC5 with power-of-two upscale and streaming, mostly
inactive rollback layers; active ones: Gunmetal, WallStone albedo/normal, SandstoneAlbedo, HillSoilAlbedo,
CourtyardCanvas, KaraveenPoster, WardBanner; WorkerDroid.glb texture BC7). The texture-memory pass later reverted the two
height-derived normal maps (Gunmetal_NormalSource, WallStone_NormalSource), so its final set is 20 importer textures. Build `Builds/batch-batch2` (development,
-nographics, 16:16). Compared with `Builds/batch-batch1`. Same machine and settings as batch 1 (see ../batch1/README.md).

## Results
- City loop: **PASS** (first attempt, `cityloop/`).
- Range tutorial check: **PASS 10/10** (`tutorial/report.json`).
- Lookbook: 100 cameras × 13:00 / 20:30 = 200 captures, 0 errors, seven chunks (`lookbook-p01…p07`, contact sheets).
- Frame time, batch 1 → batch 2, alternating runs, 2 per arm (`profile-summary.json`):

| View | 13:00 | 20:30 |
|---|---|---|
| cam_hill | 64.4 → 63.4 fps, p50 +0.25 ms | 70.5 → 68.8 fps, p50 +0.36 ms |
| cam_avenue | 56.1 → 56.3 fps, p50 −0.10 ms | 60.8 → 59.5 fps, p50 +0.33 ms |
| cam_gate | inconclusive (batch-1 arm 94 fps with p99 30 ms vs 145 fps earlier) | inconclusive |

  The gate runs overlapped agents' CPU-heavy Blender/Python jobs (they don't take the Unity lock); remeasure on a quiet
  machine in the final test.

## Review notes
- West Gate (cam_wga_*): closed steel-faced leaves, KEEP CLEAR stencil, transom grille read as a sealed working gate by
  day. At 20:30 the two bulkhead lenses clip to white boxes and the wicket is nearly black → sent to the night facade
  pass.
- Rooftops (cam_rt_*): cross-street service lines and masts read; set-back roof kit is mostly hidden at eye level.
- Berms road (cam_br_*) and range views: no errors; see sheets.
