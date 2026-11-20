# Showcase programme, phase 2 (19–20 November 2026)

Phase 1 (`art/showcase_20261119/README.md`, commits 982db591 and 9f3a9709) left six gaps unstarted. Carl asked for
them to start straight away, in a separate session, without waiting for his playtest of the phase 1 build. His
playtest notes then added a seventh item (character arms and the pistol hold). This file is the programme record.
`PROGRESS.md` beside it is the running log with real times; `AGENT-RULES.md` is what every agent was told.

**Nothing here is accepted by Carl, and nobody has listened to any of the new audio.**

## What Carl will see, and where to look

Carl on the phase 1 build: "does not feel like much changed but I guess its all in the detail". So, in the order it
shows up in ordinary play:

1. **The main character's arms.** Standing, walking and running, his arms hang by his sides with a slight bend at the
   elbow and loosely curled fingers, instead of held out like a mannequin. The lowered pistol hangs naturally while he
   walks; aiming is an extended two-handed hold at eye level instead of the gun at his face. Look at him from the
   side on the open apron by the spawn, and draw the pistol (key 2) in the Berms. The other characters stand more
   naturally in conversations (Vex, Linn and Brann most; nobody reaches at the player any more).
2. **The colonist's back in every conversation.** The suit is plain olive-brown cloth with seams and canvas repair
   patches instead of speckled camouflage, the chest rig and back plate read as one made object, the neckline is
   smooth and the hair no longer reads as dots. Press E on anyone who talks.
3. **Three new residents at work.** Nadje, a Karaveen trader, at the caravan market by the West Gate (stock crates,
   pottery stall, produce counter). Pell, the tally clerk, at the Node 07 goods dock by the Lattice ring (tally desk,
   scale, bays, handcart). Oren, an old water carrier, between the south-wall container homes and the water ration
   taps behind Vanguard Hall. Each stops at work places and says something as you pass.
4. **The Outer Berms ground between sites.** Gravel sheets, pale clay pans, washes, old Warden berm lines, dunes,
   sandstone outcrops, crater rims, half-buried wrecks and patchy ripples instead of one flat sand look. Walk out of
   the West Gate and across the bowl.
5. **The first-person rifle.** Wheel into first person and draw the rifle (key 1): it points into the view with the
   support forearm and hand on the handguard, at the hip, walking, sprinting and firing.
6. **Night lamps.** Lamps no longer pop in and out as you walk at night (far lamps hand over to a cheap pool of light
   instead of vanishing), and Mira is lit at Basic General.

Build to play: `unity/AthenHill/Builds/batch-p2-notes/AthenHill.x86_64`, built 08:47 on 20 November 2026 from the
working tree on top of commit 9f3a9709 (still uncommitted): the phase 2 build plus the fixes for Carl's six playtest
notes (section "Playtest fixes, 20 November morning" below). `Builds/LinuxDevelopment` holds the same files
(`diff -rq`: no difference). It supersedes `Builds/batch-p2-final` (01:02, the phase 2 build Carl played), which was deleted on 20 Nov at Carl's request. `unity/AthenHill/BUILDS-START-HERE.txt` opens with where to look.

## Items and outcome

