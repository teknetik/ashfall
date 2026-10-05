# Ward home, hotbar, journal and mouse look (5 October 2026)

Carl (5 Oct 2026, ~02:40): "we need a place to store our loot" → chose option 1, *rent one of the container homes*:
"a locker and shelf rack as the stash, a bunk as a rest and save point, a lease you get from Linn or the Wardens".
In the same message: "the hot bar we need to be able to configure it with items from the inventory. drag a med pack
slot 0 for example. I like to keep primary/secondary weapons on 1-2. … the hold left mouse to look around thing is
janky. maybe only release the cursor when a UI is open. We also need a "journal" screen to track missions. mission
objectives should be tracked on the compass (and map once we get to that build/upgrade). Journal screen should allow to
select your current mission for tracking purpose".

Not yet accepted by Carl. This file is the working log; another session can resume from it.

## Design (decided in this pass; Carl did not pick the lease price or giver, so these are defaults)

### Mouse look
- In play the cursor is locked and hidden and the mouse always turns the camera (no more left-drag orbit).
- Any open UI (pack, journal, dialogue, counter, bench, pause, settings, stash, rest) frees the cursor.
- Hold **Left Alt** in play to free the cursor briefly (HUD buttons, moving HUD windows); the camera holds still.
- With a weapon drawn, **left mouse fires** (aiming or not); right mouse aims; F still fires.
- Settings → mouse sensitivity and invert Y.

### Hotbar (ten slots, keys 1–9 and 0)
- **1 = primary weapon** (field rifle), **2 = secondary weapon** (scrap pistol): draw/holster, as 8/7 did before.
- **3–0 are assignable**: drag a usable item (medkit, trauma kit, nano recharge cell, surge pack) from the field pack
  (Tab) onto the new HOTBAR strip under the pack grid, or select it in the pack and press 3–9/0. Drag a strip cell off
  the strip (or right-click it) to clear it. Dropping a weapon on strip cell 1/2 equips it as primary/secondary.
- A slot uses exactly the item assigned; its count shows in the corner (0 dims the slot; the assignment stays).
- Defaults for a new game and for saves without a hotbar: 3 = Medkit, 4 = Nano Recharge Cell.
- The old fixed actions go: Flask (1), Lattice (3), Talk (4) are E; Pack (5) is Tab; Notes (6) is the journal (J).
  The upper-right utility strip keeps Inventory / Journal / Pause buttons.

### Journal (J, or the Journal button)
- Missions tab: ACTIVE and COMPLETED lists; the selected mission shows giver, area, summary, a step checklist
  (done / current / to come), rewards when known, and **Track**.
- Missions: *Arrival in Ward* (the city visit), *Warden's Primer* (Outer Berms primer), each of Ossa's field orders
  (titles from the field-order data; completed ones stay listed), *A Roof in Ward* (the home lease).
- One tracked mission (saved). The upper-right Field Notes box shows the tracked mission; the compass carries a cyan
  tracked marker everywhere (city and Berms), pinned to the compass edge with a chevron when behind; its name and
  distance show under the compass when near the centre; the in-world guidance label follows it. A newly started
  mission is tracked automatically when nothing is tracked or the tracked one completes.
- Notes tab: the Ward notes text that "City notes" showed.
- Map: not yet (Carl: "and map once we get to that build/upgrade").

