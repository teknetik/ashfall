import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import kitload
check = kitload.load('check')          # by file: "import check" can find another family's check.py
check.main(os.path.dirname(os.path.abspath(__file__)))
