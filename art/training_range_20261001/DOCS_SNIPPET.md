# Docs snippet — Warden training range (1 Oct 2026)

## For unity/EDITING.md

### Warden training range (Outer Berms, 1 Oct 2026)

Scene root **Outer Berms/Warden training range** (groups: Firing point, Range officer, Range orders, Range flags,
Distance posts, Night lighting, Machine lane, Service apron, Backstop, Decals). Sources and run order:
`art/training_range_20261001/README.md`. Editor: `TrainingRangePass` (build: textures, URP materials, prefabs in
`Prefabs/TrainingRange/`, incl. `TR_TrainingDrone` and the baked `TR_WorkerDroidShell`) and `TrainingRangeInstall`
(one-time install, verify, editor captures). Batch:
`-executeMethod AthenHill.Editor.TrainingRangePass.RunBatch --steps build|install|verify|toggle:on|off` (with
`-nographics`) or `capture:<dir>:cam_a+cam_b` (graphics, at most six cameras per run).

- Move, add or delete the kit instances in the Scene view; none of them is a render-chunk source. Keep everything
  with a collider out of the tutorial's lines of fire (the eye at the firing line, `cam_checkpoint_plate1-3`, to each
  plate's aim point) and out of the plates' 1 m fall zone; `verify` reports `shotsBlocked`.
- The earth bank (`Backstop/Backstop earth bank`, mesh `Art/TrainingRange/Structures/TR_BermEarth.asset`) is generated
  on the Berms ground by the install from `layout.json` (`berm`); it uses the Berms Ground material and has its own
  mesh collider. The timber revetment and the cable runs are world-space assets placed at their recorded origin
  (`authored-assets.json`); re-author them in Blender rather than moving them.
- Never move the plates, the range reset station, the briefing board, Ossa/Rell, the arms locker, encounters,
  respawn or the `checkpoint_*` landmarks. The retired range clutter (old firing bench and sandbags, the flag in front
  of the line, the plates' floating "PLATE 0n" text, rocks and shrubs on the range floor) is inactive in place; the
  install record lists every object (`unity/evidence/training-range/20261001/install.json`).
- Night lights are on the Ward light clock (`CityLightCircuit` practical + night-only lists); the red "range live" lamp
  is practical only. Rollback: deactivate the root (the retired objects can be reactivated from the record) or restore
  `unity/evidence/training-range/20261001/rollback/scene-before-training-range.unity`.
- Review cameras: scene root `Training range review cameras` (`cam_range_*`). Cost (A/B, native): +0.7 ms at the
  range's own wide view (210–270 fps there), +0.17 ms looking out of the West Gate, nothing at `cam_hill`.

## For the AGENTS.md baseline table

| Warden training range | 1 Oct 2026 (`art/training_range_20261001`, scene root **Outer Berms/Warden training range**): the range beyond the West Gate rebuilt as a working Warden range — three timber firing bays at the tutorial's firing line, range officer's table and RANGE ORDERS board, distance posts, a timber-revetted earth backstop with impact scars and a crest flag, a machine lane (tyre run, cover barricades, tethered training drone, stripped worker droid in a target frame) and a robot service apron (drone docks under a shade shelter, repair bench, compressor, welding cart, generator), lights on the light clock. Plates, reset station, Wardens, locker, encounters and landmarks unchanged; replaced clutter inactive. Range tutorial check 10/10 and city loop pass. Not yet accepted by Carl. |
