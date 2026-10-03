# Ward "next level" programme, 2 October 2026

Carl's request and the shared rules are in `BRIEF.md`. Three agents worked in parallel (one Unity job at a time under
the programme lock); the orchestrator ran the combined native batches. Agent reports: `character/REPORT.md`,
`enemies/REPORT.md`, `combat/REPORT.md`. Evidence: `unity/evidence/next-level/20261002/`.

| Item | Outcome |
| --- | --- |
| Main character → `main_char_OK` | Done: 595k-triangle source decimated to 60k with a 4k baked normal, Meshy re-rig (29 credits) and clips, installed through the existing player path with weapons and vest re-mounted on the new hand (`character/`). `main_char_NOK` staged in `meshy/main-char-20261002/nok-held-for-later/`. |
| New music | "Oasis of Ruins" added and leads `CityAudio.musicPlaylist`; the two old tracks remain (`unity/AUDIO.md`). |
| Rifle backwards | Cause found (the installer's thinner-end heuristic chose the stock); muzzle end is now an explicit measured setting with a guard; proven by editor captures with the muzzle marker. |
| Three more droids | Two delivered models were droids: **Scrap Reaper** (melee walker) and the **Post Sentinel**, built as a wheeled mover after Carl's note. The third file ("Ironclad Warden") is a bearded human salvager, used as Brann's new model instead (see below); the hostile version built first is retired and recoverable. No third droid model was delivered. |
| POIs, encounters, loot crates, rewards | Four new outer-ring sites (Post relay, Reaper den, Fans camp, Southern cache), 9 crates/strongboxes, new rare parts, `DroidThreat` levels on every droid (`enemies/`). |
| Threat bar grey/green/red, XP | `DroidThreat.Tier` from time-to-kill vs time-to-down with the equipped weapon and armour; HUD bars tinted, XP awarded on kills (Easy = none) with toast and level-up (`combat/`). |
| Trade sound | Quiet 34 ms digital click replaces the bell. |
| Gunners "attached" | Real cause: the gunner and lancer prefabs carried a whole nested worker/drone droid; removed. A second effect, gunners stacking on each other while firing, is fixed by droid-to-droid separation while standing, aiming and firing (`FeralDroid.separation`, 2.4 m on ranged droids). |
| Weapon ranges and accuracy | Pistol 30 m / 4° spread, rifle 95 m / 1.8°, damage falloff beyond 60 % of range, accuracy from weapon + character accuracy stat + weapon skill (`WeaponBallistics`). |
| Salvage NPC model | The delivered human biped is Brann's new body (walk/run from the rig, procedural breathing idle and counter gesture); the Meshy hauler is kept in `Prefabs/Retired/`. |

## Native batch `nl1` (17:24, tree fc2d37d0 dirty, Codex's inventory redesign merged)

- Build OK; rifle quest regression 34/34 (new colonist, Codex inventory); city loop PASS; range tutorial 10/10;
  Berms expansion check 8/8; no runtime exceptions in any run.
- A/B against `batch-rifle4` (two runs each, 13:00 and 20:30): avenue −0.4/−0.6 ms, hill +0.5/+1.0 ms, gate
  +1.0/+1.3 ms p50 (the 60k colonist in frame; 117/111 fps there). Within Carl's relaxed target; a 15k LOD1 of the
  colonist was exported but not installed.
- Gunner separation check: nest is clean (two gunners + worker, no nested droids) but a chasing gunner walked onto
  the firing one (0.68 m) → fix round.
- Next-level enemies check: encounters activate and engage, Reapers wind up, Sentinels fire bolts and roll, kills drop
  the new parts; but the sites are over-tuned for the intended kit (3 Reapers = 112 rifle shots, 5 downs; mixed camps
  0 kills) and the check's fixture pack filled up → fix round (`enemies` agent, batch `nl2`).

## Fix round `nl2` (enemies agent, 18:31, build `Builds/batch-nl2`)

- Precision barrel armour penetration +4 → +8 so the modded rifle lands full damage on armour 14; Reaper 400 HP /
  strike 18 / 0.6 s tell, Sentinel 560 HP / 3 × 16 bolts after a 1.2 s tell (≈14 and ≈20 rifle hits).
- `check_next_level_enemies.py` 42/42 with the intended kit (rifle + precision barrel, Rifle 20, full basic armour):
  Post relay 2 Sentinels 105 shots / 65 s, Reaper den 3 Reapers 45 shots / 25 s, Fans camp 73 / 41, Southern cache
  64 / 37, **0 knock-downs**; the starter pistol + field vest still reads Danger and loses (`NextLevelEnemiesTests`).
- `check_gunner_separation.py` 8/8 (≥ 1.5 m over 20 s of fighting). Edit Mode 255/255.