| # | Item | What changed | State | Where recorded |
|---|---|---|---|---|
| 1 | Light budget (OpenGL's 32-light cap) | At most 28 local lights in view, ranked per frame; demoted lamps keep their bulbs and get a ground pool that cross-fades over 0.6 s; 8 duplicate retrofit lights merged; Basic General's pier lamps tilted back onto Mira | Installed (lb-9), verify clean, native check 9/9 (lb3, lb4); seen in the game | `art/light_budget_20261120/README.md`, `LightBudgetPass20261120` |
| 2 | Colonist seen from behind | New suit albedo and normal (images only, same rig); vest, plate carrier and helmet re-fitted from the full Meshy sources; collar and sleeve rims smoothed; hair shells denser and matte | Installed (colonist_back-2), verify PASS; seen in the game | `art/colonist_back_20261120/README.md`, `ColonistBackPass20261120` |
| 3 | Outer Berms ground variety | Region mask on the 54 expansion tiles (*Berms Ground V3*), berm lines, dunes, crater rims, outcrops, wrecks, 349 kit pieces, footstep map | Installed (berms_variety-10), verify PASS; seen in the game | `art/berms_variety_20261120/README.md`, `BermsVarietyPass20261120` |
| 4 | Ward residents | Nadje, Pell, Oren: Meshy 7.1 models with finger rigs, work stops on `AmbientWalker`, 18 voiced barks | Installed (residents-16), verify OK; seen in the game; the skin crosshatch was filtered out of the textures (residents-16, no Meshy credits) and is gone in the final build's frames | `art/ward_residents_20261120/README.md`, `meshy/ward-residents-20261120/README.md`, `WardResidentsInstall20261120` |
| 5 | First-person rifle hands | Rifle view model weapon-driven like the pistol's: shooting hand on the pistol grip, support hand under the handguard, hip re-framed, ADS from the sights; pistol glove/arm-guard copies re-skinned onto the arms | Installed (rifle_hands-25), verify PASS; seen in the game | `art/rifle_hands_20261120/README.md`, `RifleHandsPass20261120` |
| 6 | Character arms and pistol hold (Carl's playtest note) | Runtime `ArmPoseCorrector` on 18 humanoid actors; relaxed finger curl; pistol carry pitch 60 → 40 with the wrist taking part of the turn; two-handed aim by IK | Installed (character_arms-8), verify PASS; seen in the game | `art/character_arms_20261120/README.md`, `CharacterArmsPass20261120` |

Every installer is under `unity/AthenHill/Assets/AthenHill/Editor/`, runs as `RunBatch --steps ...` and has `verify`
and `rollback` steps. Review cameras: `cam_lb_*` (13), `cam_cb_*` (6), `cam_bv_*` (14), `cam_res_*` (17, nine of them
follow their resident), `cam_arms_*` (29) plus seven riding review rigs. Rifle hands has no scene cameras (the stub
planned `cam_rh_*`): it is reviewed in first person by `unity/tools/capture_rifle_hands_native.py` at `rifle_stand`.
The playtest fix round added three installers, `LoadoutFixPass20261120` (catalog only, no scene change),
`LinnVoicePass20261120` (Linn's dialogue asset, no scene change) and `GateBarrelsPass20261120` (review cameras
`cam_gb_caravan_east`, `cam_gb_caravan_north`, `cam_gb_rations_west`, `cam_gb_rations_north`; QA landmarks
`gb_<line>_a/_b`).
Evidence: `unity/evidence/showcase_phase2/20261120/` (captures are git-ignored).

## Carl's playtest notes and what was done

Carl played `Builds/batch-playtest1119` (the phase 1 build) during the evening of 19 November.

- **"All the character have their arms in very strange positions"** (21:56; he ticked standing, talking, walking and
  twisted/broken). Not a regression: Mira, Torr, Vex and the player stand identically in the 3–5 October and
  19 November captures. The cause is the Meshy library clips on bulky clothed meshes (arms 12–27° out at idle,
  straight or backward-bent elbows, palms turned back), inherited by the player through the MPFB rest match, plus flat
  spread fingers written every frame by `PlayerHandGrip`. A new agent (item 6) measured every actor in every clip and
  added a runtime corrector.
- **"Is more the main character and not bad bad just in-natural and kinda camp lol"** (21:56). The arms agent was
  re-weighted to the player first: stance, wrists, hands, walk and run swing. Player idle arm lean 12° → 6°, wrists
  26° → 9°, elbows bend forward, fingers curl; walk hand travel kept at 47/41 cm. Seen in the game on build p2-b4:
  natural from four sides standing, a normal fore-and-aft swing walking and running from the side.
- **"the way he holds the pistol looks a little janky too"** (22:07). The lowered carry turned the gun 49–101° inside
  the hand and the raised hold brought it up to the face like binoculars. Now: carry pitch 40° with the wrist taking up
  to 30° of the turn, support hand relaxed while lowered, an extended two-handed aim by IK. Seen in the game: the
  lowered carry is natural while walking; the aim is an extended two-handed hold. **Not fixed:** the gun still turns
  in the hand between carry and aim (30–60°), and the first-person pistol's support fingers stand flat beside the grip.
- **"does not feel like much changed but I guess its all in the detail"** (on the phase 1 build, 21:57). This record,
  `unity/AthenHill/BUILDS-START-HERE.txt` and the end-of-run summary now lead with what is visible in ordinary play
  and where to go to see it.
- **"Upgrade Meshy"** (20:48), his answer to the residents block (below).

## Playtest fixes, 20 November morning

Carl played the phase 2 build (`batch-p2-final`) and sent six notes (`PLAYTEST-NOTES.md`, his words and the readings),
then said "fix those for now" (07:41). Three Opus agents worked on them in parallel: loadout (notes 1–4), Linn's voice
(note 5) and gate barrels (note 6).

| Note | Cause | Fix | Record and installer |
|---|---|---|---|
| 1. "Implants need a eye slot" | The implant slots were HEAD, ARMS, CHEST, WRIST, WAIST, HAND, LEGS, FEET | EYE slot `implant_eye` after HEAD in `Resources/CharacterCatalog.asset`; empty, because no eye implant exists; an empty slot says what fits it; old saves load with the eye empty | `art/loadout_fix_20261120/README.md`, `LoadoutFixPass20261120` |
| 2 and 4a. Leader lines point to the wrong places (implants, armour) | The dots were drawn at each box's own height a fixed 135 px into the map, never against the figure, which is letterboxed and moves with the panel height | `Scripts/AnatomyLayout.cs`: an anchor per body part measured on the figure image (`Resources/UI/ImplantBody.png`), boxes in a column either side as close to their dot's height as they fit, leaders from the box edge to the dot; re-laid out on every size change; compact boxes on narrow pages | same |
| 4b. Stray "Head" at the bottom of both pages | The `equipment-selection` label: the selected slot's name with nothing after it | Hidden on the IMPLANTS and ARMOUR pages; on weapon pages it always has content | same |
| 3a. Hotbar names that do not go away | Not tooltips: drag labels left by the HOTBAR strip's own drag code, which made a new label per drag and ended a drag only if the release reached the panel root | The strip uses the pack's drag: one drag label at most, ended by release on the cell or root, lost capture, a 100 ms watchdog, Escape, a page change or closing the pack | same |
| 3b. Rearranging the hotbar | `HotbarModel.Swap` existed but the strip never called it, and its drags never finished | Drag a cell (3–0) onto another to move or swap; focus a cell and press a number; 1 and 2 stay fixed to the primary weapon and sidearm; the order is saved (save v4 `hotbar`) | same |
| 5. "Linns voice does not match, should be more older and rough" | Linn spoke in Amelia, a bright younger voice (median pitch about 215 Hz); her two housing nodes had no audio at all | All 13 lines (4 dialogue nodes, 9 barks) re-voiced in Seer Morganna (`7NsaqHdLuKNFvEfjpUno`, median pitch 123 Hz), Carl's choice of three candidates ("B is the best I think"); same file paths and GUIDs; the housing offer and the reply after the lease are now voiced; the two older generators skip Linn | `art/linn_voice_20261120/README.md`, `LinnVoicePass20261120` |
| 6. "Barrels on the floor by the waste gate ... need to be able to be walked over or need to go" | The 3 Oct fix put its 0.9 m box over the broken staves at the caravan overflow and left the east whole barrel with none; the Rations stall's set sat under one 0.6 m box including its staves | Colliders re-fitted to the whole barrels only, at the Karaveen caravan overflow by the truck (14 m inside the West Gate) and beside the Rations stall; staves, lids and barrel halves (at most 0.39 m) have none; nothing moved or removed | `art/gate_barrels_20261120/README.md`, `GateBarrelsPass20261120` |

Decisions the orchestrator made, which Carl can overrule: no new implant item, and the Neural Targeting implant stays
in HEAD (its description is a neural "targeting lattice"), so the eye slot starts empty; hotbar slots 1 and 2 stay
fixed to the weapons; "waste gate" was read as the West Gate by the market, and the barrels are those 14 m inside it
at the Karaveen caravan overflow, the spot Carl raised on 3 October.

**Checks.** The `verify` steps of all nine installers (the three above and the six phase 2 passes) pass on the saved
scene (08:40–08:45). Edit Mode 428/428 (run loadout-2). A first run (n1) was 427/428: the loadout agent's own anchor
test measured brightness, which cannot tell the X-ray figure from its glow; the test now checks that each anchor lies
inside its body part's region, and no anchor moved. Native on `batch-p2-notes` (evidence
`unity/evidence/showcase_phase2/20261120/qa/notes` and `loadout_fix/notes`): loadout and hotbar
(`capture_loadout_native.py`) 72/72, inventory redesign PASS, interface 22/22, home/journal PASS, gate barrels
(`check_gate_barrels.py`) 59/59, Linn's voice (`check_linn_voice_native.py`) 25/25 (the new takes play in
conversation, the 28 s housing take plays to its end, leaving early stops her voice), NPC life 27/27, city loop PASS,
range tutorial 10/10, rifle quest 41/41, Field Supply PASS, conversation camera 99/99. Not re-run on this build: the
frame-time A/B, the other showcase checks, gunner separation, next-level enemies and Berms expansion (no rendering or
Berms change in this round). The loadout agent's builds also passed: `batch-p2-ui1` 71/72 (the check counted weapon
slots 1–2; the check was corrected), `ui2` and `ui3` 72/72 with inventory redesign 39/39, interface 22/22 and
home/journal 36/36.

