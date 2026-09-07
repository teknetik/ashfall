# U3 — restored city loop

Verified 7 September 2026 in Unity 6000.6.0f1 graphical Editor through the pinned MCP.

Passed real keyboard input: four NPC conversations and follow-up choices, modal
movement blocking, one flask purchase (25 → 21 credits), scrap sale (21 → 22),
Lattice link, all visit objectives, pause movement blocking, inventory/notes number
shortcuts, reset, Ring Gate offline message, mute toggle, reduced motion toggle,
credits route and a second Lattice destination. Setup teleports are explicitly used
by this verb test; U2 separately verifies continuous keyboard traversal.

Four Edit Mode shop tests passed, including invalid/insufficient/overflow atomicity.
`city-loop.json` records the final input run. `editmode-tests.json` records model tests.
Console returned zero errors after compilation. Three actual Game View screenshots
are included; their docked 879×397 resolution is not a 1080p performance claim.

The travel overlay has an editable four-ring tunnel during its 1.25 s transition;
reduced motion suppresses it. Rendered UXML panels were inspected for readable
labels, trade feedback and log clipping. The generic static UI detector is recorded,
but it is not a Unity layout/accessibility test.

All assets are persisted in the scene. NPC definitions/catalog, UI Builder files,
waypoint transforms and interaction markers are editable without source-code changes.
Sound, rendering budget, final visual likeness and standalone qualification remain
U4/U5 work and are not accepted by this gameplay checkpoint.
