# Prepared native tree shadow comparison

This runner is external to Unity. Preparation and fake-transport tests do not
launch a player or send Unity/native commands. Run it only after the parent
provides the new development PID/folder and exclusive command-stream handoff.

```bash
python unity/evidence/quality/20260926/tree-shadow-protocol/runner.py \
  --native /absolute/path/to/new-native-qa-folder \
  --pid ACTUAL_PLAYER_PID \
  --output /absolute/path/to/new-unused-evidence-folder \
  --note 'Native development build03; background opt-in; Editor alive/idle; desktop locked.'
```

Default matrix: hill, avenue and under-canopy cameras; 18 m/one cascade control,
48 m/two cascades and 96 m/two cascades; original versus transient LOD1 shadow
casters in AB/BA order at each profile. Each interval has three seconds of
unmeasured settling and twelve seconds of samples. This is 36 intervals, about
nine minutes plus commands/memory collection. `--pairs 1` selects one original/
reduced pair per camera/profile (18 intervals, about four and a half minutes).
Use the same duration/profile throughout a comparison; do not silently shorten
failed intervals or choose a result based only on average FPS.

The runner validates actual 1920×1080 output, render scale1, MSAA4, full textures,
4096 shadow map, post-processing on, uncapped/VSync0, stationary Play, nine actors
and no video preview. It freezes daylight at12 while actors/animation/effects
remain active. Both alternatives keep the same visible tree LODs and materials.
The reduced-caster state must report three shadow-only renderers, six original
casters disabled, and fewer triangles than source LOD0. The 18 m control is
retested on the new build; earlier binary performance is not attributed to it.

Every raw profile is immediately preserved with unique metadata and positive
counter coverage, actual settings/snapshots and separate Unity/OS/driver memory.
The raw first frame remains; only that pre-start boundary delta is omitted from
the summary. GPU and other nonpositive counters are unavailable, never zero cost.
The native settings snapshot exposes the four-cascade split, not the two-cascade
split. Current source `PC_RPAsset` declares0.25 and the audition changes no splits;
that value is source evidence rather than a separately measured runtime field.
The complete report remains explicitly `qualification: false` regardless of
whether a static interval meets average≥60FPS and p99≤16.67ms.

Command protocol checks:

- Unique command IDs; atomically published JSON; one in-flight command.
- Existing command is never overwritten. A native ownership marker is acquired
  exclusively and removed only when it still contains this runner's token.
- Malformed JSON/schema, false success, new native error, stale response file,
  and unexpected/inter-command acknowledgement IDs fail the run.
- A prior acknowledgement may remain while waiting, but cannot satisfy the new
  command. A missing matching acknowledgement times out after ten seconds.
- Evidence output must be new; each raw interval and command receipt uses
  exclusive creation. Existing native profile evidence is archived before reuse
  of the engine's fixed `profile.json` response path.
- Cleanup restores tree casting, original shadow values and original clock,
  returning the camera to follow. An existing error is preserved; cleanup alone
  may proceed while requiring that no new error replaces it. Detected competing
  ownership defers cleanup to the parent rather than writing into that race.
- Cleanup failure/new runtime exception markers leave `complete: false` and a
  nonzero process result. The player is never killed by this script.

`test_transport.py` exercises these transport contracts against private temporary
files and a fake responder, using no game/Editor process. Eleven cases passed;
see `transport-test-results.txt`. Native execution remains pending until the
explicit new-player handoff. Visual rejection, moving input verification and
target-hardware traversal qualification remain separate decisions.
