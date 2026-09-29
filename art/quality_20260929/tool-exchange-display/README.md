# Tool Exchange - stocked display and shutter hardware (task t_3751e0fd, 29 Sep 2026)

Status: **source-render reviewed only.** Nothing here is installed in Unity, native-verified or accepted. Blender/Cycles renders are
source evidence, not the game's render. Unity integration, collision/interaction checks, shade readability and frame time belong to
`game-dev`. No scene, prefab or Unity asset was touched; the only files written are under `art/quality_20260929/tool-exchange-display/`.

No Meshy task was run and **no Meshy credits were spent**. Everything is original geometry authored in Blender 5.2.1 with
procedural numpy PBR maps (project original, no third-party imagery, no generative output, no lettering anywhere).

## Scope

Only the street-facing display window (behind the existing glazing and mullion) and the closed rolling-shutter surround of Tool Exchange
revision 04. Roof, clerestory, sign, awning, masonry, other shops, colliders, Vex and the door are untouched. The current scene still
holds the revision-04 prefab at Unity (-20.6, 0.5, 9.0), yaw 90, scale 1 (`installed-tool_exchange.json`), so no constraint was needed.
Shop-front geometry was read from the preserved source `art/quality_20260909/relay-family/store-variants-04/tool_exchange/source.blend`
(sha256 3858a0f2..., opened read-only in memory, never saved over).

## Key finding for the integrator

The "black empty display" is not only missing props. Revision 04 glazes the opening with two **opaque** near-black panes
(`WardGlass`, base colour 0.024/0.045/0.048, `_Surface 0`, `_ZWrite 1`) in front of a near-black recess plane, so anything placed behind
them would stay invisible. The package therefore replaces the panes with the same two panes at the same coordinates as a **transparent**
material (`TE_Glass`, alpha 9-55 percent dust film). Hide, do not delete, the old panes. Without that swap the vignette does not show.

## What is delivered (12 modules, 17,926 triangles LOD0)

Building-local "A-space" metres, +X screen-right from the avenue, +Y up, +Z to the avenue, origin = building pivot, Y=0 porch top.
Identity rotation, uniform scale 1 on every object (verified on GLB re-import).

| Module | Tris | Size X x Y x Z (m) | Pivot (A) | Content |
| --- | --- | --- | --- | --- |
| TE_DisplayCase | 2,140 | 1.500 x 1.420 x 0.420 | (-2.15, 0.78, 2.45) | perforated shadow board (unique 2048 px/m map), timber liners, soffit, shallow bench with skirt/fence, dust drifts, palm-polished forearm strip |
| TE_PegRail | 3,392 | 1.420 x 0.196 x 0.076 | (-2.15, 1.955, 2.042) | timber rail, 6 countersunk screws, 4 pegs, 2 blank kraft repair tags on the empty saw peg, cord hank on a peg |
| TE_ToolPipeWrench | 1,388 | 0.110 x 0.458 x 0.035 | on its board peg (see build-stats-raw.json pegs.wrench), z 2.052 | enamel-red 458 mm wrench, real 13 mm eyelet bore, cast rib, knurled adjuster, jaw teeth, rivets |
| TE_ToolLumpHammer | 934 | 0.308 x 0.101 x 0.066 | (-2.02, 1.695, 2.0485) | forged head, bright struck faces, wedge, palm-polished ash haft |
| TE_ToolBoltCutters | 1,600 | 0.604 x 0.197 x 0.047 | (-2.075, 1.325, 2.056) | rubber-dipped grips, forged jaws, bright blades, pivot bolt, tag on a twine loop |
| TE_RestPegs | 760 | 0.232 x 0.444 x 0.065 | (-2.15, 1.5, 2.042) | four curl pegs under the hammer haft and cutter arms |
| TE_BenchTools | 1,812 | 1.039 x 0.245 x 0.334 | (-2.15, 0.962, 2.24) | whetstone in a cradle, cast G-clamp with tagged tie, flat file |
| TE_DisplayLamp | 1,066 | 0.192 x 0.175 x 0.246 | (-1.78, 2.185, 2.15) | swan-neck housing, geometry only (no light, no emissive) |
| TE_ShutterGuide_L / _R | 958 each | 0.140 x 2.660 x 0.140 | (-0.70, 0, 2.605) / (2.75, 0, 2.605) | formed channel: web, rear + front flange with return lip, top bracket, 11 fixings, bare-steel rub plate (0.46 m left, 0.26 m right) |
| TE_ShutterHardware | 2,830 | 1.500 x 0.820 x 0.083 | (1.025, 0, 2.655) | two handle plates + brass D-handles, lock box + escutcheon, hasp + closed padlock, kick plate (unique 2048 px/m atlas) |
| TE_DisplayGlazing | 88 | 1.435 x 1.320 x 0.034 | (-2.15, 0.83, 2.543) | the same two panes as revision 04, transparent dust-film material |