**Seen in the game** (frames from the players): on `batch-p2-notes` at 1920x1080, the implants page (EYE slot beside
HEAD, empty; every leader ends on the part its slot names) and the armour page (PACK on the shoulder; no stray label
under either figure); on `batch-p2-ui3`, a hotbar drag in progress with one label, the strip after moving the medkit
from 3 to 5, and the HUD hotbar after a restart with the saved order; on `batch-p2-ui2`, the two broken barrel sets
(caravan overflow by the truck, Rations stall) with the colonist standing among the staves, and the whole barrels
still solid. Linn's voice: Carl has heard two of the 13 installed takes (greet_shade and hill, his chosen candidate's
lines); nobody has heard the other 11.

**Open from this round.** "Berms" in "You came back from the Berms. I'm glad." transcribes as "bums" or "bombs" after
ten tries; "Karaveen" in the housing offer transcribes as "Caravene"; the greeting is slow (11.5 s) and the housing
offer runs 28.2 s. ElevenLabs: 2,777 credits spent on Linn, 8,318 left. Not verified: a real 3840x2160 screen (the test
display is 1920x1080; the panel scales with the screen); the drag watchdog when the mouse is released outside the
window; the colonist's feet passing through the 0.3 m barrel half at the caravan in motion. Left alone and reported
(not barrels): two 0.4 m steel "severed foot" slabs inside the West Gate that stop the player, off the gate lane; a
retrofit drum cluster by the Repairs wall whose collision box is shorter than its drums; the Item Lab export
`Data/Crafting/Export/ward-crafting.v1.json` is stale and lacks the eye slot.

