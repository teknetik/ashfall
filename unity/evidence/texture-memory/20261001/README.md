# Texture memory — evidence (1 Oct 2026)

Workstream 15 (texture compression), batch 3. Sources, run order and rollback: `art/texture_memory_20261001/README.md`.
Editor code: `Assets/AthenHill/Editor/TextureMemoryPass.cs` (steps) and `GltfTextureCompression.cs` (glTFast import add-on).
**No scene references, materials, prefabs or GUIDs changed.** The only scene edit is a root of six disabled review cameras.
Frame time, city loop and the combined native lookbook are **pending the orchestrator's combined test**.

## Why

A native run took about 9.5 GB of the shared 12 GB RTX 3060, and with the desktop it crossed the watchdog line. The city
paving probe found about 4.4 GB of non-streamed textures, mostly uncompressed glTF/Meshy imports.

## What was found (inventory, `inventory-before.json/.md`)

The saved scene loads 1,501 textures: 9,345 MB with every mip as stored for StandaloneLinux64, of which 4,733 MB is not
streamed. A player loads inactive objects too, and textures used only by inactive objects come to 1,624 MB.

- **glTF embedded images: 461 textures, 3,900 MB, all uncompressed and never streamed**, in 24 .glb files. glTFast
  6.20's editor importer decodes embedded PNG/JPEG with `Texture2D.LoadImage` (RGBA32/ARGB32/RGB24). It has no
  compression option and no external-object remapping. The biggest files are `WardRetrofit.glb` (161 textures,
  1,255 MB), `KaraveenMarket.glb` (204, 885 MB) and `WardenBooth.glb` (26, 415 MB).
- **TextureImporter: 62 uncompressed textures, 818 MB.** Every non-UI one is **non-power-of-two with mipmaps, which
  Unity 6000.6 leaves uncompressed even with CompressedHQ or an explicit BC7 override.** I tested this on
  `sign_emission.png` (2048×660): it stayed RGBA32. The log says "Only POT textures can be compressed to this format
  if the texture has a mipmap". The biggest is the District atlas (3 × 6144×4096, 384 MB, used only by inactive
  objects).
- All glTF-imported meshes report UV distribution metric 1 because glTFast never computes it (see open points).

## What changed

| Group | Count | Format change | Memory (all mips) | Where |
| --- | ---: | --- | --- | --- |
| glTF embedded, 24 .glb | 414 | RGB24/ARGB32 → **BC7** (162 sRGB, 252 linear), same channels, mips and orientation | 3,745 → 1,160 MB | `GltfTextureCompression` add-on + force reimport |
| glTF embedded, kept | 42 | unchanged (NPOT with mips, or 1254² with no mips in `world.glb`) | 128 MB | — |
| TextureImporter, NPOT | 20 | RGBA32 → **BC7** sRGB 12, **BC7** linear masks 4, **BC5** normal maps 4; import scaled *up* to the next power of two (`ToLarger`, never down); mip streaming on | 781 → 328 MB | Standalone overrides in the `.meta` files |
| TextureImporter, reverted | 2 | `Gunmetal_NormalSource`, `WallStone_NormalSource` put back: they are normals generated from height, and scaling the height up would flatten the bumps | 16 MB, unchanged | `rollback/meta` |
| TextureImporter, skipped | 40 | UI/package art (39) and the Berms road splat, which has the author's explicit RGBA32 override | 37 MB | — |

Records: `importers-applied.json` (before/after settings per texture), `importer-plan.json`,
`gltf-reimport-{test2,retrofit,market,rest}.json` (per texture: size, mips, format, PSNR of the BC7 mip 0 against the
decoded source), and `verify-glb-*.json`.

The changed glTF textures are **not mipmap-streamed**. Setting `m_StreamingMipmaps` on the in-memory import texture
crashed Unity at 16:05 and 16:29 (both core dumps are in `TextureStreamingManager::RemoveTextureImmediately`, when the
import unloaded the texture). The add-on now only compresses. Two crashed imports of `WardRetrofit.glb` and
`WorkerDroid.glb` were restored with a plain reimport and verified before going on (16:31).

## Memory: before → after

**Editor inventory** (`inventory-after.json`, the same scene scan):

