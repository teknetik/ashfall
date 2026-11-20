"""Run unity/tools/lookbook.py through native_check.sh (which passes no arguments): arguments come from the
environment. P2_OUT (must not exist), P2_CAMS (comma list), P2_HOURS (default 13,20.5), ATHEN_EXE, optional
P2_PROFILE (seconds of frame timing per camera) and P2_SET (a lookbook --set expression such as "Ward residents=0")."""
import os, runpy, sys
from pathlib import Path
tools = Path(__file__).resolve().parents[2] / "unity/tools"
sys.path.insert(0, str(tools))
sys.argv = [str(tools / "lookbook.py"), os.environ["P2_OUT"], "--cams", os.environ["P2_CAMS"],
            "--hours", os.environ.get("P2_HOURS", "13,20.5"), "--exe", os.environ["ATHEN_EXE"], "--sheet"]
if os.environ.get("P2_PROFILE"):
    sys.argv += ["--profile", os.environ["P2_PROFILE"]]
if os.environ.get("P2_SET"):
    sys.argv += ["--set", os.environ["P2_SET"]]
runpy.run_path(str(tools / "lookbook.py"), run_name="__main__")
