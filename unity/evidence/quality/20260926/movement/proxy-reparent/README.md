# Player shadow presentation hierarchy — 26 September 2026

The enabled shadow-only capsule was directly beneath the CharacterController
root. The movement interpolation presents `PlayerMotor.visual`, so that sibling
shadow retained 50 Hz motion and could lead the visible actor by up to 12 cm
while running. The parent authorized a narrow saved-scene correction.

Through live Unity MCP `execute_code`, the existing capsule was reparented under
the unit-scale MeshyPlayer outer visual wrapper. The operation used Undo,
validated the current clean/non-playing scene, checked the absence of collision,
and preserved world/local pose, object identity, mesh, material and renderer flags.
The current scene was saved through EditorSceneManager. No prefab asset was
replaced or applied; this is an added-child scene override.

[Scene diff](scene.diff) contains three intended changes: removal from the physics
root's child list, the proxy Transform parent, and the MeshyPlayer added-child
override. [Machine verification](verification.json) compares every before/after
field: only `parent` changed. Scene clean, nine actors retained. The recoverable
pre-change scene is retained compressed as `scene.before.unity.gz`.

First execution did not mutate anything: its in-memory C# compilation rejected
obsolete `GetInstanceID` calls. The second request uses installed Unity 6.6
`GetEntityId().ToString()` and succeeded; both request/results are retained.

`FollowCamera` caches renderers from all descendants of the player root. The proxy
stays within that subtree, so first-person hide/restore still includes it and
preserves ShadowsOnly. Its capsule is symmetric around Y, so inheriting the
visual's yaw does not distort its silhouette. Animation is nested beneath the
outer visual and does not animate this wrapper's translation.

Live per-actor renderer inspection is retained in [actor-shadows.json](actor-shadows.json):
the real player skin has 10,391 triangles and shadows On, while the retained
capsule adds 832 shadow-only triangles. All four guards (38,071 each), three
travelers (10,177 each), and mechanic (5,587) cast/receive shadows. No assignment
was changed. Capsule silhouette redundancy can be evaluated separately.

`CharacterMotionAssetTests.SavedPlayerShadowProxiesShareTheInterpolatedVisualHierarchy`
loads the saved scene in a disposable preview scene and checks shadow-proxy
ancestry, absence of proxy collision, and connected player prefab. It does not
replace the user's active scene. The full live Unity EditMode suite passed
**50/50**, with no failures/skips, in 6.297 seconds; the preview-scene test passed
in 5.831 seconds. Raw job `d63f2859ee5c4ab2a5f3de30bebe613e` is retained in
[editmode-results.json](editmode-results.json). Afterward the active AthenHill
scene remained clean with nine actors, the same root pose and the corrected proxy
parent; see [after-tests.json](after-tests.json). Native moving review remains
unverified and no AAA animation/physics acceptance is claimed.

After the later diagnostic/shader source changes settled, a final refresh and
full rerun again passed **50/50** in6.855 seconds, job
`a7b7aa2788014c249470e8d23c415198`. [Final raw result](final-editmode-results.json)
and [verification](final-suite-verification.json) record a clean active scene,
nine actors, no test output and no new clone/hideFlags/DontSave warning matches
in the Editor log. Source hashes identify the exact tested runtime/helper files.
