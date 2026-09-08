# Athen Hill — Unity game

Open `AthenHill/` in Unity **6000.6.0f1**, then open
`Assets/AthenHill/Scenes/AthenHill.unity` and press Play.
The project uses URP **17.6.0**, glTFast **6.20.0** and the supplied **MeshyPlayer**
in the saved scene. Its idle pose, walk and run come from `meshy/mpc`; see
[MESHY_PLAYER.md](MESHY_PLAYER.md). The four talking NPCs now use the supplied
Ward Guard with relaxed arms. The three non-interactive roaming NPCs use the
supplied weathered Traveler FBX and its walking loop. Both Linux builds use these models; see the
[import checks and rebuild evidence](../docs/model-import.md).
Unity is the sole active build target. The old browser project is retired;
do not rebuild or test it. Historical sources and shared art inputs are retained.

This is a saved Unity scene with editable prefab instances, materials, lights,
ScriptableObjects, waypoint transforms, Input Actions and UI Builder assets.
See [EDITING.md](EDITING.md) for the editing workflow. Nothing reconstructs the
city at runtime. Editor assembly helpers refuse to overwrite an existing scene.

The September 8 atmosphere pass adds drifting cloud layers, a warm dust horizon,
distant ridge silhouettes, olive ground variation, wind grass and sparse plaza
dust. These are saved Unity materials, meshes and a ParticleSystem under **City
Atmosphere**, with Inspector controls documented in [EDITING.md](EDITING.md).
Reduced Motion freezes wind/clouds and clears dust. Native screenshots and the
performance/interaction checks are in
[the atmosphere review](evidence/atmosphere/20260908/acceptance.md).