### The home (the rust container on the south wall)
- **Which**: `Wall home south 2` (WallHomeA, world (27.5, 0, −41.4), yaw 0, street side +Z) becomes the new prefab
  **WallHomeP** (the player's home): same exterior, a hinged door leaf, a fitted interior. The other WallHomeA
  (north 2) stays closed.
- **Lease**: Linn (hill regular, the elder) keeps the housing roll. New Linn choice "Is there anywhere in Ward I could
  stay?" → the empty container on the south wall → "I'll take the lease (40 cr)". Price lives on the scene's `WardHome`
  component. Flag `home_leased`.
- **Mission** *A Roof in Ward* starts once the primer is complete (loot begins): ask Linn → lease → store something
  in the locker.
- **Door**: locked before the lease ("Locked · Linn on the hill holds the lease"); afterwards it swings open as you come
  near and closes behind you.
- **Locker** (stash): E opens the stash window: PACK | LOCKER grids, Store/Take one or all, "Store all salvage".
  60 stacks, no weight limit, saved with the game.
- **Bunk**: E → Rest: sleep until morning (06:30) or evening (18:30), or just get up. Resting restores vitality and nano,
  saves, and Continue starts you at the bunk from then on.
- **Camera**: inside the container (2.35 m wide) the follow camera goes to first person and comes back out at the door.
- **Bench link**: Brann's workbench uses parts from the home locker once the pack runs short (the pack always first;
  only while the home is leased; `WardHome.lockerFeedsBench` turns it off). The bench shows "(n in your locker)".
- Not in this pass (next steps): more homes, home upgrades, a bench at home.

### Save
Version 4: `hotbar`, `stash`, `journal.tracked`, home flags (`home_leased`, `home_rested`). Older saves load with the
default hotbar, an empty locker and the auto-tracked mission.

## Work split
- Code (main session): input/camera, hotbar model + HUD + pack strip, journal model + panel + compass, stash model +
  panel, lease/rest/door/camera-zone components, save v4, QA tools (city loop: Tab/J instead of 5/6; rifle quest and
  next-level checks: 1/2 instead of 8/7; checkpoint: 2 instead of 7), tests, docs.
- Art (background agent): `home_interior.py` + WallHomeP variant in `art/ward_buildings_20261003/author_buildings.py`,
  Blender review renders; then `Editor/WardHomePass.cs` install with review cameras `cam_home_*`.

## Log
- 5 Oct 02:44 — survey done (GameInput, FollowCamera, PlayerCombat, GameSession, CityHud, CombatHud, PackPanel,
  CharacterLoadoutPanel drag, FieldOrders, BermsTutorial, WardSaveGame, container homes in author_buildings.py).
- 5 Oct ~03:15 — code done for mouse look, hotbar, journal, home runtime (WardHome, HomeDoor, CameraConfineZone,
  StashModel, StashPanel, RestPanel), save v4, QA snapshot fields (`cursor`, `hotbar`, `journal`, `home`), data patch
  `apply_data.py` (idempotent; previous assets in `previous/`) and `apply_input.py` (input actions). Edit Mode 286/286
  (`unity/evidence/ward-home/20261005/editmode-r2.*`; new suite `HomeJournalHotbarTests`). QA tools moved to the new keys
  (city loop and draggable UI: Tab/J; checkpoint, rifle quest, next-level enemies, the shared `qa.py`: 2 sidearm / 1
  primary; field supply: 3 medkit / 4 nano). Ossa's locker and range lines are unvoiced (their old takes say "7").
- 5 Oct 03:20 — tracking refined: until the player picks a mission (Track / T), tracking follows the most pressing active
  one (field orders, the primer once begun, the home, the city visit); a picked mission stays tracked until it completes
  (saved as `journal.chosen`). An automatically tracked mission can be pinned ("Keep tracking this mission"). Edit Mode
  286/286 (`editmode-r3`). Docs: README controls table and home paragraph, DESIGN hotbar/journal/locker, AGENTS §2 and the
  Interface row. Native check written: `unity/tools/check_home_journal_native.py` (needs the home installed).
- 5 Oct 03:40 — bench link: `CraftingModel.Reserve`/`ReserveOpen` (the leased home's locker; pack units first, locker
  units consumed after the pack transaction commits), `IngredientAllocator` over any pool, `FromReserve` for the bench
  rows. Edit Mode 287/287 (`editmode-r4`).
