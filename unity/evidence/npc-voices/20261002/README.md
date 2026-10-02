# NPC voices and developer roster — 2 October 2026

Scope: seven named NPCs, 30 existing dialogue nodes, no dialogue text/choice/ID,
route, scene placement or graphics API changes. The work was made in the
`npc-voices` managed worktree from `ward/next-level` at `7fa91cc6`.

## Generation and installation

- ElevenLabs `eleven_multilingual_v2`, 30 direct text-to-speech API requests,
  5,776 input characters. Source MP3s, exact bodies, provider request/history
  IDs, character-cost headers and hashes are in
  `unity/staging/elevenlabs-audio/npc-voices/`.
- 30 mono 44.1 kHz PCM WAV masters (382.2 seconds total) in
  `Assets/AthenHill/Audio/ElevenLabs/NpcVoices/`, with stable Unity `.meta` GUIDs.
  All 30 authored nodes reference their matching clip. `--install` reproduced
  the links using cached source files without a new API request.
- Distinct voices cover four male characters (Torr, Vex, Brann, Rell) and three
  female characters (Mira, Linn, Ossa), with British, American and Australian
  accents. The roster, area and provider voice ID are recorded in the developer
  UI seed and its local SQLite `npc_voice` table.

## Verification

- Unity 6000.6.0f1 headless Editor audit: **7 scene NPCs / 30 resolved clips**.
  [editor-audit.json](editor-audit.json) contains every clip path and duration.
- Native Linux x86-64 OpenGL development build: **Succeeded**.
  [build.json](build.json) records the build report. Unity counted three
  non-fatal Editor errors during the build; the log showed license/prewarmer
  and allocator diagnostics, with no C# compilation error.
- Real-key native run: Mira, Torr, Vex and Linn greeted with their assigned
  audio in the SFX group. Torr's second node replaced his greeting take;
  entering Mira's shop and closing conversations stopped speech. See
  [native/report.json](native/report.json) and [Player.log](native/Player.log).
- Developer console: 28 backend tests, `node --check`, and isolated Chromium
  regression passed. The [NPC tab screenshot](devui-npcs.png) uses a labelled
  browser test fixture for the connection header; its roster rows come from
  the actual SQLite API. The browser regression also checked the seven rows
  and Vex's area and voice ID.

Remaining review: accent/performance preference is subjective and should be
auditioned in the native game. The native real-key pass sampled four of the
seven actors; the Editor audit covered all 30 clip references.
