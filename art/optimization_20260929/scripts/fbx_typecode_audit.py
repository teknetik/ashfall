"""Audit the property type codes actually written in binary FBX files (7.x record walk).

The custom writer's rejection root cause: fbxlib._add_prop mapped FBX type 'C' (char/bool,
e.g. Model "Shading") to encode_bin.add_bool, which emits Blender's internal code 'B' - not a
valid FBX property type, so the Autodesk FBX SDK reports "File is corrupted". This walker reads
the raw records (no Blender parser leniency) and lists every type code per file; any code
outside the standard FBX set, or any structural inconsistency, is reported.
"""
import json
import struct
import sys

STANDARD = set("YCIFDLSRfdlibc")
FIXED = {"Y": 2, "C": 1, "I": 4, "F": 4, "D": 8, "L": 8}


def audit(path):
    buf = open(path, "rb").read()
    assert buf[:21] == b"Kaydara FBX Binary  \x00", "bad magic"
    version = struct.unpack_from("<I", buf, 23)[0]
    wide = version >= 7500
    hdr = "<3Q" if wide else "<3I"
    hsize = 24 if wide else 12
    codes = {}
    problems = []
    records = 0

    def walk(off, limit):
        nonlocal records
        while off < limit:
            end, nprops, plen = struct.unpack_from(hdr, buf, off)
            if end == 0:
                return off + hsize + 1
            nl = buf[off + hsize]
            name = buf[off + hsize + 1: off + hsize + 1 + nl].decode("ascii", "replace")
            p = off + hsize + 1 + nl
            pend = p + plen
            for _ in range(nprops):
                t = chr(buf[p])
                codes[t] = codes.get(t, 0) + 1
                p += 1
                if t in FIXED:
                    p += FIXED[t]
                elif t in "SR":
                    p += 4 + struct.unpack_from("<I", buf, p)[0]
                elif t in "fdlibc":
                    _, enc, clen = struct.unpack_from("<3I", buf, p)
                    if enc not in (0, 1):
                        problems.append(f"{name}: array encoding {enc}")
                    p += 12 + clen
                else:
                    problems.append(f"{name}: non-standard property type {t!r} at {p-1}")
                    return None
            if p != pend:
                problems.append(f"{name}: property length mismatch ({p} != {pend})")
                return None
            records += 1
            if pend < end:
                r = walk(pend, end)
                if r is None:
                    return None
            off = end
        return off

    walk(27, len(buf) - 160)
    bad = sorted(set(codes) - STANDARD)
    return {"version": version, "records": records, "typeCodes": dict(sorted(codes.items())),
            "nonStandardCodes": bad, "problems": problems[:20], "pass": not bad and not problems}


if __name__ == "__main__":
    out = {p: audit(p) for p in sys.argv[2:]}
    json.dump(out, open(sys.argv[1], "w"), indent=1)
    for p, r in out.items():
        print(("PASS " if r["pass"] else "FAIL ") + p.split("/")[-1], r["typeCodes"], r["nonStandardCodes"], r["problems"][:2])
