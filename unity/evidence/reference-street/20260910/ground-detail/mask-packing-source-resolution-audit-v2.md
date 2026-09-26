# Ground source resolution and packing audit — 10 September 2026

**The original Meshy exports preserve full source resolution; their maps are not uniformly 4K.** All five generation jobs supplied color/normal maps at 4096×4096 and metallic/roughness/emission masks at 2048×2048. Every packed pixel in the currently prepared scrap/v1 and trash/v2 matches those 2048 masks exactly. Upsampling these packed masks would not recover missing source detail.

This supersedes the earlier audit snapshot, which also encountered the incomplete crate-v4 rebake directory. The derived crate-v4 masks below are an authoring output in progress, not another original Meshy export or an accepted runtime asset.

| Folder | Kind | Color | Normal | Metallic | Roughness | Emission |
| --- | --- | --- | --- | --- | --- | --- |
| crate | original Meshy export | 4096×4096 | 4096×4096 | 2048×2048 | 2048×2048 | 2048×2048 |
| crate-v2 | local variant with copied original maps | 4096×4096 | 4096×4096 | 2048×2048 | 2048×2048 | 2048×2048 |
| crate-v3 | original Meshy export | 4096×4096 | 4096×4096 | 2048×2048 | 2048×2048 | 2048×2048 |
| crate-v3-runtime | local variant with copied original maps | 4096×4096 | 4096×4096 | 2048×2048 | 2048×2048 | 2048×2048 |
| crate-v4-runtime | in-progress local rebake | 4096×4096 | 4096×4096 | 4096×4096 | 4096×4096 | Absent |
| scrap | original Meshy export | 4096×4096 | 4096×4096 | 2048×2048 | 2048×2048 | 2048×2048 |
| trash | original Meshy export | 4096×4096 | 4096×4096 | 2048×2048 | 2048×2048 | 2048×2048 |
| trash-v2 | original Meshy export | 4096×4096 | 4096×4096 | 2048×2048 | 2048×2048 | 2048×2048 |
| trash-v2-runtime | local variant with copied original maps | 4096×4096 | 4096×4096 | 2048×2048 | 2048×2048 | 2048×2048 |

Both prepared packed PNGs have 4,194,304 pixels. All red values equal source metallic red, all alpha values equal 255 minus source roughness red, and green/blue are zero. External originals, imported copies and source contracts match by SHA-256. The JSON records the exact difference extrema and before/after hashes.

No code, source map, packed map, material or GUID was changed. No Unity or application call was made. Loaded/imported/GPU mip levels, shader correctness, source texel-density suitability and native visual quality remain separate checks; the saved quality profiles currently specify mip limit 0. No packing repair is warranted by this evidence.

[Detailed evidence](mask-packing-source-resolution-audit-v2.json)
