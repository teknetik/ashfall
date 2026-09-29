"""Side-by-side before|after sheets for the Tool Exchange display pass (native 1920x1080 originals stay in before-native/ and after-native/).

  python compare_tool_exchange_stills.py <evidence-dir>
Fixed views: before = before-native (first fixed pass; dwell copy in before-native-fixed-dwell is identical scene/build). After = after-native.
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
R = Path(sys.argv[1])
views = ['cam_audit_tool_exchange_front', 'cam_audit_tool_exchange_door', 'cam_audit_tool_exchange_side_left', 'cam_audit_tool_exchange_side_right',
         'fp_front_lane', 'fp_door_porch', 'fp_display_close', 'fp_shutter_close', 'fp_side_left', 'fp_side_right']
(R / 'comparison').mkdir(exist_ok=True)
for v in views:
    b = Image.open(R / 'before-native' / (v + '.png')).convert('RGB'); a = Image.open(R / 'after-native' / (v + '.png')).convert('RGB')
    sheet = Image.new('RGB', (1920, 540 + 26), (16, 16, 16)); d = ImageDraw.Draw(sheet)
    sheet.paste(b.resize((960, 540)), (0, 26)); sheet.paste(a.resize((960, 540)), (960, 26))
    d.text((8, 6), 'BEFORE (saved scene 2b609992, 29 Sep 07:51 dev build)  ' + v, fill=(230, 230, 230)); d.text((968, 6), 'AFTER (display + shutter fittings, scene 34d448cb)', fill=(230, 230, 230))
    sheet.save(R / 'comparison' / (v + '-before-after.jpg'), quality=90)
print('ok')