- 5 Oct ~03:50 — art: Phase 1 (home) STOPPED partway, at the user's instruction (image reads of the review renders were
  refused with "stop and wait"). State:
  * Authored: `art/ward_home_20261005/home_interior.py` (variant P: A's exterior with a real cut-in door opening, welded
    frame, threshold, kick plate, real glazed window, lower second step, awning street edge +0.15 m; door leaf as its own
    object `WallHomeP_DoorLeaf_LOD0/1`, origin = hinge axis (0.86, 0.51, 1.277), outward, closedYaw 0 / openYaw −100;
    lined, fitted interior: bunk, olive stash locker "S2", slotted-angle rack + Poly Haven prop mounts, fold-down table,
    stool, services, clothes, mirror/photo/calendar, rug; walkable colliders incl. `COL_DoorLeaf`; anchors door_hinge,
    door_centre, door_outside, door_inside, locker_use, bunk_use, wake_point, interior_bounds; three interior lights).
    Guarded `homep` edits in `art/ward_buildings_20261003/author_buildings.py` (A/B/C paths unchanged).
    Textures `textures/HP_Photo.png`, `HP_Calendar.png` (no lettering). Tools: `verify_variants.py`, `review_home.py`,
    `make_textures.py`.
  * Checked: A/B/C re-authored into `scratch/baseline/` match the committed json, triangle counts and vertex positions
    (except a pre-existing vertex-order nondeterminism in WallHomeB LOD1 rubble). Not re-run after the P edits.
  * NOT done: WallHomeP is only in `scratch/p1/` (LOD0 38,182 / LOD1 13,313 / LOD2 24 tris; that json predates the
    door_centre/closedYaw/openYaw names, which are in the script only). Nothing written to Unity's Assets. LOD1 not
    trimmed. README_home.md not written. No Unity work.
  * Renders: `review/p1_*.png` (ext_closed, doorway_west, doorway_east, plan) were inspected — interior too dark (lights
    inside opaque bulb meshes; fixed in review_home.py), ribbed VH_Paint read as shutters (swapped to WB_TankTeal,
    WG_OlivePaint, WB_BlackSteel, WG_BonePaint, WB_CylRed), toothy door-foot rust (now a band). `review/p2_*.png`
    (ext_open, doorway_west, doorway_east, plan) exist but were NOT inspected. ext_closed/locker/bunk/inside_out at p2
    and later not rendered.
  * Resume: inspect p2, fix, render remaining views, trim LOD1, author `homep` into Assets with
    `blender.sh art/ward_buildings_20261003/author_buildings.py -- homep`, re-run `verify_variants.py -- after homea homeb homec`,
    write README_home.md.
- 5 Oct ~03:55 — early native checks before the home install (`unity/evidence/ward-home/20261005/early`, `early2`;
  builds of 03:28 and ~03:50 from the working tree; the 01:29 Field Supply build is kept as `Builds/batch-fs` for A/B):
  city loop PASS, range tutorial (check_checkpoint) PASS; `check_home_journal_native.py` up to the home: cursor locked in
  play and freed by the pack and by Left Alt, real XTEST mouse motion turns the camera, the HOTBAR strip (first build: the
  strip was built but never added to the pack column — fixed, plus a PackPanel Edit Mode test), drag trauma kit → 0,
  select medkit + 7 → 7, salvage refused, HUD bar shows pistol/nano/medkit/trauma, journal lists missions, T tracks,
  Field Notes shows the tracked mission, Linn's housing roll and the 40 cr lease. Fixed after it: a "New in your
  journal" notice queued while a save was being applied (cleared on restore); the compass marker named for QA; the
  trauma-kit check now expects a full heal (armour made the 45 damage a 37.5 wound). Edit Mode 288/288 (`editmode-r6`).
  Carl back ~03:50: Codex login works again; the art agent resumed with Phase 1 + Phase 2 (install) instructions.
- 5 Oct ~04:00 — art: resumed after Carl's go-ahead. Concept target `concept/home_concept_v1.png` (Codex; prompt in
  `concept/prompts.json`). Review rounds p2–p5 inspected (Cycles CPU): fixed the black interior (review lights inside the
  bulbs; InteriorGlow must not cast shadows in Unity), ribbed VH_Paint reading as shutters (flat WB_TankTeal /
  WG_OlivePaint / WB_BlackSteel / WG_BonePaint), toothy door rust, white-board insulation (new tileable
  `textures/HP_Insulation.png`), mattress through the blanket, rug blob, trouser-scarf, flat coat, locker wear blob; added a
  duffel and boots; LOD1 trimmed (13.3k → 10.6k). Anchor names per the runtime (door_hinge closedYaw/openYaw, door_centre, …).
