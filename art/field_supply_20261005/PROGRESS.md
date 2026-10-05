# Field Supply shop (5 October 2026)

Carl (4–5 Oct 2026): "Open another shop - field supply. have a choice of low tech to mid tier packs for storage
upgrades. a digital magazine shelf that are basically recipes for crafting upgrades and packs. also sell med kits and
nano recharges."

Not yet accepted by Carl. This file is the working log; another session can resume from it.

## Design (decided in this pass)

**Where.** The existing hall-district Field Supply building (world (18.1, 0, −9), yaw −90; `art/hall_district_20260930`)
opens like Salvage did on 1 Oct: the front loading shutter rolls up and the ground floor becomes a walk-in shop with a
counter, a keeper, a pack wall, the digital magazine shelf and a med/nano cabinet.

**Keeper.** Tamsin, a former Karaveen caravan outfitter (`Data/npc_tamsin.asset`), not part of the four-colonist city
visit. Counter profile: title *Field Supply*, supplies limited to items tagged `field_supply` (stock tags), magazine shelf
on, no parts or salvage lists.

**Packs** (storage slot equipment; `Resources/CharacterCatalog.asset`). Storage kg / pack slots / carry kg:

| Item | Tier | Price | Storage | Slots | Carry | Sockets |
| --- | --- | --- | --- | --- | --- | --- |
| Field Backpack (existing, starting pack) | low | 24 | +25 | +16 | – | pouch |
| Stitched Canvas Rucksack | low | 48 | +32 | +20 | +2 | pouch |
| Karaveen Frame Pack | low | 95 | +38 | +22 | +6 | pouch, frame |
| Porter's Load Carrier | mid | 165 | +48 | +26 | +10 | pouch, pouch, frame |
| Courier Cargo Rig | mid | 245 | +58 | +30 | +14 | pouch, pouch, frame |

Carry capacity (10 kg + 2 × Strength) is what binds a starting character, so frame packs add carry as well as storage.

