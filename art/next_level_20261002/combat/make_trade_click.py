#!/usr/bin/env python3
"""Quiet digital trade click for CityAudio.tradeConfirm (2 Oct 2026). Carl: the old ElevenLabs confirm "sounds like a
bell or hitting an empty can. should be quiet but digital, *click*". Synthesized in numpy, 48 kHz mono 16-bit, 34 ms:
a 1.2 ms rectangular transient (the "click") through a 2.6 kHz band-pass colour, followed by a 22 ms soft 1.9 kHz
blip at -14 dB that reads as "digital", both under a fast exponential decay. Peak -14 dBFS, no tail, no pitch bend.
Writes Assets/AthenHill/Audio/UI/trade-click.wav. Deterministic (no randomness)."""
import wave, struct
import numpy as np
from pathlib import Path
OUT = Path('/home/teknetik/code/ao2/unity/AthenHill/Assets/AthenHill/Audio/UI/trade-click.wav')
sr = 48000
n = int(.034 * sr)
t = np.arange(n) / sr
# transient: 1.2 ms rectangle, band-passed by a short damped resonator at 2.6 kHz
click = np.zeros(n); click[: int(.0012 * sr)] = 1.0
res = np.exp(-t * 2600) * np.sin(2 * np.pi * 2600 * t)
click = np.convolve(click, res[: int(.004 * sr)])[:n]
click /= np.max(np.abs(click))
# blip: soft 1.9 kHz tone starting 3 ms in, 22 ms, sine-shaped attack and exponential decay
blip = np.zeros(n); i0 = int(.003 * sr); dur = int(.022 * sr)
tb = np.arange(dur) / sr
env = np.minimum(1, tb / .0015) * np.exp(-tb * 180)
blip[i0:i0 + dur] = np.sin(2 * np.pi * 1900 * tb) * env
blip *= 10 ** (-14 / 20)
x = click * np.exp(-t * 900) + blip
# fade the last 2 ms to zero so the clip never ends on a step
fade = int(.002 * sr); x[-fade:] *= np.linspace(1, 0, fade)
x /= np.max(np.abs(x)); x *= 10 ** (-14 / 20)          # peak -14 dBFS
pcm = (np.clip(x, -1, 1) * 32767).astype('<i2')
OUT.parent.mkdir(parents=True, exist_ok=True)
with wave.open(str(OUT), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())
rms = 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)
print(f'wrote {OUT} {n / sr * 1000:.0f} ms, peak {20 * np.log10(np.max(np.abs(x))):.1f} dBFS, rms {rms:.1f} dBFS')
