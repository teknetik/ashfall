#!/usr/bin/env bash
# Frame-cost bisection (3 Oct 2026): one dev build, the same cameras profiled with each pass's objects switched off.
set -u; W=/home/teknetik/.local/state/ward-programme; R=/home/teknetik/code/ao2; OUT=$R/unity/evidence/overnight/20261003/bisect; mkdir -p "$OUT"; cd "$R"
$W/build_player.sh "$OUT/build.log" | tee "$OUT/build.result"; grep -q "Result: Success" "$OUT/build.result" || { echo BUILD FAILED; exit 1; }
EXE=$R/unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64
declare -A V=([all]="" [no_buildings]="Ward building: =0" [no_npcs]="WardNpc_=0" [no_armour]="Armour =0" [no_both]="Ward building: =0;WardNpc_=0")
for cam in cam_hill cam_gate; do for v in all no_buildings no_npcs no_armour no_both; do
  d="$OUT/$v-$cam"; rm -rf "$d"
  $W/native.sh lookbook "$d" --cams $cam --hours 13 --profile 8 --exe "$EXE" --set "${V[$v]}" > "$d.out" 2>&1
  echo "$(date +%H:%M:%S) $v $cam rc=$?"
done; done
python3 - "$OUT" <<'PY'
import json,sys,glob,os,statistics
out=sys.argv[1]; rows={}
for f in glob.glob(f"{out}/*/lookbook.json"):
    v,cam=os.path.basename(os.path.dirname(f)).rsplit('-',1)
    for k,p in json.load(open(f)).get('profiles',{}).items(): rows.setdefault((k,v),[]).append(p['p50Ms'])
res={}
for (k,v),xs in sorted(rows.items()): res.setdefault(k,{})[v]=round(statistics.mean(xs),2)
json.dump(res,open(f"{out}/bisect-summary.json","w"),indent=1); print(json.dumps(res,indent=1))
PY
echo BISECTDONE
