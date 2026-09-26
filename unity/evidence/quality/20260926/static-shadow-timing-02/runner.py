"""Followup static shadow cost comparison: 48/64/96 m at two cascades.

Uses the recorded first-run harness and changes only output/cameras/variant list.
No real-input traversal or performance qualification is claimed.
"""
import asyncio
import importlib.util
from pathlib import Path

output = Path(__file__).resolve().parent
source = output.parent / "static-shadow-timing-01/runner.py"
spec = importlib.util.spec_from_file_location("static_shadow_timing_base", source)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
base.OUT = output
base.CAMERAS = ["cam_hill", "cam_avenue"]
base.ORDER = [(48, 2), (64, 2), (96, 2)]
base.__doc__ = __doc__

if __name__ == "__main__":
    asyncio.run(base.main())
