# Alice Unity port environment

Inspected 7 September 2026. U0 passed; no city or performance acceptance yet.

- Host workspace: `/home/teknetik/code/ao2`; branch `codex/unity-port`.
- Ubuntu 24.04.4 LTS x86-64; GNOME on X11; display `:0`, desktop capture 1600×900.
- NVIDIA GeForce RTX 3060; driver 595.84. Verified with host `nvidia-smi`.
- Graphical Editor: Unity 6000.6.0f1, installed at `/home/teknetik/Unity/Hub/Editor/6000.6.0f1/Editor/Unity`.
- This uses the already-installed 6.6 patch instead of the handover's suggested 6.3 baseline. Compatibility is being tested, not assumed.
- Editor reports OpenGL 4.5 NVIDIA hardware renderer. GPUResidentDrawer is unsupported on this API; do not count on that batching path.
- Project: `unity/AthenHill`, created from the installed URP blank template; URP 17.6.0.
- Intended first build: Linux x86-64; standalone build not tested yet.
- CoplayDev Unity MCP package pinned to v10.2.0; Python server `mcpforunityserver==10.2.0`.
- MCP uses `http://127.0.0.1:18081/mcp` because 8080, 8081 and 8082 were already occupied. No existing service was stopped.
- Live instance: `AthenHill@7f7f353bae1a07d0`.
- The task calls real MCP using `unity/tools/unity_client.py` because Unity tools were not exposed in this task's tool catalog. The Editor bootstrap only establishes the connection; scene mutations use MCP.
- All entries in `docs/unity-source.sha256` passed before project creation. Existing browser changes and frozen references retained.

## Probe diagnostics

Initial material creation failed because the Materials directory did not exist; created it and refreshed before retrying. MCP's default ID lookup hit `NotImplementedException` on this Editor patch; even name lookup eventually used that broken method. An embedded copy of v10.2.0 contains a documented Editor-only compatibility patch in `Packages/com.coplaydev.unity-mcp/ATHEN_HILL_PATCH.md`. The Python server remains unmodified 10.2.0.

Probe passed: real MCP created and saved the scene; compiled and attached ProbeRotation; entered Play; sampled cube yaw 2.9001° then 36.2726°; captured both frames; exited Play; saved and reopened the scene; captured mcp-probe.png. Final Console error query returned zero entries. The +X label was corrected after visual inspection. Tool schemas and responses are saved alongside the capture.