The mountain and terrain pass replaces the detached mesa blocks with a continuous
Blender-authored desert basin, layered sandstone shading, and atmospheric depth.
The hill has detailed soil/gravel ground cover and scattered chipped stone.
See [terrain evidence](evidence/terrain/20260908/acceptance.md) and the
[terrain editing controls](EDITING.md#mountains-and-terrain).

## Controls

| Input | Action |
| --- | --- |
| WASD / arrows | Camera-relative movement |
| Left Shift | Run |
| Hold left mouse and drag | Look / orbit camera |
| Mouse wheel up / down | Zoom in to first person / back out |
| Space | Jump |
| E | Talk / use nearby terminal |
| Escape | Close panel / pause |
| R | Return to West Gate |
| 1 / 2 | Flask / medkit information |
| 3 / 4 | Lattice / talk shortcut |
| 5 / 6 | Inventory / notes |
| Tab / Enter | Focus / activate UI controls |
| Drag UI frame, header or bronze grip | Move that panel; position is saved |
| Ctrl + drag over a UI control | Move its panel without activating the control |
| Pause → Reset UI positions | Restore the default interface layout |

The [native controls checks](evidence/controls/20260908/acceptance.md) cover first-person
zoom, left-drag look, jumping and HUD/modal input handling.

Visit the hill, meet Mira/Torr/Vex/Linn, buy a flask and sell your starting scrap at
Basic General, then establish a Lattice link. Ring Gate is deliberately offline.
Pause contains mute, reduced motion, credits and a standalone Quit button. There is no second zone or combat.

The south-court Ring Gate now uses the user's sandstone/gunmetal reference,
generated through Meshy MCP. Its editable prefab includes the control console,
cyan lights, open aperture and a walkable approach step. The offline interaction
and hum are preserved. See [gate source and task records](../meshy/ring-gate-v1/README.md)
and [native verification](evidence/ring-gate/20260908/acceptance.md).

The post-war city pass replaces eight shop fronts, Basic General, Vanguard Hall,
the hill notice board and five crates with original Meshy assets. It adds 82
salvage props: litter, battered crates, generators and industrial scrap. Patched
awnings, repaired panels and worn surfaces give the district a more lived-in feel.
Lattice Jack is excluded. See the [reference sheets and source models](../meshy/salvage-20260908/README.md)
and [screenshots and current native checks](evidence/salvage/20260908/acceptance.md).

The soundtrack alternates the supplied **Dust of the Giants** and **Dust of Alshain**
with three-second crossfades. The ElevenLabs wind, market, terminal, footstep and
travel effects remain. Music softens during dialogue and travel.

Open **Esc → Settings · Sound and video**. Sound offers Master, Music, Ambience and
Effects sliders, mute, an effects preview and a next-track button. Changes are
immediate and saved. The city pauses while settings are open; audio keeps playing
so you can hear the mix. Back returns to Pause; Escape again resumes the city.

Video offers monitor resolutions, Windowed or borderless Fullscreen, Low/Medium/High
presets, render scale, shadows, MSAA, texture quality, post-processing, VSync and a
frame limit. Individual quality edits select Custom. **Apply video** previews the
setup for 15 seconds; **Keep changes** saves it. Revert, Escape or the timeout restores
the previous setup. Closing with unapplied edits discards them. Confirmed settings
survive relaunch; explicit `-screen-*` launch arguments override a saved display setup.
The interface remains sharp when reducing render scale.
See [AUDIO.md](AUDIO.md) for source records and [settings verification](evidence/settings/20260908/acceptance.md).

## Builds and diagnostics

Use **Athen Hill → Build → Linux development player** or **Linux release player**.
Build outputs go to `AthenHill/Builds/`. The build check rejects stale render chunks;
select **City Render Chunks** and click **Rebuild Render Chunks** after editing sources.
Native Linux x86-64 / OpenGL is the first target. WebGL/mobile remain unqualified.

The development player accepts `--athen-qa /absolute/output/directory` for the local
file-based QA bridge. Without that explicit option it creates no command listener;
release players ignore it. The bridge supports only named scene diagnostics,
screenshots and profiling, not arbitrary code or network commands.

To refresh both supplied NPC types and rebuild both Linux players, run the batch
entry point `AthenHill.Editor.ImportTraveler.ImportAndBuild`; the exact command
and native checks are documented in [model-import.md](../docs/model-import.md).
It imports the traveler directly from FBX and the relaxed guard from
`unity/staging/ward-guard.glb` (generated by `npm run prepare:guard`, an asset-only
processor, not a browser build). Both importers retain existing gameplay roots.

`tools/native_check.py` launches the development player, temporarily changes the QA
display to 1080p, runs real keyboard traversal and city-loop checks, and restores the
prior display mode. `tools/unity_client.py` calls the pinned local MCP at port 18081.
The Editor connection helper retries briefly when that local server starts late.

## Status and evidence

U0–U5 technical port checks are complete; see `evidence/` for dated checks.
The development player passed continuous keyboard traversal and the full city loop.
The release player passed movement, dialogue, pause, credits and Quit checks, with
no development listener and no logged runtime exceptions. Audio capture passes.

On the RTX 3060 / i9-10850K desktop, uncapped 1080p walking averaged about 490 FPS
(p99 frame time 5.10 ms, one 66.6 ms outlier). Independent GL tracing measured
78 draw submissions and 234,938 submitted triangles at most in the sampled views
and UI states. GPU timing is unavailable; this does not qualify a medium laptop or
prove the strict every-frame 58 FPS floor. Raw reports preserve counter anomalies.

The historical U5 evidence above used PlayerCandidate. The current MeshyPlayer
and Ward Guard rebuilds have separate checks documented in `../docs/model-import.md`.
The first native build exposed a disabled SSAO/stripped-resource initialization
failure; its blank-frame run is rejected, not performance evidence.

Final likeness to the original frozen city concepts remains open. Later terrain
and salvage passes add ground detail, repaired buildings and street clutter;
their dated evidence supersedes the initial sparse-world screenshots. The tree's
silhouette and the character's likeness remain separate art work from these passes.

Original asset notices are retained in the project and available through the pause
menu. The current soundscape was generated using the project's ElevenLabs account;
its prompts, source responses and file hashes are retained in `staging/elevenlabs-audio/`.
