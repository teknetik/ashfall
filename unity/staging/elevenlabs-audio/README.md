# ElevenLabs source audio

`manifest.json` is the authoritative map from source responses to the 13 final
Unity WAV assets. Adjacent per-generation JSON records retain the exact prompt,
model, timestamp, response identifiers when supplied, and source SHA-256.

Three first-pass effects were rejected by a frequency check: `lattice-hum`,
`stone-step-02`, and `lattice-open` had over 90% of their energy above 6 kHz.
Their original MP3/JSON files and `manifest-first-pass.json` remain as provenance.
The final masters use the respective `-warm-v2.mp3` replacements. The final
dominant frequencies are approximately 100 Hz, 54 Hz and 67 Hz. Unity asset names
and GUIDs stayed unchanged during this revision.

The 40-second `hill-at-dusk.mp3` is the original instrumental composition. Its
Unity master has a three-second tail/head overlap, producing a continuous
37.03-second loop. Ambient loops use a 150 ms overlap. These edits, gain balancing
and one-shot trimming are reproducible with `unity/tools/generate_elevenlabs_audio.py`.

Source generation uses the project's ignored `.env` credential and paid
ElevenLabs APIs. Existing matching responses are reused without API calls.
The game itself contains only local audio assets and performs no API requests.
