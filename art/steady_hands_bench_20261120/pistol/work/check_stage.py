# The kit's machine checks on the staged build (work/stage/pistol/export), before anything is written to export/.
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'kit'))
import check
check.main(os.path.join(HERE, 'stage', 'pistol'))
