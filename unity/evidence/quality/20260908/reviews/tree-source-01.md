# Hero tree — independent source gate 01

8 September 2026. Reviewer: `visual_critic`, separate from tree authoring. **Decision: the candidate is suitable for a reversible native audition. It does not yet pass the tree TODO or native visual acceptance.** Raw base presentation needs integration work; outer canopy, unseen branch joins, scale, materials in URP, wind and LOD transitions remain unreviewed.

This applies only to the supplied Poly Haven Jacaranda candidate. No assets, scripts, Editor or Blender state were changed. [Baseline criteria](baseline.md) remain in force.

## Evidence inspected

- [Whole source tree](../../../../../art/quality_20260908/tree/source-whole.png).
- [Original dark trunk](../../../../../art/quality_20260908/tree/source-trunk.png) and [fill-lit trunk](../../../../../art/quality_20260908/tree/source-trunk-lit.png).
- [Original dark roots](../../../../../art/quality_20260908/tree/source-roots.png) and [fill-lit roots](../../../../../art/quality_20260908/tree/source-roots-lit.png).
- [Source inspection](../../../../../art/quality_20260908/tree/source-inspection.json) and [runtime export manifest](../../../../../art/quality_20260908/tree/export-manifest.json).
- Previous native [branch joins](../../../phase1/20260908/final-native-02/cam_hero.png), [roots](../../../phase1/20260908/final-native-02/cam_p1_tree_roots.png), [avenue](../../../phase1/20260908/final-native-02/cam_avenue.png) and [hill](../../../phase1/20260908/final-native-02/cam_hill.png), already inspected for the baseline review.

The new images are Blender source renders against a plane, not matched native comparisons. The fill-lit views reveal construction hidden in the original nearly black trunk renders. A brighter presentation is useful evidence, not itself an asset improvement or permission to brighten the game's lighting indiscriminately.

## Visible findings

| Area | Observation | Source gate |
| --- | --- | --- |
| Main branch unions | The shown fork grows continuously out of the trunk, with plausible shoulders and taper. The old native tree's exposed clipped-cylinder wedges are absent in this angle. Multiple stems and asymmetrical growth give the lower trunk more credible structure. | Pass to audition for these shown joins. Inspect their reverse sides and upper transitions before closing TREE-01. |
| Bark and local shape | Smaller bark plates, fissures and local knots follow the main trunk and branches. The shown fork avoids the previous huge stretched streaks and obvious abrupt bark direction changes. The narrow opening between stems is not, by itself, an erroneous mesh gap: it reads as separated growth. | Encouraging source evidence. Native texel scale, imported normals/tangents and specular response remain U. Do not fill a natural opening merely to make topology continuous. |
| Root transition | The root collar has more irregular, tapering volume than the old swollen lobes. However, the lower scan edge visibly floats above the plane in parts. The front root ends abruptly and the base retains a dark, skirt-like lower boundary with flattened green surface detail. | Reject the displayed ground transition. Embed the raw lower boundary into appropriate soil and fit the contacts around the actual root shape. Preserve the visible flare; do not bury the trunk in a generic mound or cover defects with dense weeds. |
| Canopy structure | Whole view has recognisable intermediate branches, asymmetrical spreading layers and more coherent leafy mass than the old speckled clumps on giant bare tubes. Lower foliage provides a gradual transition between trunk and crown. | Pass to audition for overall direction. The upper/outer twig joins are not close enough or bright enough to clear. |
| Leaves | Compound sprays are visible in the fill-lit trunk image, but some read as near-planar layers and isolated dense clusters against the sky. A still render cannot distinguish acceptable cards from distracting cross-plane behaviour or alpha shimmer. | U for near foliage and motion. Request close views from above/below and around the crown, including backlight. |
| Scale and silhouette | Source LOD0 dimensions are approximately 24.42 × 19.15 × 19.47 m in Blender axes. At the recorded uniform 0.78 scale, expected width/depth/height are approximately 19.05 × 14.94 × 15.19 m before Unity placement. The source preview has no human scale marker. | U for native landmark scale. Retain uniform scale; compare the avenue/hill silhouette and branches above playable paths with the 1.8 m actor. A smaller, more believable tree can work, but loss of the central landmark's presence needs deliberate review. |
| Cost/LOD | The manifest preserves source LOD0 and LOD1. Their triangle totals and texture sizes do not establish visual quality or acceptable performance. The alternate LOD is not shown. | U for LOD transitions and native cost. Profile the visible/shadow work after integration rather than approving or rejecting from counts. |

The source metadata lists the leaf alpha image as sRGB. That is a material-import verification item: confirm the runtime alpha mask is sampled as intended and that cutoff preserves leaf coverage. This observation does not establish that Unity currently imports it incorrectly.

## Required native handoff

1. Saved scene/build identity and exact placement/scale; actor marker and actual fitted root/soil/paving contacts. Preserve the old source recoverably.
2. Matched `cam_hill`, `cam_avenue`, `cam_hero`, `cam_p1_tree_roots`, plus root views from four quadrants at player height. Show the narrow inter-stem space and the back of each large fork. No visible raw scan skirt, floating contact, clipped trunk joint or stretched bark patch at ordinary play distance.
3. Backlit and shaded leaf/branch close-ups, canopy underside, and a full circuit along the existing walkable route. Verify no low branch blocks characters or creates camera collision errors.
4. Continuous native 30-second still and 30-second moving foliage/shadow review, with wind/reduced-motion states identified. Traverse each installed LOD boundary in both directions. Screenshots cannot pass this requirement.
5. Native performance, preservation/route checks and material import records. Keep sun/exposure/cameras matched for comparisons; identify any deliberate lighting change separately.

**No native score is upgraded by this source gate.** TREE-01/02/03 remain open until the corresponding built-game evidence clears their defects. The strongest improvement is biological branch structure; the immediate visible correction is the base-to-ground transition.