Design intent: three hung/rested hand tools at legible size (wrench 458 mm, hammer 306 mm, cutters 604 mm), a shadow board whose painted
outlines register with the tools, and one absent tool (a handsaw "out for sharpening") shown only as a clean outline plus two blank
repair tags. Directional wear: the left shutter plate is worn roughly twice as much as the right (fingertip grasp above the bar, thumb knock,
palm-heel smear); the left guide's rub plate is longer than the right's; the wrench and tool-handle pegs sit under rubbed paint; dust
banks against the bench fence and rail top and is thinner where the forearm works.

Materials (15, all distinct responses): enamel red over cast steel, cast iron, forged tool steel, brushed steel, brass, oiled timber,
palm-polished ash, dipped rubber, twine, kraft paper (rule bands, no words), dust, sharpening stone, shutter paint, plus unique maps
for the board, shutter atlas and glass. See `materials.json` (URP mapping) and `textures/manifest.json` (sha256, seeds, sizes).

## Files (all under `art/quality_20260929/tool-exchange-display/`)

- Source: `tool-exchange-display-source-v1.blend` (revision-04 scene + new collection "TE display and shutter (new)"; superseded objects
  flagged with custom property `te_retired`, listed in text block `te_retired_objects.txt`, 7 objects). Untouched original: see above.
- Scripts (deterministic, re-runnable; `bl.sh` runs Blender with a clean PATH): `make_te_textures.py`, `te_textures_base.py`, `te_spec.py`,
  `te_lib.py`, `build_te.py`, `export_te.py`, `qc_reimport.py`, `measure_te.py`, `make_handoff_te.py`, `render_review_te.py`.
- Exports: `exports/glb/*.glb` (12, Y-up, A-space, no embedded images), `exports/interchange/te-meshes-v1.json` (per-material submeshes).
- Textures: `textures/TE_*` (46 PNG, 154 MB, up to 3072 x 2908), `textures/manifest.json`, `textures/layout.json`.
- Data: `handoff.json` (pivots, placement, guidance), `materials.json`, `measurements.json`, `qc-report.json`, `build-stats-raw.json`.
- Renders (`renders/`, Cycles, AgX, source only): noon and shade for each of
  `front` (1.6 m eye, 8.5 m out), `oblique`, `eye_display` (1.6 m eye, 2.6 m from the glass), `close_display`, `close_shutter`, `close_guide`;
  `close_tools*` (glass hidden, shows the board); `new_front_scale` (1.8 m and 1.0 m rods beside a 1.8 m figure);
  old/new comparisons `compare_<view>_<noon|shade>.jpg` (old left, new right); `old_*` renders of revision 04 from the same cameras.

## Placement for game-dev

Building pivot Unity (-20.6, 0.5, 9.0), yaw 90. glTFast flips X: place a part with A pivot (px, py, pz) at building-local
(-px, py, pz), identity rotation, scale 1 (pivots in `handoff.json` -> `parts[].pivotUnityLocalToBuilding`). Check by eye that the red
wrench is in the **left** pane as seen from the avenue, bolt cutters in the right pane, and the padlock hangs under the lock box in the
middle of the shutter. Hide (not delete) `tool_exchange Recessed tool display dark recess`, `... display glass`, `Shutter guide rail`
and `Shutter lift handle`; keep the mullions, sills, reveals, all 20 slats, drum casing, ground rail, backing and every collider.
The old lift handles are replaced by the new D-handles on plates (same x positions, 0.475 and 1.575).
The transparent glass must sort after opaque geometry; nothing else in the package is transparent.

## Measurements (`measurements.json`)

