# Ward source/runtime audit — 8 September 2026

This freezes the saved Unity scene at **20:07:39 UTC**, before the broader quality
pass. Scene SHA-256: `3c18885c33cce5d79ce65923ad8e3aba90760f494c08df02ababe69f977ede52`.
Later changes need new evidence. **Accounting is complete for the snapshot;
every-asset visual review and AAA acceptance are not complete.**

The [full unique-asset ledger](../unity/evidence/quality/20260908/audit/unique-assets.json)
records 2,112 unique mesh records across 2,377 renderer records, including inactive
sources and generated chunks. Intended active content contains **1,027 unique
meshes / 1,169 instances / 1,642,388 triangles / 1,319,684 vertices**. There are
59 derived chunk meshes with 1,346,502 triangles, counted separately, nine actors,
60 materials and no LODGroups. These are source counts, not camera-visible geometry
or multipass submitted triangles. [Summary and identity](../unity/evidence/quality/20260908/audit/summary.json).

Read-only Unity MCP queries exported the [current scene inventory](../unity/evidence/quality/20260908/audit/current-scene-audit.json)
and [12 FBX runtime vertex buffers plus material properties](../unity/evidence/quality/20260908/audit/runtime-buffers-and-materials.json).
The scene stayed clean. Runtime geometry buffers were inspected for 1,023 active
unique meshes; four built-in primitives remain count/attribute-only. Retained
source/export comparisons cover 1,018 meshes. The nine remaining comparisons are
four built-in primitives, four generated hill-grass assets and the traveler whose
original delivery is FBX only. Its actual Unity buffer is included.

All compared active assets retain 100% of their retained source triangle counts.
[Meshy comparisons](../unity/evidence/quality/20260908/audit/meshy-comparisons.json)
and [original exports](../unity/evidence/quality/20260908/audit/source-exports.json)
record vertex splitting separately; FBX vertex-count changes alone do not prove
silhouette loss. The `world.glb` comparison uses its retained import buffer, not
independently reconstructed historical authoring. Zero decoder failures occurred.

## Concrete repair findings

- [Ten active building briefs](../unity/evidence/quality/20260908/audit/building-repair-briefs.json)
  preserve exact paths, bounds, scales and gameplay constraints. Seven Relay shop
  placements still share a 6,208-triangle shell with nonuniform fits. Hall proportions
  are repaired, but its native door is folded/melted and baked lettering smeared.
  Basic General has weak support/cloth/sign detail. Finery construction is better,
  but identical rust drips repeat across doors/shutters and its rear remains plain.
- [Seven rejected candidate briefs](../unity/evidence/quality/20260908/audit/rejected-building-briefs.json)
  distinguish the inactive alternatives from the game. Both retained obliques were
  inspected per model in the [labelled contact sheet](../unity/evidence/quality/20260908/audit/rejected-candidates-contact.png).
  Faceted/thin roofs, fused supports and soft construction remain; none is accepted
  for reactivation. Original 2K maps and source shapes are retained.
- [All nine actor briefs](../unity/evidence/quality/20260908/audit/character-repair-briefs.json)
  record assignments, maps and shadows. Vex retains 38,071 triangles but still has
  soft armour, a featureless black visor and static pose. Player albedo is also the
  emissive texture with factor 1, and metallic factor 1 has no mask. Player, three
  travelers, Mira, Torr and Linn cast no shadows. The latter guards have albedo only
  and a green-grey tint; travelers have no original normal map available. These are
  scoped material/import repairs, separate from source anatomy and animation work.
- Tree root/crown native views show bulbous roots, stretched bark, sparse thick
  branching and separated leaf masses. Root-flare UV anisotropy exceeds 4 on 25.2%
  of surface, with p95 17.85. Twelve secondary branches exceed 4 on 82.7–98.5% of
  surface. More texture resolution cannot fix that mapping or silhouette.

## Texture, attribute and cost accounting

[Texture imports](../unity/evidence/quality/20260908/audit/texture-imports.json)
record actual imported dimensions, source dimensions, hashes and importer settings.
Traveler albedo is 4096² → 2048²; Karaveen paper 1086×1448 → 1024²; Ward cloth
724×2172 → 512×2048. Several 1254² wall, paving, metal, canvas and terrain maps round
to 1024². Originals remain intact. Recovery should touch only measured active
importers, preserving correct normal color spaces, mip settings and UI assets.

Every active mesh has normals and UV0; 358 lack tangents: 343 legacy world meshes,
eight basin meshes, four hill-grass meshes, shared guard, player and hill stones.
Missing tangents matter where shaders need a tangent basis; projected/unlit shaders
may not. All decoded supplied normals are finite, nonzero and unit within tolerance.
Eight FBX meshes contain small numbers of tangents outside the orthogonality
tolerance; regenerate during scoped repairs if their material uses tangent normals.

UV density records are geometry diagnostics using saved scale and texture tiling.
Custom shader projection, UV overlap, compression, active mip and on-screen sampling
can change sharpness. Active mip, resident texture memory, UV-overlap packing and
final shader output are **not measured**. No new performance qualification is claimed.

[Family costs](../unity/evidence/quality/20260908/audit/family-costs.json) expose
misallocated geometry: courtyard paving 427,008 triangles, 45 tiny gravel chips
138,240 (**3,072 each**), platform 89,088, facade 76,960, vegetation 76,752 and north
stairs 73,728. The root flare is 199,200. Keep detailed originals; create reviewed
runtime variants or remove ineffective decoration when useful. This is not a new
arbitrary polygon cap or a reason to reduce hero detail without visual comparison.

## Coverage and reproduction

This task directly reviewed retained native frames for Vex, Field Supply frontage,
hall doorway, roots, Basic General oblique, Finery doorway, district crown and
mission terminals, plus two source obliques for each rejected shop. It did not
individually review every stone, branch, roof underside or building placement.
[Seven parcel-specific camera groups](../unity/evidence/quality/20260908/audit/capture-requests.json)
propose front/door/back/side/roof evidence; root must check occlusion before capture.
Actor close-ups/motion, wireframes and more ground-dressing views remain necessary.
No new visual acceptance or TODO completion was inferred from counts.

Reproduce frozen numeric reports with NumPy and Pillow:

```sh
python unity/evidence/quality/20260908/audit/audit_assets.py
python unity/evidence/quality/20260908/audit/repair_briefs.py
```

The accompanying `.cs.txt` files preserve read-only Unity export queries. Later
integrations must export a new dated snapshot instead of relabelling this baseline.
The audit did not mutate the scene, meshes, materials, importers or gameplay code.
