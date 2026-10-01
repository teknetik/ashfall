# DOCS_SNIPPET — city paving and texture streaming (1 Oct 2026)

## For unity/EDITING.md — new section "City paving (flag ground)"

The city floor `Paving` (120 × 90 m cube, render-chunk source; collider `COL_Ground` is separate) and the three visible
`AuthoredWorld/AAA Environment Dressing/Plaza inset *` bands use the shader **Athen Hill/Ward Paving Lit**
(`Assets/AthenHill/Art/CityPaving/Shaders/`) with `Materials/PV_CityFlags.mat` (courses east–west) and
`PV_CityFlags_Band.mat` (courses north–south, cooler). The flags are mapped in **world XZ** (4 m tile, 8 courses of
0.5 m); every world course gets a random shift and source course, every flag instance its own tone. Mesh UVs are only
used by the depth/meta passes. Textures (`Art/CityPaving/Textures/PV_Flags_{BaseMap,Normal,Mask}.png` 2k,
`PV_Grain_Normal.png` 1k) are **not streamed** (the floor is always under the camera; 17 MB resident).

- **Edit the look:** change `art/city_paving_20261001/tuning.json` / `tuning-band.json` and run
  `CityPavingPass.RunBatch --steps assets,bandmat` (no chunk rebuild: the chunks reference the material assets).
  In a development player, `ATHEN_MATERIAL_TUNE=<file from tune_runtime.py>` applies the values at start-up without a
  rebuild (`Scripts/TextureStreamingProbe.cs`, `MaterialTuneProbe`).
- **Edit the texture:** `author_paving.py` (through `heavy.sh`), then `--steps assets`.
- **Rollback:** point `Paving` back to `Art/Weathering/Paving Local wear.mat` and the insets to
  `PlazaPaving Local wear.mat`, reactivate `Paving Joints` (still not drawn) and the four `Avenue service band` strips if
  wanted, `ShowSources(true)` → `StaticRenderChunksEditor.Rebuild`. A pre-install scene copy is in
  `unity/evidence/city-paving/20261001/rollback/`.
- **Render chunks now record UV density.** `StaticRenderChunksEditor.Rebuild` calls
  `Mesh.RecalculateUVDistributionMetrics()` on every chunk mesh. Before 1 Oct every chunk kept the default metric 1, so
  mipmap streaming computed far too coarse mips for chunked materials (the old paving was held at mip 2, ~52 px/m).
- **Texture streaming budget.** PC quality: `streamingMipmapsMemoryBudget` 4096 → **5632 MB** (max level reduction 2).
  Non-streamed textures alone take ~4.4 GB (uncompressed glTF/Meshy imports; the district atlas is 3 × 128 MB RGBA32),
  so at 4096 MB every streamed texture was pinned at its initial 2-mip reduction (hero-tree leaves wanted mip 0, got 2).
  5632 leaves ~1.2 GB for streamed textures and stays under the VRAM watchdog (11.4 GB with the desktop) on the 3060.
  Development players log streaming with `ATHEN_TEXSTREAM_PROBE=1` (`texture-streaming.jsonl` / `-full.json` in the QA
  folder); `ATHEN_TEXSTREAM_BUDGET=<MB>`, `ATHEN_TEXSTREAM_OFF=1` override for an A/B in one build.

## For AGENTS.md §3 baseline table — one row

| City paving | 1 Oct 2026 (`art/city_paving_20261001`, shader `Athen Hill/Ward Paving Lit`): the whole city floor and the plaza bands round the hill are world-mapped dressed-sandstone flags (4 m tile, 0.5 m courses shuffled per course, per-flag tone, sanded joints, macro tint/dust, close grain), textures 2k non-streamed (17 MB). `Paving Joints` and the four `Avenue service band` strips inactive; `COL_Ground` unchanged. Chunk meshes now carry UV-density metrics; PC streaming budget 5632 MB. Old materials kept for rollback. Not yet accepted by Carl. |
