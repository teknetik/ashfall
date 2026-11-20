"""Runs unity/tools/check_inventory_redesign.py through P2/native_check.sh, which passes only environment variables:
ATHEN_OUT (a folder that must not exist yet) and ATHEN_EXE become its OUT and --exe arguments."""
import os, runpy, sys
from pathlib import Path

script = Path(__file__).resolve().parents[2] / 'unity/tools/check_inventory_redesign.py'
sys.argv = [str(script), os.environ['ATHEN_OUT'], '--exe', os.environ['ATHEN_EXE']]
sys.path.insert(0, str(script.parent))
runpy.run_path(str(script), run_name='__main__')
