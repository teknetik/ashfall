# Anonymous native shaded-leaf review — 26 September 2026

**There is a modest local lift in some variants, without a material fix for dark, merged clusters. No obvious unnatural glow is visible.** All twelve A/B/C PNGs were inspected and their 1920 × 1080 dimensions verified. The ranking in `anonymous-native-leaf-shade-preference-locked.json` was written before consulting the new mapping, source filenames, parameter records or implementation.

These are actual native frames. The task records Linux OpenGL, MSAA 4, render scale 1, 48 m/two-cascade shadows, three-second settling and a stable repaired 4096 texture at mip 0. Hidden metadata was intentionally not opened before locking. Daylight is paused, but foliage/actors animate; small shape changes are not evidence of changed geometry or missing leaves.

| Camera | Rank, best first | Confidence and finding |
| --- | --- | --- |
| Hill | A = B = C | Low confidence in a useful quality difference. All are green/olive; none repeats the conspicuous pale blue-gray Editor failure. Small brightness changes do not establish a winner at this distance. |
| Hero | A = C > B | Low confidence, small preference. A/C offer slightly easier detail reading in the upper-left/interior foliage while keeping contrast against the dark main limbs. Dense clusters remain merged. |
| Canopy below | A = C > B | Moderate confidence in the slight lift over B; insufficient confidence to split A/C. Leaves left of the trunk and around smaller branches read a little more easily. Upper-right bundles still merge in every version. |
| Canopy edge | A = B > C | Low confidence; moving foliage complicates small differences. A/B slightly lift the central/lower leaf field. The central crown still reads as overlapping sheets of similar tone. |

The native material differences are visible enough for tentative preferences, but not large enough to change the whole-point quality rubric. Material plausibility stays **3/5**. Lighting/depth stays **3/5** at hill/hero and **2/5** below/at the canopy edge. Silhouette/coverage is **4/5** in these views; native static edge quality is **3/5**, cleaner than the direct Editor evidence. Temporal stability and performance are unscored. A static native image does not establish moving quality or a passing gameplay profile.

The main unresolved defect is the response of overlapping leaf planes and dense bundles: brighter tones do not yet produce convincing layered depth. Small branches embedded in the thickest foliage are still difficult to distinguish. No gross self-lit wash, bright silhouette halo or disappearing crown area is apparent. The shaded bark remains soft. The user's orange tree is preserved in the views where visible.

Do not call the canopy finished on this result or infer a conclusive best dose from the ties. Preserve the repaired edges. Further work should target leaf-plane/cluster response with native sun/shade/backlight inspection rather than increasing uniform brightness until the entire tree glows. Wind and camera motion still need separate scrutiny.

The official ARK courtyard reference on record and the official oasis screenshot remain more convincing overall, with stronger differentiated plant response, layering and environment integration. The oasis screenshot was viewed again during this review. These are recognizable games and different scenes/species under unmatched light; reference settings/hardware and promotional processing are unknown. This is an honest reference comparison, not a genuinely blind cross-game or performance comparison. ARK remains preferred overall; no AAA parity is established.

Sources: [official courtyard announcement](https://steamcommunity.com/games/2399830/announcements/detail/4174347361792746505), [courtyard image](https://clan.fastly.steamstatic.com/images/44719856/41798a1b8cae10f220da4e4c94becd5384c83a92.jpg), [official Scorched Earth store page](https://store.steampowered.com/app/2849450/ARK_Scorched_Earth_Ascended/). Exact oasis screenshot provenance is retained in `store-reference-provenance.json`.

**Disposition: small tuning preference; canopy quality target remains rejected.**
