# Athen Hill — Unity port handover for Alice

Prepared **7 September 2026** from the working tree on the Mac. This is an implementation handover, **not an existing Unity port**. Alice's OS, GPU, Unity installation and MCP connection have not been inspected or tested.

## Start here

The user wants to attempt a **Unity port on the Linux Alice workstation using Unity MCP**. They rejected the primitive-looking character and authorized external resources, preferably free; inexpensive paid assets may be proposed for review. This direction supersedes the old guide's Three.js-only and no-marketplace restrictions. Preserve the playable city, original names, art references and measured performance goals.

The first useful result is a saved Unity scene containing the imported city and the newer armoured character, with working movement from **West Gate to Hill Tree**, collision, animation and a screenshot from `cam_hill`. Establish that checkpoint before porting every UI panel or doing another large art pass.

Four things must survive the copy:

1. **Copy the working tree, including untracked assets.** The new character, source downloads, audio and some documentation are not in HEAD. A fresh clone alone will lose them.
2. Start the Unity character audition with **`public/assets/player-candidate.glb`**. `player.glb` is still the old live model that the user disliked.
3. Keep the last verified GLB and saved Blender scene. The latest attempt to rerun character optimization failed; current authoring scripts are ahead of the verified export.
4. Audio files exist, but their browser module is **not wired into the game**. Hearing nothing in the existing web build is expected.

## 1. Source snapshot and transfer

Source path on the Mac: `/Users/carl.draper/Documents/code/ao2`.

Branch: **`codex/phase-1-greybox`**. HEAD: **`d5132e6`**, “Implement city dialogue, trading and travel with desktop and mobile QA”. No Unity project existed at handover time.

| Stage | Actual state |
| --- | --- |
| Phase 2, concepts | Eight frozen references complete under `refs/`; do not overwrite them. |
| Phase 3, world | Blender world imported; traversal and collision verified. Final art quality remains open. |
| Phase 4, actors | Old player/NPC rigs and clips work. User reopened visual acceptance. |
| Phase 5, interactions | Dialogue, trading, travel, objectives and desktop/mobile UI complete and committed. |
| New player and lighting | Candidate GLB passed browser integration/performance QA; lighting changes are uncommitted. Candidate is not the default player asset. |
| Audio | Four generated effects/beds and a standalone module exist; no game integration. |
| Phase 6/7 | Final reference likeness, audio integration and final release qualification are unfinished. |

Keep `.git`, `src/`, `public/`, `refs/`, **`concept_art/`**, `blender/scenes/`, `blender/scripts/`, `blender/sources/`, `blender/exports/`, `blender/previews/`, `docs/`, `tools/`, `scripts/`, and package/config files. Retain `previews/` if preserving the original probe evidence. Exclude regenerable `node_modules/`, `dist/`, caches, `.DS_Store`, and optional `.blend1`/`.blend2` backups. Reinstall Node dependencies on Linux if running the browser reference.

**Credential handling:** the local, user-modified `AGENTS.md` contains an API credential. Do not print it into logs, copy it into Unity `Assets`, package it in a build, or bulk-commit it. Existing GLB/audio files require no API key. Any future generation credentials belong in Alice's private environment. Do not overwrite the user's guide or concept files while preparing the port.

After copying, inspect `git status --short` and run this from the copied repository root:

```sh
sha256sum -c docs/unity-source.sha256
```

The [checksum manifest](docs/unity-source.sha256) covers the principal assets, references, source contracts and QA reports at this handover. It is a transfer/snapshot check, not an exhaustive repository inventory. If a hash differs, determine whether the file was intentionally revised before replacing it.

Create the Unity project at **`unity/AthenHill/`** in the copied repository, on a new **`codex/unity-port`** branch if that name is available. Keep the existing browser implementation as the behavioral reference. Preserve all existing changes; do not use `git clean`, reset the working tree, or broadly stage unrelated files.

Track Unity `Assets/` **with `.meta` files**, `Packages/manifest.json`, `Packages/packages-lock.json`, and `ProjectSettings/`. Ignore `Library/`, `Temp/`, `Obj/`, `Logs/`, `UserSettings/` and generated builds. Store captures/reports outside `Assets`, for example `unity/evidence/`. Keep Blender authoring sources outside Unity `Assets`; import explicit exports rather than relying on automatic `.blend` conversion.

## 2. Alice prerequisites and Unity MCP

### Suggested baseline

Use **Unity 6.3 LTS with Universal Render Pipeline (URP)** for the first port, and record/pin the actual installed patch version. This is a practical recommendation for the existing modest scene budget and possible future browser support. Start with a **native Linux x86-64 build**; a WebGL release is a separate target to qualify later. Do not switch to HDRP during the baseline import unless the intended hardware and reason are established.