## How it was run

- One Opus agent per item: light budget, colonist back, Berms variety, residents and rifle hands from 19:37; character
  arms from 21:56 after Carl's note. Agents wrote code and authored assets in parallel, then installed into the saved
  scene and verified with `-nographics`. Rules: `AGENT-RULES.md`.
- Every Unity, Blender and player job went through the wrappers in
  `~/.local/state/ward-programme/showcase-phase2-20261120/`: `seq.sh` (installs and Edit Mode tests on the shared
  Unity lock, memory-capped), `build_to.sh p2-NAME` (refuses any other name), `native_check.sh` (private display :5),
  `blender.sh` / `slot.sh` (one Blender at a time), `run.sh` / `wait.sh` (detached jobs). `lib2.sh` replaced the
  player detection at 00:08 (below).
- Verification was batched (`AGENTS.md` section 7), with one exception: the light-budget agent built and measured on
  its own, because the 32-light cap exists only in the player. The orchestrator built the combined scene, ran the
  regression, a lookbook of the review cameras at 13:00 and 20:30 and the item capture scripts, looked at the frames,
  and sent fix rounds back. Batch runner: `run_batch.sh BUILD TAG [regression packages lookbook ab]`.
- Builds made (all under `unity/AthenHill/Builds/`): `batch-p2-b1` (21:13: light budget, colonist v1, Berms v2, rifle
  hands; no residents), `batch-p2-b2` (22:31: + residents, Berms fix round 1, rifle hands -19), `batch-p2-b3` (23:12:
  + first arms install, Berms fix round 2, colonist fix round, rifle hands -25), `batch-p2-b4` (23:49: arms -8),
  `batch-p2-b5` (00:25: light budget cost round lb-9); light agent builds `batch-p2-lb2` (21:44), `batch-p2-lb3`
  (22:35), `batch-p2-lb4` (23:34). **`batch-p2-final` (01:02 on 20 Nov)** adds over b5: the residents' skin fix and follow
  cameras (residents-16) and the arms pass re-installed over the rebuilt residents. The eight intermediate builds (`b1` to `b5`,
  `lb2` to `lb4`) were deleted on 20 Nov at Carl's request; `batch-p2-final`, `LinuxDevelopment` and
  `batch-playtest1119` remain. Playtest fix round (20 Nov morning): the loadout agent's `batch-p2-ui1`, `ui2` and
  `ui3` (deleted on 20 Nov at Carl's request, with `batch-p2-final`), then **`batch-p2-notes` (08:47)**, the build to play; `LinuxDevelopment` now holds it.
- Fix rounds from the native frames: light budget (pool brightness and colour, near preference, pool cost), colonist
  (hems, collar, shoulder pad, suit v2, helmet grouping, hair), Berms (two rounds: outcrops, ripples, mid-distance,
  then rock colour and sand cap), rifle hands (hip re-framing, palm-up support grip, thumbs, lowered wrists), arms
  (working idles, talk forearms, capture rework).

## Things that went wrong and what they cost

- **19:31, the orchestrator's mistake.** While testing a name guard for `build_to.sh` it ran `build_to.sh playtest1119`
  before the guard was in the file, which started a real build under the playtest build's name. Stopped after about
  three minutes. `Builds/batch-playtest1119` was not changed. `Builds/LinuxDevelopment` had been partly rewritten (6.6
  of 9.7 GB) and was restored from `batch-playtest1119` (`diff -rq`: identical). Four stray PerformanceTestRun files
  were removed from `Assets/Resources`. `build_to.sh` now refuses any name that does not start with `p2-`. The first
  log lines had also been written with guessed times; they were corrected from file times at 19:40.
- **Memory kills.** `ward-watchdog` killed eight Unity jobs between 19:50 and 20:19 (every Edit Mode run, the p2-lb1
  build, the graphics captures) at system swap 27.3–29.3 GB; short `-nographics` installs survived. From 20:27 no
  tests, builds or graphics captures ran while other agents worked, and heavy steps then ran one at a time. Two build
  attempts of p2-b1 failed: 16 GB + 3 GB swap hit its cgroup limit at 98 s (the Edit Mode run had dropped the SENTIS
  scripting define; restoring it 7 s after Unity started made the build recompile every script), and 14 GB + 6 GB was
  killed by the watchdog at 74 s. Shapes that worked: Edit Mode with 15 GB RAM and no swap (o1, 20:40), then 17 GB +
  3 GB after o2 was killed by its own 15 GB cap (12.5 GB anonymous plus 6.2 GB file and shared memory); builds at
  17 GB + 3 GB (p2-b1 in 197 s). The parent session cleared `/tmp` at 20:39–20:41 with Carl's approval (8.6 → 4.0 GB,
  swap 23 → 18 GB). Chrome was the other large holder and was left alone.
