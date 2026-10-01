"""Write the runtime ATHEN_MATERIAL_TUNE file (dev builds) from tuning.json + tuning-band.json, so the native player can
be tuned without a rebuild: python3 tune_runtime.py [out.json]. Band = main tuning + band overrides (as the editor does)."""
import json, sys
from pathlib import Path
here = Path(__file__).resolve().parent
t = json.loads((here / 'tuning.json').read_text())
b = dict(t, **json.loads((here / 'tuning-band.json').read_text()))
out = Path(sys.argv[1]) if len(sys.argv) > 1 else here / 'tuning-runtime.json'
out.write_text(json.dumps({"PV_CityFlags": t, "PV_CityFlags_Band": b}, indent=1))
print(out)