Unity 6.3 LTS is supported until December 2027. Its Linux requirements document Ubuntu 22.04/24.04 x64, GNOME and supported GPU/driver configurations. Verify Alice against those requirements rather than assuming “Linux” is sufficient. Use an actual graphical Editor session with a working hardware renderer for visual/performance QA. Complete Unity Hub/editor licensing if required; do not treat a headless software-rendered session as GPU performance evidence. [Unity support policy](https://unity.com/releases/unity-6/support), [Unity 6.3 system requirements](https://docs.unity3d.com/6000.3/Documentation/Manual/system-requirements.html), [Linux Hub installation](https://docs.unity.com/en-us/hub/install-hub-linux).

Record OS, desktop session, GPU, driver, graphics API, display resolution, Unity patch, URP version and build target in `unity/evidence/environment.md`.

### Plugin choice and installation

First inspect whether Alice already has a working Unity MCP integration. Use it if suitable, and discover its real tool schemas. Otherwise the researched default is **CoplayDev/unity-mcp v10.2.0**, a community plugin, with its matching Python server. It supports Unity 2021.3 onward, including Unity 6; it needs Git, Python ≥3.10, `uv`/`uvx`, and an open Unity Editor. Node is not a dependency of this MCP server. [Pinned release](https://github.com/CoplayDev/unity-mcp/releases/tag/v10.2.0), [package manifest](https://github.com/CoplayDev/unity-mcp/blob/v10.2.0/MCPForUnity/package.json), [installation guide](https://coplaydev.github.io/unity-mcp/getting-started/install), [server dependencies](https://github.com/CoplayDev/unity-mcp/blob/v10.2.0/Server/pyproject.toml).

In Unity Package Manager, add from Git URL:

```text
https://github.com/CoplayDev/unity-mcp.git?path=/MCPForUnity#v10.2.0
```

Pin the server to **`mcpforunityserver==10.2.0`** as well. Do not silently update either half during port verification. If a later version is selected, document the change and repeat the connection probe. [Published server version](https://pypi.org/project/mcpforunityserver/10.2.0/).

### Connection topology

Run the **Unity Editor, Python server and Codex execution host on Alice**. A Codex desktop UI on the Mac is fine if its task and tools execute on Alice. `127.0.0.1` always means the machine running that client process; a Mac-local MCP process cannot reach Alice's loopback merely by copying this configuration.

Open **Window → MCP for Unity**, complete dependency detection, choose **HTTP Local**, and start/connect the local server. Configure Alice's Codex MCP entry:

```toml
[mcp_servers.unityMCP]
url = "http://127.0.0.1:8080/mcp"
tool_timeout_sec = 300
```

Equivalent registration:

```sh
codex mcp add unityMCP --url http://127.0.0.1:8080/mcp
```

If the Unity window does not manage the server, launch the pinned server manually **instead of starting a second copy**:

```sh
uvx --from mcpforunityserver==10.2.0 mcp-for-unity \
  --transport http --http-url http://127.0.0.1:8080
```

The server base URL omits `/mcp`; the MCP client URL includes it. Keep the service on loopback. If using a Mac-local client, explicitly arrange remote execution or an SSH tunnel and verify which host owns the files and Editor. [Transport documentation](https://coplaydev.github.io/unity-mcp/architecture/transports), [pinned server CLI](https://github.com/CoplayDev/unity-mcp/blob/v10.2.0/Server/src/main.py).

An alternative is stdio. Select that transport in Unity and **replace**, rather than duplicate, the HTTP entry:

```toml
[mcp_servers.unityMCP]
command = "/replace/with/absolute/path/to/uvx"
args = ["--from", "mcpforunityserver==10.2.0", "mcp-for-unity", "--transport", "stdio"]
startup_timeout_sec = 60
tool_timeout_sec = 300
```

Use `command -v uvx` to resolve the real executable path, then restart/reconnect the Codex client. Current Codex supports both transports; older “Codex is stdio-only” advice is stale. [HTTP restoration in the plugin](https://github.com/CoplayDev/unity-mcp/pull/1305), [OpenAI MCP configuration](https://learn.chatgpt.com/docs/extend/mcp).

### Mandatory smoke probe

Before city imports, use MCP to discover/select the correct Editor instance (`mcpforunity://instances`, `set_active_instance` where available). Report its project path, Editor version and active pipeline. Then:

1. Create and save `Assets/AthenHill/Scenes/MCPProbe.unity`.
2. Add a ground plane, a **2 m blue `PROBE_CUBE`**, directional light and camera with URP-compatible materials.
3. Add an asymmetric marker labelled +X and a different marker at +Z; this also establishes an orientation reference for the later import test.
4. Create/attach a tiny rotation script using the plugin, refresh, wait for compilation, inspect Console errors, enter Play mode and verify visible motion across two frames.
5. Exit Play mode, save the scene, capture the actual PNG into project-relative `Captures/`, then copy it to repository-level `unity/evidence/mcp-probe.png`. Reopen/inspect the saved scene. Record the result and actual tool names used.

If a step fails, diagnose the actual connection, compilation or rendering error before continuing. A successful package install or returned tool string is not proof that the Editor scene changed. Do not report imaginary captures or substitute a CLI-only port for the requested MCP workflow. [First-prompt workflow](https://coplaydev.github.io/unity-mcp/getting-started/first-prompt).

### MCP workflow during the port

Tool names below are from the researched plugin; discover live schemas before calls. Only `core` is enabled by default. Use `manage_tools(action="list_groups")` and activate additional groups as needed. [Tool reference](https://coplaydev.github.io/unity-mcp/reference/tools), [tool groups](https://coplaydev.github.io/unity-mcp/guides/tool-groups).

| Purpose | Relevant tools |
| --- | --- |
| Inspect scene and failures | `manage_scene`, `find_gameobjects`, `read_console` |
| Assemble/import | `manage_asset`, `manage_gameobject`, `manage_components`, `manage_material`, `manage_prefabs` |
| C# implementation | `create_script`, `script_apply_edits`, `validate_script`, `refresh_unity` |
| Animation and UI | `manage_animation`, tools in the `ui` group |
| Capture/profile/test/build | `manage_camera`, `manage_profiler`, `run_tests`, `get_test_job`, `manage_build` |

Use **one agent for Unity scene mutations**, even if research, C# review and test design run in parallel. Persist repeatable import/scene assembly logic under `Assets/AthenHill/Editor/`; make it idempotent, so retries update named assets without duplicating the city. After code changes: refresh → wait for compilation/domain reload → inspect Console → run the behavior → capture → save. Inspect current state before retrying a timed-out mutation. [Multi-instance/concurrency guide](https://coplaydev.github.io/unity-mcp/guides/multi-instance).

Use Editor APIs/tools to create scenes and prefabs; avoid hand-writing Unity scene YAML. Exit Play mode before persistent scene edits. Named-camera MCP screenshots exclude Screen Space Overlay UI; capture the Game View as well when verifying the HUD. The screenshot tool's `output_folder` must be **inside the Unity project**: use `Captures/`, verify the returned file, then copy it with filesystem tools to `unity/evidence/` outside the project. Do not pass that repository-level evidence path directly as the tool's output folder. [Screenshot API](https://coplaydev.github.io/unity-mcp/reference/tools/core/manage_camera).

## 3. Reuse these assets

| Source file | Role and caveat |
| --- | --- |
| `public/assets/world.glb` | Authored city, 19,997,640 bytes; 1,358 mesh definitions including collision proxies, 9 materials, no animation. Render geometry is about 64k triangles before actors/shadow passes. |
| **`public/assets/player-candidate.glb`** | New armoured male audition, 18,922,656 bytes; 9 mesh definitions, 8 materials, one 53-joint skin, four clips. **35,029 total triangles: 32,578 visible + 2,451 shadow proxy.** |
| `public/assets/player.glb` | Original live player, 3,797,336 bytes, 19-joint rig. Retain for comparison/rollback; do not mistake it for the replacement. |
| `public/assets/npcs.glb` | Old shared NPC body, 3,501,488 bytes, 5,262 source triangles, 19-joint rig. Instantiate for four named and three ambient actors initially. Their appearance still needs improvement. |
| `public/assets/world-manifest.json` | Required world landmark groups; collider details are in GLB node metadata and the importer code. |
| `public/assets/probe.glb` | Original Blender round-trip asset; add asymmetry when testing handedness. |
| `blender/scenes/15_character_candidate.blend` | Last saved candidate scene associated with the successful export. Open a copy before experimenting. |
| `blender/scenes/10_cliff_silhouettes.blend`, `11_characters.blend` | Earlier authored world and original character stages. |
| `blender/sources/`, `blender/exports/colonist-textures/` | Downloaded source packs, licences, manifests and derived textures. Preserve these for editing and provenance. |
| `public/assets/audio/*-mix.mp3` | Four level-adjusted audio files suitable for a Unity audition; see section 7. |

GLBs embed their runtime textures. Start from these exports; a missing Mac texture path in a Blender authoring file should not block the initial Unity import.

### GLB import

Install **glTFast**, package ID **`com.unity.cloud.gltfast`**, using a version compatible with the chosen Unity/URP version; record and lock that version. Its Editor importer creates Unity assets from `.glb`/`.gltf` placed in `Assets`. Inspect its generated meshes, materials, textures and animation clips before changing them. Avoid two competing default glTF importers. The linked documentation describes glTFast 6.0 behavior; check the installed version's manual as well. [glTFast Editor import](https://docs.unity3d.com/Packages/com.unity.cloud.gltfast@6.0/manual/ImportEditor.html).

Suggested organization: `Assets/AthenHill/Art/Imported/`, `Materials/`, `Prefabs/`, `Scenes/`, `Scripts/`, `Data/`, `Audio/`, and `Editor/`. Keep imported originals intact and make scene/prefab variants for project adaptations.

Unity MCP's optional `asset_gen` tool **`import_model_file`** supports local GLB/glTF with glTFast and needs no generation API key. In v10.2.0, GLB/glTF goes directly through glTFast and **does not use `target_size`**. Its FBX/OBJ path can normalize the largest dimension to 1 m when a size is omitted and AutoNormalize is enabled: use `target_size=0` or disable AutoNormalize to preserve authored scale, and specify `animation_type="generic"` for a rigged FBX baseline. Verify the resulting scale in every case. **Do not normalize a 120 m city or a 1.8 m character to a generic prop size.** [Local model import tool](https://coplaydev.github.io/unity-mcp/reference/tools/asset_gen/import_model_file), [pinned importer implementation](https://github.com/CoplayDev/unity-mcp/blob/v10.2.0/MCPForUnity/Editor/Tools/AssetGen/ImportModelFile.cs), [normalization pipeline](https://github.com/CoplayDev/unity-mcp/blob/v10.2.0/MCPForUnity/Editor/Services/AssetGen/Import/ModelImportPipeline.cs).

Repeated `import_model_file` calls create suffixed asset copies rather than updating the original. For repeatable imports, either reuse the returned asset paths or copy exports to controlled paths under `Assets` and refresh/import through the Editor. Do not create a new duplicate asset every time the assembly script runs.

### Materials: frequent ways to ruin this character during import

- Preserve **vertex colour (`COLOR_0`) multiplied by albedo**. The armour's olive/graphite/cyan separation relies on it. Assigning a plain replacement material can erase the design.
- Some surface maps use **`TEXCOORD_1` / SurfaceUV**. Preserve both UV sets and texture-coordinate selection. Unity lightmap UV generation must not overwrite an authored set still used by the material; reserve a separate channel or remap the material deliberately.
- glTF metallic/roughness packing is **roughness in G, metalness in B**. Unity material workflows may require repacking and roughness-to-smoothness conversion. Preserve normal-map interpretation, normal strengths, colour-space settings and emission when converting. First establish the importer-generated material baseline; only then author URP Shader Graph variants if needed.
- Hair, eyebrows and beard use alpha **MASK/cutout**, cutoffs around **0.32–0.35**, with double-sided cards. Keep skin/eyes opaque. Check eyelashes/brows and beard edges at portrait scale, not only from the follow camera.
- Verify tree leaf cards, baked vertex colours, cyan panels and transparent world materials too. Avoid automatic material conversion that silently drops those properties.

### Animation and the shadow proxy

Candidate clips are **`idle`, `walk`, `run`, `talk`**, approximately 3.0 / 0.8 / 0.8 / 3.0 seconds, sampled at 120 Hz. Locomotion is in place. Keep controller displacement authoritative and root motion off initially.

The candidate's nominal stride speeds, stored as animation extras, are **1.503112134 m/s** for walk and **3.610416400 m/s** for run. The current browser scales clip playback by actual speed divided by those values. At gameplay speeds 3.4/6 m/s that is roughly **2.262× / 1.662×**. Preserve the calibration or deliberately improve the clips; playing both at 1× produces foot sliding.

Use the authored skeleton/clips first. Depending on the glTFast version, animation may arrive through an `Animation` component/legacy clips rather than a ready-to-use Animator Controller. Inspect the result and choose a Generic/Playable or explicit clip-conversion path. Humanoid retargeting is a later option after validating the Avatar mapping, rest pose and hands/feet. Do not assume the 19-joint NPC rig and 53-joint candidate share an Avatar. If GLB import cannot retain a required feature, export a separate, versioned FBX from Blender and verify it; do not overwrite the good GLB.

The object **`COLONIST_shadow_proxy`** is a skinned shadow mesh, **not a collision mesh**. It has `shadowProxy: true` in extras. Some metadata retains an earlier triangle target; the actual mesh has **2,451 triangles**. In Unity, test `ShadowCastingMode.ShadowsOnly` on its renderer. Visible character meshes should initially receive shadows but not cast their own duplicate shadows. Do not disable the proxy GameObject/renderer, which would remove its shadow as well. Verify animated skinned bounds, culling, and shadows from the fixed and follow cameras. `COL_` world collision names and this proxy are different cases.

### Interrupted Blender rebuild — known issue

Local authoring used Blender **5.2.1 LTS** and MPFB **2.0.17**. Stages are `12_character_audition.py`, `13_colonist_armour.py`, `14_colonist_animation.py`, `16_colonist_materials.py`, `15_colonist_optimize.py`, then `17_colonist_export.py`.

After the last successful candidate export, collar clearance and hair/beard material changes were attempted. Rerunning optimization failed with **“Optimized output has missing skin weights or invalid UV values”**. Source checks did not identify invalid source data; the derived reduction/batching/proxy failure remains unresolved. Stage 15 now includes a `ColonistOptimizationError` diagnostic report, but that diagnostic revision has not been successfully rerun. The latest scripts therefore do not reproduce the hashed GLB without further investigation.

**Do not blindly rerun the pipeline or replace the successful export.** Start the Unity port from the saved GLB; investigate the Blender issue separately in a copied scene. The interrupted live Blender scene is not a safer baseline than the saved files. Scripts and texture references include hard-coded Mac paths; parameterize the repository root and remap source textures on Alice before any regeneration. Respect case-sensitive paths and install a Linux-compatible Blender/MPFB setup rather than copying Mac add-on installation paths.

## 4. Coordinates, collision and camera contract

The source runtime uses **metres, Y up, north = −Z**. Landmark/player positions are **feet**, not capsule centres. GLBs already contain Blender-to-glTF axis conversion. Unity uses a different handedness, and the importer may perform its own reflection.

Define one conversion function for source data. A useful intended convention is `UnityPosition = (source.x, source.y, -source.z)`, but verify that it matches the actual imported geometry first. Test an asymmetric imported marker, world bounds, West Gate, the Lattice Jack and the character's facing direction. If the importer uses a different reflection, adapt the data conversion once. Apply the same convention to points, directions, camera targets, collider transforms and rotations. Do not double-flip the meshes, guess quaternion sign changes, or leave negative scale on a skinned root.

The browser currently rotates the player's visual root by π because its controller faces −Z while the authored character faces +Z. That is a source-runtime correction, **not an instruction to rotate the Unity character blindly**.

### Collision and movement

Read [`src/world-assets.ts`](src/world-assets.ts), particularly `colliderFromMesh`, and [`src/physics.ts`](src/physics.ts). The GLB has **262 `COL_` proxies**; the runtime adds its ground halfspace for **263 static collider definitions**. Exclude those proxy meshes from visible rendering.

Preserve GLB extras such as `colliderKind`, `colliderRadius`, `colliderHalfHeight` and landmark identifiers. If glTFast does not expose extras in imported GameObjects, parse the GLB JSON into a sidecar/Editor import report and resolve nodes by their stable names. Do not assume Unity automatically creates the correct colliders from the naming convention.

Convert boxes using local mesh bounds plus the accumulated transform/rotation; a world AABB incorrectly fattens rotated objects. Unity has no direct cylinder collider equivalent: use a suitably simple convex cylinder MeshCollider for these static proxies, with its dimensions and contact behavior verified. Recreate the ground as a sufficiently large static collider with its top at Y=0; preserve the playable boundary. Keep stairs as actual **0.25 m steps**, porches at **0.5 m**, and hill plaza at **1.5 m**. Do not put a detailed city-wide MeshCollider on the render mesh.

Recommended initial C# controller: Unity `CharacterController`, explicit gravity, camera-relative motion, and a separate visual child. Start with height **1.8**, radius **0.35**, centre Y **0.9**, step offset **0.3**, slope limit **45°**, walk **3.4 m/s**, run **6 m/s**. Implement/validate the source's **0.4 m ground snap** behavior; it is not a one-property Rapier-to-PhysX translation. Retain a 60 Hz simulation target and sensible delta clamping. Avoid adding a competing dynamic Rigidbody to the same controller.

The follow boom is **4.2 m**, targeting feet + **1.5 m**, with a **0.23 m sphere sweep** against the world; exclude the player's own collider. Pull inward immediately when obstructed and restore distance smoothly. Re-run the full route and wall/stair/camera tests because different physics engines are not behaviorally identical.

### Landmarks and fixed cameras

Use [`src/layout.ts`](src/layout.ts) for all landmark coordinates and the detailed no-teleport `WALK_ROUTE`. Key source-space positions:

| Landmark ID | Feet `(x, y, z)` |
| --- | --- |
| `west_gate` | `(-43, 0, 0)` |
| `hill_tree` / `oa_hill` | `(-4, 1.5, 0)` / `(-4, 1.5, 4)` |
| `shop_row_e` / `shop_row_w` | `(16, 0.5, 9)` / `(-16, 0.5, 9)` |
| `basic_general` | `(-8, 0.5, 16)` |
| `vanguard_hall` | `(10, 0.5, -25.5)` |
| `grid_kiosk` / `lattice_jack` | `(0, 0.5, -36.5)` |
| `whompah` / `ring_gate` | `(0, 0.5, 36)` |
| `mission_slab` | `(-8, 0.25, -12.5)` |
| `east_wreck` | `(51, 0, 0)` |

Create named camera objects from [`src/camera.ts`](src/camera.ts). These use a **50° vertical FOV at 1920×1080 / 16:9**. Convert both position and look target using the chosen coordinate convention.

| Camera | Source position | Source look target |
| --- | --- | --- |
| `cam_gate` | `(-32, 9, 18)` | `(-48, 3.4, 5)` |
| `cam_avenue` | `(-12, 7, 34)` | `(0, 9, -5)` |
| `cam_hill` | `(23, 14, 27)` | `(0, 9, 0)` |
| `cam_grid` | `(-10, 6, -28)` | `(0, 2, -38)` |
| `cam_whompah` | `(13, 6.5, 26)` | `(0, 3, 36)` |
| `cam_hero` | `(-5, 3.4, 9)` | `(0, 9, 0)` |

Also recreate the source's `character` and `portrait` review cameras, **35° vertical FOV**, to inspect the face and suit. Camera distance/target calculations are in `updateReviews()`; derive the front from the actual imported character transform.

## 5. Port the behavior, using C# implementations

The TypeScript is the behavior/data reference; it is not directly executable Unity gameplay code. Prefer small MonoBehaviours and plain C# models, with ScriptableObjects/serialized assets for reusable definitions. No server, database, network backend or automatic TypeScript transpiler is needed.

| Source | Suggested Unity responsibility |
| --- | --- |
| `src/game.ts` | `GameSession`: boot/play/dialogue/shop/grid/paused/error, objective progression and orchestration. |
| `src/layout.ts`, `src/world-assets.ts`, `src/world.ts` | Editor importer, world prefabs, collision metadata and landmark data. |
| `src/input.ts`, `src/player.ts`, `src/physics.ts`, `src/camera.ts` | Input System actions, character controller, physics queries and follow/fixed cameras. |
| `src/characters.ts` | Actor prefab, authored clips, playback calibration, rig and shadow-proxy handling. |
| `src/npc.ts`, `src/dialogue.ts` | NPC definitions, waypoint walkers, interaction selection and dialogue graph. |
| `src/shop.ts` | Plain C# inventory/trade model with atomic validation. |
| `src/travel.ts` | Lattice transition and sector-map state; Ring Gate offline interaction. |
| `src/ui.ts`, `src/style.css` | Unity UI panels, focus/input handling, HUD, nametags, quick actions and notices. Recreate the layout; HTML/CSS will not import as native Unity UI. |
| `src/atmosphere.ts` | Visual reference for sun, sky, haze and material exposure. Recreate using Unity lights/sky/fog/probes rather than translating the Three.js shader literally. |
| `src/audio.ts` | AudioMixer/AudioSource orchestration; behavior reference only, not yet connected in the browser. |
| `src/debug.ts` | `AthenDebugBridge` plus Editor/MCP-accessible diagnostic actions. |

Preserve these user-facing behaviors:

- Spawn at West Gate. WASD/arrows walk relative to camera; Shift runs; right-drag rotates; E interacts; Esc pauses/closes as appropriate; R returns to gate; slots 1–6 retain their existing actions. Use separate gameplay/UI input maps so modal panels do not move the player.
- **Mira** at `(-8, .5, 15.8)`, **Torr** at `(-9, .25, -12)`, **Vex** at `(-41.7, 0, -1.5)`, **Linn** at `(-2.5, 1.5, 4.7)`, all in source space. Interaction range **2.4 m**. Preserve the two-choice dialogue branches and original wording from `src/dialogue.ts`.
- Three ambient walkers follow the exact closed routes/speeds in `src/npc.ts`. A simple waypoint controller is sufficient initially; NavMesh is optional, not required to recreate those routes.
- Start with **25 credits and one Scrap Coil**. Water Flask buy/sell **4/2**, Medkit **9/4**, Scrap Coil **2/1**. Each transaction moves one item. Insufficient funds, empty inventory and unknown IDs must not partially mutate balances.
- Lattice Jack: approximately **1.25-second** tunnel transition, then three named nodes and a “link established” result. Selecting a node does not load a second zone or move the player. Retain the reduced-motion behavior. Ring Gate reports its destination offline.
- Complete the visit objective by reaching the hill, speaking to all four NPCs, buying a flask, selling scrap and establishing a Lattice link.
- Keep the six-slot HUD, vitality/nano bars, small log, inventory/notes panels, readable nametags and interaction prompt. Implement pause/focus behavior and a visible credits route. Port touch/responsive controls when qualifying a mobile/WebGL target; desktop keyboard/mouse is the first Linux milestone.

Do not add combat, multiplayer, accounts, character creation or another zone during the port.

## 6. Art direction and performance

The governing character target is **[`concept_art/main_male_human_player_character.jpg`](concept_art/main_male_human_player_character.jpg)**: a mature bearded human with convincing anatomy, worn layered olive armour, dark flexible joints, detailed boots/gloves and restrained cyan strips. It supersedes the earlier simplified recruit interpretation in `refs/06_pc_threequarter.png`. Keep both originals.

For the city, retain the frozen [`refs/`](refs/) and supplied [`concept_art/`](concept_art/) as references: dusty gold daylight, pale stone, gunmetal structures, faded red cloth, cyan terminals and a monumental tree. Avoid letting the character's forest backdrop turn the whole city into a new biome.

**Moving to Unity does not repair weak geometry.** The free candidate is a useful imported baseline, still visibly more stylized than the user's reference: smooth face, hard beard edge, bulky hair and broad simplified plates. The original NPCs remain primitive. Prove import fidelity first, then improve one asset/material/lighting family at a time and capture the result in the game. A vendor render or Blender beauty still is not Unity visual acceptance.

Use URP lighting, a coherent sky/environment, one dominant warm sun, restrained fill, reflection probes and controlled shadows. Bake appropriate static lighting only after scale and materials work. Avoid adding heavy post-processing to conceal import defects. The latest uncommitted `src/atmosphere.ts` opens the olive materials and restores a muted blue sky/warm horizon; its browser captures are the comparison baseline.

The world GLB's **1,358 mesh definitions should not become 1,358 independent draw calls**. The current importer excludes collision meshes and batches render geometry into about ten groups. In Unity, preserve modular source prefabs but group static render geometry by material and sensible spatial chunks; instance compatible repeated geometry. SRP Batcher reduces submission overhead but does not by itself merge all draws. Check the Frame Debugger/Profiler before deciding how to batch; avoid one city-wide mesh that destroys culling or editability.

Preserve the project target of **60 FPS at 1920×1080**, with the existing acceptance floor of **58 FPS**, approximately **≤250k rendered triangles and ≤80 draw calls**. Measure all eight actors, shadows, UI and active effects on a representative walking route. Report render scale, graphics API, quality settings, frame-time distribution and CPU/GPU timings; record batches, SetPass calls and triangle counts separately because Unity and Three.js counters need not count passes identically. Do not claim a medium-laptop gate passed solely from Alice if Alice is much more powerful. Measure a standalone build as well as Editor Play mode; a VSync-capped 60 FPS sample alone does not establish headroom.

For `cam_hill`, `cam_avenue`, `cam_gate`, score palette, sky/haze, silhouette, light direction, roughness, density, scale and HUD integration from 0–5 against the references. Preserve the original minimum **4/5 for palette, silhouette and light direction**, plus the frame-rate gate. Label differences honestly; don't lower the target to declare the engine port visually complete.

## 7. Audio, licences and optional paid art

Reuse the level-adjusted files under `public/assets/audio/`:

| File | Intended use |
| --- | --- |
| `desert-bed-mix.mp3` | 12-second quiet wind/market bed, loop. |
| `stone-step-mix.mp3` | Approximately 0.8-second single step. Trigger from grounded movement/cadence. |
| `terminal-click-mix.mp3` | Approximately 0.5-second UI confirmation. |
| `transport-hum-mix.mp3` | 5-second terminal power loop; use a spatial source. |

Prefer these mixes over the unlevelled source MP3s, particularly the original loud hum. Set up ambience/SFX/UI mixer groups, pause/mute controls and spatial falloff. Test loop seams and decode/import quality in Unity. [`manifest.json`](public/assets/audio/manifest.json), [`qa.json`](public/assets/audio/qa.json) and [`runtime-qa.json`](public/assets/audio/runtime-qa.json) preserve generation and standalone Web Audio QA. They do not prove in-game audio integration. There is no completed 40-second music bed or voice set. Account-specific distribution terms were not independently reviewed; retain the manifest's caveat for release review.

Keep [`public/assets/THIRD_PARTY_LICENSES.md`](public/assets/THIRD_PARTY_LICENSES.md), [`public/credits.html`](public/credits.html), and the raw source/pack manifests under `blender/sources/`. Provide equivalent Unity credits for distributed derived assets. The selected sources include MakeHuman/MPFB graphical assets, Grump hair by Elvaerwyn, Sigmund beard by grinsegold, Aksel skin normal by Mindfront, and Poly Haven textures. The notice distinguishes the graphical asset licences from add-on code licences, retains the hair's source-specified CC-BY attribution, and records the Sigmund legacy-header/current-pack licence discrepancy. Do not erase that provenance when importing.

No paid model has been purchased. One previously researched option is [Base Male And Sci-Fi Game Character Starter by Aarón Hernández](https://superhivemarket.com/products/base-male-and-sci-fi-game-character-starter), listed at **US$24.99 when checked on 7 September 2026**. It may improve the anatomical/skin/hair base; it does not include the desired armour and its hairstyle needs adaptation. Recheck price and licence if proposing it, show the concrete asset and expected benefit, and obtain purchase approval. The user's willingness to review cheap assets is not blanket spending authorization. The free path can continue independently. Further source details are in [`docs/character-replacement.md`](docs/character-replacement.md).

Use original public names **Athen Hill**, **Free Column**, **Lattice Jack**, **Ring Gate**. Do not import extracted Anarchy Online/Funcom meshes, textures, sounds, logos or official NPC names.

## 8. Evidence and acceptance milestones

### Existing browser evidence

These reports are historical Mac/browser checks, not Linux/Unity results:

| Evidence | Verified result |
| --- | --- |
| [Phase 5 report](tools/phase5-support/runs/2026-09-07T11-07-20.844Z-31068/report.json) | PASS: dialogue, shop, travel, objective and desktop/mobile checks. About 120.06 FPS, max 57 draws / 224,596 rendered triangles, Apple M4 Max / ANGLE Metal. Old player. |
| [Latest candidate + lighting report](tools/character-replacement/runs/2026-09-07T11-54-58.633Z/report.json) | PASS: 1920×1080, about 59.99 FPS, 63 draws / 236,780 rendered triangles, no reported browser errors. Candidate bytes were routed into the unchanged `player.glb` request. This is not evidence the default asset was replaced. |
| [Candidate full view](tools/character-replacement/runs/2026-09-07T11-54-58.633Z/character-full-clean.png), [portrait](tools/character-replacement/runs/2026-09-07T11-54-58.633Z/character-portrait-clean.png), [hill](tools/character-replacement/runs/2026-09-07T11-54-58.633Z/cam_hill.png) | Actual browser captures. Other fixed views and walk/run frames are alongside them. Visual likeness remains unaccepted. |

To inspect the web reference on Alice, use Node **22.12+**, `npm ci`, then `npm run dev`. Dev is `http://127.0.0.1:5173/`; production preview is port 4173 after `npm run build` and `npm run preview`. The supplied QA scripts include Mac-specific Chromium/Metal flags: adapt those for Linux and record the actual GPU backend before running them. A plain web launch still shows the old player. `tools/verify-character-replacement.mjs` documents the local candidate request routing; `--live` instead tests the old default asset unless it has been deliberately changed.

Some older prose is stale: README's “Next phase” still describes Phase 2 as future work, and the earlier character document describes an audition before the successful export. Use this dated snapshot, actual files, hashes and reports for handover status; use the older documents for their detailed implementation/provenance evidence.

### Unity milestones — save and verify each one

| Milestone | Deliverable and pass gate |
| --- | --- |
| **U0 — connected Editor** | Version/pipeline/environment record, pinned packages, saved MCP probe scene, rotation visibly verified, no unresolved Console errors, actual capture. |
| **U1 — import fidelity** | World/candidate/NPC imports with correct metres, orientation, materials, all four clips and shadow handling. Save a baseline scene and six fixed cameras. Inspect face, alpha cards, UVs and world collision metadata. |
| **U2 — first playable slice** | Controller and follow camera; keyboard walk West Gate → Hill Tree without teleports, falling or camera penetration. Then extend to Ring Gate, Lattice Jack, porches and both gate tunnels using the source route. |
| **U3 — restored city loop** | Four conversations, three walkers, atomic shop trades, Lattice overlay, Ring bark, objective completion, pause/input focus and HUD. Use real inputs to test verbs; landmark teleports are only setup aids. |
| **U4 — sound and visual pass** | Audible mixed ambience/steps/terminal hum, working mute/pause, fixed-camera scorecard and measured full-scene performance. Separate faithful port status from remaining art-quality work. |
| **U5 — Linux build** | Reopen from disk, build Linux x86-64, launch outside the Editor, complete the route and city loop, inspect player logs, capture representative frames, verify credits and record remaining limitations. |

Commit only coherent Unity changes/evidence after each passed milestone; do not auto-commit unrelated source edits or secrets. Do not advance on a false acceptance claim. An asset likeness failure can be recorded as an open art issue while a faithful technical import is accepted, but it cannot be called finished visual work.

Implement an **`AthenDebugBridge`** reachable through Editor menu actions or a registered MCP custom tool. It should expose state, feet position/yaw, grounded state, actor/clip counts, selected camera, colliders near the player, shop/objective state and profiler samples, plus operations equivalent to `goto(landmark)`, `view(camera)`, `capture(camera)`, `pause` and `reset`. Gate development controls in release builds. This replaces `window.__ATHEN__`; do not promise a browser global in a native Unity player.

Use Edit Mode tests for the shop/state model and Play Mode checks for traversal, modal input and animation transitions. After automated checks, inspect actual Game View captures and run the standalone Linux build. Save reports/captures under `unity/evidence/` with dates and versions. A build success alone does not establish playable or visual acceptance.

## 9. Paste-ready first prompt for the Alice agent

```text
Read UNITY_PORT_HANDOVER.md in this copied repository and inspect the actual
working tree before changing anything. The user now authorizes a Unity port
using Unity MCP and external free assets. This supersedes the older guide's
Three.js-only/no-marketplace restrictions. Paid assets require a concrete
proposal and purchase approval; no asset has been purchased so far.

Preserve the browser project, uncommitted work, source licences and frozen
references. Do not print or commit the credential in AGENTS.md. Check
docs/unity-source.sha256. Work in unity/AthenHill on a codex/unity-port branch
without resetting existing changes. Verify Alice's OS/GPU/Unity first.

Use a working installed Unity MCP, or set up the pinned CoplayDev plugin and
matching server described in the handover. Use the real Editor through MCP.
First prove instance selection, scene creation, C# compilation, Play mode
motion, saving and screenshot capture with the MCPProbe scene. If a probe
fails, report and diagnose the actual error before building on it.

Then attempt Unity 6.3 LTS + URP: install a compatible pinned glTFast, import
world.glb and player-candidate.glb, preserve materials/UVs/vertex colours,
animation and the skinned shadow proxy, and validate units/handedness with an
asymmetric probe. The default player.glb is the rejected old character.
Do not rerun the currently failing Blender optimization pipeline or overwrite
the last verified GLB. The existing audio module is not integrated.

Complete the first playable West Gate to Hill Tree slice with real keyboard
movement, collision, animation and the follow camera. Save/reopen the scene,
capture cam_hill plus the character close-up, inspect Console and measure the
actual render. Continue through the handover's U0–U5 milestones as each passes.
Use one agent for scene mutations and independent review where useful.

Preserve the four NPCs, shop, travel overlay and objective behavior before
adding features. Target 60 FPS at 1080p with the existing budgets. Distinguish
a faithful engine port from final visual quality: the supplied realistic
bearded-armour concept remains the character target. Report real screenshots,
tested behavior, measured hardware and remaining defects; do not declare the
graphics solved merely because the project now runs in Unity.
```
