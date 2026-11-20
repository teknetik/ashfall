# Ward / Athen Hill — Unity production guide

Updated 28 September 2026. This replaces the historical browser MVP guide.

## Kanban board for Ashfall

For all future Kanban tasks concerning this project (the Ashfall game, including
Ward / Athen Hill), use the dedicated **Ashfall** Kanban board. Pass
`board="Ashfall"` explicitly when creating each task, including delegated,
review, QA and follow-up cards; do not rely on the default/current board.
Use the same board for task lookups, comments, links, blockers and completion
so the full task history stays together. Include this board instruction in any
handoff that may create further Ashfall tasks.

## 1. Direction and authority

Build and test **only the native Linux Unity game** in `unity/AthenHill`.
The user wants visual quality on par with **GTA6**. Treat that as an ambitious
reference for believable real-time environments, materials, lighting, characters,
animation and presentation. The immediate deliverable is a polished, playable
Ward district. GTA6-level quality is not established by an engine choice, a Meshy
export, a successful build, a high frame rate or this document. It requires
sustained asset production, art direction and in-game review; do not promise
whole-game parity, production scale or a schedule without evidence and planning.

Authority for future work:

1. The user's latest explicit instructions and accepted reference feedback.
2. This guide for production rules, and [lore.md](lore.md) for setting canon.
3. The actual saved Unity scene, serialized data and current source records for
   implementation status; dated evidence applies only to the build it tested.
4. [unity/EDITING.md](unity/EDITING.md) for editing operations,
   [unity/DESIGN.md](unity/DESIGN.md) for the accepted interface, and the linked
   asset manifests for provenance and recovery instructions.
5. Older handovers, phase reports and numbered concept frames are historical
   references where they conflict with the direction above.

Do not develop, rebuild or browser-test the retired TypeScript/Vite game.
Historical web files and shared art/audio production inputs may be read or reused;
asset-only processing is allowed. Preserve unrelated and uncommitted work.
Do not restart the port, regenerate the city or follow old browser build prompts.

## 2. Setting and product scope

**Tir** is the planet; **Ward** is the surviving oasis city. The Fall, Great Rebuild,
Quantum Tube network, Karaveen, Wardens and Outer Berms come from `lore.md`.
The unknown reason for Tir's isolation remains unknown. Do not invent a definitive
answer, new faction history, or a civil-war origin for the Fall.

Use that setting for new concepts and writing. Athen Hill remains the repository,
scene and current build label. Free Column, Lattice Jack, Ring Gate, Vanguard Hall
and the old NPC dialogue still exist in the implementation. Reconcile player-facing
names in a deliberate content pass; keep stable asset GUIDs, scene identifiers,
dialogue IDs, routes and save/data references. Do not automatically equate the
Free Column with the Wardens or turn goods-only Tube lore into confirmed passenger
transport. Names left in the current build are not additional setting canon.

The long-term game vision includes survival, settlement rebuilding/expansion,
nanotech-and-scrap weapons and FPS combat. These are future production milestones,
not permanently forbidden features and not already implemented. This guide update
does not authorize starting all those systems at once. Establish the district's
visual standard and preserve its working loop before expanding its scope.
Multiplayer, accounts, vehicles and extra playable regions are not current tasks.

**Gate names (Carl, 19 November 2026).** Two gates had both come to be called West Gate. The **West Gate** is the gate
near the market: the -X portal into the Outer Berms, with Ossa's post beyond it. The +X spawn arches are the
**East Gate** in everything the player reads (name picked by the agent; `art/gate_names_20261119`). Scene objects, QA
landmark ids (`west_gate` is at the spawn), review cameras, Editor passes, asset folders and the older rows of this
guide still say "West Gate" for the spawn arches: read them by position, and do not rename stable identifiers.

The existing city loop must continue to work:

- Spawn at the East Gate (the +X arches; called West Gate until 19 Nov 2026); walk the avenue, hill stairs, porches and gate openings.
- Talk to Mira, Torr, Vex and Linn; retain dialogue branches and objectives.
- Trade at Basic General, including flask purchase and scrap sale with atomic
  inventory/credit changes. Prices and starting inventory live in CityCatalog.
- Use the Lattice transition and sector overlay. In the Outer Berms, 2 draws the scrap pistol and 1 the field rifle once one is equipped (hotbar since 5 Oct 2026). The Meshy ring across the hill
  is the single Lattice Jack since 3 Oct 2026 (no offline Ring Gate response any more).
- Preserve movement, jumping, always-on mouse look (cursor locked in play, freed by any open window or Left Alt;
  replaced the left-drag look on 5 Oct 2026), wheel zoom into first person,
  interactions, modal input blocking, inventory, notes, pause, audio, reduced motion
  and keyboard access. [unity/README.md](unity/README.md) records current controls.

## 3. Current Unity and asset baseline

Versions recorded in the project: **Unity 6000.6.0f1**, **URP 17.6.0**,
**glTFast 6.20.0**, Unity MCP **v10.2.0**. Inspect ProjectVersion, package manifest
and lockfile before changing dependencies. Keep Linux x86-64 working; existing
native evidence uses OpenGL. Do not silently change the graphics API or pipeline.

