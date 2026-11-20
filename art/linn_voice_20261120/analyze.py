"""Objective voice measures (Praat via parselmouth): median F0, HNR, jitter, shimmer.
uv run --with praat-parselmouth --with numpy python analyze.py files... > out.json
Lower F0 = deeper; lower HNR and higher jitter/shimmer = rougher, breathier, more gravel."""
import json, sys, subprocess, tempfile, os
import numpy as np, parselmouth
from parselmouth.praat import call
def measure(path):
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "a.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-ac", "1", "-ar", "22050", wav], check=True)
        s = parselmouth.Sound(wav)
    pitch = s.to_pitch_ac(time_step=0.01, pitch_floor=60, pitch_ceiling=500)
    f0 = pitch.selected_array["frequency"]; f0 = f0[f0 > 0]
    pp = call(s, "To PointProcess (periodic, cc)", 60, 500)
    jit = call(pp, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
    shim = call([s, pp], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
    harm = s.to_harmonicity_cc(0.01, 60, 0.1, 1.0)
    h = harm.values[harm.values != -200]
    return {"file": os.path.basename(path), "seconds": round(s.duration, 2), "f0_median": round(float(np.median(f0)), 1) if len(f0) else None,
            "f0_p10": round(float(np.percentile(f0, 10)), 1) if len(f0) else None, "voiced_frac": round(len(f0) / max(1, pitch.n_frames), 2),
            "hnr_db": round(float(np.mean(h)), 2), "jitter_pct": round(jit * 100, 2), "shimmer_pct": round(shim * 100, 2)}
if __name__ == "__main__":
    rows = []
    for p in sys.argv[1:]:
        try: rows.append(measure(p))
        except Exception as e: rows.append({"file": os.path.basename(p), "error": str(e)[:200]})
    print(json.dumps(rows, indent=1))
