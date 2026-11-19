"""Run unity/tools/lookbook.py through native_check.sh (which passes no arguments): arguments come from the
environment. GN_OUT (must not exist), GN_CAMS, GN_HOURS, ATHEN_EXE."""
import os, runpy, sys
from pathlib import Path
tools = Path(__file__).resolve().parents[2] / "unity/tools"
sys.path.insert(0, str(tools))
sys.argv = [str(tools / "lookbook.py"), os.environ["GN_OUT"], "--cams", os.environ["GN_CAMS"], "--hours", os.environ.get("GN_HOURS", "13,20.5"),
            "--exe", os.environ["ATHEN_EXE"], "--sheet"]
runpy.run_path(str(tools / "lookbook.py"), run_name="__main__")
