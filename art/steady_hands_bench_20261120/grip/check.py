# The grip family's checks: contract, the assembly sweep (with the stripped pistol, the servo family's gimbal unit and
# four case screws, and the materials family's plates and bent strap), the two grip screws, and the export.
#   SH/blender.sh grip/check.py [-- --standins]
# The plates and the strap are the real ones from materials/export/materials.blend when that file is there; with
# --standins (or without that file) the stand-ins built from interface.json inside grip.blend are swept instead.
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'kit'))
import kitload
check = kitload.load('check')          # by file: "import check" can find another family's check.py

UNIT = ['servo.gimbal_cradle', 'servo.gimbal_coil', 'servo.gimbal_ring', 'servo.gimbal_race', 'servo.gimbal_rotor', 'servo.gimbal_retainer',
        'servo.gimbal_grit_1', 'servo.gimbal_grit_2', 'servo.gimbal_grit_3']          # the three leads are cut and re-made by then
SCREWS = ['servo.screw_case_a', 'servo.screw_case_b', 'servo.screw_case_c', 'servo.screw_case_d']
MADE = ['materials.sheet_a_plate', 'materials.sheet_b_plate', 'materials.strap_bent']
ext = [('../pistol', None), ('../servo', UNIT + SCREWS, 'absent')]
if '--standins' not in sys.argv and os.path.exists(os.path.join(HERE, '..', 'materials', 'export', 'materials.blend')):
    ext.append(('../materials', MADE, 'absent'))
check.main(HERE, externals=ext)
