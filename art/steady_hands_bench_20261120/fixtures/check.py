# The machine checks for this family (ANYMACHINE.md section 3): SH/blender.sh <family>/check.py -> export/check.json
# The fixtures family's own check module (src/check_fx.py, a copy of tools/src/check_mb.py extended for Milestone 3).
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'src'))
import check_fx
check_fx.main(HERE)
