# Rooftops and service cables — progress (1 Oct 2026, batch 2)

Workstream brief: `/home/teknetik/.local/state/ward-programme/prompts/09-rooftops-and-cables.md` (next-wins item 8).

## Status

- 15:05 Read the brief, BRIEF.md (memory safety, revised DoD), AGENTS §1–8, EDITING.md. Verified the review claim on
  the cited 30 Sep native stills (`review/before-sheet.jpg`): every shop roofline is an unbroken cornice from the street;
  only the Air + Water tank dome, the Repairs container, Relay's mast and Salvage's shed/stovepipe break it.
- 15:10 Orchestrator go-ahead received: the batch-1 build has been taken; installing into the saved scene is allowed
  (one-time install with rollback copy, verify with -nographics). No player builds / native runs of my own.
- Roof data gathered from the shop records (`Art/WardShops/Models/*.json`, author scripts): roof decks, copings,
  existing roof furniture, night-life smoke columns (Repairs flue ~(19.85, 4.83), Salvage stovepipe ~(-20.3, 20.65)).

- 15:20–15:40 Kit authored (`author_roof_kit.py`, 19 objects incl. ladder/rail variants) and reviewed in Blender
  (`review/kit_*.png`); layout (`layout.py` → `layout.json`, 35 placements, 8 spans, 8 conduit runs) validates with
  0 problems against the fresh audit (`unity/evidence/rooftops/20261001/audit-before.json`); cables (`author_cables.py`);
  street-level Blender reviews (`review/street_sheet_v2*.jpg`).
- 15:41 Unity: `RooftopsPass` build (27 prefabs, 0 unmapped materials) → **installed** (one time, rollback copy in
  `unity/evidence/rooftops/20261001/rollback/`) → verify OK (43 instances, all prefab-linked, 0 missing materials,
  chunk fingerprint unchanged, 6 review cameras `cam_rt_*`).

- 15:50–16:10 Editor captures v1 (`unity/evidence/rooftops/20261001/editor-v1`, on and off): the kit reads from the
  avenue mainly where it sits at the front parapet or rises well above it; Tool Exchange's PV frame and Thread + Hide's
  tank were hidden; an ambient walker stood in front of cam_rt_east_north. Fix round: PV frame raised to 0.9 m, the
  horizontal tank put on a 1.15 m braced stand, a front rail on Thread + Hide's drying terrace, street-kit seat shadows
  off, east_north camera moved off walker 03's loop, row cameras pitched up. Closer "roof-targeted" cameras were tried
  in Blender and rejected (inside ~10 m of a 9 m facade the parapet hides everything behind it).
- 15:53 Reinstalled (authoring `reinstall`) and verified: 44 instances, all prefab-linked, 0 missing materials,
  4 shadow-casting renderers (the two tanks), 0 lights, chunk fingerprint unchanged.

- 16:00–16:10 Editor captures v2 (cam_rt_*) and the review's cited views on/off (`editor-cited`, matched): from the cited
  district views the cornices are now broken; the dew net read as a blank billboard and the shade canvas as slate grey.
  Fix: net rebuilt as two darker, sparser bellied nets on three posts; canvas normals flipped up. Reinstalled 16:07,
  verify OK (44/44 linked, 0 missing materials, chunks unchanged). v3 captures: net reads as netting, canvas madder.
- Two wide editor capture runs were VRAM-killed (16:01, 16:07). Orchestrator (16:10): editor captures only for close
  views, ≤ 3 cameras per run; skyline judged in Blender and in the combined native lookbook. Unused Rail590 removed.
- 16:15 Evidence README, DOCS_SNIPPET, report sent. **Done for batch 2; waiting for the combined-test defects.**

## Next

1. Fix round on the orchestrator's combined-test defects (native 13:00/20:30 lookbook of cam_rt_*, A/B, city loop).
   Authoring changes: `layout.py` / `author_roof_kit.py` / `author_cables.py` → `RooftopsPass.RunBatch --steps
   build,reinstall,verify -nographics` (reinstall keeps the first rollback copy).
