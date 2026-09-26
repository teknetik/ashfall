# Proposed saved gate review cameras

`plan.json` contains three prospective disabled cameras. No scene changes or camera creation have been performed. The placements derive from the actual saved paving and gate geometry in `unity/evidence/quality/20260926/ground-audit`, with the authored noon light profile.

- **Threshold:** `(41.5,1.65,-0.7)` → `(47.6,1.05,0)`, vertical FOV 55°. The camera stands just inside the candidate patch's city approach and frames the opening plus pier contacts.
- **Paving close-up:** `(44.5,1.65,0)` → `(45.2,0.02,0.8)`, FOV 50°. This keeps a human eye height while looking down at the phase-aligned stone/joint texture.
- **Shaded pier:** `(44.3,1.65,-3.7)` → `(46.32,0.12,-3.2)`, FOV 50°. It addresses the negative-Z pier's city-facing foot. At hour 12, light travels toward −X/−Z; the city's −X face should therefore be shaded. A ray check and native image must confirm the actual mesh contact and shade.

Keep GameObjects active for named lookup, Camera components disabled, no AudioListener, no MainCamera tag, no FollowCamera or input components. Match existing fixed-view rendering configuration, aspect 16:9, near clip 0.08 and far clip 250. Adding cameras does not alter geometry or render-chunk membership; the resulting scene must remain buildable with its existing source fingerprint.

Before installation, run the planned read-only camera/path overlap and target/shade ray checks. The full geometric camera plans are hypotheses until those checks and native frame inspection succeed. When installation is explicitly handed over, create only missing named cameras, preserve their stable scene IDs on later tuning, save the existing scene and build a new native baseline **before changing paving materials or geometry**.

The included six-second pass commands have offsets of 1.2 m, 0.7 m and 0.8 m. These fit `NativeAssetReview`'s 4 m travel/3–30 s limits and keep the target away from the path. They are future diagnostic asset-camera passes, not player movement. Start them only with explicit mailbox ownership; poll `reviewAssetState` after completion, preserve overlap counts and restore `reviewReset` afterward. Do not run them during performance sampling. Match lighting, lens, settings, HUD policy and resolution across before/after captures.

## Read-only placement result

The probe completed against the clean saved scene without creating cameras. All 13 positions along each proposed path cleared a 0.20 m sphere test. The close-up ray reached `COL_Ground` at `(45.2086,0,0.8098)`. The pier ray first reached the accepted Meshy gate collider at `(46.3330,0.1101,-3.1968)`, normal `(-0.9787,-0.0448,0.2004)`, which turns away from the noon sun (normal dot toward-sun ≈ −0.390). The ground shade probe just beside that foot found no occluder; do not call the neighboring paving shaded without native evidence. The camera appropriately targets the shaded-facing pier surface, with native lighting confirmation still required. No proposed camera name already exists.