**Pack upgrades** (modifications for the pack's sockets; fabricated only): Side Pouch Pair (pouch: +4 slots, +3 kg),
Nanoweave Expansion Pouch (pouch: +6 slots, +6 kg), Padded Hip Belt (frame: +4 kg carry), Servo Load Lifter (frame:
+9 kg carry).

**Digital magazine shelf.** Magazines are catalog items tagged `magazine`; buying one downloads it to the field slate
(never enters the pack) and teaches every recipe whose unlocks list `{type: magazine, id: <magazine>}`. Ownership is the
set of known recipes, so saves need no new field.

| Magazine | Price | Teaches (Brann's workbench) |
| --- | --- | --- |
| Packcraft Quarterly · Issue 12 | 30 | Canvas Rucksack, Side Pouch Pair, Padded Hip Belt |
| Karaveen Freight Notes · Vol. 3 | 45 | Karaveen Frame Pack, Porter's Load Carrier |
| Nanoweave Monthly · Load Tech | 70 | Nanoweave Expansion Pouch, Servo Load Lifter, Courier Cargo Rig |
| Ward Armourer's Digest · Liners & Plates | 40 | Impact Liner, Thermal Liner, Ablative Chest Plate |

**Med kits and nano recharges** (consumables; `CityCatalog.consumables`). Medkit (existing, heals 40) and Trauma Kit
(heals 90), both scaled by the Healing efficiency stat (Medicine). Nano Recharge Cell (refills 100 nano and overclocks the
regulator for 15 s: +50 % regen with no pause while firing) and Nano Surge Pack (refill, 40 s, +100 %). Hotbar 2 uses a
medkit (the smallest that covers the missing health, else the largest); hotbar 9 uses a nano recharge.

## Log

- 5 Oct 00:xx — survey of shop/inventory/crafting/consumable code; Carl's player was running, so code and data first.
- 5 Oct ~00:30 — code: ShopProfile stock/exclude tags + magazine shelf flag, MerchantStock rules, MerchantPanel MAGAZINES
  tab, GameSession.BuyMagazine / UseItem / ConsumableFor, hotbar 2 (medkit) and 9 (nano, new Slot9 action), counts on the
  hotbar, PlayerCombat.Recharge overclock (nano bar brightens), CraftingModel magazine helpers, RecipeGroup Gear and
  ArmourMod, PackPanel price line names the counter. Data: `apply_data.py` (idempotent). Tests: `FieldSupplyTests.cs`.
- Icons: Codex login had expired ("refresh token was already used"; Carl must sign in to Codex again), so the 15 icons
  went through Meshy text-to-image (135 credits), `icons/meshy_icons.py`, fitted to UI/Art by `icons/fit_icons.sh`.
- Tamsin concept: Meshy text-to-image, two sheets (18 credits); v1 chosen (`concept/tamsin_sheet_v1.png`).
- Meshy balance ran out (402 Insufficient funds; 10 credits left after Tamsin's model and the five pack models were
  submitted). Tamsin: rig + idle_248 only; talk reuses Torr's talk_309 (same library clip, same Meshy bone names).
  Medkit, trauma kit and nano props were never submitted: modelled in Blender instead.
- 5 Oct ~00:40 — art: Tamsin (Meshy multi-image-to-3D 30 + rig 5 + idle_248 3 credits; talk = Torr's talk_309), five
  Meshy packs from their icons (150 credits; `meshy/field-supply-20261005/props`, prep `packs/prepare_packs.py`), cover
  art via the OpenAI key (gpt-image-2; mastheads set in Noto Sans, `covers/make_atlas.sh`). Walk-in interior authored
  (`field_supply_interior.py`, hooked into `author_ward_shops.py field_supply()`; exterior record unchanged apart from
  the rolled-up shutter slats). Blender review renders in `review/` (mirror-imaged, as the Salvage ones).
- 5 Oct ~00:50 — Unity: `FieldSupplyShopPass` materials/models/packs/tamsin/install/verify all clean; Edit Mode 276/276
  (4 older tests updated for the new groups, magazines and the second interior; new FieldSupplyTests incl. a scene
  test). WardNpcInstall's import/prefab steps now take a spec list and a record folder (behaviour unchanged).
- Editor captures: the first bake turned the room chrome. Cause: baked probes render only Reflection Probe Static
  objects (none were), so the probe saw the street, and a few pixels at the half-float max dominated it. Fixed (flags +
  EXR clamp in `bake`). Covers were mirror-imaged in Unity (fixed in `post_build`); the FIELD READS band had lost its
  lettering when the atlas went square (fixed). Captures: `unity/evidence/field-supply/20261005/editor/`.
- 5 Oct 01:13–01:16 — development build killed twice by the ward watchdog (MemAvailable < 1.2 GB; the desktop's
  compressed swap holds ~8.6 GB, ~12 GB free, a build needs ~14–15 GB). `qa/wait_build.sh` starts it once 15 GB is
  free. The native check is ready: `unity/tools/check_field_supply_native.py` (+ a dev-only `damage` QA command and
  `nanoOverclocked` in the snapshot). Native tests, city loop, range tutorial and A/B wait for that build.
- Spawned a separate task for the Salvage probe (same ReflectionProbeStatic gap; its probe shows the sky).
- Tamsin's voice: ElevenLabs returned 401 payment_issue ("Your subscription has a failed or incomplete payment"), so her
  five nodes have no voice clips yet (the dialogue text shows, as designed when a clip is absent). To voice her once the
  account is paid: add `{"id": "npc_tamsin", "name": "Tamsin", "area": "Ward / Field Supply", "voiceName": "Lily",
  "accent": "British", "voiceId": "pFZP5JQG7iQjIQuC4Bku", "lineCount": 5}` to `unity/tools/devui/npc_roster.json` and
  run `python3 unity/tools/generate_npc_voices.py --generate` (every other NPC's cached takes were verified current).
- 5 Oct 01:29 — development build succeeded once 15 GB was free (anon peak 12.9 GB). Native on that build:
  `check_field_supply_native.py` 25/25 (walk-in, Tamsin's dialogue and flag, Field Supply stock only, buying, magazine
  download teaches 3 schematics and is not carried, no double download, sell-back, medkit on 2 refused at full health
  and heals +40, nano on 9 refills and overclocks, slot 9 shown, bench lists the schematics, save keeps them, no
  exceptions); city loop PASS; range tutorial 10/10. Evidence: `unity/evidence/field-supply/20261005/`.
  (The first native run failed at the rucksack purchase because the test save had no character block, so no backpack
  was worn and 5 kg base storage could not take it; the counter refused correctly. The save now wears the issue kit.)
- 5 Oct 01:52 — A/B vs Builds/batch-tb (4 Oct 19:45), 2 alternating runs per arm, p50 ms delta (13:00 / 20:30):
  cam_hill −0.53 / +0.06, cam_avenue +0.69 / +0.35, cam_nf_field_supply (looking into the open bay) +0.50 / +0.40,
  cam_gate −0.02 / +0.04 (clean re-run, `ab-gate/`; the first gate "after" arm had a failed launch and one run with a
  single 10.8 s stall, p50 unchanged). All within the desktop's ±1–1.5 ms drift; avenue noon averaged 58.3 fps after vs
  60.7 before (p99 19.1 vs 18.1 ms), the only view under 60. Summaries: `ab/ab-summary.json`, `ab-gate/ab-summary.json`.