- Every display part lies inside the dressed opening (x -2.90..-1.40, y 0.78..2.20) and behind the glass rear face (z 2.543); frontmost display geometry z 2.450, so a 93 mm air gap to the glass. Deepest part is 0.42 m behind the masonry face (bench and lining), fully inside the closed shell: no interior is walkable.
- Board face z 2.042; tools stand off 3.5 mm (wrench), 3.0 mm (hammer) and 8.2 mm (cutters) from it; pegs 48-64 mm long.
- Shutter hardware frontmost z 2.738 = 38 mm proud of the front-wall collider face (z 2.70) and **25 mm behind** revision 04's old lift handles (z 2.763). Guides frontmost z 2.722. No new geometry lies beyond the old handle line, so the pedestrian path, door collider, first-step and interaction root are not encroached; the wall collider itself is unchanged.
- Eye-height legibility (1.6 m eye): wrench 5.8 deg, hammer 3.9 deg, cutters 7.7 deg at 2.5 m from the glass; 3.1 / 2.1 / 4.1 deg from 6 m.

## Verification done (Blender only)

- All 12 GLBs re-imported into a clean scene: triangle counts and bounds match the source (within 2 tris / 0.002 m), scale 1, no negative determinant, UV0 present and finite, no loose vertices, **0 degenerate UV triangles** after fixing the glass and escutcheon caps (they had 32 and 72 before; fixed and re-run). Non-manifold edges are reported not failed (`qc-report.json`): tags, twine, pegs and tool parts overlap by construction; the shutter hardware and glazing have none.
- Geometry and texture maps were inspected, not only the previews: the board map, shutter atlas and glass map were viewed at full size; the wrench, hammer and cutters were checked against the painted outlines in glass-off close-ups. Two problems were found and corrected during the pass: the lamp originally hung in front of the mullion (moved to x -1.78) and the file end and wrench nut poked outside the opening (file moved, nut narrowed). The escutcheon keyhole now sits on its brass disc.
- Old vs new rendered from identical cameras at noon and in shade.

## What this does NOT establish (honest gaps)

1. **Not a Unity render.** Materials are wired with the URP channel convention but never loaded in Unity; shade look, normal-map orientation and the alpha glass sorting are untested. The Blender sky/bounce lights in the previews are source-review lights.
2. **Shade.** The alcove is closed and lit only through the glass, so it reads darker in the game's shade than in these previews; the dust film also lowers contrast. A modest practical light (anchor: the lamp head at A (-1.78, 2.01, 2.27)) is a game-dev decision; nothing here depends on one.
3. **Legibility at range.** From the avenue the vignette reads as three tool shapes and a bench; the tags, twine and cord are only visible within about 3 m.
4. **The shutter plates are moderate, not subtle in flat light.** The hardware is authored as real plates with directional wear; if it reads too busy in the native player, drop the kick plate or the right plate.
5. **Texture memory is high**: 46 maps, about 217 Mpx referenced, roughly 276 MiB as BC7 with mips (1.1 GiB uncompressed). Source resolution is kept per the brief; tiny-prop families (twine, paper, sand, stone, rubber) use 2048 tiles for objects a few centimetres across and should be trialled at 1024 or shared, with mip streaming. Not measured in Unity.
6. Wrench eyelet-on-peg contact and small-part overlaps were checked visually in close-ups, not in wireframe or a physics test. No LOD1 was authored (parts are small; 13.2k triangles in the 1.5 x 1.4 m opening plus 4.7k on the shutter).
7. No visual acceptance, native capture, frame-time claim, "AAA" claim, or gameplay verification. Scores against AGENTS.md section 7 for the source view only: composition 3.5, scale 4, material detail 3.5, lighting/depth 3 (source lights), density/storytelling 3.5.

## Credit / task ledger and recoverables

- Meshy: none. Credits spent: 0. Task IDs: none. Other generative tools: none. Rights: all project original.
- Originals preserved: revision-04 `source.blend`, `meshes.json`, prefab and scene untouched (the scene file modification in `git status` predates this task and belongs to the Basic General integration parent, t_7f421ed1). The retired revision-04 objects remain in the review `.blend`.
- Rollback: in Unity, re-enable the four hidden renderer groups and disable the new parts; nothing was overwritten.
