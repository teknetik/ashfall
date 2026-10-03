# Field rifle and Warden plate carrier, 2 October 2026

Carl: "make the rifle in game too, make a quest to get it. and armour."

## What was built

- **Held field rifle** (`Berms held rifle` under the colonist's right hand): the Meshy field rifle Codex generated for
  the inventory inspect view (`meshy/field-rifle-20261002`, 29,785 triangles, 0.9 m), mounted for the two-handed rifle
  hold. Barrel axis and muzzle end are measured from the mesh by `RifleArmourInstall.Rifle`; the holder is unit-scale
  under the 0.01-scaled Meshy hand bone like the pistol holder.
- **Rifle holds**: two library clips fetched on a fresh Meshy rig of the colonist (the 27 Sep rig had expired;
  `meshy/character-feel-20260927/rig_player_rifle.py`, record `player-rifle/rig.json`, 5 + 5 × 3 credits):
  "Rifle Turn Left" (573) frozen at 95 % as `rifle_hold.anim` (the raised two-hand hold), "Lower Weapon, Look, Raise"
  (334) frozen at 50 % as `rifle_carry.anim` (hand at the hip, muzzle down-forward). Retargeted with the character-feel
  bind-pose deltas. `PlayerWeaponPose` mixes carry and hold on legacy layer 5 so the upper body always holds the rifle
  while it is drawn; the raise weight follows aiming, shots and the draw as for the pistol.
- **Controls**: 8 draws / holsters the rifle once a primary weapon is equipped (slot 8 on the hotbar shows it); 7 the
  pistol; drawing one holsters the other. The rifle fires while the button is held (`automaticWeaponIds`). First person
  shows no rifle view model yet (the pistol view model hides while the rifle is drawn).
- **Warden plate carrier** (`Warden plate carrier` under the chest bone `Spine`): Meshy text-to-3D
  (`meshy/plate-carrier-20261002`, 30 credits, 24,192 triangles), 0.58 m tall, shown by `PlayerArmourVisuals` while
  `warden_plate_carrier` is equipped in `armour_chest`.
- **Quest**: two field orders after Steady Hands. *Long Arm* (CraftItem): a rifle receiver from the relay-knoll gunners,
  report to Brann, fabricate the Field Rifle at his bench (receiver + 6 alloy + 3 filament + 4 nanite, engineering 20).
  *Plate Carrier* (CollectItem): clear the caravan scavengers and search the caravan strongbox (the hauler cargo bed
  node, now on `loot_caravan_strongbox`). Ossa and Brann have order-aware lines. Guidance targets `relay_knoll` and
  `caravan`, encounter bindings for both.
- Saves: a field rifle issued by the earlier catalog's starting pack is withdrawn on load until Long Arm is complete.

## Editor audition (edit mode, open range apron at `RifleArmourInstall.Stand`)

`editor/sheet.png`: carry quarter and side, hold front/side/quarter, vest front/quarter/back.
`editor/tune/tune.png`: carry frames 0–80 % of clip 334 (50 % chosen) and vest heights 0.50/0.58/0.66 m (0.58 chosen).

## Native verification (batch `rifle3`, development build of the dirty tree at 7fdbd282, 2 Oct 14:12)

`unity/tools/check_rifle_quest.py` (real keyboard and mouse input through the QA bridge), report in
`rifle3/quest/report.json`, captures in `rifle3/quest/run-a` and `run-b`:

- Phase A, new game: locker, draw, three plates; **first contact is two scrap drones 30.4 and 33.6 m from the gate
  marker**, the HUD marker reads "SCRAP DRONE · 8 m", the pair goes down to real F input (7 shots), the depot nest
  (6 droids) is cleared and the primer completes. The pistol carry capture shows the muzzle-down hold. No runtime
  exceptions.
- Phase B, Continue on a fixture save at Long Arm: Brann opens with the receiver line and the order moves to
  fabrication; E at the workbench opens the fabricator and the Field Rifle is fabricated (receiver consumed);
  Long Arm completes and Plate Carrier becomes current; the rifle is equipped by inventory drag; 8 draws it (notice,
  hotbar slot 8 live); holding F fires a 5-shot burst; 7 switches to the pistol while armed and 8 holsters; the
  pistol view model stays hidden in first person with the rifle; the caravan scavengers are cleared with the rifle
  (4 kills, 18 shots); the strongbox search yields the plate carrier (+ alloy, filament, capacitor); Plate Carrier
  completes and the Depot Foreman order follows. No runtime exceptions.
- Three failures were the check's own measurements, fixed for the re-run (`rifle4`): it read the crafting session's
  default weapon id instead of the active loadout (the snapshot now reports `activeSlot`, `weaponId`, `rifleShown`,
  `wornArmour`), the vest drag did not scroll the chest slot into its scroll view, and the depot marker was read
  before facing the depot. The aim captures were taken from behind the colonist; the re-run turns it to the camera.

Batch `rifle3` results: city loop PASS, range tutorial 10/10, Berms expansion check 8/8, Edit Mode tests 207/207
(`editmode-2.xml`, after the fixture updates in `editmode-2a.xml`); A/B against `batch-berms-expanse` at cam_hill,
cam_avenue and cam_gate (13:00 and 20:30, two runs each) within the desktop's run-to-run drift: p50 deltas
+0.24/-0.02, +1.04/-0.32, -0.09/-0.17 ms (`rifle3/ab/ab-summary.json`); the held rifle and vest are inactive in those
views, so no cost was expected there. Lookbook of the pass cameras in `rifle3/lookbook-p01/`.

**Re-run `rifle4`** (14:39, rebuilt with the snapshot fields, data fixes and test icons): `check_rifle_quest.py`
**34/34 checks pass** (`rifle4/quest/report.json`, captures `rifle4/quest/run-a`, `run-b`, sheet
`rifle4/quest/final-sheet.png`): first contact 30.2 / 31.7 m from the gate, "SCRAP DRONE · 7 m" then
"MACHINE DEPOT · 24 m" markers, primer complete; Brann, bench, Field Rifle built; rifle equipped and drawn with 8
(rifle model shown, pistol hidden), 5-shot burst, 7/8 switching; caravan cleared with the rifle, strongbox gives the
plate carrier, it equips in the chest slot, the vest model shows on the colonist, and the save records both.
`Builds/LinuxDevelopment` is this build.

Known gaps: no first-person rifle view model; the rifle fires the pistol's sound layers; the open-hand rig has no
finger bones (both weapons sit in an open hand); the vest's back panel sits inside the suit's back shell; the gunner
receiver and carrier item icons are crops of the Meshy renders, not the inventory illustration set.
