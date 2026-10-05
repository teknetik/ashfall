# Main character: shoulder and clothing polish — 5 October 2026

Request: improve the basic character design and bad animation, particularly shoulders rising and falling while walking.

The saved MPFB player, GUID, 54-bone rest rig, skin UVs, equipment mounts, body proportions and gameplay tuning are retained. The existing export at `unity/AthenHill/Assets/AthenHill/Art/Imported/Meshy/colonist.glb` is replaced by a reviewed candidate built from the retained `art/tutorial_set_20261002/blender/mpfb/final_m0.25.blend`. No city rebuild or runtime pose override.

## Diagnosis and changes

The former walk's clavicle directions differed by 37–40 degrees from idle; run differed by 27–33 degrees. Applying those clips to the already lowered MPFB clavicles collapsed the shoulders when entering locomotion. The walking sole also floated about 5–6 cm above the idle sole. These faults were reproduced on the original source and the current native build.

`author_polish.py` retains the existing arm swings but anchors the shoulder attachment to the relaxed idle, retaining a small amount of source clavicle motion. It lowers the retargeted gait to the idle ground level, reduces excess pelvis bounce and sway, and uses two-bone leg constraints to preserve foot placements. A short quaternion blend closes the original loop seam. No movement speed or camera changes. Idle, weapon and jump clips are retained.

The pinched, high collar is lowered and softened on the suit mesh. Fabric is non-metallic, roughness 0.84, with the old coarse normal bake reduced to 0.42 strength. `author_belt.py` adds a fitted cloth utility belt, small canvas pockets, bound seams and bronze catches; this is clothing detail, not new inventory capacity or equipment. Its woven tile is original deterministic procedural artwork. Original skin/face/hair and clothing maps keep their resolution.

The body grows from 71,867 to 76,043 triangles, with seven material slots (formerly five). The new export is 68.8 MB, versus 70.5 MB before. Full source detail and the previous export remain recoverable.

## Reproduction and recovery

1. In Blender 5.2, open the original `final_m0.25.blend` in a separate call, then execute `author_polish.py`. The separate call is necessary because opening a `.blend` invalidates the live MCP execution context. The script writes `player_polish.blend`, `colonist_polish.glb`, `authoring.json` and `field_canvas.png` here.
2. Inspect the candidate in Blender, then copy `colonist_polish.glb` onto the existing Unity colonist asset, leaving its `.meta` alone. The prefab and saved scene inherit the change; no full character installer is needed.
3. Run `AthenHill.Editor.CharacterPolish20261005.RunBatch -nographics` using the memory-capped Unity wrapper. Add `--capture -force-glcore` without `-nographics` for the six small editor views. This helper does not save or reconstruct the scene. `MainCharacterInstall.Check` verifies the current integration.
4. `audit_gltf.py` compares the retained and candidate animation and asserts unchanged rest transforms and inverse bind matrices. `PlayerLocomotionTests` guards the idle-to-gait shoulder relationship and loop closure.
5. Restore `rollback/colonist.glb` onto the same Unity asset to undo this visual/animation pass, then rebuild. No scene restoration is required. `rollback/AthenHill.unity` and `MeshyPlayer.before.prefab` capture the pre-pass working state for recovery only; do not overwrite subsequent unrelated changes with them.

Blender was initially disconnected; a private memory-capped live instance was started and used through MCP, then closed before Unity. Unity MCP reported no connected editor, so the established capped batch editor performed import, inspection and rendering. No dependency or graphics API changes.

## Verification

`motion-comparison.json` records the measured source comparison. Walk clavicle deviation from idle is now at most 0.62 degrees and run at most 2.41 degrees. Walk pelvis vertical excursion falls from 6.64 to 4.50 cm; run from 6.32 to 5.18 cm. The rest nodes and bind matrices are numerically unchanged.

`unity/integration-check.json`: PASS, 54 bones, no missing references, all pistol/rifle hold paths bind, 1.800 m idle height, soles at controller origin. Unity's 33-sample gait audit records residual sole penetration up to 11.5 mm walking / 18.3 mm running between baked keys. This is a remaining animation limitation, not zero ground error.

Native evidence and final test results: [character review](../../unity/evidence/character-polish/20261005/README.md). The rebuilt Linux player passed the city loop (29 checks), range tutorial (10 checks) and rifle quest (38 checks, including first-person pistol/rifle and equipment attachment). Matched front/rear walk, run and jump recordings show the corrected shoulder attachment in play. The comparison video is `unity/evidence/character-polish/20261005/shoulders-before-after.mp4`.

The short alternating native walk samples show no distinguishable cost increase: median changes of -0.37 ms and +0.05 ms. Both versions run below the 60 FPS target in this view (about 41–43 FPS); this does not qualify overall performance. The first build attempt exceeded its memory cap; a second build with reduced importer/job worker concurrency succeeded without changing assets or rendering settings. Build identity, measurements and remaining visual defects are recorded with the evidence.

This is a focused improvement to the existing character, not a new high-end character production or an assertion of GTA6 parity. Face/hair close-up quality, source garment noise and the underlying walk/run performance remain further art-direction work. Acceptance is pending Carl's review.

Edit Mode: **290/290 passed** (`editmode.xml`), including the added shoulder relationship and loop-seam regression.