- **The machine went down at 20:53** and was rebooted at 20:54; the session restarted about 21:07. Kernel log: the
  NVIDIA driver's "can't alloc VA space for mapping" / NV_ERR_NO_MEMORY and failed modesets at 20:53:08, the power key
  at 20:53:41. Running at the time: the orchestrator's `-nographics` build p2-b1, 21 s in (5.5 GB RAM, no GPU; system
  VRAM read 3.9 GB). Carl's game had closed at 20:52:16. A colonist Blender render had taken VRAM to 11.7 GB at 20:51
  while his game was still open. **Cause not established.** After the reboot the watchdog was restarted (it is a
  transient unit), the scene (saved 20:35) and `LinuxDevelopment` were intact, the tree compiled, and the two resumed
  agents (colonist fix round, residents) had been stopped and were restarted. The wrappers were changed: the Blender
  slot waits while Carl's game runs, and native runs hold the Blender slot, so a render never shares the GPU with a
  player. The other `Builds/batch-*` folders (76 GB) were deleted about 20:52 by the parent session at Carl's request;
  the A/B reference is `batch-playtest1119`.
- **Meshy refused the free plan.** From 19:51 every task creation returned 402 ("Task creation on the free plan is no
  longer supported"), with 126 credits on the account and nothing spent. The residents item stopped with routes, work
  stops, 18 voiced lines and its installer ready. Carl answered "Upgrade Meshy" at 20:48; a paid key went into `.env`
  (balance 1100; the old key kept, not used). The residents cost 123 credits (balance 977). `codex exec` image
  generation had also hit its ChatGPT usage limit until 21 November, so the concept sheets used the `.env` OpenAI key.
- **False "Carl is playing".** `lib.sh`'s `user_player_running` counted every QA test player as Carl's game (test
  players run in `run-p<pid>` scopes, not `ward-*`). Carl's own `Player.log` was last written at 20:51:59: he did not
  play after 20:52. Every later "Carl is playing" in the log and in the orchestrator's messages to him (batch-p2-lb2 at
  22:13, batch-p2-lb3 at 22:53, the waits at 22:20, 23:12, 23:41 and 23:50) was a test run by an agent or by the
  orchestrator. Effects: builds, Blender jobs and agents waited for test runs to end, and two agents handed back
  early. Found at 00:08 and fixed in `lib2.sh` (a player started with `--athen-qa` is not Carl's), which the phase 2
  wrappers use.
- **Editor graphics captures do not fit in memory.** The Unity Editor's main process alone passed 12.8 GB within 30 s
  in graphics mode; it was killed at 12 GB and 14 GB caps, three tries. So review in the Editor was replaced by
  Blender renders, a CPU point-splat renderer (arms), a CPU z-buffer renderer (rifle hands) and frames from the
  development players.
- Smaller: the gunner separation check pressed 7 for the pistol, which has been key 2 since 5 October (corrected); the
  arms, rifle and residents capture scripts' HUD-hide threw outside a dialogue, so the call was removed and their
  frames keep the HUD; the residents' fixed face cameras
  showed walls because the residents are elsewhere on their routes, so the face cameras now follow them.

## Native results

What the orchestrator saw in frames from the development players (paths in `PROGRESS.md`):

- **Light budget:** at the spawn apron 141 lamps want to be lit and 26 real lights are on; Mira is lit at her counter;
  no painted-looking pools after the brightness fix. Lamps popping during fast camera turns were not judged.
- **Colonist:** hair no longer reads as dots, smooth neckline, vest and back plate read as one object, arms by his
  sides.
- **Berms:** the ground reads as varied desert (gravel sheets, pale pans, washes, berm lines, patchy ripples);
  outcrops match the basin sandstone after the second fix round (b4).
- **Residents:** all three read as distinct people at conversation distance and are seen working at their stops
  (17:00, b4).
- **Rifle hands:** before (b1) no hands in frame; after (b3) the rifle points into the view with the support forearm
  and hand on the handguard at the hip, walking, sprinting and firing; ADS sight picture clean; arm guards and gloves
  show.
- **Character arms:** conversations fixed (b3); the player stands, walks and runs naturally seen from the side, the
  lowered pistol carry is natural, the aim is an extended two-handed hold (b4).

Measured:

- Edit Mode: 413/413 (o1, 20:40), **421/421** (o3, 00:21 on 20 Nov).
- Regression on `batch-p2-b1`: city loop PASS, range tutorial 10/10, rifle quest 41/41 (first rifle-hands install),
  home/journal PASS, Field Supply PASS, Berms expansion PASS; gunner separation 7/8 (the stale key in the check; check
  corrected); next-level enemies 40/41 (an empty loot prompt at the southern cache, the same kind of intermittent
  failure recorded on 3 October).
- Light budget, on the agent's builds (lb3, lb4): 21–26 enabled local lights at every review camera at 20:30 with the
  budget on, 30–178 with it off; `check_showcase_light_budget.py` 9/9; check walk 0 of 6,522 frames over 30 lights;
  faces unchanged except Mira (51 → 98–100). Frame time on lb4 (three alternating runs): unchanged at cam_hill,
  cam_avenue and cam_night_spawn_apron, +1.4 ms at cam_night_avenue_west (109 pools). The cost round (lb-9: at most 44
  pools a frame, none under 6 px) did not remove it. Budget off / on / phase 1 build, p50 at 20:30, three alternating
  launches each: on b5, cam_night_avenue_west 22.78 / 24.33 / 22.55 ms; on the final build, cam_hill 16.61 / 16.54 /
  16.11, cam_avenue 16.43 / 16.37 / 16.27, cam_night_spawn_apron 27.59 / 27.62 / 26.71, cam_night_avenue_west 22.48 /
  23.48 / 21.90 ms. So the budget costs nothing at three views and about +1.0 ms at avenue west (44.4 → 42.5 fps); the
  +0.5 ms target was not met there. A two-way test with a tune file (off against on only) gave +0.1 to +0.2 ms at the
  same view for pool caps of 24, 44 and uncapped, but both of its states ran 2 ms slower than in the three-way runs,
  so it does not overturn the three-way figure; the disagreement is not explained.
- Final combined batch on `batch-p2-final` (01:02–02:31 on 20 Nov; `unity/evidence/showcase_phase2/20261120/qa/final`):
  - Saved scene: all six phase 2 `verify` steps pass (the rifle pass after its `rebaseline` step took over the arms
    pass's pistol carry change; the scene file is byte-identical before and after that step). Edit Mode **421/421** on
    the final tree (00:58).
  - Regression: city loop PASS, range tutorial 10/10, rifle quest 41/41 (with the first-person hands assertions),
    home/journal PASS, Field Supply PASS, Berms expansion 8/8, next-level enemies 42/42 (the b1 loot-prompt failure did
    not repeat). **Gunner separation 7/8**: the two relay-knoll gunners came within 1.42 m for two samples (the check
    wants 1.5 m). Three more alternating runs of each build gave a worst separation of 1.84, 2.23 and 1.34 m on the
    phase 1 build and 1.83, 1.36 and 1.44 m on the final build, so the check is marginal on both and the result cannot
    be attributed to phase 2. The droids never overlap.
  - Package checks: combat feel 23/23, combat audio 14/14, NPC life 27/27, camera 99/99, interface 22/22, weather
    13/13, gate names 12/12, light budget 9/9. World map 28/29, then 29/29 after correcting the check: it assumed
    Carl's save had no `map` field, but since his playtest of 19 November the save records the scrapper camp he found.
  - Item captures: character arms 10/10, residents 6/6, rifle hands 12/12, all frames looked at by the orchestrator.
    The runtime actor count is 19, as verify recorded.
  - Frame time against `batch-playtest1119` (`check_showcase_ab.py`, three alternating fresh launches of each build,
    8 s per view, 1920×1080 High with TAA, uncapped; average FPS and p50, phase 1 → final):

    | View | Phase 1 build | Final build | p50 change | Spread of one build's runs |
    |---|---|---|---|---|
    | cam_hill 13:00 | 63.4 fps, 15.69 ms | 62.5 fps, 15.91 ms | +0.22 ms | 1.1 ms |
    | cam_avenue 13:00 | 60.6 fps, 16.47 ms | 59.7 fps, 16.77 ms | +0.30 ms | 0.7–1.0 ms |
    | cam_gate 13:00 | 82.5 fps, 11.25 ms | 88.6 fps, 11.17 ms | −0.08 ms | 0.8–1.8 ms |
    | cam_hill 20:30 | 58.4 fps, 16.04 ms | 60.7 fps, 16.38 ms | +0.34 ms | 0.9–1.1 ms |
    | cam_avenue 20:30 | 63.4 fps, 15.67 ms | 62.4 fps, 15.93 ms | +0.26 ms | 0.7–0.9 ms |
    | cam_gate 20:30 | 91.5 fps, 10.85 ms | 83.9 fps, 11.29 ms | +0.44 ms | 1.0–1.3 ms |

    Reading: phase 2 is about 0.3 ms slower at the city views, five views of six in the same direction but inside the
    spread of one build's own runs; submitted triangles rise by about 0.5 %. The city views sit at 60–63 fps on both
    builds on the rebooted machine. The two heavy night views of the light-budget test are slower than on the phase 1
    build: cam_night_spawn_apron 26.71 → 27.62 ms (37.3 → 36.0 fps, none of it from the light budget) and
    cam_night_avenue_west 21.90 → 23.48 ms (45.5 → 42.5 fps, about 1.0 ms of it the lamp pools). The Berms and the
    residents were not measured on their own (no A/B with their roots switched off).
  - Lookbook of the 50 `cam_lb_*`, `cam_cb_*`, `cam_bv_*` and `cam_res_*` cameras at 13:00 and 20:30 (`qa/final/lookbook-1`
    to `-7`): the night sheets were looked at (Basic General lit with Mira at her counter, courtyard and hall lamps and
    pools reading as light, the colonist's back at night); the day frames of the final build were looked at through
    the item captures and the b4 lookbook, not sheet by sheet.

## What is not verified

- Nobody has listened to the residents' 18 lines (Kirsty, Alfie, Bill) or heard them in the game.
- Lamps promoting and demoting during fast turns at night; the ×1.25 rear-door lamps in the rear alleys; pools on
  characters walking through a demoted lamp's range; the light budget's `rollback` (never run).
- The colonist's helmet in the game (the frames seen were bare-headed); the plate carrier and the other armour pieces
  from behind; the collar-band smoothing step was never rendered on its own.
- The Berms at night after the glass and scorch change; the outcrops close up at player height in every direction;
  footstep sounds on the new map by ear; the world map's survey picture, which now shows the old bowl.
- Residents: foot sliding at the eased stop speeds, LOD switch, faces at 20:30, their frame cost.
- Rifle hands: game-shaded frames without the HUD; with armour worn compared side by side with the pistol.
- Character arms: the aim pose from every side (range bay props block some views); jumps; the yard mechanic and the
  Wardens' Berms copies by eye.
- Tamsin's working idle behind the Field Supply counter with the arms corrector: seen at three instants only (a wide
  stance with the arms now lower than before); not judged in motion.
- The frame cost of the Berms variety pass and of the three residents on their own; a night walk with the mouse.
- Playtest fixes (20 Nov morning): the loadout pages on a real 3840x2160 screen; the hotbar drag watchdog with the mouse
  released outside the window; the colonist's feet passing through the 0.3 m barrel half at the caravan in motion;
  11 of Linn's 13 takes, which nobody has heard; the frame-time A/B and the Berms, gunner and enemy checks on
  `batch-p2-notes`.

## Open defects

- **Light budget:** no frame-time win (URP already shaded only 30 lights per camera); about +1.0 ms at
  cam_night_avenue_west on the final build, the cost round's pool cap notwithstanding. Mira's face (~98/255) is now brighter than the other night faces
  (31–54): deliberate, for Carl to judge. Cookie projection on pools not compared with the real cookie. `pinned` uses
  the main camera, not the player. The night spawn apron (35 fps) and avenue west (43 fps) views are slow in every
  build, phase 1 included; that cost is not lights.
- **Colonist:** a small torn dark shape at the vest's right side strap, slivers at the sleeve hems, a crumpled crease
  under the collar (hidden by the vest), plain cloth in shade. Helmet still a busy riveted design (a remodel or a
  hand-painted retexture would fix it). Plate carrier texture flat with a smeared band at the lower back. Arm guards,
  gloves, boots and leg armour were not re-fitted. The left shoulder pad may meet the deltoid with the arm raised.
- **Berms:** craters are painted, not dug (the ground mesh is locked). Long views draw about 200–230 objects, mostly
  kit prefabs (estimate; merge into zone chunks if the A/B asks). UV seam on each outcrop. World map survey picture
  out of date (`WorldMapInstall20261119 --steps survey`, needs graphics).
- **Residents:** a woven crosshatch shows on the skin (Pell most, at 1.4 m; Oren faint) on b4; filtered out of the
  skin texels (FFT de-weave, residents-16) and gone in the final build's frames, except a faint grain on Nadje's
  forehead at 1.0 m. Oren's Stand and Drink is an empty hand at the mouth; Nadje's apron shows on her back; the
  voices are unheard.
- **Rifle hands:** the shooting hand is mostly below the frame; the left elbow sits just below the frame edge and its
  sleeve shows as a ragged shape at the bottom in the grey renders; thumb bases overlap the rifle by a few mm (not
  visible in first person); the rifle fills more of the frame than the pistol.
- **Character arms:** the pistol still turns 30–60° in the hand between carry and aim (a carry hand pose or a
  low-ready clip would fix it); the first-person pistol's support fingers stand flat beside the grip (view-model work);
  no contact solve for the support hand in the aim; talk gestures keep their character (Linn shrugs, Brann gestures
  forward); residents' and Tamsin's working idles still raise their arms.
- **Loadout:** the eye slot is empty (no eye implant exists); at 4:3 the ARMOUR page is narrow, the boxes go compact
  and long names wrap; the HEAD and EYE dots sit about 15 reference pixels apart at 1080p; the Item Lab export
  `Data/Crafting/Export/ward-crafting.v1.json` is stale and lacks the eye slot.
- **Linn's voice:** "Berms" in "You came back from the Berms. I'm glad." heard as "bums" or "bombs"; "Karaveen" heard
  as "Caravene"; the greeting is slow (11.5 s) and the housing offer runs 28.2 s; Seer Morganna is a fortune-teller
  character voice, and whether she sounds theatrical across all 13 lines is for Carl's ear.
- **Near the West Gate (not barrels):** two 0.4 m steel "severed foot" slabs inside the gate stop the player (off the
  gate lane); the drum cluster by the Repairs wall has a collision box shorter than its drums.

## Proposed next round

1. Carl's playtest of `batch-p2-notes`: the loadout pages and hotbar reorder at his 4K screen, Linn's full set of
   lines (the word "Berms" first), his feet among the broken staves at the caravan; then, at night as well as by day,
   the arms and pistol, the lamps while turning, Mira's brightness and the residents' voices.
2. The pistol in the hand: a carry hand pose or a low-ready carry clip for the player (ask before spending Meshy
   credits), and the first-person pistol's support fingers.
3. The rifle's shooting hand in frame at the hip.
4. The colonist's helmet (remodel or retexture), the plate carrier texture and the remaining armour pieces seen from
   behind; the torn shape at the vest strap.
5. Re-render the world map survey for the new Berms ground.
6. The slow night views (spawn apron, avenue west), which are not a light-count cost.
7. The gunner separation check is marginal on both builds (worst separation 1.3–2.2 m against a 1.5 m limit): decide
   whether the droids should keep more distance or the limit should be 1.2 m. A HUD-hide for captures outside a
   dialogue.
8. The lamp pools' cost at the night avenue view, and why the two-way and three-way tests disagree.
9. If Carl wants them: an eye implant item for the new slot; Linn's "Berms" line in another voice or with changed
   text; a ramp collider on the West Gate wreck slabs; the Repairs drum cluster's collider; regenerate the Item Lab
   export.