| | Before | After |
| --- | ---: | ---: |
| All textures, every mip | 9,345 MB | 6,287 MB |
| Not streamed | 4,733 MB | 1,744 MB |
| Uncompressed | 557 textures, 4,720 MB | 119 textures, 167 MB |

**Native**, with the paving pass's dev-only probe (`ATHEN_TEXSTREAM_PROBE=1`): cam_hill, cam_avenue, cam_gate at 13:00,
1920×1080, budget 5632 MB, OpenGL. Before = `Builds/batch-batch2` (it already contains the 20 importer changes).
After = `Builds/tm-after`, the same scene with the glb reimports, deleted after measuring.

| Counter | Before (batch 2) | After | Change |
| --- | ---: | ---: | ---: |
| `Texture.nonStreamingTextureMemory` | 4,033 MB | 1,573 MB | −2,460 MB |
| `Texture.currentTextureMemory` (resident) | 4,692 MB | 2,238 MB | −2,454 MB |
| `Texture.desiredTextureMemory` (max) | 4,666 MB | 2,211 MB | −2,455 MB |
| `Texture.totalTextureMemory` (all at mip 0) | 8,568 MB | 6,113 MB | −2,455 MB |
| Player process VRAM (nvidia-smi, max) | 8,012 MiB | 4,538 MiB | **−3,474 MiB** |
| System VRAM peak during the run (desktop included) | 11,150 MiB | 8,932 MiB | −2,218 MiB |

Reduced textures (loaded mip above the calculated mip): 0 in both runs. Data: `native-before-batch2/` and
`native-after/` (`texture-streaming.jsonl`, `texture-streaming-full.json`) and `vram-*.csv`. The batch-1-era probe
(paving pass) had 4,399 MB not streamed. The 20 importer changes in batch 2 saved a further 453 MB, mostly
inactive-only textures. The probe hitches every 8 s, so it was never used for frame times.

## Import cost (`jobs-texture-memory.log`)

| Job | Wall | Import | Peaks |
| --- | ---: | ---: | --- |
| 20 TextureImporter overrides (incl. three 8192×4096 BC7/BC5) | 42 s | 17 s | anon 4.0 GB |
| WardRetrofit.glb (161 textures) + verify | 61 s | 26 s | anon 7.5 GB, file 6.2 GB |
| KaraveenMarket.glb (204) + verify | 91 s | 42 s | anon 6.9 GB |
| Remaining 20 .glb + verify | 66 s | ~30 s | anon 6.8 GB |
| Inventory (scene scan) | 51–62 s | — | **anon 9.2–12.0 GB, swap 2.9–3.1 GB (at the 3 GB cap)**. This is the heaviest step; split it or skip the active-use pass if repeated |
| Measurement build `tm-after` | 132 s | — | anon 12.9 GB, swap 2.2 GB |

