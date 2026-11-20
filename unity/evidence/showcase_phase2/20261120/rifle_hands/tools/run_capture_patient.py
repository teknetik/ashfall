"""Runs capture_rifle_hands_native.py with a 30 s bridge-command timeout (fpframe round, 20 Nov 2026: the 10 s default
timed out on the first goto twice on batch-p2-fpframe while the game kept answering other commands)."""
import runpy, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / 'unity/tools')); sys.path.insert(0, str(ROOT / 'unity/evidence/gameplay-v2/20260930-reqa2'))
import qa
_cmd = qa.cmd
def cmd(action, timeout=30, settle=.12, **kw):
    return _cmd(action, timeout=max(timeout, 30), settle=settle, **kw)
qa.cmd = cmd
sys.argv = [str(ROOT / 'unity/tools/capture_rifle_hands_native.py')] + sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