- 5 Oct ~04:05 — art: **WallHomeP authored into Assets** (`Art/WardBuildings/Models/WallHomeP_LOD0/1/2.glb` 36,167 / 10,569 /
  24 tris, `homep.json`; source `art/ward_buildings_20261003/homep-source.blend`). A/B/C files byte-identical before/after;
  re-authored A/B/C identical to the committed records except the pre-existing nondeterministic WallHomeB LOD1 rubble
  (`logs/verify-after.log`). README: `README_home.md` (anchors, colliders, lights, new HP_* materials, remaining defects).
  Phase 1 done; Phase 2 (Unity install, `Editor/WardHomePass.cs`) next.
- 5 Oct ~04:15 — art: **Phase 2 (Unity) done**, `Editor/WardHomePass.cs` (models, install, verify, uninstall, bake,
  capture, revertlightdata). Prefab `Prefabs/WardBuildings/WallHomeP.prefab`; scene root "Ward home" at the old WallHomeA
  transform (27.5, 0, −41.4), that instance inactive; WardHome/HomeDoor/CameraConfineZone wired; InteriorLighting + baked
  probe; landmarks home_door/inside/locker/bunk; cameras cam_home_*. `verify.json` clean (wiring, landmarks, capsule
  paths with the door open, closed leaf blocks, camera clearance, leaf swing clear of Nanofab 2, scene diff). Editor
  captures `unity/evidence/ward-home/20261005/editor/open/` (13:00). Fixed after them (not re-captured in Unity):
  cam_home_door was inside Nanofab 2 (moved), floor timber grain across the boards (UVs turned), insulation too yellow.
  The first bake had saved URP light data onto 13 lights of other passes: reverted (`revert-light-data.json`), bake guarded.
