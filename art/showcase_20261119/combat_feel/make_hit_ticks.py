#!/usr/bin/env python3
"""Synthesises the three hit-feedback ticks for CombatHud (19 Nov 2026 combat feel pass).

No downloaded audio: each sound is a few decaying sine partials plus a filtered noise click, written as
44.1 kHz 16-bit mono WAV into Assets/AthenHill/Audio/UI/. Deterministic (fixed seed), so re-running gives
identical files. Usage, from the repository root:

    python3 art/showcase_20261119/combat_feel/make_hit_ticks.py
"""
import os
import wave

import numpy as np

RATE = 44100
OUT = os.path.join(os.path.dirname(__file__), "../../../unity/AthenHill/Assets/AthenHill/Audio/UI")
rng = np.random.default_rng(20261119)


def t_axis(seconds):
    return np.arange(int(RATE * seconds)) / RATE


def partial(t, freq, tau, gain, delay=0.0, glide=0.0):
    """Sine with an exponential decay starting at delay; glide bends the pitch up by that fraction."""
    local = np.clip(t - delay, 0, None)
    f = freq * (1 + glide * (1 - np.exp(-local / 0.01)))
    phase = 2 * np.pi * np.cumsum(f) / RATE
    env = np.where(t >= delay, np.exp(-local / tau), 0.0)
    return gain * env * np.sin(phase)


def click(t, tau, gain, brightness=0.85):
    """Short noise transient, high-passed by a one-pole difference so it reads as a tick, not a hiss."""
    n = rng.standard_normal(len(t))
    hp = np.empty_like(n)
    prev = 0.0
    for i, x in enumerate(n):
        prev = brightness * (prev + x - (n[i - 1] if i else 0.0))
        hp[i] = prev
    return gain * hp * np.exp(-t / tau)


def finish(x, peak_db=-3.0):
    fade = int(RATE * 0.002)
    x = x.copy()
    x[:fade] *= np.linspace(0, 1, fade)
    x[-fade:] *= np.linspace(1, 0, fade)
    x /= max(1e-9, np.max(np.abs(x)))
    return x * (10 ** (peak_db / 20))


def write(name, x):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.normpath(os.path.join(OUT, name))
    data = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data)
    print(f"{path}: {len(x) / RATE * 1000:.0f} ms")


def hit_tick():
    # dry metallic tick: reads under gunfire without competing with the shot's transient
    t = t_axis(0.05)
    x = click(t, 0.0025, 0.6) + partial(t, 2850, 0.006, 0.8) + partial(t, 4300, 0.004, 0.35)
    return finish(x, -4.0)


def critical_tick():
    # brighter, ringing double strike with a small upward glide: unmistakably "better" than a hit
    t = t_axis(0.11)
    x = (click(t, 0.003, 0.7) + partial(t, 3400, 0.018, 0.75, glide=0.06) + partial(t, 5150, 0.012, 0.35, glide=0.06)
         + partial(t, 3900, 0.014, 0.45, delay=0.022) + click(np.clip(t - 0.022, 0, None), 0.002, 0.3) * (t >= 0.022))
    return finish(x, -3.0)


def kill_confirm():
    # low body thunk, then a rising two-note chime: a confirmation, not an alarm
    t = t_axis(0.3)
    x = (partial(t, 170, 0.045, 0.7) + click(t, 0.004, 0.45, 0.6)
         + partial(t, 1900, 0.07, 0.5, delay=0.012) + partial(t, 2850, 0.09, 0.55, delay=0.075)
         + partial(t, 5700, 0.03, 0.12, delay=0.075))
    return finish(x, -3.0)


if __name__ == "__main__":
    write("hit-tick.wav", hit_tick())
    write("hit-critical.wav", critical_tick())
    write("hit-kill.wav", kill_confirm())
