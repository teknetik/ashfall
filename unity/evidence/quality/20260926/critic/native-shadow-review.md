# Native shadow comparison — 26 September 2026

**Judgment: prefer 96 m / four cascades for continued qualification. Reject 18 m / one cascade as the district's high-quality shadow profile because prominent visible structures lose their expected cast shadows. This is a static rendering preference, not gameplay, performance, or AAA acceptance.**

This was a labels-known review. I inspected all 18 full images in `../native-shadow-verified-viewport/`, comparing the nine named camera pairs. It was not blind. The padded-leaf candidates reviewed separately are not the foliage shown in these native pairs; the remaining pale leaf appearance must not be attributed to a failed padded-texture integration from this evidence.

## Evidence and limits

- All 18 PNG headers and all 18 per-frame snapshots report **1920 × 1080**. The HUD and scene occupy the full viewport; the earlier window-strip/clipping problem is absent in these captures.
- `shadow-audition.json` records the matching cameras, 18 m / one cascade and 96 m / four cascades, fixed noon, 4096 shadow resolution, 100% render scale, MSAA 4, post-processing, OpenGLCore on RTX 3060 (12 GB) / i9-10850K, Unity 6000.6.0f1, NVIDIA 610.57.04, nine actors, uncapped and VSync off.
- Its top-level stored video/environment dimensions still say **1896 × 1040**. Those fields are stale relative to the actual frame snapshots and PNGs; annotate/correct them before using the report as an unambiguous display-settings record. This does not change the observed image dimensions.
- Actors, foliage wind and particles continue animating between frames. Poses and some actor positions differ. These are not controlled stationary-character comparisons and cannot establish foot-contact softness or temporal stability. Single-frame FPS values are not a representative performance result. No traversal or frame-time acceptance is implied.

## Camera findings

| Camera | Preference | Specific observation |
| --- | --- | --- |
| `cam_whompah` | 96 m, strong | The ring's recognizable full cast silhouette appears across the paving at right. At 18 m most of it is absent beyond the base region. This is the clearest isolated demonstration of the distance defect. Ring geometry/open aperture and nearby surface detail remain readable. |
| `cam_hill` | 96 m, strong | The hero crown acquires shaded interior depth; tree and building shadows ground the plaza. The 18 m view leaves a largely white, flat crown and broad ungrounded space. Both retain the user's orange tree. |
| `cam_avenue` | 96 m, strong | Tree interior, street/terrace shade and distant structural shadows read more coherently. The short profile makes the crown and farther street too evenly lit. |
| `cam_gate` | 96 m, strong | The arch and lamp cast useful shadows across the opening and paving. Near wall/paving texture detail survives. Small dark surface speckles are present in both frames; this pair does not substantiate a new 96 m contact-acne defect. |
| `cam_grid` | 96 m | The long hall/building shadow extends coherently across the ground. Nearby terminal/base/bolt and bollard details remain visible; no gross near-shadow detail collapse is evident. |
| `cam_p1_tree_roots` | 96 m, modest | Nearby bark and dappled ground shadow are broadly similar; distant hall recess/overhang and building shading become more credible. No new large striped acne pattern or conspicuously detached root shadow is visible. |
| `cam_hero` | No decisive near-view winner | Fine branch/leaf coverage is comparable. Some shading changes, but neither profile resolves the pale leaf material. |
| `cam_tree_canopy_below` | No decisive near-view winner | Local trunk/self-shadow differences are small relative to the persistent foliage-material problem. No severe new large block/band artifact is apparent. |
| `cam_tree_canopy_edge` | No decisive near-view winner | Crown shape and small-leaf coverage survive. Subtle shade changes do not establish a near-detail improvement or a severe resolution regression. |

**Best presentation pair:** `cam_whompah` for explaining exactly what disappears; `cam_hill` for the overall environmental-depth gain. Show both full frames at equal scale. Do not substitute the near canopy pairs as evidence that the foliage material is finished.

## Resolution, contact and remaining rejection points

The increased distance does not produce a clearly disqualifying static shadow-resolution regression in these images. I do not see newly introduced severe geometric banding, obvious broad contact-acne stripes, or wholesale loss of nearby structural shadow detail. That is a bounded observation about these images, not proof that such artifacts cannot occur elsewhere or during movement.

**Near-character softness remains unqualified.** Different actor poses/positions and limited close foot coverage prevent a fair conclusion. A fixed-pose, player-height body/feet pair under the same light is the useful next shadow-specific still. A moving native pass must also inspect cascade transitions, foliage shimmer, shadow crawling and contact changes. Measure that pass separately; the attractive wide frame alone cannot justify its cost.

Both profiles still fail the requested finished art standard. The pale canopy lacks convincing living-leaf color and differentiated response. Player-height roots expose stiff triangular grass, soft bark, and an abrupt artificial soil-to-paving boundary. Broader frames retain repeated ground/facade motifs and underdeveloped ground integration. These are visible art defects, not evidence of a regression caused by longer shadows.

For lighting/depth alone, the representative hill/avenue/ring views move from roughly **2/5 to 3/5**. Near-tree material detail remains roughly **2/5** in this native set. Native MSAA resolves the fine edges more smoothly than the earlier direct Editor captures; their earlier edge score cannot automatically be applied here. Temporal stability and near-character contact quality are **not scored** from these stills. No applicable hero-view category is awarded a 5.

## Actual ARK comparison

The official Scorched Earth courtyard reference still looks substantially more finished: layered sandstone construction, integrated ground debris, richer vegetation response and readable interior plant shading. The 96 m setting closes an obvious shadow-coverage gap but does not reverse that overall preference. Identities and subject differences are recognizable, so this is not a genuinely blind cross-game comparison. Reference hardware, quality settings, lens and promotional processing are unknown; no cross-game performance or physics inference is valid.

- Official Studio Wildcard source: https://steamcommunity.com/games/2399830/announcements/detail/4174347361792746505
- Courtyard reference: https://clan.fastly.steamstatic.com/images/44719856/41798a1b8cae10f220da4e4c94becd5384c83a92.jpg
- Local inspected reference: `ark-scorched-earth-official-courtyard.jpg`; additional official foliage reference/provenance: `store-reference-provenance.json`.

**Next focused work:** retain the long-shadow candidate for native motion/cost checks while iterating leaf shade readability independently. Do not repair pale leaves by reducing useful environmental shadows. Preserve the existing tree geometry and orange tree during the material audition.
