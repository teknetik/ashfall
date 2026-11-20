# Linn's voice: three candidates (20 Nov 2026)

**Outcome:** Carl chose B, Seer Morganna ("B is the best I think"). She is installed for all 13 lines; A and C stay
cached. The "(installed)" mark on A below is from before his choice.

Carl's note: "Linns voice does not match, should be more older and rough". Nobody has listened to any of these takes;
the choice was made from the ElevenLabs library labels and descriptions plus Praat measurements (pitch, roughness) and
speech-to-text. Each candidate speaks the same two lines of Linn's, mastered like the game clips (-20 LUFS, peak
-2 dBFS or lower, mono 44.1 kHz), then saved as MP3:

- `*-greet_shade.mp3`: her short greeting bark, "Sit a while. The shade's free."
- `*-hill.mp3`: her longer dialogue line, "You can see the gate, hear the market, and get out of the dust. No terminal
  needs to explain that. If we get separated, meet me on the hill."

All three use the model `eleven_multilingual_v2` (as every other colonist) with stability 0.5, similarity 0.8, style 0.1,
speaker boost on, speed 0.92 (a little slower than normal, for an unhurried delivery).

The old voice for comparison: **Amelia** (`ZF6FPAbjXT4488VcRRnw`, British), median pitch about 215 Hz on Linn's takes.

| | Voice | Pitch (median) | Roughness (shimmer / jitter) | Background noise in the take | Pace on the long line |
| --- | --- | --- | --- | --- | --- |
| A (installed) | Empress | about 117 Hz | 9.9 % / 2.3 % | clean | 11.3 s |
| B | Seer Morganna | about 110 to 136 Hz | 6.4 % / 1.8 % | slight | 11.1 s |
| C | Maria Moody | about 152 Hz | 9.4 % / 3.1 % | **audible hiss** | 12.6 s |
| (old) | Amelia | about 215 Hz | 7.3 % / 1.8 % | clean | 10.2 s |

Higher shimmer and jitter mean a rougher, less steady voice; lower pitch means deeper. The figures come from Praat and
are only a guide: none of this replaces listening.

## A: Empress (installed default)

- Files: `A-default-Empress-greet_shade.mp3`, `A-default-Empress-hill.mp3`
- Voice id: `MHPwHxLx0nmGIb5Jnbly`
- Library labels: female, old, American, "deep", narrative story. Title "Empress - Smoky, Breathy, and Neutral".
- Library description: "Strong, Confident, 60-year-old Black Woman."
- Why: the only "old" English library voice that is both low and rough on every measure, with a clean recording. Smoky,
  deep and unhurried rather than sweet, which fits a hard old woman who lived through the Fall and the rebuilding.
- Risk: very low for a woman (about 117 Hz) and labelled as 60 rather than 75+. She may read as strong and smoky more
  than old, or the breathiness may come across as sultry.

## B: Seer Morganna

- Files: `B-SeerMorganna-greet_shade.mp3`, `B-SeerMorganna-hill.mp3`
- Voice id: `7NsaqHdLuKNFvEfjpUno`
- Library labels: female, old, no accent given, "wise", characters and animation. Title "Seer Morganna - Intimidating,
  and Clear".
- Library description: "The voice of an old wise seer woman telling people of their fortunes. Works well for
  Animations and characters in a story."
- Why: an old woman by design, low and slow, with some grain. A good pick if A sounds too young or too smooth.
- Risk: made as a fortune-teller character voice, so she may sound theatrical or a little like a crone. Slightly less
  rough than A on the measures.

## C: Maria Moody

- Files: `C-MariaMoody-greet_shade.mp3`, `C-MariaMoody-hill.mp3`
- Voice id: `wGcFBfKz5yUQqhqr0mVy`
- Library labels: female, old, American, "calm", narrative story. Title "Maria Moody - Grandmotherly Storykeeper".
- Library description (shortened): an octogenarian whose voice carries "patience in the pauses, wisdom in the
  restraint", someone who "speaks now only what matters".
- Why: she sounds the oldest on the measures (the most tremor and creak, the slowest pace), in a natural pitch for an
  old woman.
- Risk: her takes have a constant background hiss, only about 30 to 37 dB below the voice. None of the other colonists
  have that, so it may stand out in the game. Her library title is "grandmotherly", the kindly storyteller Carl may not
  want. All 13 of Linn's lines are already made in this voice (an earlier default), so switching to her costs nothing.

## Switching

From the repository root, then one short Unity run so the clips re-import and the check runs:

    python3 art/linn_voice_20261120/linn_voice.py --generate --voice <voice id>
    ~/.local/state/ward-programme/showcase-phase2-20261120/seq.sh install linn_voice-N AthenHill.Editor.LinnVoicePass20261120.RunBatch install,verify

Cost: C costs 0 characters (cached). B costs about 1,100 characters of text, about 450 of the account's credits at
today's rate. Any other library voice id works the same way.
