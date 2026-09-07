# U2 first playable slice — 7 September 2026

PASS on the saved/reopened Unity scene. The user can edit the controller, camera,
input asset, player prefab and landmark objects in the engine.

- Real X11 W keyboard input, with deterministic camera headings, walked the complete source route: West Gate → Hill Tree → Ring Gate → Lattice Jack. No teleports were used between route checkpoints. Reports include feet position and grounded state for every stop.
- A second route after reopening traversed both shop porches and shallow interiors, then both West Gate tunnels. All checkpoints grounded within 0.15 m of expected height.
- Walk measured 3.40004 m/s, run 5.99991 m/s. Authored animation playback was 2.2620× and 1.6618× respectively, matching the source stride calibration. Actual motion captures and clip-state snapshots saved.
- Camera sphere sweep checked at four headings each at gate, both shops and hill: 16/16 camera positions clear of world collision.
- Actual 1920×1080 cam_hill render saved after reaching the hill in the traversal test; this final pose used a diagnostic teleport for screenshot setup, distinct from the keyboard route evidence.
- Ordinary saved Player GameObject, CharacterController, visual prefab child, FollowCamera, Controls.inputactions and Landmarks. No runtime city generation.

Still open: full NPC/shop/travel/UI loop, audio, batching and 1080p standalone performance, material/lighting refinement, final visual reference scoring and Linux build qualification. The editor FPS observed in the smaller Game View is not the final performance gate.
