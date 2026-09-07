# Supplied Meshy player

The saved AthenHill Unity scene now uses **MeshyPlayer**. Open the scene and press
Play to try WASD and Shift. The prior PlayerCandidate prefab and source asset are
retained. NPCs, movement, collision, camera controls and gameplay scripts are unchanged.

Source files are the three user-supplied GLBs in `meshy/mpc/`: Character_output,
Walking_withSkin and Running_withSkin. `tools/prepare_meshy.py` combines their clips
into `Assets/AthenHill/Art/Imported/Meshy/colonist.glb` with one shared mesh/texture
set, preserving the source files. This imports as legacy Animation to use the
existing ActorAnimation component. No external assets or generation services used.

The model has 10,391 triangles, 24 bones, one material and one embedded texture.
The runtime GLB is 27.1 MB, so texture size is a future optimization opportunity.
The standing animation is 1.670 m tall; the prefab normalizes it to 1.8 m with the
soles at the controller origin. The bind-pose bounds are different and must not be
used to choose the height or floor offset. Walking and running are already in place;
controller movement remains authoritative. Nominal animation speeds are 1.6 and
3.5 m/s, exposed on the prefab for gait tuning.

To reproduce after preparing the GLB, use **Athen Hill → Characters → Use supplied
Meshy player**. The helper updates the MeshyPlayer prefab and replaces the current
player visual in the open scene. It preserves the controller, spawn and footsteps.
The source standing export has one frame: idle and talk use that static pose.
For future character exports, include animated idle, walk, run and optionally talk,
with the same skeleton and in-place locomotion clips.

## Verification — 7 September 2026

- Unity compilation and Console: no errors.
- Real keyboard gate → west stairs → Hill Tree traversal passed, grounded at each stop.
- Real keyboard idle → walk → run → idle transitions passed; measured speeds 0,
  3.400 and 6.000 m/s, with advancing animation times and grounded controller.
- Sampled skinned standing geometry: 1.800000 m height, soles within 0.000001 m of
  controller feet. Controller retains its existing small floor clearance.
- Inspected 1080p idle/walk/run screenshots. No missing textures or broken rig.
- Focused Editor checks reported 218–365 fps, 71–75 draw calls and 210k–222k
  triangles. These are local Editor observations, not a fresh standalone/laptop
  performance qualification. Earlier unfocused/shared Editor samples were throttled.

Evidence is in `evidence/meshy/`; `tools/check_meshy_player.py` repeats the live
keyboard animation checks using the local MCP and X11 input. The gate-to-hill
route uses the existing `tools/walk_route.py`.

The historical U5 release evidence predates this character. The later Ward Guard
import rebuilt both Linux executables with MeshyPlayer and verified native
movement and the city loop; see [the rebuild record](../docs/model-import.md).
