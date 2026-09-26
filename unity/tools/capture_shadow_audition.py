"""Matched native shadow auditions; static evidence, never traversal qualification.

Use a fresh explicit development QA launch directory. Background rendering is
allowed for this capture, but no keyboard input or frame-time pass is claimed.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import shutil

from PIL import Image
from native_client import Client


async def capture(folder, output=None):
    folder = folder.resolve()
    output = output.resolve() if output else folder
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "shadow-audition.json"
    if report_path.exists():
        raise FileExistsError("Use a fresh capture directory; retain earlier evidence.")
    os.environ["ATHEN_NATIVE_DIR"] = str(folder)
    client = Client()
    report = {"complete": False, "purpose": __doc__.splitlines()[0],
              "nativeDirectory": str(folder), "views": [],
              "limitations": "Fixed cameras; actors, foliage wind and particles remain animated. No real-input or performance qualification."}

    def read(name):
        return json.loads((folder / name).read_text())

    async def command(request):
        await client.command(request)
        error = folder / "qa-error.json"
        if error.exists():
            raise RuntimeError(error.read_text())

    try:
        initial = read("snapshot.json")
        if initial["session"]["state"] != "Play":
            raise RuntimeError("Start an untouched Play session for the comparison.")
        if [initial["width"], initial["height"]] != [1920, 1080]:
            await command({"action": "resize", "width": 1920, "height": 1080})
            await asyncio.sleep(2)
        await command({"action": "settingsSnapshot"})
        report["settings"] = read("settings.json")
        report["environment"] = read("environment.json")
        assert report["settings"]["renderScale"] == 1
        assert report["environment"]["actorCount"] == 9
        await command({"action": "timeReset"})
        await command({"action": "timePause", "paused": True})
        await command({"action": "timeState"})
        report["time"] = read("time-state.json")
        await command({"action": "goto", "landmark": "basic_general"})
        for camera in ["cam_hill", "cam_avenue", "cam_gate", "cam_grid",
                       "cam_whompah", "cam_hero", "cam_tree_canopy_below",
                       "cam_tree_canopy_edge", "cam_p1_tree_roots"]:
            await command({"action": "view", "camera": camera})
            for distance, cascades in [(18, 1), (96, 4)]:
                await command({"action": "reviewTree", "shadowDistance": distance,
                               "shadowCascades": cascades})
                await command({"action": "settingsSnapshot"})
                settings = read("settings.json")
                assert settings["shadowDistance"] == distance
                assert settings["shadowCascades"] == cascades
                await asyncio.sleep(1.2)
                state = read("snapshot.json")
                assert [state["width"], state["height"]] == [1920, 1080], state
                name = f"{camera}-{distance}m-{cascades}cascade"
                capture_name = name if output == folder else output.name + "-" + name
                path = folder / (capture_name + ".png")
                if path.exists() or (output != folder and (output / (name + ".png")).exists()):
                    raise FileExistsError("Retain earlier captures; choose a fresh output directory/name: " + name)
                await command({"action": "capture", "name": capture_name})
                for _ in range(80):
                    try:
                        with Image.open(path) as im:
                            im.load()
                            assert im.size == (1920, 1080)
                            # A tiled Xwayland window can disagree with Screen.width.
                            # Reject the known clipped backbuffer even if PNG dimensions match.
                            assert im.convert("RGB").crop((0, 0, 1920, 8)).getbbox(), "Black top strip: verify the actual window size."
                        break
                    except (FileNotFoundError, OSError):
                        await asyncio.sleep(.1)
                else:
                    raise TimeoutError("Capture incomplete: " + name)
                if output != folder:
                    destination = output / (name + ".png")
                    shutil.copyfile(path, destination)
                    path = destination
                report["views"].append({"camera": camera, "image": path.name,
                    "shadowDistance": distance, "shadowCascades": cascades,
                    "settings": settings,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "snapshot": state, "accepted": False})
                report_path.write_text(json.dumps(report, indent=2) + "\n")
                print("Captured " + name, flush=True)
        report["complete"] = True
    except Exception as error:
        report["error"] = str(error)
        raise
    finally:
        restore_errors = []
        for action in ["reviewReset", "timeReset"]:
            try:
                await command({"action": action})
            except Exception as error:
                restore_errors.append({"action": action, "error": str(error)})
        report["restoreErrors"] = restore_errors
        if restore_errors:
            report["complete"] = False
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        if restore_errors and "error" not in report:
            raise RuntimeError("QA restoration failed: " + str(restore_errors))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native", type=Path)
    parser.add_argument("--output", type=Path, help="Fresh evidence directory; keep the running player's command directory unchanged.")
    args = parser.parse_args()
    asyncio.run(capture(args.native, args.output))