- 5 Oct ~04:25 — art: door leaf now parks flat against the container face (main session: at openYaw −100 it stood across the
  only approach, the lane west of Nanofab 2's pier, with its collider off). `OPEN_YAW = -176` in home_interior.py and
  homep.json (outward, west-hinged; parked x −0.16..0.86, 6–14 cm off the corrugation, handle 7 cm clear, free end 9 cm
  short of the exterior junction box, foot 0.51 over the planter and steps); A's bucket moved out of the arc to (−0.15, 0, 2.2).
  Only WallHomeP re-authored (A/B/C files unchanged). WardHomePass verify now sweeps the leaf box 0 → −176° in 5° steps
  against all scene colliders: 0 hits; paths clear; closed leaf blocks; scene diff clean. No graphics run.
- 5 Oct ~04:15–04:45 — art agent finished Phase 1 + 2 (WallHomeP 36.2k/11.3k/24 tris, `Editor/WardHomePass.cs`, scene
  root "Ward home", old WallHomeA south 2 inactive; verify clean; see README_home.md); door re-parked flat (openYaw −176)
  so the open leaf no longer blocks the only approach (west of the Nanofab pier). Edit Mode 289/289 (`editmode-r7`, with
  the scene test). Build 3 (`build-3.log`). Combined batch (`unity/evidence/ward-home/20261005/batch`): city loop PASS,
  range tutorial PASS; home check FAIL at the walk-in, Field Supply FAIL at a walk, rifle quest 4 failures (plates,
  first contact, caravan fight) — all the same QA artefact: under Hyprland/XWayland an XTEST pointer left off the window
  centre feeds the locked-cursor camera a delta every frame (the camera spins, so bridge-set yaw/aim is overridden;
  pitch pinned at 80). The harness (`qa.py`) now parks the pointer at the window centre before camera/goto/view
  commands (`centre_pointer`); the home check re-centres after closing windows. New `unity/tools/check_mouse_look_native.py`
  drives a temporary uinput relative mouse (a real device path through libinput/Hyprland/XWayland) to check that the
  camera stops when a real mouse stops. Re-runs queued after the A/B: mouselook, home2, quest2, fieldsupply2.
- 5 Oct ~05:00–05:20 — mouse-look investigation (`unity/evidence/ward-home/20261005/diag`). A walk trace (`diag_walkin.py`)
  showed the camera yaw climbing ~2000°/s with pitch pinned at 80 while the harness held W: a phantom delta, not
  geometry. With the virtual relative mouse (`diag_mouse.py`, uinput → libinput → Hyprland → XWayland): old build
  (batch-fs) left-drag orbit 34°, aim mode 19.5° (Hyprland cursor held still = pointer lock); **new build: plain motion
  turns the camera 19.5° with the cursor locked, aim 19.5°** — the real-mouse path works. The earlier 0° in
  check_mouse_look came from Hyprland's cursor being outside the game window (no pointer lock, motion went elsewhere).
  The spin is a QA-only clash: when Hyprland's cursor is over the window it gives XWayland a pointer lock, and the
  harness's XTEST pointer moves (every tap/hold calls focus(), which moves it) fight that lock. Fixes in `qa.py`:
  `park_compositor_cursor()` after the window is floated (PARK_COMPOSITOR, default on) keeps the lock from engaging for
  XTEST-driven checks; `centre_pointer()` before camera/goto/view commands. `check_mouse_look_native.py` does the
  opposite (cursor into the window, no XTEST moves) to exercise the real path. Re-runs: `rerun/`.
- 5 Oct ~05:05 — correction to the entry above: parking Hyprland's cursor outside the window does not hold (every
  `qa.focus()` re-activates the window and Hyprland warps its cursor back in; focus follows the mouse). The "spin" is
  discrete: each XTEST pointer move made while the game's cursor is locked (focus() moved it on every tap/hold) arrives
  under Hyprland's pointer lock as one large delta (~300°, pitch to the clamp). `qa.py` now skips XTEST pointer moves
  while the snapshot reports a locked cursor (`pointer_locked()`); the parking and pre-command centring were removed.
  Real-mouse check `check_mouse_look_native.py` 14/14 (`rerun/mouselook`): a uinput relative mouse turns and pitches the
  camera and it stops when the mouse stops; the pack frees the cursor and gives the camera back without a jump; Left Alt
  frees it; the real left button fires. Second re-run of home / Field Supply / rifle quest queued (`rerun2/`).
- 5 Oct 05:13 — final native results on the 04:27 build (Builds/LinuxDevelopment; the 01:29 Field Supply build is kept
  as Builds/batch-fs): home/journal/hotbar `check_home_journal_native.py` 36/36 (lease, door opens, walk in with the
  camera held in first person, locker store-all/take-one, journal hand-over, bunk to 06:30 with full vitality, LMB fire
  in the Berms, save v4, Continue wakes at the bunk with the locker and hotbar kept), real-mouse
  `check_mouse_look_native.py` 14/14, Field Supply 25/25 (hotbar 3/4), rifle quest 38/38 (hotbar 1/2), city loop PASS,
  range tutorial PASS (`batch/`, `rerun/`, `rerun2/`). A/B vs batch-fs, 2 alternating runs per arm, p50 Δ at 13:00 /
  20:30: cam_hill −0.01 / +0.15 ms, cam_avenue −0.05 / −0.07, cam_gate +0.05 / +0.07, cam_wb_home_south +0.20 / +0.25
  (~300 fps view) — within drift. AGENTS.md row "Container home", START-HERE.txt playtest notes. Nothing committed.
  Open: interior sparser than the concept (under the bunk, shelves, ceiling), wear is geometry only, the coat is stiff,
  the open door leaf has no collider (by design, parked flat), Ossa's two lines unvoiced, no map yet; Carl's save has
  26 cr (the lease is 40).
