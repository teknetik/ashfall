# The machine checks for this family (ANYMACHINE.md section 3): SH/blender.sh <family>/check.py -> export/check.json
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools', 'src'))
import check_mb
check_mb.main(HERE)