| Area | Current state to preserve |
| --- | --- |
| Player | **MPFB2 colonist since 2 Oct 2026 evening** (`art/tutorial_set_20261002`, provenance `meshy/tutorial-set-20261002/README.md`): MPFB 2.0.17 base human (CC0 MakeHuman base mesh/eyes/lashes; since 3 Oct the skin, painted face, hair and beard are a Meshy retexture on the MPFB UVs with alpha-clipped hair/beard shells, see below) on the MPFB `game_engine` rig with fingers, its 22 body bones renamed to the game's Meshy names plus `head_end`/`headfront` (54 bones, so clips, mounts and installers carry over); wearing Carl's `main_char_OK` flight suit refitted to the MPFB body with the Meshy crash-repaired retexture; idle/walk/run retargeted in Blender, library clips by `CharacterFeelPass` (its bind hip height fix: rest positions from fresh model instances). 72k triangles, 5 materials, one skinned mesh; `colonist.glb` same path/GUID, installed through `MainCharacterInstall`. Tutorial set armour as skinned pieces on the same bones via `TutorialSetInstall` (helmet `field_helmet` and the refitted Warden carrier so far; the other five Field pieces wait for Meshy credits). Full tutorial set since 3 Oct (helmet, chest rig = field_vest worn from the start with field_boots, bracers, fingerless gloves as a shell over the hands, knee/shin plates, boot plates; the rest is built from Berms salvage at Brann's bench through Ossa's four Warden Kit orders since 3 Oct, `art/armour_mission_20261003`; the primer grants none), armour decimated to 40 % for runtime; MPFB rest pose matched to the Meshy rig so clips transfer 1:1 (holds were overhead before); grip measured per install from the palm (0.051 m) and `PlayerHandGrip` curls the fingers round drawn weapons. First-person view models for both weapons rebuilt on the MPFB arms (since 3 Oct both on the player's own arms; the pistol's is weapon-driven, see below; the rifle gets its own view model with support-hand IK); `SupportHandIK` puts the left hand on the rifle handguard in third person while aiming. Final overnight batch `on3` (`unity/evidence/overnight/20261003/on3`, all overnight work together): rifle quest 37/37 (incl. first-person pistol/rifle checks), gunner separation 8/8, city loop PASS, range tutorial 10/10, expansion 8/8, enemies 39/42 (intermittent loot-prompt failures at one site per run, follow-up queued); A/B vs ts1 −0.7 ms hill, +1.2 ms avenue noon, +1.5–2.3 ms gate (~88–97 fps). Open: first-person hands still not convincing, gabion bastions read as tiled boxes. Previous `main_char_OK` colonist recoverable from `meshy/tutorial-set-20261002/previous/`. Fingers are at rest (no grip curl yet). 3 Oct posture fix (Carl: "shoulders are too high, back needs to be straighter"): the rest match to the Meshy rig now covers limbs only and the collarbones drop 18° (`finish_body.py`); previous outputs in `art/tutorial_set_20261002/blender/previous_restmatch_20261003/`. **3 Oct face and first-person hands pass** (`art/player_face_20261003`, `meshy/player-face-20261003`, `Editor/PlayerFace20261003.cs`): Meshy multi-view retexture of the MPFB skin mesh from a Codex face concept (4k base/normal, 2k roughness; 30 credits), MakeHuman card hair/beard/brows replaced by four alpha-MASK shell layers on the painted hair (+9k tris), lashes MASK instead of BLEND, red MPFB iris re-tinted; the pistol view model on the player's MPFB arms (17.8k tris instead of the 110k FP hands v2, kept inactive), weapon-driven (`ViewModelArmsRig` camera anchor, both arms IK'd with elbow poles onto grip points, ADS 0.46 m), contact-solved finger grips in `PlayerHandGrip` for the view models and the body, worn gloves/arm guards mirrored onto the view models. Rifle view model still clip-driven (shooting hand on the magazine well, open). Review cameras `cam_player_face_20261003_*` at the spawn. Edit Mode 268/268; not natively tested. Rollback: `--steps rollback` (previous outputs in `art/tutorial_set_20261002/blender/previous_face_20261003/`). Not yet accepted by Carl. 20 Nov 2026: suit texture and armour re-fit, first-person rifle hands and the arm/pistol corrector are in the rows **Colonist seen from behind**, **First-person rifle hands** and **Character arms and pistol hold** below. |
| Talking NPCs and Wardens | 3 Oct 2026 (`art/ward_npcs_20261003`, `meshy/ward-npcs-20261003`, `Editor/WardNpcInstall.cs`): the six actors that shared the supplied Ward Guard each have their own Meshy character (concept sheet, multi-image-to-3D, Meshy rig, own library idle/talk): Mira (shop apron), Torr (fixer, tool vest), Vex (Free Column gate guard, padded jacket), Linn (elder, patched quilted vest), Wardens Ossa and Rell (scrap-plate Warden kit). Prefabs `Prefabs/WardNpcs/WardNpc_<Name>`; NpcAgent roots, definitions, dialogue, voices and colliders unchanged; old guard visuals inactive in the scene (`RunBatch --steps rollback` restores them). Weapons: Ossa's scrap pistol in her drop-leg holster (RightUpLeg), Rell's field rifle slung on his back (Spine); Meshy rigs have no finger bones. Performance round 3 Oct 01:00: LOD0 ~20k (head protected) / LOD1 6–9k in a LODGroup, skinning only when visible (fixed pose bounds), Animation culled off-screen; first native batch measured 8.6 ms for the 60k versions at cam_hill, re-measure pending. Not yet accepted by Carl. |
| Three ambient walkers | 3 Oct 2026 (`art/ward_walkers_20261003`, `meshy/ward-walkers-20261003`, `Editor/WardWalkerInstall.cs`): three distinct Meshy residents replace the shared supplied traveler: **Daro**, a Karaveen caravan porter with a pack frame (`npc_walker_01`, east avenue lane from the West Gate), **Sel**, a nanofab technician in a patched work coat (`npc_walker_02`, by the Quantum Tube gate) and **Anso**, a hydroponics grower with a straw hat and a satchel of greens (`npc_walker_03`, hall district). Meshy rigs (24 bones) and library walks (Walking 2 / Quick Walk) made in place, with stride speed measured from the clip so playback is 0.91–1.16× at the unchanged route speeds (no foot sliding); LOD0 20k / LOD1 6k LODGroup, sampled bounds, skinning and animation culled off-screen. Roots, waypoints, speeds, phases and turn settings unchanged (verified against a snapshot); the old `Traveler` children stay inactive (`--steps rollback`). The yard mechanic was inspected and kept. Edit Mode 255/255; face close-ups shade patchy in low sun in editor captures (geometry/skin verified clean), to be judged natively. Not yet natively tested or accepted by Carl. |
| Additional ambient actor | Yard mechanic, Humanoid Animator and its separate four-point service-yard loop. The current roster (20 Nov 2026) is the player; eight colonists you can talk to (Mira, Torr, Vex, Linn, Brann, Tamsin, Wardens Ossa and Rell); three walkers (Daro, Sel, Anso); the yard mechanic; and three residents with work stops (Nadje, Pell, Oren; row **Ward residents**). The saved scene has 19 active `ActorAnimation` components (Ossa and Rell each also have a Berms copy, and the Berms mining droid has one), 7 active `AmbientWalker`s (Daro, Sel, Anso, the mechanic and the three residents) and 8 talking colonists. |
| Lattice Jack (Meshy ring) | Accepted 12,009-triangle Meshy model (formerly the offline South Ring Gate), open aperture, console, approach step and hum. Since 3 Oct 2026 (Carl: "we just need one lattice jack") it is the only Lattice Jack: the Lattice interaction sits at its console and the offline response is gone; the old glb Jack behind Vanguard Hall is retired (`PlaytestFixes20261003`, `art/playtest_fixes_20261003`, `--steps rollback`). If it reads badly as the Jack in play, rebuild it as a dedicated model. The 6,263-triangle remesh was rejected. |
| Mission terminals | Three saved Meshy terminal instances and the MissionTerminal prefab. Preserve the mission slab, nearby interaction access and `cam_terminal`; task records are in `meshy/mission-terminal-v1`. Since 1 Oct 2026 the three renderers use the emissive variant `MissionTerminal_Lit` (night lighting row below); `MissionTerminal.mat` is unchanged for rollback. |
| Shops and salvage | Restored Relay-based shops, Basic General and the community board. The 8 Sep salvage scatter (trash, crates, scrap, generators) is retired and replaced by the street dressing kit (below). |
| Vanguard Hall | Rebuilt 30 Sep 2026 from the accepted concept (`art/vanguard_hall_20260930`): authored ashlar hall with LODs, own colliders, lamps on the city light clock, weathering and old battle damage from the shared `art/ward_masonry_kit`. The two facade uplights are Carl's Meshy tripod floodlights (`Prefabs/WardHill/WardFloodlight`, 30 Sep) in place of the modelled boxes. The Meshy hall stays in the scene inactive for rollback. See [EDITING](unity/EDITING.md). |
| Hall district shops | 30 Sep 2026: Relay Works, Air + Water, Tool Exchange (sci-fi display, Meshy props), Finery and Field Supply rebuilt in modelled stone (`art/hall_district_20260930`) with door recesses, clock-driven lamps and a new sign family (incl. Basic General). Old layers inactive; porch colliders, filter bank and routes kept. Not yet accepted by Carl. |
| North avenue shops | 30 Sep 2026: Salvage (hoist, rubble-patched breach), Repairs (braced canopy, flue, roof container), Thread + Hide (balcony with cloth and hides, lit display) and the Basic General booth (stone walls and piers, red lintel carrying its family sign) rebuilt on the same masonry kit, signs and weathering (`art/north_avenue_20260930`). Mira, counter dressing, stock, colliders and routes kept; old layers inactive. Not yet accepted by Carl. Salvage is a walk-in shop since 1 Oct (next row). |
| Salvage shop (walk-in) | 1 Oct 2026 (`art/salvage_shop_20261001`, scene root **Salvage shop interior**): bay shutter rolled up; ground-floor room on the masonry kit (inner skin, flagged floor, steel beams with a hoist monorail, timber deck, salvaged-panel counter, pendants). **Brann** (Meshy salvage hauler, `Prefabs/SalvageDealer.prefab`) trades parts and salvage at the counter and keeps the **workbench** (Meshy `SS_Workbench`), now the only crafting station (station id unchanged; the West Gate tool cart is dressing). Field order 1 has a Report stage: gathered parts send the player to Brann, whose quest-aware dialogue opens the bench. Interior lamps on rendering layer 7 with an `InteriorLighting` ambient probe and a portal test through the bay (the room is not drawn from elsewhere); walk-in colliders from the shop record. Native real-input check 25/25, city loop and range tutorial pass; walk A/B against the batch-2 final build within run-to-run drift, +0.3 ms when facing the bay from 13 m. Not yet accepted by Carl. |
| Rooftops and service lines | 1 Oct 2026 (`art/rooftops_20261001`, scene root **Ward rooftops**): 44 instances that break the shop cornices seen from the avenue: water tanks (Finery, Thread + Hide), dew/condensate nets (Air + Water), PV panels (Tool Exchange), HF whip (Relay Works), dish (Repairs), ridge vents (Field Supply), a shaded terrace (Salvage), guard rails and cowls; service lines on pin-insulator masts across both cross streets and the alleys, conduit drops into junction boxes, two caged ladders. LOD0 67k / LOD1 28k triangles, shadows on the two tanks only, no lights, clear of the night-life smoke columns; nothing retired. Not yet accepted by Carl. |
| District replacements | Two active west-gate arches (closed by gates since 1 Oct; see the next row) and the mechanic remain. Seven rejected shop candidates under `District rebuild` stay inactive until revised and reviewed. |
| West Gate arches | 1 Oct 2026 (`art/west_gate_arches_20261001`, scene root **Ward west gate arches**): the two Meshy `District gate` arches at the +X spawn closed with steel-faced timber gates set 1.6 m back in the passage: braced leaves on strap hinges and jamb pintles, a wicket door (arch A), drop bar in stirrups, transom and head grille, worn steel threshold, guard stones, cart-rut, scuff, sand, grime and KEEP CLEAR decals, a bulkhead lamp per arch on the light clock (retuned by the night facade tune). LOD0–2; one box collider seals each opening. Meshy arches, their render chunks and saved colliders unchanged; nothing retired. Not yet accepted by Carl. |
| Hill and hero tree | 30 Sep 2026 (`art/hill_20260930`, scene root **Ward hill**): the plinth, stairs, tree ring, paving, beds, soil and roots rebuilt on the Ward masonry kit (same stone as the hall and shops), Poly Haven planting on a wind shader, Carl's Meshy "Reclaim & Save Point" kiosks on the three terminal slots (decorative, as before), tree uplights on the light clock. The hero tree mesh itself is unchanged. Saved hill/stair colliders kept; old visuals inactive. Not yet accepted by Carl. |
| Courtyard trees | 30 Sep 2026 (`art/courtyard_trees_20260930`, scene root **Courtyard tree beds**): `birch 3` and `birch 4b` moved north (1.2 m / 1.8 m) into stone beds built like the hero ring (seat coping, litter, roots, drip line, apron, uplights on the light clock). Trees keep their prefab links and trunk capsules. 1 Oct 2026 (`art/birch_canopy_20261001`, `BirchCanopyPass`): both birches on baked canopy mesh copies (crown occlusion, per-card yellow-green season mix and brightness jitter, crown-volume leaf normals; same triangles) and the *Ward Canopy* shader (wind, leaf transmission, no metallic); each bed's two uplights split into a trunk wash and a crown beam, with their own dimmer lens `BC_UplightLens`. LODGroups, draw calls and light count unchanged. Not yet accepted by Carl. |
| Street dressing | 30 Sep 2026 (`art/street_dressing_20260930`, scene root **Ward street dressing**): 145 instances of a 68-prop kit (CC0 Poly Haven scans, four Meshy pieces, Blender sacks/tarp/skip/litter) in 30 purposeful vignettes along walls, porch ends, lanes and yards, grime/scuff decals, NPC sit points on seats; old scatter and cube dressing inactive. Lanes, doors, stairs and routes kept clear (`layout.py`). Not yet accepted by Carl. |
| Shade sails | 1 Oct 2026 (`art/shade_sails_20261001`, scene root **Ward shade sails**): four form-found canvas sails (madder, indigo, natural and natural/indigo cloths with patches, seams and stencils) over the terminal court, the market rest spot, the West Gate apron and the Lattice approach, on raked steel poles with stone footings or guyed sandbag bases (two tied to the retrofit service poles), with festoon strings and 7 unshadowed festoon lights on the light clock (practical + night-only). Canvas shadows come from offset ShadowsOnly proxies; camera-only canvas colliders keep the follow camera under the sails. 98.5k / 28.8k triangles at LOD0 / LOD1; routes, doors, NPC points and the Lattice and terminal sightlines kept clear; nothing retired. Not yet accepted by Carl. |
| Wall-foot sand | 1 Oct 2026 (`art/wall_foot_drifts_20261001`, scene root **Ward wall-foot drifts**): 334 wind-laid sand banks (eight-piece kit, LOD0–2, no shadows or colliders) at the measured feet of the eight shops, Basic General, Vanguard Hall, the hill plinth and stair cheeks, inside corners, step ends, posts and the shop alleys, heavier on faces into the west-south-west wind, plus 320 decals (sand film, wall dust and grime skirt, post collars, alley sheets) on an angle-fading copy of the Ward decal graph. Doors, step middles, props, routes and NPC points kept clear; nothing retired. Not yet accepted by Carl. |
| Perimeter walls | 1 Oct 2026 (`art/perimeter_walls_20261001`, scene root **Ward perimeter walls**): 87 instances of a 32-module kit on the Ward masonry: north/south curtain walls with merlons and piers, the +X rampart with buttresses and wall walk either side of the District gate arches, the strip wall, the −X Berms walls. Weathered, repaired, broken-parapet and shell-damaged bays, collapsed sections in the north and south walls, and the old siege breach by the West Gate portal closed with HESCO and welded sheet. LOD0–2 plus an inset shadow-only massing mesh; saved wall colliders unchanged; old wall visuals inactive. Not yet accepted by Carl. |
| Ward buildings (retrofit replacements) | 3 Oct 2026 (`art/ward_buildings_20261003`, `WardBuildingsPass`): the 26 Sep retrofit boxes rebuilt on the Ward masonry kit with blackened steel and restrained sci-fi: **Nanofab 2** (SE yard: ashlar storey, banded corner piers with banners, composite clean-room module with a cyan status strip, half-raised hazard-framed bay showing a lit fabricator, gas bank, lean-to), **Processing 11** (NE yard: roofless shelled ashlar hall, broken stepped wall tops, barred windows, piers with crane rails and a stranded crane, sagged trusses, rubble), **four Warden corner watchtowers** (ashlar shafts on battered taluses, corbelled armoured cabins with searchlights, ladders up the city face), **AQUIFER 3** (SW: pump hall with clerestory, hoist, strapped corners, well head and rising main, three riveted tanks), the **Quantum Tube** goods nodes and conduit (stone pylons, armoured conduit, "GOODS ONLY"), and five **converted container homes** on the wall feet. Old groups inactive for rollback; 24+ `cam_wb_*` review cameras. Native batch `on2` (`unity/evidence/overnight/20261003/on2`): lookbook of every `cam_wb_*` camera at 13:00/20:30; bisection put the buildings at ~0.6 ms at cam_hill; A/B vs ts1 within drift at hill/avenue, +1 ms at the gate (~100 fps). Round two (3 Oct night): four distinct watchtowers (two armoured-cabin, two open crenellated tops; patched, rebuilt,
breached and timber-shored), Processing 11 turned into a Warden-permitted salvage works, painted tanks/cylinders fixed,
and the **West Gate bastions** (two gabion gun positions with sandbag courses, pintle guns, lamps) replacing the
retrofit `Gate defences` at the spawn. 15 `cam_wb2_*` cameras. Not yet accepted by Carl. |
| Ward life (gate gabions, water ration court, Node 07 dock) | 3 Oct 2026 (`art/ward_life_20261003`, `Editor/WardLifePass.cs`, three scene roots **Ward life: …**): the West Gate bastions rebuilt as welded-mesh stone gabions (`WL_GateBastionS/N`: baked stone fill on Masonry Lit seen through an alpha-clipped weathered 100 mm mesh, 2/1.5/1 m and 0.5 m stepped baskets that bulge and sag, binders, sandbags draped over what is under them; south post's blown basket and spilled scree, north post's re-meshed burst basket with a strapped plate) replacing round two's tiled cells (`Ward building: West Gate bastions` inactive; gun, props, lamps and colliders as before); the court behind Vanguard Hall (old Lattice Jack site) as the Wardens' **water ration point** (`WL_WaterPoint`: AQUIFER 3 header tank, buried main under trench covers, four-tap stand and trough, tally desk, ration board, queue of cans and carts, damp decals); the empty paving east of the Meshy ring as the **Node 07 goods dock** (painted bays, goods canisters on pallets, platform scale, tally desk, dock board, porters' carts). No new lights, no Meshy credits; routes, NPC points, hall loop and the ring approach kept clear (`layout.py` 0 problems, verify 0 conflicts). 12 `cam_wl_*` review cameras. Not yet accepted by Carl. |
| Field Supply (walk-in) | 5 Oct 2026 (`art/field_supply_20261005`, `meshy/field-supply-20261005`, `Editor/FieldSupplyShopPass.cs`, scene root **Field Supply interior**): the hall-district Field Supply's loading shutter is rolled up and its ground floor is **Tamsin**'s outfitter's shop (Meshy keeper from a concept sheet, rig + idle_248, talk reuses Torr's talk_309; `Data/npc_tamsin.asset`, not in the four-colonist visit): counter, med/nano cabinet, pack wall and stand with the five Meshy packs, and the **digital magazine shelf** (slates showing four authored covers, `covers/`). Counter profile: stock tags (`field_supply`) and Basic General's exclude tags (`field_supply_only`); BUY/SELL plus a **MAGAZINES** tab. Packs on the storage slot (Field Backpack +25 kg/+16 slots → Canvas Rucksack, Karaveen Frame Pack, Porter's Load Carrier, Courier Cargo Rig +58/+30/+14 kg carry) with pouch/frame upgrade sockets; magazines download schematics for Brann's bench (packs, four pack upgrades, three armour upgrades; recipe unlock type `magazine`). Medkits and trauma kits heal on hotbar 2 (× Healing efficiency), nano recharge cells/surge packs refill and overclock the weapon charge on hotbar 9 (new Slot9 action). Data patch `apply_data.py` (idempotent). Edit Mode 276/276; verify clean; native (build 5 Oct 01:29, `unity/evidence/field-supply/20261005`): shop check 25/25, city loop PASS, range tutorial 10/10; A/B vs the 4 Oct build within drift (p50 −0.5 to +0.7 ms; Field Supply view +0.4–0.5 ms; avenue noon 58.3 vs 60.7 fps). Tamsin is unvoiced (ElevenLabs payment issue). Rollback in the pass header. Not yet accepted by Carl. |
| Container home (lease, locker, bunk) | 5 Oct 2026 (`art/ward_home_20261005`, `Editor/WardHomePass.cs`, scene root **Ward home**, prefab `WallHomeP`): the rust container `Wall home south 2` (27.5, 0, −41.4) is the player's home (the WallHomeA instance stays inactive): real door opening with a hinged leaf that opens for the tenant and parks flat against the wall (open yaw −176), two steps, glazed window, and a fitted interior (plywood lining with exposed insulation, board floor and rug, steel bunk, olive stash locker "S2", slotted rack of salvage bins, fold-down table, interior lamps on layer 7, baked probe); LOD0/1/2 36.2k/11.3k/24 tris; camera held in first person inside (`CameraConfineZone`). Linn's housing roll (after the primer) leases it for 40 credits (`WardHome.leasePrice`); the locker (`StashModel`, 60 stacks, no weight limit, Store all salvage) feeds Brann's bench once the pack runs short; the bunk rests to 06:30/18:30, heals, saves, and Continue then wakes there; journal mission *A Roof in Ward*; save v4 (hotbar, stash, tracked mission). Native (build 5 Oct ~04:25, `unity/evidence/ward-home/20261005/rerun2`, `rerun`, `batch`): home/journal/hotbar check 36/36, real-mouse check 14/14 (uinput), Field Supply 25/25, rifle quest 38/38, city loop PASS, range tutorial PASS; A/B vs the Field Supply build within drift (hill/avenue/gate −0.07…+0.15 ms p50, at the homes +0.2 ms). QA harness: `qa.py` makes no XTEST pointer moves while the game cursor is locked (they arrive as one large delta under Hyprland's pointer lock). Not yet accepted by Carl. |
| Meshy turret and benches | 4 Oct 2026 (`art/turret_bench_20261004`, `meshy/turret-bench-20261004`, `Editor/TurretBenchPass20261004.cs`): Carl's Meshy **sentinel turret** replaces the pintle gun and shield on both West Gate gabion bastions (bastions re-authored with `GATE_GUN = False` in `author_life.py`, prefabs rebound in place, turret under `Fittings` at ±1.1/0.32, yaw ±50°, clear of the return); his **cybernetic bench** replaces all 7 Poly Haven `SD_bench_painted` placements (old ones inactive) and the four primitive avenue slabs `PROP_bench_00–03` (two benches each, root **Ward Meshy benches**, chunks rebuilt). LODs 29.6k/7.4k/2.2k (turret) and 45k/9k/2.1k (bench), 2k Meshy maps, bench metallic ×0.5; sit points kept. `cam_tb_*` cameras. Verify PASS, owning passes' verifies clean, Edit Mode 268/268; not natively tested; `--steps rollback`. Not yet accepted by Carl. |
| Hydroponics greenhouses | 1 Oct 2026 (`art/hydroponics_20261001`, scene root **Ward hydroponics**): both retrofit quonsets fitted out (racks, NFT channels, feed lines, LED bars on the light clock, vine gutters) and planted in 12 crop sections with LODs (lettuces, chard, herbs, seedlings, tomatoes, runner beans); polycarbonate skin on a filmed copy with no shadow pass; a working yard of 58 props in 12 vignettes (harvest crates, potting bench, nursery shade with drying herbs, rest bench with sit points, market handcart, nutrient totes, dosing trolley, compost); four night-only grow-glow lights. Retrofit Detail (succulents) and Glow inactive; the quonsets are still solid, not enterable. Not yet accepted by Carl. |
| Night lighting and ambient life | 1 Oct 2026 (`art/night_life_20261001`, scene root **Ward night life**): 8 merged-part Ward utility posts and 3 wall brackets in the dark pockets (courtyard and terminals, Lattice court, hall corner, hill benches, gate apron, both wall collapses, south lane, rampart foot) with warm unshadowed night-only spots on the light clock; the three Meshy mission terminals on an emissive material variant with cool night fills; a barrel fire with embers and flicker light, two flue smokes, Air + Water steam puffs and generator haze driven by `AmbientLife` (stopped by Reduced Motion). Not yet accepted by Carl. |
| World | Editable terrain basin, stone/soil detail, cloud/dust atmosphere, landmarks and collision sources. Existing assets are a baseline, not a permanent quality ceiling. 1 Oct 2026: **Basin mountains** (`art/basin_mountains_20261001`, scene root **Basin mountains**) replace the backdrop ring with an eroded heightfield on the original layout (stream-power valleys and gullies, strata benches aligned with the shader's beds, talus, outcrops; 185k triangles in the eight original sectors with shared borders), the Berms ground toe kept exact, on `SandstoneBasinV3` with new haze-shape controls; the old `DesertBasin` chunks are inactive. **Berms road ground** (`art/berms_road_20261001`): `Outer Berms/Berms ground` on *Berms Ground V2* (the basin's scree/sand/rock model plus a repainted road with wheel paths, ruts, crown, gravel windrows and potholes, blending to the basin over 7 m), 24 edge stones and 2 cairns, footstep map rebaked; ground mesh, collider, routes, encounters and range unchanged. **City paving** (`art/city_paving_20261001`): the city floor and the plaza bands round the hill on world-mapped dressed-sandstone flags (*Ward Paving Lit*: 4 m tile, 0.5 m courses shuffled per course, per-flag tone, sanded joints, 2k textures, not streamed); `Paving Joints` and the four `Avenue service band` strips inactive, `COL_Ground` unchanged. Old materials kept for rollback. Not yet accepted by Carl. |
| Interface | Accepted worn bronze/metal UI Toolkit art, open center view, corner HUD. 5 Oct 2026 (`art/ward_home_20261005`, not yet accepted by Carl): the ten-slot hotbar is configurable (1 primary weapon, 2 sidearm, 3–0 items dragged from the field pack's HOTBAR strip or assigned by key, and since 20 Nov 2026 reordered by dragging one strip cell onto another; medkit on 3 and nano cell on 4 by default), the cursor is locked in play with always-on mouse look (Left Alt or any window frees it; left mouse fires), Settings has a Controls tab (sensitivity, invert), and the J journal lists missions (city visit, primer, each field order, the home lease) with one tracked mission shown in Field Notes, on the compass and as the in-world marker. Notes became the journal's Ward notes tab. 20 Nov 2026: body-map leaders, the EYE implant slot and the hotbar reorder are in the row **Loadout body maps, eye implant slot and hotbar reorder** below. |
| Sound | Existing ElevenLabs music, ambience, spatial hums, footsteps and interaction cues; retain mixer, mute and reduced-motion behavior. 20 Nov 2026: Linn re-voiced, see the row **Linn's voice** below. |
| Outer Berms loop | Scrap pistol with grip/barrel/cell mods, refined components, seeded loot with bad-luck protection, salvage caches, scrap heaps, Depot Foreman elite, Ossa's five field orders (the first reports to Brann at Salvage), Basic General Supplies / Buy parts / Sell salvage, Brann's Salvage counter (parts, salvage) and workbench (fabricate and fit), versioned save with Continue. Content lives in `Data/Crafting/WardCrafting.asset`, `CityCatalog.asset` and the field-order set; see [unity/EDITING.md](unity/EDITING.md). Timed crafting since 3 Oct 2026 (`art/timed_crafting_20261003`): each recipe's Craft Seconds (components 4–6 s, mods 8–12 s, armour 15–25 s, rifle 20 s) runs at the bench with progress and Cancel; parts are used only when it completes; Esc, Cancel or damage stop it with nothing used; a craft in progress is not saved. Not yet accepted by Carl. |
| Warden training range | 1 Oct 2026 (`art/training_range_20261001`, scene root **Outer Berms/Warden training range**): the range beyond the West Gate rebuilt as a working Warden range: three timber firing bays at the tutorial's firing line, range officer's table and RANGE ORDERS board, distance posts, a timber-revetted earth backstop with impact scars and a crest flag, a machine lane (tyre run, cover barricades, tethered training drone, stripped worker droid in a target frame) and a drone service apron (charge docks under a shade shelter, repair bench, compressor, welding cart, generator), lights on the light clock. Plates, reset station, Wardens, locker, encounters, respawn and landmarks unchanged; replaced clutter inactive. Range tutorial check 10/10 and city loop passed in the pass's own test and in combined batches 1 and 2. Not yet accepted by Carl. |
| Outer Berms expansion | 2 Oct 2026 (`art/berms_expanse_20261002`, roots **Basin expanse** and **Outer Berms/Berms expanse**): the Berms grew from 44 × 102 m to a ~495 × 425 m bowl west of the West Gate; western mountains rebuilt around it (old **Basin mountains** inactive), 54 walkable LOD ground tiles meeting the untouched old Berms ground, edge walls (old boundary inactive), 835 rock/scrub scatter, Warden trail cairns, twelve sites (props, 39 droids, 21 salvage nodes, three Meshy hero landmarks in `meshy/berms-landmarks-20261002`), a Warden waystation that becomes the respawn point once found, a damage-direction ring on the HUD and a 1,600 m camera far clip. Droids: tougher workers/drones that call their pack and flank; two Meshy ranged droids (`meshy/ranged-enemies-20261002`: FeralGunnerDroid, FeralLancerDrone) firing dodgeable bolts after a laser tell. Primer: the depot nest is five droids; Foreman unchanged (the pass's first contact past the depot rise was reverted on 2 Oct, see the First contact row). Batch native test: expansion check 8/8 (`unity/tools/check_berms_expanse.py`), city loop PASS, range tutorial 10/10; A/B on/off within drift in the city, +1.9–2.6 ms p50 looking into the Berms (85–137 FPS there), relay-knoll gunner fight 90 FPS avg. Not yet accepted by Carl. |
| Pistol carry | 2 Oct 2026 (`unity/evidence/pistol-carry/20261002`): the drawn-but-lowered scrap pistol turns in the hand onto a muzzle-down carry line (`PlayerWeaponPose.carryPitch` 60°) instead of sticking 117° out of the hanging idle hand (since 20 Nov 2026 `carryPitch` is 40° with part of the turn taken by the wrist: row **Character arms and pistol hold**); the aim mount and the raised hold are unchanged. The rig has no finger bones, so the open hand is a known limit. Native (batches `rifle3`/`rifle4`, 2 Oct): real-input quest check 34/34, city loop, range tutorial 10/10, expansion check 8/8, Edit Mode 207/207, A/B within drift; gaps: no first-person rifle view model, pistol sound layers reused, open hands. Not yet accepted by Carl. |
| First contact | 2 Oct 2026: the primer's first contact is back on the service road beside the gate (two scrap drones at (-83,-13) and (-89,-6), 30 m from the gate marker); the expansion's "past the depot rise" placement left nothing in sight after the plates. HUD guidance markers for the FirstContact ("SCRAP DRONE") and Depot ("MACHINE DEPOT") steps. Native (batches `rifle3`/`rifle4`, 2 Oct): two drones 30–32 m from the gate, markers shown, shot with real input, primer completes. |
| Field rifle and plate carrier | 2 Oct 2026 (`unity/evidence/rifle-armour/20261002`, `art/rifle_armour_20261002`): the Meshy field rifle (Codex's inventory model) in the colonist's hands with a two-hand rifle hold and a lowered carry from library clips 573/334 on a fresh Meshy rig (`meshy/character-feel-20260927/player-rifle`); 8 draws it once a primary weapon is equipped, 7 the pistol, hold-to-fire bursts, no first-person rifle view model yet. The Warden plate carrier (Meshy, `meshy/plate-carrier-20261002`) shows on the chest while `warden_plate_carrier` is equipped (`PlayerArmourVisuals`). Two field orders after Steady Hands: *Long Arm* (receiver from the relay-knoll gunners, Brann's bench builds the rifle; engineering 20, rifle skill 20 to equip) and *Plate Carrier* (caravan strongbox). A test-issue rifle in older saves is withdrawn on load. `RifleArmourInstall` (Editor) rebuilds the holders, holds, bindings, QA landmarks and `cam_rifle_*`/`cam_vest_*` cameras; `art/rifle_armour_20261002/apply_data.py` re-applies the catalog/order/dialogue data (re-run after Codex's inventory work lands). Native (batches `rifle3`/`rifle4`, 2 Oct): real-input quest check 34/34, city loop, range tutorial 10/10, expansion check 8/8, Edit Mode 207/207, A/B within drift; gaps: no first-person rifle view model, pistol sound layers reused, open hands. Not yet accepted by Carl. |
| Salvage dealer (Brann) | 2 Oct 2026: the delivered "Ironclad Warden" human (bearded salvager, holstered pistol) is Brann's model (`Prefabs/SalvageDealer.prefab` rebuilt in place, same root/dialogue/counter; walk/run from the delivered rig, procedural breathing idle and counter talk gesture); the Meshy hauler is kept in `Prefabs/Retired/`. The hostile Ironclad Warden droid built first from that file is retired (recoverable under `Prefabs/OuterBerms/Retired`). Native (batches `nl1`–`nl3`, 2 Oct evening, `unity/evidence/next-level/20261002`, programme README `art/next_level_20261002/README.md`): rifle quest regression, city loop, range tutorial 10/10, expansion 8/8, gunner separation 8/8 and the next-level enemies check 42/42 (balance fix round) pass; A/B against the rifle batch within drift except +1.1 ms at the gate view with the 60k colonist in frame. Not yet accepted by Carl. |
| Next-level droids and POIs | 2 Oct 2026 (`art/next_level_20261002/enemies`, scene root **Outer Berms/Next level sites**): two higher-level droids from the delivered models, the **Scrap Reaper** (level 3 melee walker) and the wheeled **Post Sentinel** (new `DroidKind.Wheeled`, rolls on its split wheel, hip-fired bolt bursts), with flat droid armour; four POIs in the outer ring (Post relay, Reaper den, Fans camp, Southern cache) with encounters, 9 loot crates/strongboxes, new rare parts (`reaper_blade`, `sentinel_optic`), `DroidThreat` levels/experience on every droid prefab, QA landmarks `nextlevel_*` and `cam_nextlevel_*` cameras. Tuned so the starter pistol cannot take them but a modded rifle and the basic armour set can. A third droid model was not delivered. Native (batches `nl1`–`nl3`, 2 Oct evening, `unity/evidence/next-level/20261002`, programme README `art/next_level_20261002/README.md`): rifle quest regression, city loop, range tutorial 10/10, expansion 8/8, gunner separation 8/8 and the next-level enemies check 42/42 (balance fix round) pass; A/B against the rifle batch within drift except +1.1 ms at the gate view with the 60k colonist in frame. Not yet accepted by Carl. |
| Combat systems | 2 Oct 2026 (`art/next_level_20261002/combat`): weapon ranges with damage falloff (pistol 30 m / 4° spread, rifle 95 m / 1.8°), accuracy from weapon stats plus the character's accuracy stat and weapon skill (`WeaponBallistics`), enemy threat tiers (`DroidThreat.Tier`: grey easy/no XP, green normal, red danger) tinting the HUD health bars and awarding experience on kills with a toast and level-up notice; the field rifle's muzzle end is an explicit measured setting (it was mounted stock-forward); the gunner and lancer prefabs no longer carry a nested worker/drone droid ("gunners attached to other droids"); trade cue is a quiet digital click (`Audio/UI/trade-click.wav`); "Oasis of Ruins" leads the music playlist. Native (batches `nl1`–`nl3`, 2 Oct evening, `unity/evidence/next-level/20261002`, programme README `art/next_level_20261002/README.md`): rifle quest regression, city loop, range tutorial 10/10, expansion 8/8, gunner separation 8/8 and the next-level enemies check 42/42 (balance fix round) pass; A/B against the rifle batch within drift except +1.1 ms at the gate view with the 60k colonist in frame. Not yet accepted by Carl. |
| Gate names | 19 Nov 2026 (`art/gate_names_20261119`, `Editor/GateNamesPass20261119.cs` with `install`, `verify`, `rollback`; scene roots **Gate name plaques** and **Gate name review cameras**): the +X spawn arches read **East Gate**. The "— WEST GATE —" plaques baked into the Meshy arch texture (both faces of both arches) are covered by four authored iron plates (4.54 × 0.965 × 0.07 m, 12 triangles each, one URP Lit material, no colliders, not chunk sources); the Meshy arch, its render chunks and colliders are untouched. Start menu, pause button and controls list, Settings note, catalog notes, the Continue summary and the map label (`city:barred_gates`, id kept) say East Gate; everything about the Berms portal keeps West Gate, and no voiced line was affected. Native on `Builds/batch-gates` (18:50, the 17:32 showcase tree plus this pass): gate names 12/12, world map 29/29, interface 22/22, city loop PASS, range tutorial 10/10; Edit Mode 393/393. The other package checks were last run on the 17:32 build. The outer-face plates cannot be seen by a player and were checked by placement only. The name and plates are not yet accepted by Carl. |
| Showcase programme | 19 Nov 2026 (`art/showcase_20261119`, native record `unity/evidence/showcase/20261119/qa/README.md`, editing in [EDITING](unity/EDITING.md)): seven packages plus a night pass, each from its own Editor installer with a `verify` step. **Combat feel**: hit, critical and kill markers with ticks, camera shake (off under Reduced Motion), a low-vitality edge, droid optic weak points (critical ×1.5 at levels 1–2, ×1.25 at level 3), enemy bolts with a glow halo, hot core and longer streak (no lights added), at most two FX lights. **Combat audio**: the field rifle's own layers and 35 droid clips with a 10-voice limiter. **Weather** (root **Ward weather**): wind through the day and dust fronts that Ossa announces, held back until the primer is done and for 8 minutes after loading; droid sight shortens in a front. **NPC life**: 80 voiced bark lines (greetings by hour, remarks, reactions to a drawn weapon, walkers' passing lines with a glance) with captions; Tamsin and Ossa's locker/range lines voiced. **Conversation camera and photo mode**: talking frames the colonist over the player's shoulder with depth of field (eye line when too close; first person keeps the old centred window); P opens photo mode (fly camera, lens, time of day, F12 saves 1080p and 2× stills to `~/Pictures/Ashfall`). **Interface**: lower-third dialogue while the camera frames, with the other panels faded; Settings rows for bark captions, conversation camera and Interface Full/Adaptive (default Full). **World map** on M: survey picture, sites discovered within 55 m, respawn ring, knock-down cross, tracked mission; the save gains an additive `map` field (still v4). **Night readability** (`art/night_readability_20261119`): night ambient about doubled, moon shadow strength 0.92 → 0.65 at night, `NightActorLighting` on actors; faces at 20:30 went from 3–17 to 31–54 of 255 and day frames are unchanged. Native on `Builds/batch-showcase-qa`: every package check passes (combat feel 23/23, combat audio 14/14, NPC life 27/27, camera 99/99, weather 13/13, interface 22/22, map 29/29), city loop PASS, range tutorial 10/10, rifle quest 38/38, home/journal 37/37, Field Supply 26/26, Berms expansion 8/8, Edit Mode 390/390. A/B against a build of the last commit (`Builds/batch-baseline-head`, three alternating runs each): within ±0.13 ms p50 at cam_hill, cam_avenue and cam_gate at 13:00 and 20:30 (hill 59 vs 59 fps, avenue 56 vs 56, gate 88 vs 88), so no measurable cost; hill and avenue sit just under 60 fps on both builds on this desktop. Carl's answers, 19 Nov: fronts only after the primer and lamps staying off in a front are confirmed (more interesting, and Ward saves power); the 55 m discovery radius is confirmed; the 6 s Adaptive HUD quiet time is a start to judge in play. Open: nobody has listened to the new audio; the optic may be too small to hit (4 of 12 aimed shots); the weather look, Mira's face against her lit floor, and the colonist's suit seen from behind in every conversation need Carl's eye; Berms ground variety, more residents and first-person rifle hands were not started. Not yet accepted by Carl. |
| Light budget | 19–20 Nov 2026, showcase phase 2 (`art/light_budget_20261120`, programme record `art/showcase_phase2_20261120/README.md`, `Editor/LightBudgetPass20261120.cs` with `survey`, `install`, `mira`, `verify`, `rollback`; scene roots **Ward light budget** and **Light budget review cameras**, 13 `cam_lb_*`): URP's 32-light cap on the OpenGL player is now kept by design. `LightBudget` (execution order 2000, after the light clock) ranks the 184 managed lights (137 clock lamps, 6 static lights, 41 salvage markers) for the rendering camera by the apparent brightness and size of their pools, with a near preference, and keeps at most 28 local lights enabled in view (`hardCap`; interior lamps, fires and combat FX are counted, not touched). Demoted lamps keep their bulbs and get a depth-buffer pool (`Shaders/LampPool.shader`, `poolGain` 0.65; at most 44 pools a frame, none under 6 px, none beyond 120 m or by day) that cross-fades over 0.6 s, with hysteresis ×1.35 and a 1 s hold. The clock's hours, night-only switching, daytime strength, distance fade, shadows and the dust-front rule are unchanged. 8 retrofit rear-door ambers merged into the shops' rear door lamps (×1.25). Basic General's two front pier lamps tilted back onto Mira (face 51 → 98–100 at 20:30; the counter lamps keep their night-facade aim); this overrides `NightFacadePass`: do not re-run it. Values in `lb-tune.json`, originals in `originals.json`. Switch: `ATHEN_LIGHT_BUDGET=0` (development players) or disable **Ward light budget**. Native on the agent's builds `batch-p2-lb3`/`lb4` (`unity/evidence/showcase_phase2/20261120/light_budget`): 21–26 lights in view at every review camera at 20:30 (30–178 without), `check_showcase_light_budget.py` 9/9, 0 of 6,522 check-walk frames over 30 lights, faces unchanged except Mira; frame time neutral at cam_hill, cam_avenue and cam_night_spawn_apron, +1.4 ms at cam_night_avenue_west (109 pools) before the pool cap (lb-9), and still about +1.0 ms there on the final build with it (22.48 ms off, 23.48 ms on; the phase 1 build 21.90 ms): the cost target of +0.5 ms was not met. Seen in the game: at the spawn apron 141 lamps want to be lit and 26 real lights are on; Mira lit; no painted-looking pools. Not judged: pop during fast camera turns. Rollback never run. Edit Mode 421/421. Native on `Builds/batch-p2-final` (20 Nov 01:02, `unity/evidence/showcase_phase2/20261120/qa/final`): `check_showcase_light_budget.py` 9/9, verify clean; night sheets looked at (Basic General lit with Mira, courtyard and hall pools read as light). Not yet accepted by Carl. |
| Colonist seen from behind | 19–20 Nov 2026, showcase phase 2 (`art/colonist_back_20261120`, `Editor/ColonistBackPass20261120.cs` with `install`, `verify`, `rollback`, `capture`; root **Colonist back review cameras**: `cam_cb_conv`, `cam_cb_follow`, `cam_cb_back`, `cam_cb_quarter`, `cam_cb_helmet`, `cam_cb_vest`): the phase 1 conversation camera puts the colonist's back across a third of every dialogue frame, where the suit read as speckled camouflage and the chest rig had holes, torn edges and side flaps. Causes: the Meshy suit albedo was a patchwork of unrelated fragments; the 3 Oct armour fit deleted inner faces (`strip_inner`), decimated meshes still split at UV seams, and gave the vest arm and clavicle weights. `colonist.glb`: only the suit's base colour and normal images swapped (`patch_glb.py`; synthesised olive-brown plain weave with top-stitched seams, sun-fade, wear and the concept's canvas repair patches, `make_suit.py` v2), collar and sleeve rims moved onto smooth rings (`edit_suit_mesh.py`), hair shells denser and matte (`hair_tex.py`); same GUID, 54-joint order, inverse bind matrices and clips (76,043 triangles). `TS_FieldVest` (14.0k), `TS_WardenCarrier` (9.0k) and `TS_Helmet` (12.0k triangles; were 8.1k/5.8k/8.0k) re-fitted from the full Meshy sources (no `strip_inner`, seams merged, texture-aware decimation, torso-only weights, hem cut at the plates, shoulder pad as a cap, helmet texels grouped into shell, bands and straps); texture memory unchanged. Do not re-export the armour with `tutorial_set_20261002/blender/rebuild_armour.sh`. Installed as colonist_back-2, verify PASS (-nographics, bind diffs 0). Seen in the game (`batch-p2-b3`): hair no longer reads as dots, smooth neckline, vest and back plate read as one made object. Open: a small torn dark shape at the vest's right side strap, slivers at the sleeve hems, a crumpled crease under the collar (hidden by the vest), plain cloth in shade; helmet still busy and not seen in the game; carrier texture flat; arm guards, gloves, boots and leg armour not re-fitted. Rollback `--steps rollback` (shipped files in `rollback/` with `sha256.json`). Edit Mode 421/421. Native on `Builds/batch-p2-final` (20 Nov 01:02, `unity/evidence/showcase_phase2/20261120/qa/final`): verify PASS; conversation camera check 99/99 and rifle quest 41/41 with the new assets; `cam_cb_*` looked at by day (b3) and at 20:30 (final). Not yet accepted by Carl. |
| Outer Berms ground variety | 19–20 Nov 2026, showcase phase 2 (`art/berms_variety_20261120`, `Editor/BermsVarietyPass20261120.cs` with `survey`, `material`, `install`, `verify`, `toggle:on`/`toggle:off`, `rollback`, `cost`, `capture`; scene root **Outer Berms/Berms variety**, 14 `cam_bv_*`): additive. The 54 expansion ground tiles (108 LOD renderers) on *Berms Ground V3* (`Art/BermsVariety/Ground/BermsVarietyGround.mat`: V2 plus a bowl-wide region mask at 0.25 m: clay pans, hardpan, lee sand with patchy, turning ripples, gravel fans and varnished lag, wash bars and silt, Warden/Karaveen/haul/sentinel tracks, scorch, glass and painted crater bowls; it fades out before the playable edge and the old Berms ground, which keeps V2). Relief: 364 m of old Warden berm lines and redoubts in 11 segments, 7 dunes and 13 crater rims (walkable, MeshColliders), 23 sandstone outcrops on a recoloured Poly Haven Cliff Side scan (`BermsVarietyRock.mat`, matched to the basin sandstone) with domed tops, patchy sand caps and drifted aprons; 349 kit prefab instances (34 half-buried wrecks, talus, scrub, rockfalls, Karaveen litter). Footsteps: an additive `FootstepAudio` *Berms variety map* (sand, gravel, stone; the tiles always played Stone before). No site, spawn, loot, route or existing collider moved; the ground mesh and its collider are unchanged. Installed as berms_variety-10, verify PASS (0 problems; 9 of 4,194 droid's-eye rays blocked by the pass). Cost estimate (`cost` step, not a GPU measurement): about 200–230 colour draws in the long views, mostly kit prefabs; its frame cost was not measured on its own (no A/B with the root switched off). Seen in the game (`batch-p2-b2`, `b4`): the ground reads as varied desert (gravel sheets, pale pans, washes, berm lines, patchy ripples); outcrops match the basin sandstone. Open: craters are painted, not dug; the world map's survey picture shows the old bowl and needs `WorldMapInstall20261119 --steps survey` (graphics). Edit Mode 421/421. Native on `Builds/batch-p2-final` (20 Nov 01:02, `unity/evidence/showcase_phase2/20261120/qa/final`): verify PASS; Berms expansion 8/8, next-level enemies 42/42, rifle quest 41/41. Gunner separation 7/8 (the relay-knoll gunners 1.42 m apart for a moment against a 1.5 m limit); three more alternating runs gave 1.84, 2.23, 1.34 m on the phase 1 build and 1.83, 1.36, 1.44 m on this one, so the check is marginal on both and the result is not attributable to this pass. Not yet accepted by Carl. |
| Ward residents | 20 Nov 2026, showcase phase 2 (`art/ward_residents_20261120`, `meshy/ward-residents-20261120`, `Editor/WardResidentsInstall20261120.cs` with `barks`, `simulate`, `import`, `prefab`, `install`, `verify`, `rollback`, `capture`; scene roots **Ward residents** and **Ward residents review cameras**, 17 `cam_res_*` of which the nine face/body/beside cameras follow their resident; QA landmarks `res_nadje`, `res_pell`, `res_oren`): three residents in places built to show how Ward lives that had nobody in them. **Nadje**, a Karaveen produce and pottery trader, at the caravan market by the West Gate (stock crates, pottery stall, produce counter); **Pell**, the Node 07 goods dock tally clerk (tally desk, platform scale, bays 1 and 2, handcart); **Oren**, an old water carrier, from his door in the south-wall container homes to the ration taps behind Vanguard Hall and back. Meshy 7.1 multi-image models from gpt-image-2 concept sheets, rigs with finger bones (`SmartRigArmature`, 66–68 bones), LOD0 20k / LOD1 6k, 4k base colour; 123 Meshy credits (paid plan since the evening of 19 Nov). `AmbientWalker` gained work stops (`stops`: waypoint, seconds, facing, talk clip; speed eases in and out; walkers without stops run the old code path, checked against `before.json`); routes in `routes.json`, checked offline and by two simulated laps against the saved colliders. 18 ElevenLabs bark lines (voices Kirsty, Alfie, Bill): Passing lines, and Idle remarks while at work; `BarkDirector` has 14 speakers (re-running `NpcLifeInstall20261119 --steps scene` drops the residents: re-run this `install` after it). Installed as residents-16 (skin de-weave and follow cameras), verify OK. Seen in the game (`batch-p2-b4`): three distinct people at conversation distance, working at their stops at 17:00. A woven crosshatch in the Meshy skin albedo (Pell most, Oren faint, seen on b4) was filtered out of the skin texels (FFT de-weave, `tex/deweave.py`, residents-16; no Meshy credits) and is gone in the final build's frames except a faint grain on Nadje's forehead at 1.0 m. Open: voices unheard; Oren's drink is an empty hand; their frame cost was not measured on its own. Edit Mode 421/421. Native on `Builds/batch-p2-final` (20 Nov 01:02, `unity/evidence/showcase_phase2/20261120/qa/final`): verify OK; `capture_residents_native.py` 6/6 (follow cameras find all three; frames looked at); NPC life 27/27; city loop PASS; runtime actor count 19. Not yet accepted by Carl. |
| First-person rifle hands | 19–20 Nov 2026, showcase phase 2 (`art/rifle_hands_20261120`, `Editor/RifleHandsPass20261120.cs` with `install`, `verify`, `rollback`, `dump`, `capture`; no scene cameras, native frames by `unity/tools/capture_rifle_hands_native.py` at `rifle_stand`): the rifle view model is weapon-driven like the pistol's (`RH weapon mount`; `ViewModelArmsRig` hip and aim anchors; the arms follow 60 % of the weapon's motion and all of the draw). `RH right arm IK` and the arms' `SupportHandIK` (`twistShare` 0.6) hold `RH shooting grip` (palm on the pistol grip, 0.795 of the length from the muzzle; the old mount at 0.35 from the butt was the magazine well) and `RH support grip` (palm up under the front receiver, 24 cm ahead); fingers and thumbs contact-solved into `PlayerHandGrip.rifleRight/rifleLeft`. Hip re-framed: `hipOffset (0.13, −0.19, 0.40)` → `(0.17, −0.15, 0.56)`, the bore converging on the crosshair; ADS from the sights (`aimOffset (0.011, −0.1723, 0.33)`: front sight on the crosshair, butt behind the eye). Muzzle, flash, tracer, ballistics, recoil and sway unchanged. Also re-skinned the pistol's glove/arm-guard copies onto its arms (they were bound to its weapon mount). `check_rifle_quest.py` asserts both hands within 2 cm of their grips (41/41 on `batch-p2-b1`, first install). Installed as rifle_hands-25, verify PASS. Seen in the game (`batch-p2-b3`): before, no hands in frame; now the rifle points into the view with the support forearm and hand on the handguard at the hip, walking, sprinting and firing; the shooting hand is mostly below the frame. Open: the sleeve at the left elbow can show at the bottom edge; thumb bases overlap the rifle by a few mm. Do not re-run `MainCharacterInstall`/`TutorialSetInstall` with this pass installed (`rollback` first, `install` after). A pass that deliberately changes `PlayerWeaponPose` afterwards needs `--steps rebaseline --keys body.pose` (done once, for the arms pass's pistol carry; it changes no scene data). Edit Mode 421/421. Native on `Builds/batch-p2-final` (20 Nov 01:02, `unity/evidence/showcase_phase2/20261120/qa/final`): verify PASS; rifle quest 41/41 with the hands assertions; `capture_rifle_hands_native.py` 12/12 (frames looked at, HUD on). Not yet accepted by Carl. |
| Character arms and pistol hold | 20 Nov 2026, showcase phase 2 (`art/character_arms_20261120`, `Editor/CharacterArmsPass20261120.cs` with `survey`, `dump`, `install`, `verify`, `rollback`; runtime `Scripts/ArmPose/`; root **Character arms review cameras**, 29 `cam_arms_*` plus seven inactive riding review rigs): Carl's playtest notes on `batch-playtest1119` (arms "in-natural and kinda camp", mostly the main character; the pistol hold "a little janky"). Not a regression: the Meshy library clips hold the arms 12–27° out with straight or backward-bent elbows, the player inherited them through the MPFB rest match, and `PlayerHandGrip` held his fingers flat and spread. `ArmPoseCorrector` (order −20, after the clips) on 18 humanoid actors (every `ActorAnimation` except the Berms mining droid) pulls collarbones, arm lean, reach, elbow turn-out and bend, forearm twist and wrist bend into a per-state envelope (idle, walk, run, talk, air); `ArmPoseFingerPass` curls relaxed fingers; walk and run keep their swing (player hand travel 47/41 cm). Player idle arm lean 12° → 6°, wrists 26° → 9°. Pistol: `PlayerWeaponPose.carryPitch` 60 → 40 with `carryWristShare` 0.8 and `carryWristMax` 30 (the wrist takes part of the carry turn), support hand relaxed while lowered, a two-handed extended aim by IK. Values in `characters.json` (profiles `meshy` and `player`, per-character overrides); `install` overwrites Inspector edits and picks up new actors. Installed as character_arms-8, verify PASS. Seen in the game (`batch-p2-b3`, `b4`): conversations natural (Vex, Linn, Brann); the player stands, walks and runs naturally seen from the side; the lowered carry is natural; the aim is an extended two-handed hold. Open: the pistol still turns 30–60° in the hand between carry and aim; the first-person pistol's support fingers stand flat beside the grip; talk gestures keep their character; Tamsin's working idle behind her counter was seen at three instants only. Re-installed over the residents before the final build. Edit Mode 421/421. Native on `Builds/batch-p2-final` (20 Nov 01:02, `unity/evidence/showcase_phase2/20261120/qa/final`): verify PASS; `capture_character_arms_native.py` 10/10 (stance, walk and run from the side, pistol carry, aim and fire, eight conversations: frames looked at); camera check 99/99. Not yet accepted by Carl. |
| Loadout body maps, eye implant slot and hotbar reorder | 20 Nov 2026, playtest fixes (`art/loadout_fix_20261120`, programme record `art/showcase_phase2_20261120/README.md`, `Editor/LoadoutFixPass20261120.cs` with `install`, `verify`, `rollback`; runtime `Scripts/AnatomyLayout.cs`, `CharacterLoadoutPanel.cs`, `PackPanel.cs`, `UI/CityHUD.uss`; no scene change): Carl's notes 1–4 ("Implants need a eye slot", slots "point to the wrong places", hotbar "titles dont go away" and no way to rearrange it, a "Random word "head""). EYE implant slot `implant_eye` after HEAD in `Resources/CharacterCatalog.asset`, empty: no eye implant exists and the Neural Targeting implant stays in HEAD (orchestrator's decision, Carl can overrule); an empty slot says what fits it; old saves load with the eye empty (equipment is saved per slot id). The implant and armour leaders had been drawn at each box's own height a fixed 135 px into the map, never against the letterboxed figure: now each body part has an anchor measured on `Resources/UI/ImplantBody.png` (1024 × 1536; PACK on the shoulder), boxes stand in a column either side as close to their dot's height as they fit, and `AnatomyLayout.Arrange` re-runs on every size change (compact 88 px boxes on narrow pages). The stray "Head" was the selection label, now hidden on the body-map pages. The lingering hotbar names were drag labels left by the HOTBAR strip's own drag code; the strip now uses the pack's drag (one label at most, ended by release, lost capture, a 100 ms watchdog, Escape, a page change or closing the pack) and reorders: drag a cell 3–0 onto another to move or swap, or focus a cell and press a number; 1 and 2 stay fixed to the primary weapon and sidearm; order saved in the v4 `hotbar` field. Edit Mode 428/428 (run loadout-2). Native: loadout and hotbar check (`unity/tools/capture_loadout_native.py`) 72/72, inventory redesign PASS, interface 22/22, home/journal PASS on `batch-p2-notes` (and 72/72, 39/39, 22/22, 36/36 on the agent's `batch-p2-ui3`). Seen in the game: the implants page (EYE beside HEAD, every leader on its part) and the armour page (PACK on the shoulder, no stray label) at 1920x1080 on `batch-p2-notes`; a drag with one label, the medkit moved from 3 to 5 and the order kept after a restart on `ui3`. Not verified: a real 3840x2160 screen; a release outside the window. Open: the Item Lab export `Data/Crafting/Export/ward-crafting.v1.json` is stale and lacks the eye slot. Not yet accepted by Carl. |
| Linn's voice | 20 Nov 2026, playtest fixes (`art/linn_voice_20261120`, `Editor/LinnVoicePass20261120.cs` with `install`, `verify`, `rollback`; no scene change): Carl: "Linns voice does not match, should be more older and rough". Linn spoke in Amelia (`ZF6FPAbjXT4488VcRRnw`, median pitch about 215 Hz). All 13 of her lines (dialogue nodes `greeting`, `hill`, `housing`, `housing_leased`; 9 barks) are now in **Seer Morganna** (`7NsaqHdLuKNFvEfjpUno`, median 123 Hz), Carl's pick from three candidates ("B is the best I think"; Empress and Maria Moody cached for a free switch). Same WAV paths, `.meta` files and GUIDs; `eleven_multilingual_v2`, stability 0.5, similarity 0.8, style 0.1, speed 0.92, mastered to about −20 LUFS; settings in `voice.json`, generator `linn_voice.py`. The housing offer and the reply after the lease had no audio before and are now bound in `Data/npc_linn.asset`. The two older generators (`unity/tools/generate_npc_voices.py`, `art/showcase_20261119/npc_life/generate_voices.py`) skip Linn so they cannot re-make her in Amelia. ElevenLabs: 2,777 credits on this item, 8,318 left. Native on `batch-p2-notes`: `check_linn_voice_native.py` 25/25 (new takes play in conversation, the 28 s housing take plays to its end, leaving early stops her voice), NPC life 27/27. Open for Carl's ear: he has heard 2 of the 13 takes; "Berms" in "You came back from the Berms. I'm glad." transcribes as "bums" or "bombs" after ten tries; "Karaveen" in the housing offer as "Caravene"; the greeting is slow (11.5 s) and the housing offer runs 28.2 s. Rollback to Amelia: `art/linn_voice_20261120/rollback.sh` (not exercised). Voice chosen by Carl from three candidates; the full set not yet accepted. |
| West Gate market barrels | 20 Nov 2026, playtest fixes (`art/gate_barrels_20261120`, `Editor/GateBarrelsPass20261120.cs` with `survey`, `heightmaps`, `lines-before`, `lines-after`, `install`, `verify`, `rollback`; scene roots **Gate barrels colliders** and **Gate barrels review cameras**: `cam_gb_caravan_east`, `cam_gb_caravan_north`, `cam_gb_rations_west`, `cam_gb_rations_north`; landmarks `gb_<line>_a/_b`): Carl: "Barrels on the floor by the waste gate, the broken ones on the floor need to be able to be walked over or need to go", read as the West Gate by the market (orchestrator's reading). The Poly Haven `wooden_barrels_01` set (two whole barrels and a broken one in pieces) is merged into two market `Goods` meshes. At the Karaveen caravan overflow by the truck (−45.5, 6.3; about 14 m inside the West Gate, the spot Carl raised on 3 Oct) the 3 Oct box stood over the broken staves and left the east whole barrel open; at the Rations stall (−36.8, −16.6) one 0.6 m box covered the whole set. Now `Caravan stock/COL_barrels` holds the west barrel, a new `COL_caravan_barrel_east` the east one, and `Stall Rations/COL_goods.010` the two small barrels; staves, lids and barrel halves (at most 0.39 m) have no collider. Nothing moved or removed; market kit untouched (instance overrides and one added collider). Positions measured from the LOD0 vertices (`heightmaps`), not the build script. Verify: five walk lines clear both ways (ten crossings) with a player-copy CharacterController (before: slowed or stopped). Native: `check_gate_barrels.py` 59/59 on `batch-p2-notes` (real W input, no pop, no camera pull-in); seen on `batch-p2-ui2`: the colonist standing among the staves, whole barrels still solid. Not verified: his feet passing through the 0.3 m barrel half in motion. Reported, not changed: two 0.4 m steel "severed foot" wreck slabs inside the West Gate that stop the player (off the gate lane); the Repairs wall drum cluster's box is shorter than its drums. Rollback `--steps rollback` (tested, values restored exactly). Not yet accepted by Carl. |
| Rendering baseline | Forward+, 150 m / 4-cascade sun shadows, HDR grading, TAA on High, procedural sky v2, interior-mapped windows, terrain v2, combat FX, truck/tree LODs. Measure changes with `unity/tools/lookbook.py` and `profile_scene.py`; the player is GPU-bound on the reference machine. **Light limit** (found by the birch canopy pass, 1 Oct 2026): on the Linux OpenGL Core player URP draws at most 32 lights per camera (sun, fill and the 30 nearest local lights). Courtyard views see 68–85 lights, so lamps beyond about 26–36 m are culled. Carl left this to the agent on 19 Nov 2026 ("your discretion"). **Decision: a light-budget pass on OpenGL; no move to Vulkan now.** Reasons: the installed URP gives OpenGL Core 32 visible lights and other desktop APIs 256 (`UniversalRenderPipeline.maxVisibleAdditionalLights`), so Vulkan would lift the cap, but the Linux player ships OpenGL Core only (every shader variant, every native check and all evidence are on it, and the QA harness forces `-force-glcore`), the game is GPU-bound with hill and avenue views at 56–59 fps, and drawing up to 138 lights instead of 32 would cost frame time where there is none to spare. A budget pass (nearest lamps real, far lamps as emissive bulbs with cheap ground pools that hand over to the real light on approach, redundant lights merged) removes the pop-in and should recover frame time. It also fits Ward saving power. Done 19–20 Nov 2026 (row **Light budget** above): at most 28 local lights in view, 21–26 at every review camera at 20:30 (30–178 without the budget), demoted lamps as pools; it removes the cull by design but did **not** recover frame time (URP already shaded only 30 lights per camera): neutral at cam_hill, cam_avenue and cam_night_spawn_apron, about +1.0 ms at cam_night_avenue_west on the final build even with the pool cap (44.4 → 42.5 fps). Against the phase 1 build the whole of phase 2 is about 0.3 ms slower at the hill, avenue and gate views at 13:00 and 20:30 (inside the run spread; 60–63 fps at hill and avenue on both builds) and 0.9–1.6 ms slower at the two heavy night views (spawn apron 37.3 → 36.0 fps, avenue west 45.5 → 42.5 fps). Pop-in during fast turns is not judged. Revisit Vulkan only as a measured side-by-side experiment if the pass cannot hide the cull. **Texture memory** (1 Oct 2026, `art/texture_memory_20261001`): 434 scene textures compressed with no source downsampled and no reference changed: 414 glTF-embedded images to BC7 by the glTFast import add-on `GltfTextureCompression` (on by default, so every .glb import compresses), 20 non-power-of-two TextureImporter maps to BC7/BC5, scaled up to a power of two and streamed. Native at three views: non-streamed textures 4.0 → 1.6 GB, resident 4.7 → 2.2 GB, player VRAM 8.0 → 4.5 GB. glTF textures are not streamed and glTF meshes keep UV distribution metric 1 (open). Render-chunk meshes record UV distribution metrics since the paving pass. The PC texture streaming budget is 5,632 MB (raised from 4,096 by the paving pass, pending Carl); after compression the texture-memory pass recommends 3,584 MB (Carl decides). **Night facade tune** (1 Oct 2026, `art/night_facade_20261001`, `NightFacadePass`): the 34 caged wall lamps of the nine shops and Vanguard Hall are down-and-out cookie spots with dimmer bulbs and glowing globes, the two West Gate arch bulkheads retuned, shop windows on per-street *Ward Window Interior* materials (less room light, more blinds, a third lamp colour), Ward masonry normal scale 0.65, the orphaned Finery porch decals and the floating jib-hoist remnant (the 13:00 hill-bench shadow) retired; values in `facade-tune.json`, originals recorded for rollback. Not yet accepted by Carl. |

Read the relevant source records before replacing assets:
[character imports](docs/model-import.md),
[animation reference and user-supplied Meshy list](docs/animation-reference.md),
[Ring Gate](meshy/ring-gate-v1/README.md),
[mission terminal manifest](meshy/mission-terminal-v1/model/meshy-manifest.json),
[salvage](meshy/salvage-20260908/README.md),
[district/rejected shops](meshy/district-20260908/README.md),
[audio](unity/AUDIO.md).

## 4. Visual direction: contemporary fidelity on Tir

Keep the desert colony identity: sun-warmed mineral surfaces, salvaged industrial
metal, patched cloth, restrained cyan technology, an oasis tree, layered desert
terrain and a settlement with visible work and history. Early MMO city references
inform atmosphere and social readability. They do **not** prescribe 2001 rendering,
low polygon counts, muddy textures, primitive anatomy or crude animation.

Build visual storytelling from the lore: aquifer infrastructure, hydroponics,
food stalls, nanofabrication workshops, adapted industrial droids, caravan repairs
and defensive works are useful motifs. They should explain how Ward survives.
Art motifs do not imply working simulation systems. Place wear at joints, handles,
drainage paths and repair sites; avoid uniform grunge across every surface.

Use warm sandstone, varied weathered metals, restrained cloth accents, localized
vegetation and cool sky/shade. The old hex palette is reference, not a rule that
all materials must share one tint. Keep distinguishable stone, painted metal,
bare metal, rubber, fabric, soil, bark and skin under the same lighting.

Requirements for the visual target:

- **Architecture:** believable construction and human scale, coherent rooflines,
  doors, recesses, supports, trims and functional thresholds. Build depth where the
  player can see it. Repeated modules need meaningful structural/material variants.
- **Street composition:** intentional foreground/middle/background, readable
  landmarks, shade, working spaces and localized clutter. Preserve clear paths;
  density means purposeful activity and construction, not random prop counts.
- **Hero tree and terrain:** convincing roots, branching, canopy mass, bark scale,
  leaf clusters, ground transitions and layered geology. Judge silhouettes at
  distance and surfaces/foliage at player height, including motion.
- **Characters:** convincing anatomy, face/hair, fabric and armour construction,
  hands/feet, deformation and ground contact. Natural idle, turn and locomotion
  transitions are quality work; source static poses are not final animation.
  Supplied models are a starting point, not a fixed assignment: replace them when a better character serves the role
  (e.g. give Mira, Torr, Vex and Linn distinct faces, clothing and silhouettes instead of one armoured guard).
  Use Meshy (generation, texturing, remeshing, rigging, animation — pre-approved in §5) or other licensed sources,
  keep the gameplay roots, dialogue IDs, routes and save/data references, and keep the previous model recoverable.
- **Materials:** correct scale and UVs; distinct albedo, normals, roughness and
  metallic response; controlled dirt and edge wear. Keep shading readable in shade.
  Do not bake strong directional light or shiny highlights into base color.
- **Lighting:** a coherent sun/sky/exposure relationship, plausible bounce and
  shadow contact, local practical lights and reflections where justified.
  Atmosphere should establish distance without flattening all depth into beige.
- **Presentation:** stable antialiasing, clean contact/shadow edges, readable UI,
  spatial audio and responsive camera/movement. Inspect shimmering, ghosting,
  popping, clipping, sliding feet and animation stiffness in moving gameplay.

Author scale in metres; Unity ground plane is X/Z and +Y is up. Use the existing
1.8 m actor and controller clearance as measuring references. Typical human doors
should read around 2–2.4 m unless an industrial opening is intentionally larger.
Preserve existing layout and routes during asset replacements. Retire the old
hard-coded browser coordinate diagram as an editing authority; inspect the saved
scene. Layout or playable-area expansion is a separate design task.

Preserve accepted concept images and prompts. Save new targets as dated versions
and explicitly record what they supersede. Older low-fidelity frames cannot veto
improvements requested by the user. Use matched reference angles and close-ups;
a concept image or Meshy thumbnail is never evidence of the game's final render.

## 5. Meshy and asset production

**Meshy credit approval, 8 September 2026:** routine Meshy generation, texturing,
remeshing, rigging and exports needed for requested asset work are preapproved.
Proceed without asking again about those costs. Record task IDs, options, usage
and outcomes. This is not blanket approval for unrelated asset purchases.
Free/licensed external resources are allowed with provenance and appropriate
usage rights. Keep original work; do not ship extracted Funcom/Rockstar content,
copied logos, UI chrome, music or game models.

Use Meshy for generation, Blender for authoring/cleanup/baking where appropriate,
and Unity for assembly and final verification. There is no Blender-only sourcing
rule. Use the live Blender MCP for Blender authoring and the working Unity MCP
for Editor operations. Inspect connection/instance state before mutations; report
an actual unavailable tool without treating it as a failure of unrelated tools.

For each replacement:

1. **Brief:** choose the accepted reference, real dimensions, closest player view,
   material regions, functional openings and placement. Include consistent
   front/side/back views when helpful. Distinguish source quality from runtime LOD.
2. **Generate/author:** retain detailed source geometry and full source textures.
   Do not default a hero building to a 3,500-triangle job or request low-poly art
   solely because the historical guide had a small scene budget.
3. **Inspect before installation:** compare the whole shape and pedestrian views.
   Check doors, roof thickness, railings, open apertures, fused parts, floaters,
   warped panels, holes, normals and baked text. Repair, split into modules,
   regenerate or reject failures. Extra texture resolution cannot repair geometry.
4. **Fit and shade:** normalize orientation, pivot and scale without changing
   proportions. Use uniform scale for whole buildings/characters; change geometry
   deliberately if a parcel needs another shape. Never stretch axes to fill an old
   bounding box. Give signs separately authored, readable lettering.
5. **Prepare runtime variants:** create materials, collider proxies, LODs and
   texture settings. Preserve originals and task records; no destructive remesh or
   source downsampling. Judge each reduced version against the detailed source.
6. **Audition in Unity:** inspect a saved prefab instance at its intended placement,
   in sun and shade, from orbit and first-person cameras, with a human scale marker.
   Check collision/access, animation and draw/texture cost before broad rollout.
7. **Integrate and verify:** replace only the intended visuals, preserve gameplay
   roots/data and rebuild derived render chunks. Capture native views and test the
   affected real-input route. Keep a recoverable previous version.

The rejected district shops are a recorded failure case: independent X/Y/Z scaling
stretched Field Supply's relative height about 2.6 times; low-detail source meshes
lost roof/facade structure; 2k maps became 1k atlas tiles. The later uniform-scale
fix did not repair those assets. Do not re-enable them on that fix alone. The
rejected Ring Gate remesh similarly lost console/platform detail. Preserve these
records so later work does not repeat the same optimization mistake.

## 6. Geometry, textures and rendering budgets

The **250k visible-triangle limit, 80-draw limit, fixed light count, blanket ban on
real-time GI, one-material-per-family rule and fixed 512/1k/2k texture ceilings are
retired**. They were prototype constraints, not universal measures of efficiency
or requirements for native Unity. Do not replace them with arbitrary giant budgets.

Allocate cost according to screen coverage, viewing distance, material needs and
measured CPU/GPU/memory limits. Spend detail on silhouettes and surfaces the player
can inspect. Use modular architecture, tiling materials, trim sheets and decals
where appropriate, plus dedicated hero materials when sharing would lose quality.
A single atlas for an entire district must not erase its facade detail.

- **Geometry:** retain a detailed near LOD and build lower LODs for distance.
  Inspect transitions, silhouettes, normals and shadows. Use instancing and spatial
  culling for repetitions; retain editable source objects behind render chunks.
- **Textures:** choose texel density from the closest intended view. 2k–4k sets
  are useful starting points for material regions, not guarantees or ceilings.
  Use higher resolution when justified; large facades often need tiling/trim detail
  instead of one stretched unique map. Verify mip selection, anisotropic filtering,
  compression and atlas padding in the native player. Record VRAM/resident texture
  use; use mip streaming when appropriate rather than discarding source detail.
- **Material import:** verify normal-map orientation, color spaces and packed-map
  channels. Convert roughness to smoothness where the Unity shader requires it.
  Confirm metallic masks do not turn stone, dust, rubber or cloth into metal.
- **UVs:** the normal Unity convention is UV0 (`Mesh.uv`) for material textures,
  with separate non-overlapping lightmap UVs in UV1 (`Mesh.uv2`) when needed.
  Check importer behavior and any custom shader assumptions. Do not follow the
  historical guide's reversed lightmap/tiling assignment.
- **Lighting:** use appropriate baked/mixed lighting, probes, local lights, shadows,
  ambient occlusion and reflections. Dynamic GI, volumetrics or ray tracing are
  options to evaluate if supported and beneficial, not required labels for quality.
  Do not use bloom, fog, grading or depth of field to conceal bad source assets.

The current **URP** implementation is the working baseline, not an untouchable
limit. Before a pipeline/API migration, compare the same representative scene,
assets and cameras and document the visual gain, Linux support, shader/material
conversion, performance and maintenance cost. Preserve the working scene during
that experiment. Do not assume HDRP or an upgrade automatically repairs art.

Unity's [2026 pipeline strategy](https://unity.com/topics/render-pipelines-strategy-for-2026)
prioritizes URP development and HDRP maintenance. Roadmap features are not proof of
availability in installed URP 17.6.0. Verify actual package/API support; HDRP's
Linux support uses Vulkan in Unity's
[feature comparison](https://docs.unity3d.com/6000.0/Documentation/Manual/render-pipelines-feature-comparison.html).

Technical references:
[LOD](https://docs.unity3d.com/6000.0/Documentation/Manual/LevelOfDetail.html),
[mipmap streaming](https://docs.unity3d.com/6000.0/Documentation/Manual/TextureStreaming.html),
[lightmap UVs](https://docs.unity3d.com/6000.0/Documentation/Manual/LightingGiUvs.html).
Consult documentation matching installed versions before implementing a feature.

## 7. Performance and visual acceptance

The first playable performance target is an **average of 60 FPS at native
1920×1080 on the High preset** (render scale 100 %, no frame generation) on the
reference machine, the Linux **RTX 3060 12 GB / i9-10850K** host. Revised
30 September 2026: the 3060 is an older GPU, so occasional frame-time spikes are
accepted; a p99 or maximum above 16.67 ms is reported, not a failure on its own.
Record actual hardware/VRAM, driver, API, quality and render scale for each run.
A vague medium laptop is not a qualified platform. Establish additional named
hardware and quality profiles when that becomes a delivery task.
Optional high-quality screenshots must state their settings and cannot substitute
for the native gameplay target. Do not hide a lower render scale or frame generation.

Measure a warmed, representative standalone traversal with every current actor (the player, eight colonists you can
talk to, three walkers, the yard mechanic and three residents),
shadows, HUD and active effects, including shop/travel states. For new quality
qualification, target average FPS >= 60 on the recorded baseline; report duration,
p50/p95/p99/max, hitches, CPU/GPU time when available, memory and loading
separately. Judge cost with alternating before/after runs of the same walk (this
desktop drifts about ±1–1.5 ms between runs), once per batch of passes (below),
and state the change.
A pass that takes the average below 60 FPS, or adds repeated hitches during normal
walking, is a regression to fix or explain. Keep uncapped timing samples separate
from VSync-limited play. Report unavailable counters as unavailable, never zero cost.
Distinguish visible geometry from submitted triangles across shadow/depth/color
passes; draw calls, batches and SetPass counts are different measurements.

Historical reports and QA scripts may still assert 250k triangles, 80 draws or a
58 FPS threshold. Those are previous test contracts, not current art constraints.
When updating qualification tooling for a new visual pass, replace obsolete
budget assertions with explicit recorded profiles and the current frame-time
criteria. Keep old evidence intact; do not remove measurements, hide failures or
weaken checks merely to claim success. This documentation revision does not change
those scripts or retrospectively qualify any build.

For every significant visual pass:

1. Capture a baseline of the current saved native build. Use `cam_hill`,
   `cam_avenue`, `cam_gate`, `cam_grid`, `cam_whompah`, `cam_hero` and relevant
   asset cameras; keep position, lens, exposure and resolution matched.
2. Add **player-height close-ups**, character face/full-body views and a moving
   walkthrough. Inspect sun/shade, thresholds, foliage, LOD changes and first-person
   proximity. Wide skyline screenshots alone cannot accept a building.
3. Compare reference, before and after. Score composition/silhouette, scale,
   material detail, lighting/depth, density/storytelling, character/animation,
   temporal stability and UI/readability from 0–5, with specific defects.
   A score of 4 means strong at the intended viewing distance with minor remaining
   issues; 5 means the chosen reference target is met in that view.
4. Aim for at least 4 in every applicable category at hero views and close range.
   Broken anatomy, warped architecture, soft focal textures, clipping and blocked
   traversal are rejection reasons regardless of the average score. Scores support
   review; they do not certify whole-game AAA or GTA6 parity.
5. Exercise affected verbs with real input, inspect runtime logs and record
   performance. An image improvement with a broken route or excessive frame time
   remains unfinished. Preserve the user's rejection/acceptance decisions.

**Batched verification (1 October 2026).** Per-pass builds, native lookbooks, A/B
profiles and city loops were taking most of the working time. When several passes
run, steps 1–5 apply to the batch, not to each pass:

- **Each pass:** authors and reviews with Blender renders and a few small editor
  captures, then installs into the saved scene. It verifies the scene with
  `-nographics` (installed, prefab links, no missing materials, chunk fingerprint,
  retired objects inactive). It validates placements against colliders, routes,
  doors and NPC points, and adds `cam_<pass>_*` review cameras at player height.
  It does not build the player or run native tests of its own.
- **Each batch:** one combined native test, made of a development build, a
  lookbook of every review camera at 13:00 and 20:30, alternating frame-time runs
  against the previous batch's build, the city loop and the range tutorial check.
- **Afterwards:** defects and costs go back to the owning pass for a fix round. If
  a batch is over budget, toggle pass roots to find which pass is responsible.

Iterate a focused family of changes to keep comparisons useful. Coupled fixes
(such as geometry, UVs and its texture bake) may be developed together when they
solve one documented problem. Do not let a rigid one-family rule block necessary
work or turn every small document edit into a full game test run.

## 8. Editing, architecture and verification

The game must remain ordinary editable Unity content: saved scenes, modular
prefabs, materials, animation assets, Inspector controls, serialized gameplay data,
Input Actions and UI Builder assets. No runtime script may reconstruct the whole
city to hide missing authoring. Scene assembly/import helpers are Editor-only;
one-time installers must not overwrite an already edited city.

Use [unity/EDITING.md](unity/EDITING.md) for the source-edit/rebuild workflow.
Show source renderers before editing, then explicitly rebuild render chunks.
Keep source transforms, collider proxies and prefab links. Do not edit disposable
chunk meshes directly or bypass the stale-source build guard. Use narrowly scoped
operations and preserve GUIDs; do not rewrite the entire scene for a visual fix.

Current implementation map:

- `PlayerMotor`, `FollowCamera`, `GameInput`, `ActorAnimation`, `AmbientWalker`:
  movement, camera, controls and actors.
- `GameSession`, `CityCatalog`, `NpcDefinition`, `ShopModel`: interactions, data,
  objectives and trading. Keep tuning and content serialized.
- `CityHud`, `UI/CityHUD.uxml`, `UI/CityHUD.uss`, `unity/DESIGN.md`: interface,
  bindings and shared visual rules. Keep UI labels editable and reserves inactive.
- `CityAudio`, `CityAtmosphere`, materials and scene objects: ambience and atmosphere.
- `AthenDebugBridge`, `NativeQa`, `unity/tools`: named cameras, state, captures,
  native profiling and real keyboard verification. No browser globals are required.

Use relevant existing Edit/Play Mode checks for logic changes and real-input
native checks for traversal, animation and UI changes. Build and launch the Linux
player after meaningful runtime/asset integration; verify the saved/reopened scene
and shipping materials/shaders, not just Editor Play mode. Release builds must
retain the development-bridge restrictions. Documentation-only edits need link,
content and diff review, not a game rebuild.

**Machine limits.** The reference machine has 32 GB of RAM and a 12 GB RTX 3060,
both shared with the user's desktop. Swap is zram, which itself uses RAM, followed
by a btrfs swapfile. Parallel Unity, Blender and player jobs crashed it three times
between 29 September and 1 October 2026: an NVIDIA out-of-memory error took the
desktop down, systemd-oomd killed the whole Claude app, and swap thrashing froze
the machine until it was reset. These rules apply to every session and tool:

- Run one Unity or native-player job at a time.
- Use `-nographics` for player builds and every Unity step that does not render.
  A graphics-mode build alone took about 9 GB of VRAM.
- Run Unity, Blender and the player each in its own memory-capped
  `systemd-run --user --scope` with a small swap allowance, so a runaway job is
  killed alone. A killed Unity can leave its import workers and Unity.DataStore
  behind, so stop the whole scope.
- Keep batch editor captures to about six cameras per run.
- Close the Unity Editor before native runs.
- Keep run state and scripts out of `/tmp`, which a reboot clears.

Keep dated evidence under `unity/evidence/`, with the tested revision or working-tree
snapshot/build identity, references, settings, captures, logs and remaining defects.
Do not attribute old performance, route or image acceptance to a newly changed scene.
Keep credentials out of documentation, source and logs; use the configured local
secret mechanism. Retain asset/task provenance and distribution notices.

## 9. Production milestones from the current build

This is the working outline, not authorization to implement every phase at once.
Continue from the existing city instead of restarting historical phases 0–7.

| Milestone | Work and exit evidence |
| --- | --- |
| Quality baseline | Record the current native district, close-ups, moving route and performance; agree on versioned contemporary visual references and document the visible gaps. |
| Representative street | Bring one facade, its threshold/ground/props and lighting to the target together. Preserve source detail, correct proportions, readable materials and traversal; accept at player height before replicating the approach. |
| Hero landmarks | Improve the hill tree, gate, hall and skyline using the established material/detail standard. Preserve existing accepted Meshy gate/terminal work unless it is the subject of the pass. |
| Characters and life | Improve faces, hair, clothing, idle/turn/locomotion and purposeful ambient behavior without breaking current NPC roles/routes. Keep costs measured; density expands through explicit gameplay work. |
| District rollout | Extend accepted modules/material standards through the city; add lore-grounded working spaces and prop clusters. Recheck repetition, paths, first-person detail and performance. |
| Presentation and qualification | Finish light/shadow/reflection quality, temporal stability, audio mix and UI cohesion. Pass native route/verbs and frame-time criteria, with honest remaining art gaps. |
| Future gameplay slice | When requested, design one bounded survival/FPS/settlement loop from the lore, then prototype and qualify it before larger world/system expansion. |

Prioritize the weakest visible part of the actual gameplay frame. The current
[recovery screenshots](unity/evidence/district/20260908/recovery/native) still show
repetitive facades, broad empty paving, limited
tree/canopy structure and uneven close-up surface quality. These are starting
observations, not acceptance of those limitations as the game's style.
