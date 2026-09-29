"""Side-by-side before|after sheets for the Basic General counter pass (native 1920x1080 originals stay in before-native/ and after-native/)."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
R = Path(sys.argv[1])
views = ['cam_audit_basic_general_front', 'cam_audit_basic_general_door', 'cam_audit_basic_general_side_left', 'cam_audit_basic_general_side_right',
         'fp_street_centre', 'fp_street_left', 'fp_street_right', 'fp_porch_counter']
(R / 'comparison').mkdir(exist_ok=True)
for v in views:
    b = Image.open(R / 'before-native' / (v + '.png')).convert('RGB'); a = Image.open(R / 'after-native' / (v + '.png')).convert('RGB')
    sheet = Image.new('RGB', (1920, 540 + 26), (16, 16, 16)); d = ImageDraw.Draw(sheet)
    sheet.paste(b.resize((960, 540)), (0, 26)); sheet.paste(a.resize((960, 540)), (960, 26))
    d.text((8, 6), 'BEFORE (28 Sep scene/build)  ' + v, fill=(230, 230, 230)); d.text((968, 6), 'AFTER (counter dressing, 29 Sep)', fill=(230, 230, 230))
    sheet.save(R / 'comparison' / (v + '-before-after.jpg'), quality=90)
print('ok')
