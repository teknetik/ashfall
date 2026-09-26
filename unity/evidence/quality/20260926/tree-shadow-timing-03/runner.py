"""Compare original and transient LOD1 tree shadow casters in matched native views.

Attach only after the owner hands over the new PID and native QA command folder.
This never launches a player, injects input, edits the Editor, or qualifies a build.
"""
import argparse
import asyncio
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "unity/tools"))
from native_memory import snapshot as memory_snapshot

RESPONSES = {"settingsSnapshot": "settings.json", "actorSnapshot": "actors.json",
    "timeState": "time-state.json", "memorySnapshot": "memory.json",
    "profileStop": "profile.json", "reviewTree": "visual-review-state.json",
    "reviewTreeShadow": "visual-review-state.json", "reviewReset": "visual-review-state.json"}


def read_json(path):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Cannot read valid JSON from {path}: {error}") from error


def write_new(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def process_identity(pid):
    proc = Path("/proc") / str(pid)
    # Field 22 after removing pid/(comm); detects reuse of the numeric PID.
    fields = (proc / "stat").read_text().rsplit(")", 1)[1].split()
    return str((proc / "exe").resolve(strict=True)), fields[19]


class NativeClient:
    def __init__(self, folder, pid, receipts, timeout=10):
        self.folder, self.pid, self.receipts = Path(folder), pid, Path(receipts)
        self.timeout, self.identity = timeout, process_identity(pid)
        self.sequence = 0
        self.competing_writer = False
        self.last_ack_id = None
        self.observed_ack = False

    def check_process(self):
        if process_identity(self.pid) != self.identity:
            raise RuntimeError("Native process exited or PID was reused")

    def error_bytes(self):
        path = self.folder / "qa-error.json"
        return path.read_bytes() if path.exists() else None

    def ack(self):
        path = self.folder / "ack.json"
        if not path.exists():
            return None
        ack = read_json(path)
        if not isinstance(ack, dict) or not isinstance(ack.get("id"), str) or type(ack.get("success")) is not bool:
            raise RuntimeError("Malformed acknowledgement: expected string id and boolean success")
        return ack

    async def command(self, request, cleanup=False):
        self.check_process()
        error_before = self.error_bytes()
        if error_before is not None and not cleanup:
            raise RuntimeError("Native qa-error.json exists; preserve and investigate before continuing")
        previous = self.ack()
        if self.observed_ack and (previous["id"] if previous else None) != self.last_ack_id:
            self.competing_writer = True
            raise RuntimeError("Acknowledgement changed between commands; command ownership was lost")
        self.last_ack_id = previous["id"] if previous else None
        self.observed_ack = True
        if previous and previous["success"] is not True and not cleanup:
            raise RuntimeError("Prior acknowledgement explicitly failed")
        if (self.folder / "command.json").exists():
            self.competing_writer = True
            raise RuntimeError("Unconsumed command exists; refusing to replace another command")
        self.sequence += 1
        command = dict(request, id=uuid.uuid4().hex)
        receipt = dict(sequence=self.sequence, request=command, cleanup=cleanup,
            utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            previousAckId=previous["id"] if previous else None, accepted=False)
        response_name = RESPONSES.get(request["action"])
        response = self.folder / response_name if response_name else None
        stamp_before = response.stat().st_mtime_ns if response and response.exists() else None
        started = time.monotonic()
        temporary = self.folder / ("command-" + command["id"] + ".tmp")
        try:
            write_new(temporary, command)
            # Same-directory rename keeps Unity's reader from seeing partial JSON.
            temporary.rename(self.folder / "command.json")
            while time.monotonic() - started < self.timeout:
                self.check_process()
                error = self.error_bytes()
                if error is not None and (not cleanup or error != error_before):
                    raise RuntimeError("Native command error written to qa-error.json")
                ack = self.ack()
                if ack and ack["id"] == command["id"]:
                    self.last_ack_id = ack["id"]
                    if ack["success"] is not True:
                        raise RuntimeError("Matching acknowledgement explicitly failed")
                    if response:
                        if not response.exists() or response.stat().st_mtime_ns == stamp_before:
                            raise RuntimeError("Acknowledged command left a missing/stale response: " + response.name)
                        receipt["responseSha256"] = hashlib.sha256(response.read_bytes()).hexdigest()
                        result = read_json(response)
                    else:
                        result = None
                    receipt["accepted"] = True
                    return result
                if ack and (previous is None or ack["id"] != previous["id"]):
                    self.competing_writer = True
                    raise RuntimeError("Unexpected acknowledgement ID; another writer may own this folder")
                await asyncio.sleep(.02)
            raise TimeoutError("No matching acknowledgement; prior/stale ack was not accepted")
        except Exception as error:
            receipt["error"] = repr(error)
            raise
        finally:
            receipt["seconds"] = time.monotonic() - started
            write_new(self.receipts / f"{self.sequence:04}-{command['id']}.json", receipt)
            if temporary.exists():
                temporary.unlink()  # Only this command's uniquely named temporary file.


def percentile(values, quantile):
    values = sorted(values)
    index = (len(values) - 1) * quantile
    low, high = int(index), min(int(index) + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (index - low)


def summarize(frames):
    dt = [f["dt"] * 1000 for f in frames]
    if not dt or not all(math.isfinite(v) and v > 0 for v in dt):
        raise ValueError("Missing/invalid frame deltas")
    result = dict(frames=len(frames), seconds=sum(dt)/1000, averageFps=1000*len(dt)/sum(dt),
        p50Ms=percentile(dt,.5), p95Ms=percentile(dt,.95), p99Ms=percentile(dt,.99),
        maxMs=max(dt), hitchesOver33ms=sum(v>33.33 for v in dt), hitchesOver50ms=sum(v>50 for v in dt))
    result["meetsCriteriaInThisStaticInterval"] = result["averageFps"] >= 60 and result["p99Ms"] <= 16.67
    for key in ["mainMs","renderMs","cpuMs","gpuMs","draws","tris","batches","setPass"]:
        values = [f[key] for f in frames if math.isfinite(f.get(key,-1)) and f.get(key,-1)>0]
        result[key] = dict(samples=len(values), coverage=len(values)/len(frames),
            mean=statistics.mean(values), p50=percentile(values,.5), p95=percentile(values,.95),
            p99=percentile(values,.99), maximum=max(values)) if values else None
    return result


def validate_state(settings, state, review=None, variant=None):
    assert [state["width"],state["height"]] == [1920,1080], "Actual viewport must be 1920x1080"
    assert state["session"]["state"] == "Play" and state["player"]["speed"] < .01, "Expected stationary Play"
    expected = dict(renderScale=1,msaa=4,shadowResolution=4096,textureLimit=0,vSync=0,frameLimit=-1,timeScale=1)
    for key,value in expected.items():
        assert settings[key] == value, (key,settings[key],value)
    assert not settings["previewing"] and settings["postProcessing"], "Quality preview/post-processing mismatch"
    if variant:
        distance,cascades,reduced = variant
        assert settings["shadowDistance"] == distance and settings["shadowCascades"] == cascades
        assert review["shadowDistance"] == distance and review["shadowCascades"] == cascades
        assert not review["hudHidden"] and not review["transmission"] and not review.get("ambientTransmission",[])
        tree = review["treeShadow"]
        assert tree["enabled"] is reduced
        if reduced:
            assert tree["shadowRendererCount"] == 3 and 0 < tree["shadowTrianglesPerDraw"] < tree["sourceLod0Triangles"]
            assert len(tree["sourceCasting"]) == 6 and all(s["current"] == "Off" for s in tree["sourceCasting"])
        else:
            assert tree["shadowRendererCount"] == 0 and tree["sourceCasting"] == []


async def run(args):
    native, output = args.native.resolve(), args.output.resolve()
    if not native.is_dir():
        raise FileNotFoundError(native)
    output.mkdir(parents=True, exist_ok=False)  # Never reuse or overwrite an earlier run.
    receipts = output / "commands"
    receipts.mkdir()
    write_new(output / "invocation.json", vars(args) | {"native":str(native),"output":str(output)})
    (output / "runner.py").write_bytes(Path(__file__).read_bytes())
    client = NativeClient(native,args.pid,receipts)
    ownership = native / ".tree-shadow-command-owner.json"
    token = uuid.uuid4().hex
    write_new(ownership,dict(token=token,runnerPid=os.getpid(),playerPid=args.pid,output=str(output)))
    os.environ["ATHEN_NATIVE_PID"] = str(args.pid)
    report = dict(complete=False,qualification=False,purpose=__doc__,nativeFolder=str(native),pid=args.pid,
        warmupSeconds=args.warmup,sampleSeconds=args.seconds,pairs=args.pairs,intervals=[],
        note=args.note,cameras=args.cameras,profiles=[(18,1),(48,2),(96,2)],
        limitations=["Stationary short intervals only; no real-input traversal or functional/visual acceptance.",
            "Nonpositive timing/counter values are unavailable, never zero cost; valid coverage is reported.",
            "Latest GPU timestamps may be absent or repeated and lack frame IDs in NativeQa. CPU/main-thread include waits.",
            "Triangles include all passes; draw calls, batches and SetPass are separate counters.",
            "Clock fixed at12; animation, nine actors, foliage/dust/audio continue at differing phases.",
            "Actual viewport comes from snapshots; launch environment and saved video dimensions may be stale.",
            "Native settings expose cascade4Split but not cascade2Split. The diagnostic does not change splits; current source PC_RPAsset declares cascade2Split0.25, not a live measured field.",
            "Raw first frame retained; summary omits only its pre-start boundary delta.",
            "Normal development QA snapshot IO/profiling allocations remain active for both alternatives."])
    log_path = native / "Player.log"
    log_start = log_path.stat().st_size if log_path.exists() else 0
    initial_time = None
    profiling = False
    touched = False
    def update_report():
        temporary = output / "report.json.tmp"
        temporary.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
        temporary.replace(output / "report.json")
    def snapshot():
        return read_json(native / "snapshot.json")
    try:
        if client.error_bytes() is not None:
            raise RuntimeError("Preexisting qa-error.json; run refused without deleting evidence")
        initial_review_path = native / "visual-review-state.json"
        if initial_review_path.exists():
            review = read_json(initial_review_path)
            assert not review["hudHidden"] and not review["transmission"] and not review.get("ambientTransmission",[]) and review["shadowDistance"] is None
            assert not review.get("treeShadow",{}).get("enabled",False), "Finish prior audition first"
        exe = Path(client.identity[0])
        report["build"] = dict(executable=str(exe),sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),processStartTicks=client.identity[1])
        assembly = exe.parent / "AthenHill_Data/Managed/Assembly-CSharp.dll"
        if assembly.exists():
            report["build"]["assemblySha256"] = hashlib.sha256(assembly.read_bytes()).hexdigest()
        if (native / "profile.json").exists():
            with (output / "preexisting-profile.json").open("xb") as stream:
                stream.write((native / "profile.json").read_bytes())
        report["initialSettings"] = await client.command({"action":"settingsSnapshot"})
        report["initialSnapshot"] = snapshot()
        validate_state(report["initialSettings"],report["initialSnapshot"])
        report["environment"] = read_json(native / "environment.json")
        report["actors"] = await client.command({"action":"actorSnapshot"})
        assert len(report["actors"]) == 9 and report["environment"]["actorCount"] == 9
        initial_time = await client.command({"action":"timeState"})
        report["initialTime"] = initial_time
        touched = True
        await client.command({"action":"timePause","paused":True})
        await client.command({"action":"timeSet","hour":12})
        report["lighting"] = await client.command({"action":"timeState"})
        assert report["lighting"]["paused"] and report["lighting"]["hour"] == 12
        assert not report["lighting"]["reflections"]["pending"]
        report["initialMemory"] = await memory_snapshot(client,native)
        update_report()
        for camera in args.cameras:
            await client.command({"action":"view","camera":camera})
            for distance,cascades in [(18,1),(48,2),(96,2)]:
                for pair in range(args.pairs):
                    # First pair original/reduced; second pair reverses order.
                    for reduced in ([False,True] if pair%2==0 else [True,False]):
                        number = len(report["intervals"])+1
                        name = f"{number:02}-{camera}-{distance}m-{cascades}cascade-{'reduced' if reduced else 'original'}"
                        await client.command({"action":"reviewTree","shadowDistance":distance,"shadowCascades":cascades})
                        review = await client.command({"action":"reviewTreeShadow","enabled":reduced})
                        await asyncio.sleep(args.warmup)
                        settings = await client.command({"action":"settingsSnapshot"})
                        before = snapshot()
                        validate_state(settings,before,review,(distance,cascades,reduced))
                        await client.command({"action":"profileStart"})
                        profiling = True
                        await asyncio.sleep(args.seconds)
                        frames = await client.command({"action":"profileStop"})
                        profiling = False
                        write_new(output / (name+"-frames.json"),frames)
                        after = snapshot()
                        validate_state(settings,after,review,(distance,cascades,reduced))
                        assert after["frame"] > before["frame"] and len(frames)>30
                        assert all(f["state"]=="Play" and f["speed"]<.01 for f in frames)
                        result = dict(name=name,camera=camera,distance=distance,cascades=cascades,reduced=reduced,pair=pair+1,
                            settings=settings,review=review,before=before,after=after,rawFile=name+"-frames.json",
                            rawFrames=len(frames),summary=summarize(frames[1:]),memoryAfter=await memory_snapshot(client,native))
                        write_new(output / (name+"-metadata.json"),result)
                        report["intervals"].append(result)
                        update_report()
                        print(json.dumps(dict(interval=name,fps=round(result["summary"]["averageFps"],2),
                            p99Ms=round(result["summary"]["p99Ms"],2),gpuMs=result["summary"]["gpuMs"])),flush=True)
        report["samplingComplete"] = True
    except Exception as error:
        report["error"] = repr(error)
        raise
    finally:
        try:
            if touched and not client.competing_writer:
                if profiling:
                    frames = await client.command({"action":"profileStop"},cleanup=True)
                    write_new(output / "interrupted-frames.json",frames)
                report["restoredReview"] = await client.command({"action":"reviewReset"},cleanup=True)
                await client.command({"action":"timeSet","hour":initial_time["hour"]},cleanup=True)
                await client.command({"action":"timeSpeed","speed":initial_time["speed"]},cleanup=True)
                await client.command({"action":"timePause","paused":initial_time["paused"]},cleanup=True)
                report["restoredSettings"] = await client.command({"action":"settingsSnapshot"},cleanup=True)
                restored = report["restoredReview"]
                assert restored["treeShadow"]["enabled"] is False and restored["shadowDistance"] is None
                for key in ["shadowDistance","shadowCascades"]:
                    assert report["restoredSettings"][key] == report["initialSettings"][key]
                report["cleanup"] = "Original caster modes/shadows and clock restored; camera follow; player position unchanged."
            elif client.competing_writer:
                raise RuntimeError("Competing command writer detected: cleanup deferred to owner to avoid another mutation race")
            report["complete"] = report.get("samplingComplete",False)
        except Exception as error:
            report["cleanupError"] = repr(error)
            report["complete"] = False
        if client.error_bytes() is not None:
            (output / "native-qa-error.json").write_bytes(client.error_bytes())
        if log_path.exists():
            markers = ["Exception:","NullReferenceException","Shader error","is not supported on this GPU","Assertion failed"]
            with log_path.open("rb") as stream:
                stream.seek(log_start)
                new_log = stream.read().decode(errors="replace")
            matches = [line for line in new_log.splitlines() if any(marker in line for marker in markers)]
            report["runtimeLog"] = dict(path=str(log_path),startByte=log_start,matchingLines=matches,markers=markers)
            if matches:
                report["complete"] = False
        update_report()
        if ownership.exists() and read_json(ownership).get("token") == token:
            ownership.unlink()
    if not report["complete"]:
        raise RuntimeError("Run incomplete; inspect retained report and cleanup/runtime errors")


def parse_args():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native",type=Path,required=True)
    parser.add_argument("--pid",type=int,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--warmup",type=float,default=3)
    parser.add_argument("--seconds",type=float,default=12)
    parser.add_argument("--pairs",type=int,default=2)
    parser.add_argument("--cameras",nargs="+",default=["cam_hill","cam_avenue","cam_tree_canopy_below"])
    parser.add_argument("--note",default="Explicit background development capture; record other active applications separately.")
    args=parser.parse_args()
    if not math.isfinite(args.warmup) or not math.isfinite(args.seconds) or args.warmup<0 or args.seconds<=0 or args.pairs<1:
        parser.error("Warmup>=0, seconds>0 and pairs>=1 are required")
    return args


if __name__=="__main__":
    asyncio.run(run(parse_args()))
