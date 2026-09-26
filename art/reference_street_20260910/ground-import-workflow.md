# Ground detail candidate import — 10 September 2026

`GroundDetailPass.cs` is staged outside Unity's `Assets` directory. It was compiled
offline against the installed Unity 6000.6.0f1 assemblies and current game/Editor
assemblies, with no compiler errors. No Unity operation was executed by this
authoring task. The read-only source findings are in `ground-import-audit.json`.

The original retained exports contain 432 triangles for trash, 896 for scrap,
679 for crates and 1,619 for generators. The saved old prefab visual scale ratios
are respectively 1.215, 1.284, 1.071 and 1.488. The new candidate maps inspected
for trash, scrap and crates are all 4096 × 4096. These figures establish source
and import facts; they do not establish visual acceptance.

## Revision 2 helper changes

The staged helper now supports a different immutable source folder for each
family/revision. For a repaired candidate, use for example:

```csharp
GroundDetailPass.Prepare("crate", "v2", "meshy/ground-detail-20260910/crate-v2");
GroundDetailPass.DryRunSelected(new[] { "crate" }, "v2");
GroundDetailPass.AuditionSelected(new[] { "crate" }, "v2");
```

Relative source overrides resolve against the repository; absolute folders are
also accepted. Each revision saves `SourceContract.json` containing its actual
source folder and SHA-256 for the FBX and four PBR input maps. Preparation, dry
run and installation verify both the retained input and copied Unity file against
that contract. Editing an old source, redirecting a prepared revision, or replacing
its imported file requires a new revision. All existing two-argument `Prepare`
calls remain valid and use the original family folder.

`DryRunSelected`, `AuditionSelected` and `RolloutSelected` operate only on named
families. They can therefore progress reviewed scrap/crates while trash is being
regenerated. Selected-family evidence names include the selected family names;
all-family wrappers retain their previous names. Rollout requires an audition
record for every selected family at that revision, plus the actual independent
native review file. A family already auditioned at a revision cannot silently
receive a second audition at a different placement.

```csharp
GroundDetailPass.RolloutSelected(new[] { "scrap", "crate" }, "v2", absoluteReviewPath);
```

For a candidate already prepared by the first helper, explicitly call
`BindExistingSourceContract(family, revision, sourceFolderOverride)` before using
the updated checks. This verifies all five existing Unity input copies against
the specified original source and writes only the new provenance contract; it
does not overwrite a prefab or infer acceptance.

The first trash candidate is rejected at source review: the saved topology audit
records 19,849 non-manifold edges including 14,649 over-shared edges, and source
views show holes. High triangle counts did not make it acceptable. Scrap/crate
repairs and regenerated trash must each pass their own source and native reviews.
The helper does not convert topology statistics into a visual approval.

## Explicit operations

After inspecting the live Unity instance and finishing any work that must survive
an assembly reload, copy the staged helper into `Assets/AthenHill/Editor`. Execute
each operation separately through the working Unity MCP and inspect its result.

1. Inspect the Meshy candidate's whole geometry and close views in the retained
   Blender source review. The helper requires
   `meshy/ground-detail-20260910/{family}/model.fbx` and
   `model_textures/{base_color,normal,metallic,roughness}.png`.
2. Call `GroundDetailPass.Prepare("trash", "v1")`, then the same method for `scrap`
   and `crate`. `PrepareAll("v1")` is available if all three source reviews pass.
   Each operation creates new assets only, using a temporary preview scene. It
   refuses to overwrite prepared materials or prefabs. Partial failed preparation
   remains recoverable; inspect it and use a new revision when its inputs change.
3. Call `GroundDetailPass.DryRun("v1", "dry-run-v1.json")`. This changes no scene
   data. It checks source hashes, original FBX mesh references, UV0, tangent and
   submesh completeness, full texture resolution, color spaces, shader bindings,
   mips, anisotropic filtering and emission. Read its candidate dimensions and
   selected street placements before auditioning.
4. Call `GroundDetailPass.AuditionAll("v1")` only after source and fit review.
   It changes one nearest existing street instance per family. New visuals are
   ordinary prefab children. The old source renderers are disabled and retained;
   their GameObjects and any collider components remain untouched. A single
   scale factor fits each candidate inside the old visual envelope and existing
   root BoxCollider where present. Root placements, rotations and scales remain
   fixed. The helper guards every collider and all four ambient actor routes,
   explicitly rebuilds render chunks, saves the scene and writes dated evidence.
5. Build and capture native sun/shade, player-height closeups and a moving route.
   Inspect geometry, contact, paper/cloth/dust metallic masks and normal direction.
   The prepared normal convention is tangent-space +Y, with no green inversion.
   Imported emission remains off. The helper's scalar-mask statistics do not
   substitute for checking what material each mask covers.
6. Only after independent native acceptance of these candidates, call
   `GroundDetailPass.RolloutReviewed("v1", absoluteReviewPath)`. It records the
   review path and hash and requires that this revision has been auditioned. The
   caller must actually read the independent decision; a file's existence is
   explicitly not an acceptance decision. Remaining original instances receive
   the same reviewed prefab. Run the affected native routes and representative
   timing again before accepting the rollout.

Reports and recovery scenes are written under
`unity/evidence/reference-street/20260910/ground-detail`. Existing reports cannot
be overwritten. Preparation produces separate dated assets under
`Assets/AthenHill/Art/Imported/Meshy/GroundDetail/20260910/{family}/{revision}`.
No old prefab, source download, generator, gameplay script or city layout is
rewritten. The full downloaded unreduced GLBs remain in the external source
record, and every imported candidate triangle remains in the near prefab.

This first audition deliberately has no fabricated LOD. Evaluate the actual
source at player height and measure native cost before authoring a lower variant.
The current static chunk builder does not preserve per-instance LODGroups, so
adding one to a source prefab alone would not create functioning runtime LODs.

Before chunk rebuild, a failed scene invariant rolls back the scoped source
changes. A failure during chunk rebuild leaves the editable source and recovery
scene available for deliberate repair; Unity Undo cannot restore deleted chunk
assets. Do not automatically reload a scene and discard unrelated work.
