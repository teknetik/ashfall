# Ground mask source and packing audit — 10 September 2026

**The correct description is “full source resolution,” not “all 4K maps.”** Meshy supplied color/normal images at 4096×4096 and metallic/roughness/emission masks at 2048×2048 for every inspected new ground revision. Increasing the packed image to 4096 would upsample the masks without adding detail.

| External source revision | Color | Normal | Metallic | Roughness | Emission |
| --- | --- | --- | --- | --- | --- |
| crate | 4096×4096 | 4096×4096 | 2048×2048 | 2048×2048 | 2048×2048 |
| crate-v2 | 4096×4096 | 4096×4096 | 2048×2048 | 2048×2048 | 2048×2048 |
| crate-v3 | 4096×4096 | 4096×4096 | 2048×2048 | 2048×2048 | 2048×2048 |
| crate-v3-runtime | 4096×4096 | 4096×4096 | 2048×2048 | 2048×2048 | 2048×2048 |
| crate-v4-runtime | 4096×4096 | Absent | Absent | Absent | Absent |
| scrap | 4096×4096 | 4096×4096 | 2048×2048 | 2048×2048 | 2048×2048 |
| trash | 4096×4096 | 4096×4096 | 2048×2048 | 2048×2048 | 2048×2048 |
| trash-v2 | 4096×4096 | 4096×4096 | 2048×2048 | 2048×2048 | 2048×2048 |
| trash-v2-runtime | 4096×4096 | 4096×4096 | 2048×2048 | 2048×2048 | 2048×2048 |

Both prepared `scrap/v1` and `trash/v2` packed PNGs are 2048×2048. Every packed red pixel equals the original metallic red pixel, every packed alpha pixel equals 255 minus the original roughness red pixel, and every green/blue pixel is zero. All 4,194,304 pixels per map were compared. Their external masks, imported copies and immutable source contracts have identical SHA-256 hashes. No packing fix or repack is needed.

Original maps, material files, GUIDs, packed files and the staged `GroundDetailPass.cs` remain unchanged. The JSON records before/after hashes, image integrity, dimensions and exact per-channel comparison extrema. This was entirely offline; current imported/GPU mip levels and visual acceptance remain separate checks. Saved quality profiles currently specify mip limit 0.

This finding corrects the broad 4K-mask assumption for these new assets. It does not certify that their texel density or visual quality meets the reference; those decisions still require native close-up review.

[Detailed evidence](mask-packing-source-resolution-audit.json)
