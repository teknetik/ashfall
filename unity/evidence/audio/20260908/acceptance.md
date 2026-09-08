# ElevenLabs audio acceptance — 8 September 2026

Result: passed in the final native Linux development and release players.

- 13 shipped assets: one instrumental and 12 effects/ambient beds; eight saved AudioSources.
- 13 development recordings exercise capture routing, a full music wrap, walking,
  market ambience, buy/sell, Lattice hum/activation/link, Ring offline feedback,
  pause, mute and restoration.
- Music remained playing through its 37.03-second loop boundary. The 42-second
  capture observed one wrap.
- Shop/dialogue music reached 65% of its gameplay volume; travel reached 40%.
- Each trade/link emitted one cue; UI progress refreshes did not repeat feedback.
- Pause and mute recorded exact zero RMS/peak; the paused music timeline stayed fixed.
- Release startup produced audible output with no audio-loading/runtime exceptions.
- All source WAVs decode, match their manifest hashes and retain at least 3 dB
  asset peak headroom. All five loop boundaries have no anomalous amplitude step.

Peak recorded development output: 0.4896 (-6.20 dBFS).
Release output RMS: 0.08164; peak: 0.3925.

## Evidence

- [Native recordings and report](native/report.json)
- [Final asset measurements](asset-checks.json)
- [Loop boundary measurements](loop-boundaries.json)
- [Saved audio configuration](scene-audio.json)
- [Combined build references and report hashes](combined-build-references.json)
- [Final generation manifest](../../../staging/elevenlabs-audio/manifest.json)

Both final build results are Succeeded. Their raw summaries retain two startup
licensing errors; those are preserved in the terrain task's build reports/logs.
No C# or shader compilation errors were reported in those final builds.

The first recording attempt captured the empty temporary sink because Unity/FMOD
selected its enumerated device instead of honoring PULSE_SINK. That rejected
capture is documented in capture-routing-first-attempt.json. The corrected check
moves only its own player's PulseAudio stream to the sink and verifies live
signal before the longer tests. The temporary sink and test players were cleaned
up afterwards; other applications' audio was not moved.

The first source versions of three overly bright effects are retained outside
Unity. Their lower-register replacements were included before the final builds.
