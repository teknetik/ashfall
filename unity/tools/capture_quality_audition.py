"""Capture saved native audit cameras and unmodified runtime evidence; leave player open.

Debug positioning supports image comparison only. It does not qualify traversal.
"""
import argparse, asyncio, hashlib, json, os, time
from pathlib import Path
from PIL import Image
from native_client import Client
from desktop_input import focus, key

VIEWS = ["cam_hill", "cam_avenue", "cam_gate", "cam_grid", "cam_whompah", "cam_hero",
         "cam_terminal", "cam_courtyard_facade", "cam_shop_recovery_close", "cam_salvage_general",
         "cam_p1_hall_front", "cam_p1_hall_door", "cam_p1_tree_roots", "cam_fidelity_guard", "cam_p1_vex_face",
         "cam_p1_finery_front", "cam_p1_finery_door", "cam_p1_finery_roof",
         "cam_tree_root_north", "cam_tree_root_east", "cam_tree_root_south", "cam_tree_root_west",
         "cam_tree_bark_close", "cam_tree_canopy_below", "cam_tree_canopy_edge"]

def read(path): return json.loads(path.read_text())
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

async def capture(args):
    out = args.native.resolve()
    os.environ.update(ATHEN_NATIVE_DIR=str(out), ATHEN_NATIVE_PID=(out / "pid").read_text().strip())
    report_path = out / "audition-report.json"
    assert not report_path.exists(), "Use a new QA launch folder to retain earlier evidence."
    d, client = focus(), Client()
    report = {"startedUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "complete": False,
              "buildRecord": read(args.build_record), "buildRecordSha256": digest(args.build_record),
              "purpose": "Static native visual evidence, not gameplay or performance acceptance", "views": []}
    try:
        if read(out / "snapshot.json")["session"]["state"] == "Paused":
            key(d, "Escape", True); await asyncio.sleep(.1); key(d, "Escape", False); await asyncio.sleep(.4)
        snapshot = read(out / "snapshot.json")
        assert [snapshot["width"], snapshot["height"]] == [1920, 1080]
        await client.command({"action": "settingsSnapshot"})
        report["settings"] = read(out / "settings.json")
        report["environment"] = read(out / "environment.json")
        assert report["settings"]["renderScale"] == 1
        assert report["environment"]["actorCount"] == 9
        await client.command({"action": "timeReset"})
        await client.command({"action": "timeState"})
        report["time"] = read(out / "time-state.json")
        await client.command({"action": "goto", "landmark": "basic_general"})
        for name in VIEWS:
            await client.command({"action": "view", "camera": name})
            await asyncio.sleep(1)
            snapshot = read(out / "snapshot.json")
            await client.command({"action": "capture", "name": name})
            image = out / (name + ".png")
            for _ in range(60):
                try:
                    with Image.open(image) as im:
                        im.load(); assert im.size == (1920, 1080)
                    break
                except (FileNotFoundError, OSError): await asyncio.sleep(.1)
            else: raise TimeoutError("Image incomplete: " + name)
            report["views"].append({"name": name, "image": image.name, "sha256": digest(image), "snapshot": snapshot, "accepted": False})
            report_path.write_text(json.dumps(report, indent=2))
            print("Captured " + name, flush=True)
        await client.command({"action": "actorSnapshot"})
        report["complete"] = True
    except Exception as error:
        report["error"] = str(error)
        raise
    finally:
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        key(d, "w", False)
        await client.command({"action": "view", "camera": "follow"})

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native", type=Path)
    parser.add_argument("--build-record", required=True, type=Path)
    asyncio.run(capture(parser.parse_args()))
