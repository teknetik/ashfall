# Outer Berms combat primer — 26 September 2026 (first pass)

Installed by `AthenHill.Editor.OuterBermsPass` (`Editor/OuterBermsInstaller.cs`; menu **Athen Hill → Outer Berms**).
`pass.json` records sizes, spawns and placements; `editor/` holds Editor stills from the `cam_berms_*` cameras
(worker droid and drone were placed temporarily for the depot still; they spawn only at runtime).

- West wall opened behind the Karaveen truck (z −2.5…4.5). Original wall + collider kept inactive; two clipped
  segments joined the render chunks (rebuilt).
- Ground mesh over the basin floor (SandstoneBasin material, basin vertex lighting), service road, Warden post
  (Warden Ossa sentry, arms locker), three range plates, machine depot, invisible boundary walls.
- Tutorial (`BermsTutorial` on the `Outer Berms` root): locker → 7 draw → three plates → one scrap drone →
  depot nest (2 worker droids + drone) → 15 cr + 2 scrap coils. Depot re-forms 120 s after completion.
- Combat: `PlayerCombat` + `Health` on Player; `CombatHud` on City HUD (live Vitality/Nano, crosshair, hit marker,
  enemy bars, Field Notes line, pistol slot 7). Input actions added: Slot7 (7), Aim (RMB), Fire (F); LMB fires while aiming.
- Sources: `meshy/outer-berms-20260926` (task records, rig/animation ids and credits), merge script
  `art/outer_berms_20260926/merge_worker_droid.py`, SFX `unity/tools/generate_berms_combat_audio.py`.

Verification: EditMode tests 55/55 pass (incl. new Health and ShopModel.Grant tests). Linux development build
succeeded (0 errors) at `Builds/LinuxDevelopment/AthenHill.x86_64`. **Not yet done:** native real-input play-through,
performance run, city-loop regression check, release build, held-pistol orientation check, acceptance scores.
Known gaps: no aim/shoot pose on the player; close-range ground texture is blobby; depot walls are plain boxes.
