"""Paired static-camera shadow cost diagnostic; never traversal qualification."""
import asyncio
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "unity/tools"))
from native_client import Client
from native_memory import snapshot as memory_snapshot

OUT = Path(__file__).resolve().parent
NATIVE = ROOT / "unity/evidence/quality/20260926/candidate-native-02"
PID = 1037608
CAMERAS = ["cam_hill", "cam_avenue", "cam_tree_canopy_below"]
ORDER = [(18, 1), (96, 4), (96, 4), (18, 1)]
os.environ.update(ATHEN_NATIVE_DIR=str(NATIVE), ATHEN_NATIVE_PID=str(PID))


def read(name):
    return json.loads((NATIVE / name).read_text())


def save(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2) + "\n")


def percentile(values, p):
    values = sorted(values)
    index = (len(values) - 1) * p
    low = int(index)
    high = min(low + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (index - low)


def summarize(frames):
    dt = [f["dt"] * 1000 for f in frames]
    if not dt or not all(math.isfinite(v) and v > 0 for v in dt):
        raise ValueError("Missing or invalid frame deltas")
    result = dict(frames=len(frames), seconds=sum(dt) / 1000,
        averageFps=1000 * len(dt) / sum(dt), p50Ms=percentile(dt, .5),
        p95Ms=percentile(dt, .95), p99Ms=percentile(dt, .99), maxMs=max(dt),
        hitchesOver33ms=sum(v > 33.33 for v in dt),
        hitchesOver50ms=sum(v > 50 for v in dt))
    for key in ["mainMs", "renderMs", "cpuMs", "gpuMs", "draws", "tris", "batches", "setPass"]:
        values = [f[key] for f in frames if math.isfinite(f.get(key, -1)) and f.get(key, -1) > 0]
        result[key] = dict(samples=len(values), coverage=len(values)/len(frames),
            mean=statistics.mean(values), p50=percentile(values, .5),
            p95=percentile(values, .95), p99=percentile(values, .99), maximum=max(values)) if values else None
    return result


async def main():
    if (OUT / "report.json").exists():
        raise FileExistsError("Preserve this run; choose a new output folder")
    client = Client()
    report = dict(complete=False, qualification=False, purpose=__doc__,
        utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), pid=PID,
        nativeFolder=str(NATIVE), cameras=CAMERAS, order=ORDER,
        requestedWarmupSeconds=3, requestedSampleSeconds=12, intervals=[],
        conditions="Opt-in background native OpenGL development player; desktop locked; Editor alive and idle. No real input or loading, traversal, shop or travel coverage.",
        counterNotes=[
            "Nonpositive timing counters are unavailable, never zero cost; positive coverage is reported.",
            "FrameTimingManager.GetLatestTimings(1) provides asynchronous latest timing without a frame timestamp in this recorder. GPU timing samples may repeat and cannot be aligned exactly to dt.",
            "Main-thread time includes waits. dt is frame wall time, not isolated GPU work. Render-thread recorder may be invalid.",
            "Unity triangles and draws include rendering passes; triangles are not visible geometry and batches/SetPass/draws are distinct.",
            "First recorded sample is retained raw but excluded from interval summary: profileStart runs in Update, after that frame delta began.",
            "Day/night time is fixed; nine actors, animation, foliage, dust and audio remain active and their phases vary.",
            "Environment dimensions describe launch; interval snapshots establish actual output resolution. Video/draft dimensions can be stale after QA resize.",
            "3-second settling and 12-second samples are a short exploratory comparison, not sustained performance or whole-game qualification.",
            "Native QA writes snapshots at 10Hz and allocates profiling samples. That overhead remains enabled for both alternatives."])
    initial_time = None
    profiling = False
    async def command(request):
        await client.command(request)
        if (NATIVE / "qa-error.json").exists():
            raise RuntimeError((NATIVE / "qa-error.json").read_text())
    def validate(settings, state, distance=None, cascades=None):
        assert [state["width"], state["height"]] == [1920, 1080], state
        assert state["session"]["state"] == "Play" and state["player"]["speed"] < .01, state
        assert settings["timeScale"] == 1 and not settings["previewing"], settings
        assert settings["renderScale"] == 1 and settings["vSync"] == 0 and settings["frameLimit"] == -1, settings
        assert settings["msaa"] == 4 and settings["textureLimit"] == 0 and settings["shadowResolution"] == 4096, settings
        if distance is not None:
            assert settings["shadowDistance"] == distance and settings["shadowCascades"] == cascades, settings
    try:
        assert not (NATIVE / "qa-error.json").exists(), "Existing QA error requires review"
        review = read("visual-review-state.json")
        assert not review["hudHidden"] and not review["transmission"] and review["shadowDistance"] is None, review
        executable = Path(f"/proc/{PID}/exe").resolve(strict=True)
        report["build"] = {"executable": str(executable), "sha256": hashlib.sha256(executable.read_bytes()).hexdigest()}
        managed = executable.parent / "AthenHill_Data/Managed/Assembly-CSharp.dll"
        if managed.exists():
            report["build"]["assemblySha256"] = hashlib.sha256(managed.read_bytes()).hexdigest()
        if (NATIVE / "profile.json").exists():
            shutil.copy2(NATIVE / "profile.json", OUT / "preexisting-profile.json")
        await command({"action": "settingsSnapshot"})
        report["initialSettings"] = read("settings.json")
        report["initialSnapshot"] = read("snapshot.json")
        report["environment"] = read("environment.json")
        validate(report["initialSettings"], report["initialSnapshot"])
        assert report["environment"]["actorCount"] == 9
        await command({"action": "actorSnapshot"})
        report["actors"] = read("actors.json")
        await command({"action": "timeState"})
        initial_time = read("time-state.json")
        report["initialTime"] = initial_time
        await command({"action": "timePause", "paused": True})
        await command({"action": "timeSet", "hour": 12})
        await command({"action": "timeState"})
        report["lighting"] = read("time-state.json")
        assert report["lighting"]["paused"] and report["lighting"]["hour"] == 12
        assert not report["lighting"]["reflections"]["pending"]
        report["initialMemory"] = await memory_snapshot(client, NATIVE)
        save("report.json", report)
        for camera in CAMERAS:
            await command({"action": "view", "camera": camera})
            for index, (distance, cascades) in enumerate(ORDER):
                name = f"{camera}-{index+1}-{distance}m-{cascades}cascade"
                await command({"action": "reviewTree", "shadowDistance": distance, "shadowCascades": cascades})
                await asyncio.sleep(3)
                await command({"action": "settingsSnapshot"})
                settings, before = read("settings.json"), read("snapshot.json")
                validate(settings, before, distance, cascades)
                started = time.monotonic()
                await command({"action": "profileStart"})
                profiling = True
                await asyncio.sleep(12)
                await command({"action": "profileStop"})
                profiling = False
                shutil.copy2(NATIVE / "profile.json", OUT / (name + "-frames.json"))
                frames = read("profile.json")
                after = read("snapshot.json")
                validate(settings, after, distance, cascades)
                assert len(frames) > 30 and after["frame"] > before["frame"]
                assert all(f["state"] == "Play" and f["speed"] < .01 for f in frames)
                result = dict(camera=camera, order=index+1, shadowDistance=distance,
                    shadowCascades=cascades, settings=settings, before=before, after=after,
                    wallSeconds=time.monotonic()-started, rawFile=name+"-frames.json",
                    summary=summarize(frames[1:]), rawSampleCount=len(frames),
                    review=read("visual-review-state.json"))
                result["memoryAfter"] = await memory_snapshot(client, NATIVE)
                save(name + "-metadata.json", result)
                report["intervals"].append(result)
                save("report.json", report)
                s=result["summary"]
                print(json.dumps(dict(interval=name, fps=round(s["averageFps"],2),
                    p99Ms=round(s["p99Ms"],2), gpuMs=s["gpuMs"]["mean"] if s["gpuMs"] else None)), flush=True)
        report["samplingComplete"] = True
    except Exception as error:
        report["error"] = repr(error)
        raise
    finally:
        try:
            if profiling:
                await command({"action": "profileStop"})
                shutil.copy2(NATIVE / "profile.json", OUT / "interrupted-frames.json")
            await command({"action": "reviewReset"})
            if initial_time:
                await command({"action": "timeSet", "hour": initial_time["hour"]})
                await command({"action": "timeSpeed", "speed": initial_time["speed"]})
                await command({"action": "timePause", "paused": initial_time["paused"]})
            await command({"action": "settingsSnapshot"})
            report["restoredSettings"] = read("settings.json")
            report["restoredReview"] = read("visual-review-state.json")
            report["cleanup"] = "Original shadow values and clock restored; reviewReset returns camera to follow. Player position unchanged."
            report["complete"] = report.get("samplingComplete", False)
        except Exception as error:
            report["cleanupError"] = repr(error)
            report["complete"] = False
        save("report.json", report)


if __name__ == "__main__":
    asyncio.run(main())
