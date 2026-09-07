# Athen Hill — Unity port

Open `AthenHill/` in Unity **6000.6.0f1**, then open
`Assets/AthenHill/Scenes/AthenHill.unity` and press Play.
The project uses URP **17.6.0**, glTFast **6.20.0** and the imported armoured
`player-candidate.glb`. It preserves the browser project alongside the Unity port.

This is a saved Unity scene with editable prefab instances, materials, lights,
ScriptableObjects, waypoint transforms, Input Actions and UI Builder assets.
See [EDITING.md](EDITING.md) for the editing workflow. Nothing reconstructs the
city at runtime. Editor assembly helpers refuse to overwrite an existing scene.

## Controls

| Input | Action |
| --- | --- |
| WASD / arrows | Camera-relative movement |
| Left Shift | Run |
| Hold right mouse and drag | Orbit camera |
| E | Talk / use nearby terminal |
| Escape | Close panel / pause |
| R | Return to West Gate |
| 1 / 2 | Flask / medkit information |
| 3 / 4 | Lattice / talk shortcut |
| 5 / 6 | Inventory / notes |
| Tab / Enter | Focus / activate UI controls |

Visit the hill, meet Mira/Torr/Vex/Linn, buy a flask and sell your starting scrap at
Basic General, then establish a Lattice link. Ring Gate is deliberately offline.
Pause contains mute, reduced motion, credits and a standalone Quit button. There is no second zone or combat.

## Builds and diagnostics

Use **Athen Hill → Build → Linux development player** or **Linux release player**.
Build outputs go to `AthenHill/Builds/`. The build check rejects stale render chunks;
select **City Render Chunks** and click **Rebuild Render Chunks** after editing sources.
Native Linux x86-64 / OpenGL is the first target. WebGL/mobile remain unqualified.

The development player accepts `--athen-qa /absolute/output/directory` for the local
file-based QA bridge. Without that explicit option it creates no command listener;
release players ignore it. The bridge supports only named scene diagnostics,
screenshots and profiling, not arbitrary code or network commands.

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

The qualified builds use the imported PlayerCandidate. A separate Meshy character
replacement is being developed in the same workspace and needs its own build QA.
The first native build exposed a disabled SSAO/stripped-resource initialization
failure; its blank-frame run is rejected, not performance evidence.

Final likeness to the frozen concepts remains open. The inherited world is sparse,
the tree lacks the reference's irregular silhouette and grassy mound, and the
candidate's face/armour remain more stylized than the supplied character concept.
A successful engine port is not a claim that those art requirements are solved.

Original asset notices are retained in the project and available through the pause
menu. Generated audio uses the supplied mixes; account-specific distribution terms
still carry the source manifest's caveat. No paid assets were purchased.
