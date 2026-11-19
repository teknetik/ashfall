#!/usr/bin/env python3
"""Synthesise the two weather loops (wind bed, dust-front layer) for Ward's weather layer.

Nothing is downloaded and no paid service is used: every sound is shaped white noise from a fixed seed.
Noise is shaped in the frequency domain over the whole loop (rfft -> spectral gain -> irfft), which makes every
layer exactly periodic, and every amplitude modulation is either a whole number of cycles per loop or periodic
low-passed noise, so the last sample flows into the first with no click and no crossfade.

  python3 art/showcase_20261119/weather/generate_weather_audio.py

Writes 16-bit mono 44.1 kHz WAVs to unity/AthenHill/Assets/AthenHill/Audio/Weather/ and a provenance record
(seed, parameters, sha256) next to this script. Only numpy and the standard library are needed.
"""
import hashlib
import json
import os
import wave
from datetime import datetime, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(REPO, "unity", "AthenHill", "Assets", "AthenHill", "Audio", "Weather")
SR = 44100
SECONDS = 30
N = SR * SECONDS
SEED = 20261119


def band_noise(rng, lo, hi, tilt=-1.0, q_lo=1.0, q_hi=1.0):
    """Periodic noise with a smooth band-pass and a spectral tilt (tilt -1 ~ pink, -2 ~ brown) between lo and hi Hz."""
    spec = np.fft.rfft(rng.standard_normal(N))
    f = np.fft.rfftfreq(N, 1 / SR)
    f[0] = 1e-3
    gain = (f / 1000.0) ** (tilt / 2.0)
    gain *= 1 / (1 + (lo / f) ** (2 * q_lo))  # high-pass skirt
    gain *= 1 / (1 + (f / hi) ** (2 * q_hi))  # low-pass skirt
    gain[0] = 0
    x = np.fft.irfft(spec * gain, N)
    return x / np.sqrt(np.mean(x ** 2))


def resonance(rng, centre, width):
    """Periodic narrow-band noise: the whistle of wind over edges and wires."""
    spec = np.fft.rfft(rng.standard_normal(N))
    f = np.fft.rfftfreq(N, 1 / SR)
    gain = np.exp(-0.5 * ((f - centre) / width) ** 2)
    x = np.fft.irfft(spec * gain, N)
    return x / np.sqrt(np.mean(x ** 2))


def slow_envelope(rng, max_hz, floor, depth):
    """Periodic low-passed noise in [floor, floor + depth]: gusts that wander without repeating inside the loop."""
    spec = np.fft.rfft(rng.standard_normal(N))
    f = np.fft.rfftfreq(N, 1 / SR)
    spec[f > max_hz] = 0
    spec[0] = 0
    e = np.fft.irfft(spec, N)
    e = (e - e.min()) / (e.max() - e.min())
    return floor + depth * e


def lfo(cycles, phase=0.0):
    """Whole cycles per loop, so it is seamless."""
    t = np.arange(N) / N
    return 0.5 + 0.5 * np.sin(2 * np.pi * cycles * t + phase)


def normalise(x, peak_db):
    return x * (10 ** (peak_db / 20) / np.max(np.abs(x)))


def write(path, x):
    pcm = np.clip(np.round(x * 32767), -32768, 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def wind_bed(rng):
    # Broad, soft body of moving air, a darker low layer, and two faint whistles that swell in turn.
    body = band_noise(rng, 90, 900, tilt=-1.2) * slow_envelope(rng, 0.18, 0.45, 0.55)
    low = band_noise(rng, 35, 220, tilt=-1.8) * slow_envelope(rng, 0.1, 0.5, 0.5)
    w1 = resonance(rng, 520, 40) * lfo(3, 0.0) ** 2 * 0.10
    w2 = resonance(rng, 780, 55) * lfo(4, 1.9) ** 2 * 0.07
    x = 0.65 * body + 0.45 * low + w1 + w2
    return normalise(x, -4.0)


def dust_front(rng):
    # Heavier, turbulent roar with sand hiss riding the gusts; louder and busier than the bed, still no impacts.
    roar = band_noise(rng, 40, 650, tilt=-1.6)
    gusts = slow_envelope(rng, 0.45, 0.35, 0.65)
    hiss = band_noise(rng, 2200, 9000, tilt=-0.6, q_lo=2.0) * (0.15 + 0.85 * gusts ** 2)
    grit = band_noise(rng, 900, 3000, tilt=-1.0) * slow_envelope(rng, 1.2, 0.2, 0.8)
    x = 0.75 * roar * gusts + 0.22 * hiss + 0.16 * grit
    return normalise(x, -3.0)


def main():
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(SEED)
    files = {}
    for name, fn in (("weather_wind_bed.wav", wind_bed), ("weather_dust_front.wav", dust_front)):
        x = fn(rng)
        path = os.path.join(OUT, name)
        sha = write(path, x)
        files[name] = {
            "sha256": sha,
            "rms_dbfs": round(float(20 * np.log10(np.sqrt(np.mean(x ** 2)))), 2),
            "loop_seam_step": round(float(abs(x[0] - x[-1])), 5),
        }
        print(name, files[name])
    record = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": "art/showcase_20261119/weather/generate_weather_audio.py",
        "method": "numpy-shaped white noise (periodic FFT filtering), whole-loop periodic modulation; no downloads, no paid services",
        "seed": SEED, "sample_rate": SR, "seconds": SECONDS, "format": "PCM 16-bit mono WAV",
        "numpy": np.__version__, "licence": "Original work for Ward / Athen Hill",
        "files": files,
    }
    with open(os.path.join(HERE, "audio-provenance.json"), "w") as fh:
        json.dump(record, fh, indent=2)


if __name__ == "__main__":
    main()
