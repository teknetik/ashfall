# Rejected first native run

The development build completed, but the player rendered a blank frame. URP tried
to create a disabled ScreenSpaceAmbientOcclusion feature after its resources had
been stripped. That threw during pipeline creation, followed by repeated Blitter
initialization exceptions. Draw counters were 0 / 2 triangles, so the apparent high
FPS was invalid and is not performance evidence. The route test was interrupted.

Correction: remove the unused feature reference from PC_Renderer, rather than
leaving it disabled in the renderer list. The feature subasset remains available
for deliberate future configuration. The native preflight now rejects startup
exceptions and a scene that is not drawing before running the route.

The Editor also exited after this first completed build and faulted during native
cleanup. Its local MCP server was no longer running. Both were restarted in detached
processes; the saved AthenHill scene reopened with 32 roots and no Console errors.
The exact cause of that process exit is not established by the native stack alone.
