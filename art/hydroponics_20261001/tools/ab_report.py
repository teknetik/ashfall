"""Print frame-time summaries from lookbook.json files: ab_report.py <evidence dir> <run dir>..."""
import json, sys
E = sys.argv[1]
for d in sys.argv[2:]:
    try:
        L = json.load(open(f"{E}/{d}/lookbook.json"))
        for k, p in L["profiles"].items():
            print(d, k, "fps %.1f p50 %.2f p95 %.2f p99 %.2f max %.2f cpu %.2f tris %.0f setpass %.0f" % (
                p["averageFps"], p["p50Ms"], p["p95Ms"], p["p99Ms"], p["maxMs"], p["cpuMs"]["mean"], p["tris"]["mean"], p["setPass"]["mean"]))
        print(d, "errors", L["errors"], "load", [round(x, 1) for x in L["loadAverage"]])
    except Exception as e:
        print(d, "no report", e)
