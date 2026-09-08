"""Exercise the district pass using the shared native asset/interaction harness."""
import json, os, runpy
from pathlib import Path
root=Path(__file__).resolve().parents[1]
os.environ.setdefault('ATHEN_SALVAGE_EVIDENCE',str(root/'evidence/district/20260908/native'))
os.environ['ATHEN_EXPECT_ACTORS']='9'
os.environ['ATHEN_ACTOR_CHECK']='1'
os.environ.setdefault('ATHEN_ASSET_ROUTE',str(root/'evidence/district/20260908/route.json'))
os.environ['ATHEN_ASSET_CAMERAS']=json.dumps(['cam_hill','cam_avenue','cam_gate']+['cam_district_'+n for n in ['water','tools','salvage','finery','field','repairs','thread','gate','mechanic']])
runpy.run_path(str(root/'tools/check_salvage.py'),run_name='__main__')
