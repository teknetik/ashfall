# Two intermittent native check failures (3 October 2026)

Code-level investigation only (no native run in this pass); the round's native batch verifies the fixes.

## a) `check_rifle_quest.py` "A: the HUD marker now points at the machine depot"

**Seen:** FAIL in `unity/evidence/playtest/20261003/pt1/quest.out` and `overnight/20261003/on2/quest.out`; PASS in `on1`
and `on3` ("MACHINE DEPOT · 25/26 m").

**How the marker works.** `CombatHud.UpdateGuidance` shows the label only while the target point (the target + 1.8 m) is
in front of the camera, inside 5–95 % of the view's width and 8–92 % of its height, and within `guidanceRange` 60 m.
During the primer's Depot step the target is `BermsTutorial.NearestLive(depot)`: the nearest live, active depot droid.

**Ruled out (game side).**
- Droids not there yet: `DroidEncounter.Activate` instantiates every spawn synchronously in the same call that flips the
  step to Depot (`BermsTutorial.Advance`), so `NearestLive` has a target from the next HUD frame.
- Parking: the depot nest's `parkBeyond` is 0 in the scene (only the outer-site clusters park at 170 m), so its droids
  are never switched off.
- Range: the nearest depot droid was 25–26 m away in the passing runs (spawns at about (-84, -28); the player ends the
  first-contact fight near (-76, -6)).
- Occlusion, combat or aim state: the marker has no raycast and no combat/aim condition.

**What the evidence shows.** The last `ui-layout.json` of the failing phase A (written by the last poll, nothing after
it calls `uiSnapshot`) still has the marker's text from the first-contact fight, "SCRAP DRONE · 3 m", with
`visible: false`: during all eight polls (about 4.5 s) the marker was never drawn, although the depot target existed.
So the target was outside the viewport window for the whole poll.

**Cause.** The check's camera. `qa.face()` sets only the yaw; the pitch stays where the fight helper's last `aim_at`
left it. `aim_at` pitches straight at the droid it shoots, clamped to -35..40 degrees, and the first-contact fight ends
with a scrap drone killed about 3 m away (the label above), where that pitch is steep and depends on how high the
drone was hovering at the moment. With `qa.view('follow')` the vertical field of view is 50 degrees and the marker needs
the point within ±21 degrees of the centre line, so a pitch beyond about 24 degrees down or 18 degrees up puts a target
25 m away (only a few degrees below eye level) outside the window. The outcome depends on where the last drone died,
which matches the run-to-run flip. The camera pitch was not recorded, so this is the most likely cause rather than a
measured one; the fixed check now records it.

A player is not affected the same way: the marker is deliberately in-view only, and a player looking at the depot sees
it. A possible design follow-up (not done here, a UI decision): clamp an off-screen guidance marker to the screen edge
as an arrow.

**Fix (check).** `unity/tools/check_rifle_quest.py`: each poll faces the nearest live droid within 60 m (the marker's
own target, falling back to the depot centre) **and sets the pitch to 6 degrees**; it records the camera after the
first-contact fight (`report.phases.a.cameraAfterFirstContact`) and per poll the pitch, yaw, player, target, live count
and the guidance label's text and visibility (`report.phases.a.depotMarker`), so a remaining failure is diagnosable.

**Native batch should verify:** the check passes; `cameraAfterFirstContact.pitch` across runs (a steep value in a run
that would have failed confirms the cause).

## b) `check_next_level_enemies.py` "<site>: a salvage cache collected with real E" (prompt "")

**Seen:** `post_relay` in `pt1` and `on1`; `southern_cache` in `on3` (also both of that site's crate checks); PASS in the
other runs. The loot roll happened every time (`lastLoot` "Dropped: …").

**Evidence.** Every failing `collected` record has `walk: "walk_to (...) stuck at [...]"`:

| run | site | cache target | player stuck at |
| --- | --- | --- | --- |
| pt1 | post_relay | (-432.8, 23.3) | (-422.9, 4.0, 23.3) |
| on1 | post_relay | (-435.2, 22.2) | (-422.9, 4.0, 22.4) |
| on3 | southern_cache | (-243.7, -146.2) | (-238.9, 0.0, -142.3) |

The player never got within the cache's interaction range (WorldInteractable `range` 2.3 m), so there was no prompt.
In the passing post_relay runs the chosen kill was at (-429.7, 28.1) / (-428.6, 30.8), north of the obstruction.

**Cause (check navigation, not the cache).** `qa.collect_at` walks a straight line from the site landmark to the death
position and tries four ±0.9 m offsets around it, all reached along the same line. At Post relay the line from the
landmark (about (-410, 21)) runs into the toppled relay mast props at (-426.1, 24.6) / (-429.2, 22.8); at Southern
cache it runs into the pump-house props and wash bank south-west of (-239, -142). The crate searches at the same sites
pass because `search_crate` already circles the target and comes in through 6 m waypoints from other sides. In on3
the player stayed on the far side of the same obstacle for the two crates too, then reached the third crate as soon
as a waypoint led round it (so the player was not trapped; the straight-line approaches were blocked).

Also checked on the game side: the cache spawns where the wreck settles, on a flat clear spot up to 1.5 m from it
(`SalvageCache.FindSpot`), so the death position is only approximate; the cache prefab has no collider, so it cannot
trap the player; its prompt is set in `Fill` → `Refresh` the frame it spawns.

**Fix (check + QA data).**
- `NativeQa` `crafting.json` now lists the live caches (`caches`: position, stack count, source).
- `check_next_level_enemies.py` `collect_cache()` replaces `qa.collect_at` for this check: it targets the listed cache
  nearest the death position (within 4 m), and comes in at 1.0 / 0.7 / 1.4 m from seven sides, routing through 6 m
  waypoints when a side is blocked (the crate search's method). `report.sites.<id>.collected` records `cacheListed`
  and every failed walk.

**Native batch should verify:** all four sites pass "a salvage cache collected with real E", and `cacheListed` is true.