No watchdog kills. The two rc=139 runs are the crashes above. The rc=1 run at 16:49 was my one-minute compile error
(fixed at 16:50; it also failed the night-facade agent's 16:49:39 job, which has been told to rerun).

## Visual parity

- **Isolated editor captures** (new empty scene, one sun, flat ambient, no post; the city is never loaded; VRAM peak
  5.8 GB), before = uncompressed and after = BC7: `parity/before/`, `parity/after/`. Side-by-side pairs with a ×8
  difference strip and a 2× crop of the worst block: `parity/compare/pair-*.jpg`. Metrics: `parity/compare/parity.json`.
  Asset-pixel PSNR is **46–59 dB**, 99.9th-percentile pixel error 2–10 /255:

  | View | Asset PSNR | p99.9 error |
  | --- | ---: | ---: |
  | tm_market_pottery / tm_market_tools | 55.6 / 54.8 dB | 4 / 4 |
  | tm_retro_pump / tm_retro_nanofab | 53.2 / 59.0 dB | 4 / 2 |
  | tm_droid | 46.2 dB | 9 |
  | tm_target_plate | 51.4 dB | 4 |
  | tm_tool_wall | 49.0 dB | 6 |
  | tm_arms_locker | 56.5 dB | 3 |
  | tm_warden_booth | 52.8 dB | 4 |
  | tm_terminal | 49.4 dB | 6 |
  | tm_pistol_mods | 49.7 dB | 10 |

  `tm_district_gate` is identical before and after: the gate prefab doesn't use the District atlas, so the atlas is
  covered by the tiles below instead.
- **Per texture, glTF** (BC7 mip 0 against the decoded source, at import, all 414): the worst channel's PSNR has a
  median of 47.1 dB and a 5th percentile of 41.0 dB. Only 3 textures are below 38 dB (the lowest is 34.3 dB). The
  worst single pixel per texture is 20 /255 at the median and 86 /255 at most, in high-contrast detail. Per-texture
  values are in `gltf-reimport-*.json` (`addon` field).
- **TextureImporter tiles**: the same 256×256-texel window of the source file and of the imported texture, both at 2×
  with the same sampler. Pairs are in `parity/importers/*.png` (source left); tile PSNR 34–56 dB, mostly from the
  power-of-two upscale (`importers-board.json`). Full-size R/G PSNR of the BC5 normals against their sources is
  37–70 dB (`importers-psnr.json`).
- At 2× and in the renders I saw no banding, no blocking, no normal-map artefacts and no colour shift.
- The native before/after captures at cam_hill/avenue/gate match apart from clouds, animation and other passes'
  changes: `native-*/cam_*-h13.00.png`.

## Review cameras

Root "Texture memory review cameras" (disabled; eye 1.62 m above the ground found by a ray):
`cam_tm_market_pottery`, `cam_tm_retro_pump`, `cam_tm_retro_nanofab`, `cam_tm_mining_droid`, `cam_tm_warden_post`,
`cam_tm_range_plate` (`review-cameras.json`). Scene copy before the cameras were added:
`rollback/before-texture-memory-cameras.unity`.

## Verify (`verify-saved-scene.json`, -nographics, 17:01)

- All 20 importer overrides are in place and compressed.
- The add-on is on (`DefaultOn`).
- Six review cameras are present.
- Scene-wide missing material slots: 0.
- All 24 .glb files: sub-assets present, and every renderer that comes from them (1,788) keeps its mesh and every
  material slot.

## Budget recommendation (Carl decides; not changed here)

With non-streamed textures down to about 1.6 GB and resident textures to about 2.2 GB at the three test views, a
budget of **3584 MB** (down from 5632) covers the measured desired set with about 1.3 GB of headroom. The paving pass
saw a 13-camera session grow resident textures by about 0.55 GB, which this also covers. It caps worst-case growth
about 2 GB lower than 5632. 3072 MB would also hold today's set but leaves little room for new passes. Keeping 5632
would no longer exceed the card at these views, but over a long session resident textures could creep towards 5.6 GB
again.

## Open points / not done

- **glTF textures aren't streamed** (1,160 MB compressed and always resident) because of the crash above. Streaming
  them needs a different mechanism, such as extracting them to TextureImporter assets with a material remap (invasive:
  prefab overrides) or patching glTFast.
- **UV distribution metric 1 on every glTF mesh.** glTFast never calls `RecalculateUVDistributionMetrics`, so the
  streamer picks mips for every streamed TextureImporter texture drawn on a .glb mesh (masonry kit, shops, hall) as
  if one UV unit were 1 m². Big surfaces can sit up to `maxLevelReduction` (2) mips too coarse and small dense ones
  too fine. A `MeshAdded` hook in the same add-on fixes this (tested: WorkerDroid 1 → 27) but changes every pass's
  streaming, so it needs its own A/B. Not enabled.
- **Compressed but not streamed TextureImporter textures: 96, 437 MB.** Examples: the Berms ground arrays, which can't
  stream; the Traveler 4k albedo; the Mission Terminal maps. Turning on streaming is a flag change, but on .glb meshes
  it depends on the UV-metric fix above.
- 42 NPOT glTF textures (128 MB) and 9 NPOT 1254² TextureImporter textures stay uncompressed: about 165 MB in all.
- Inactive objects still cost 1,186 MB of textures (Phase1 shops, ReferenceStreet, District atlas). Deleting retired
  layers is outside this pass.
- `GltfTextureCompression.DefaultOn = true`: any future .glb import compresses its power-of-two embedded images to BC7.
  `ATHEN_GLTF_COMPRESS=0` turns it off for one Unity run.
