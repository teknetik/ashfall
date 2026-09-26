# Threshold v2 — diagnosed defects and guarded repair

The two native rejection views are
`unity/evidence/reference-street/20260910/iteration-01b-native/cam_ground_trash.png`
and `iteration-first-person-field-threshold.png`. This revision addresses their
stretched side faces, repeated crack patches and incorrect glossy response while
preserving every existing geometry position, triangle index and walking height.

## Confirmed causes

1. **The exported UV buffer is the old cube layout.** V1 `uv_shade` creates and
   writes `UV0 two metre mineral scale`, but `export` subsequently reads
   `me.uv_layers.active` without explicitly selecting the new layer. The saved V1
   JSON remains in approximately 0–1 UV space for each entire threshold, despite
   world coordinates requiring multiple two-metre tiles. Each primitive retains
   its repeated normalized cube patch; long/thin faces stretch that patch. V2
   computes the intended UV buffer explicitly and assigns/exports that exact
   buffer. It never reads an unspecified active layer.
2. **The roughness was lost during packing.** The source roughness JPEG is
   4096×4096, with red values 176–255, mean roughness 0.907871. V1 loads that JPEG,
   writes smoothness into the same texture's alpha, then encodes it. The resulting
   `MetalSmooth.png` is PNG color type **2 (RGB)**. All decoded alpha values are
   255; all RGB values are zero. Installed URP Lit uses this alpha multiplied by
   `_Smoothness=1`, making the stones fully smooth despite their rough source.
   V2 reads the source JPEG but allocates a **separate RGBA32 output**, packs
   `R/G/B=0, A=255-source roughness R`, and checks every encoded pixel. Expected
   smoothness is 0–0.309804 rather than 1. No arbitrary smoothness multiplier,
   source-image editing or roughness remapping is introduced.
3. **Some tiny triangles have invalid corner shading normals.** The offline
   exported-buffer audit found 466 triangles whose average corner normal points
   behind the geometric face, totaling 0.000264 m² across all 36 parts. Individual
   corner checks identify 1,469 normals to correct. V2 replaces only corners whose
   dot product with their triangle's geometric normal is ≤0 with that face normal;
   it preserves every other normal. It does not claim these tiny cases explain
   the entire visible glare; the all-smooth packed map is a separate confirmed
   material defect.

## Chip and topology finding

All 36 exported parts have **zero open boundary edges** and no inconsistent
winding across ordinary two-face shared edges. The audit also records 36
overshared edges, mainly near the Boolean cuts; these are retained for inspection
and are not hidden by a claim of clean manifold topology. Edge tests use the
existing six-decimal exported positions and do not detect every possible overlap.

V1 deliberately cut irregular concave losses across front top/riser arrises. The
dark triangular recess visible near the trash camera is consistent with a closed
Boolean cut under the incorrect glossy shading; an actual open mesh hole is not
established by the exported topology. No filling or geometry deletion is justified
yet. Review that same recess with the corrected rough material in native sun,
shade and an oblique moving pass. Persistent bad geometry remains a rejection.

## Authoring and installation

`author_stone_thresholds_v2.py` uses the immutable V1 JSON geometry rather than
regenerating random stones. All 36 parts and 235,138 triangles retain exactly the
same positions and indices. The four assemblies still contain 18, 5, 4 and 25
connected stones respectively. Their collision tops and collider sources are
unchanged. UVs use the geometric face's dominant axis, world metres at two metres
per tile, a deterministic per-stone offset and a small rotation bounded by ±8°.
Scale never varies by stone. Metric projected-area checks prevent another
normalized/stretched export.

The script was staged and verified offline, then executed successfully through
the live Blender session by the agent owning Blender. It writes:

- `stone-thresholds-v2.blend` — source scene and dependencies, without overwriting
  another active main Blender file.
- `stone-threshold-meshes-v2.json` — exact retained geometry with explicit V2 UVs
  and the recorded corner-normal corrections.
- `stone-threshold-manifest-v2.json` — output hashes and per-part invariants.

Root installs the reviewed source with staged
`StoneThresholdDetailPassV2.cs` → `AthenHill.Editor.StoneThresholdDetailPassV2.Apply()`.
The helper has not been copied to Assets by this subtask. It requires the saved,
clean scene and fresh chunks, checks the 48-file V1/source contract and all 36
current mesh paths, and stream-compares V1/V2 geometry. New assets go under
`Art/ReferenceStreet/20260910/ThresholdsV2`. Three material variants retain the old
color/normal assets and tint while referencing the corrected packed map. The old
32-addition parent is disabled intact; the four existing threshold roots remain.
Original colliders, actor state, all source assets and material GUIDs are retained.

Installation saves a before-scene and collider/actor evidence under
`unity/evidence/reference-street/20260910/threshold-install-v2`, explicitly
rebuilds render chunks, and records after invariants. Existing output/evidence
causes a guard failure; inspect a partial attempt instead of retrying over it.

## Validation and limits

- Offline source processing passed exact position/index preservation, component
  counts, metric UV area checks and the targeted normal-correction assertions.
- The V2 helper compiled against installed Unity 6000.6 and current project
  assemblies with zero warnings and errors. No Unity call occurred in this task.
- Local installed URP `Shaders/LitInput.hlsl`, `SampleMetallicSpecGloss`, confirms
  packed map alpha is multiplied by `_Smoothness` when the albedo-alpha keyword is
  disabled. The V2 helper explicitly selects that path.
- Source buffers use double-precision calculations; native Unity float precision,
  tangents, compressed maps, actual lighting and moving appearance require the
  next native audition. The helper's successful compile is not native acceptance.

Detailed records: `threshold-v1-offline-defect-audit.json`,
`threshold-v2-offline-preview.json`, `threshold-v2-install-contract.json`,
`stone-threshold-manifest-v2.json`, and `threshold-v2-compiler-check.json`.
