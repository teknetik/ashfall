"""Split generated orthographic atlas panels for Meshy's same-object multiview input.
No redraw or image synthesis: source sheets remain immutable beside their crops.
"""
import argparse,json,shutil
from pathlib import Path
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('source',type=Path);p.add_argument('--cuts',required=True);p.add_argument('--bottom',type=int,required=True);p.add_argument('--output-root',type=Path,default=Path(__file__).resolve().parents[2]/'refs/salvage_20260908');a=p.parse_args()
out=a.output_root/a.name;out.mkdir(parents=True,exist_ok=True)
im=Image.open(a.source);shutil.copy2(a.source,out/'turnaround.png');cuts=list(map(int,a.cuts.split(',')))
for view,left,right in zip(['front','side','back'],cuts,cuts[1:]):
 im.crop((left,0,right,a.bottom)).save(out/(view+'.png'))
(out/'source.json').write_text(json.dumps({'source':str(a.source.resolve()),'size':im.size,'cuts':cuts,'bottom':a.bottom},indent=2))
print(out)
