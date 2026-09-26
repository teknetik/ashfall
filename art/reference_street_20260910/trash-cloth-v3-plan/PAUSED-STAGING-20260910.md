# Paused at user request — 10 September 2026

No live Blender, Unity, native input or Assets operations were performed by this subagent. The user requested a safe stop before the new sack selection candidate was executed.

Saved staging:

- `../stage_trash_sack_selection_v1.py`: staged live-Blender entry. Explicit globals are `TRASH_SELECTION_REVISION='selection-v1'` and `RUN_TRASH_SACK_SELECTION=True`. Python syntax passes. The raw FBX parser and contour classification were exercised offline against the actual retained runtime FBX. The Blender importer, corner-normal digest, material assignment, rendering and library save calls remain unexecuted and may require correction at their first actual run. Do not describe it as live-validated.
- `selection-contours-v1.json`: deliberately traced top/front/side candidate boundaries, six explicit jug/can/cardboard exclusions, actual projection-file hashes and interpretation limits. The left side envelope is partly inferred because it is occluded; rolled mouths and contact/underside folds remain incomplete. This is a candidate, not final semantic truth.
- Offline raw-face selection has2548 left and1405 central triangles, with393/403 uncertain edge triangles. Both known sack seed triangles are fully selected; the three known jug/can seeds are excluded. This does not prove zero leakage on unreviewed surfaces. No image mask or runtime mesh has been exported.

The source has180,000 triangles and86,482 vertices. Exactly35 vertex-index triangle sets occur twice. Each duplicate pair has opposite winding and different corner UVs; none is a zero-area triangle. The35 groups explain the count difference to the recorded179,965-triangle Blender import, but their actual surviving winding/UV member must be verified live. The staged script matches every imported face against the complete unique raw triangle roster and an exact source winding/UV alternative before recording imported face IDs. It does not delete, remesh or alter source geometry.

On a later resumed task, the script is intended to import a fresh derivative in a separate scene, preserve its geometry/UV/corner-normal digest, label provisional faces and render actual Blender front/back/top/right/left/underside coverage plus matching original-albedo views. It writes separate candidate face rosters and correspondence evidence, then a standalone source-only .blend. The current scene is restored at cleanup. No existing source scene, material, FBX, original image or Unity asset is overwritten.

Review those native Blender coverage frames first. Reject cloth coverage on jug/can/cardboard/ground and refine incomplete fabric boundaries. Only after accepted face rosters should a later task inspect UV overlap/gutters and author a DetailMask. No final cloth mask, material correction, native acceptance or quality claim exists yet.
