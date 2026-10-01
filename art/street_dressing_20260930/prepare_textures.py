"""Unity maps for the Ward street dressing kit (30 Sep 2026).
Run: uv run --with pillow --with numpy python prepare_textures.py

* Poly Haven props (Props/ph-props.json): base colour and OpenGL normal maps copied byte-for-byte; the ARM map becomes a
  URP Lit mask map (R metallic = ARM B, G occlusion = ARM R, B 0, A smoothness = 1 - ARM G). Blended alpha (broom
  bristles) goes into a PNG base map for alpha clipping. Masks are 1k for props under 1 m, else 2k (sources untouched).
* Meshy props (Props/meshy-props.json): the same mask from the glTF metal-rough map (R metallic = B, A = 1 - G).
* Blender-authored litter (original art, no text from real products): SD_Paper (2x2 atlas of notices and forms),
  SD_Card (kraft carton, two halves) and SD_Tin (two faded label colours) with normal and mask maps.
* Hessian (sacks, tarp, rope) and painted steel (scrap skip) use the Poly Haven textures rough_linen /
  rusty_painted_metal / green_metal_rust as tiling maps with per-material tints set in Unity.
Writes unity/AthenHill/Assets/AthenHill/Art/StreetDressing/Textures/... and Textures/materials.json (material specs).
"""
import json, math, random, shutil
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
PH = HERE / "polyhaven"
UNITY = HERE.parents[1] / "unity/AthenHill/Assets/AthenHill/Art/StreetDressing"
TEX = UNITY / "Textures"
PROPS = UNITY / "Props"
TEX.mkdir(parents=True, exist_ok=True)
ASSET = "Assets/AthenHill/Art/StreetDressing/Textures/"


# galvanised bins read black against the city's small sky probe at full metallic: scale their metallic down
METAL_SCALE = {"metal_trash_can": 0.45, "metal_trash_can_rust": 0.45, "metal_trash_can_rust.001": 0.45, "metal_jug": 0.7,
               "watering_can_metal_01": 0.75}
BRIGHTEN = {"metal_trash_can": 1.25, "metal_trash_can_rust": 1.15, "metal_trash_can_rust.001": 1.15}


def mask_from_arm(src, dst, size, ao=True, arm_order="ARM", metal_scale=1.0):
    a = Image.open(src).convert("RGB")
    if size and a.size[0] > size:
        a = a.resize((size, size), Image.LANCZOS)
    x = np.asarray(a).astype(np.float32) / 255
    if arm_order == "ARM":
        occ, rough, metal = x[..., 0], x[..., 1], x[..., 2]
    else:   # glTF metal-rough (R unused, G roughness, B metallic)
        occ, rough, metal = np.ones_like(x[..., 0]), x[..., 1], x[..., 2]
    m = np.stack([metal * metal_scale, occ if ao else np.ones_like(occ), np.zeros_like(metal), 1 - rough], -1)
    Image.fromarray((m * 255 + 0.5).astype(np.uint8), "RGBA").save(dst)


materials = {}
report = {"polyhaven": {}, "meshy": {}, "authored": {}}

# ------------------------------------------------------------------ Poly Haven props
ph = json.loads((PROPS / "ph-props.json").read_text())
done = set()
for pid, e in ph.items():
    big = max(e["size"]) >= 1.0
    for mname, spec in e["materials"].items():
        if not spec or "shared" in spec:
            materials.setdefault(mname.split(".")[0], {"shared": (spec or {}).get("shared", mname)})
            continue
        key = mname.split(".")[0] if mname.split(".")[0] in ("planter_pot_clay",) else mname
        if key in done:
            continue
        done.add(key)
        model = spec["model"]
        d = TEX / model
        d.mkdir(exist_ok=True)
        out = {"kind": "polyhaven", "model": model, "doubleSided": spec.get("doubleSided", False)}
        if spec.get("base"):
            src = PH / "models" / model / spec["base"]
            if spec.get("alphaMap"):
                base = Image.open(src).convert("RGB")
                alpha = Image.open(PH / "models" / model / spec["alphaMap"]).convert("L").resize(base.size)
                base.putalpha(alpha)
                dst = d / (Path(spec["base"]).stem + "_alpha.png")
                base.save(dst, optimize=True)
                out.update(alphaClip=True, cutoff=0.45)
            else:
                dst = d / Path(spec["base"]).name
                shutil.copyfile(src, dst)
            out["base"] = ASSET + f"{model}/{dst.name}"
        if spec.get("normal"):
            dst = d / Path(spec["normal"]).name
            shutil.copyfile(PH / "models" / model / spec["normal"], dst)
            out["normal"] = ASSET + f"{model}/{dst.name}"
        if spec.get("arm"):
            dst = d / (Path(spec["arm"]).stem.replace("_arm", "") + "_Mask.png")
            mask_from_arm(PH / "models" / model / spec["arm"], dst, 2048 if big else 1024, metal_scale=METAL_SCALE.get(key, 1.0))
            out["mask"] = ASSET + f"{model}/{dst.name}"
        else:
            out.update(metallic=spec.get("metallic", 0.0), smoothness=1 - spec.get("roughness", 0.8))
        if key in BRIGHTEN:
            out["tint"] = [BRIGHTEN[key]] * 3
        materials[key] = out
    report["polyhaven"][pid] = sorted(e["materials"])

# ------------------------------------------------------------------ Meshy props
meshy = json.loads((PROPS / "meshy-props.json").read_text())
for pid, e in meshy.items():
    d = PROPS / pid
    mask_from_arm(d / e["maps"]["MetalRough"]["file"], d / f"{pid}_Mask.png", 2048 if max(e["size"]) >= 1.0 else 1024, arm_order="MR")
    materials[f"SD_{pid}"] = {"kind": "meshy", "base": f"Assets/AthenHill/Art/StreetDressing/Props/{pid}/{e['maps']['BaseColor']['file']}",
                              "normal": f"Assets/AthenHill/Art/StreetDressing/Props/{pid}/{e['maps']['Normal']['file']}",
                              "mask": f"Assets/AthenHill/Art/StreetDressing/Props/{pid}/{pid}_Mask.png"}
    report["meshy"][pid] = materials[f"SD_{pid}"]

# ------------------------------------------------------------------ authored litter textures
rng = random.Random(20260930)
A = TEX / "Authored"
A.mkdir(exist_ok=True)


def noise(size, scale, seed):
    r = np.random.default_rng(seed)
    small = r.random((max(2, size // scale), max(2, size // scale))).astype(np.float32)
    return np.asarray(Image.fromarray((small * 255).astype(np.uint8)).resize((size, size), Image.BICUBIC)).astype(np.float32) / 255


def height_to_normal(h, strength):
    gy, gx = np.gradient(h)
    n = np.stack([-gx * strength, gy * strength, np.ones_like(h)], -1)   # OpenGL (+Y up)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return Image.fromarray(((n * 0.5 + 0.5) * 255 + 0.5).astype(np.uint8), "RGB")


def save_set(name, albedo, height, strength, smooth, metal=None):
    albedo.save(A / f"{name}_BaseMap.png", optimize=True)
    height_to_normal(height, strength).save(A / f"{name}_Normal.png", optimize=True)
    s = albedo.size[0]
    met = metal if metal is not None else np.zeros((s, s), np.float32)
    sm = smooth if isinstance(smooth, np.ndarray) else np.full((s, s), smooth, np.float32)
    m = np.stack([met, np.ones_like(met), np.zeros_like(met), sm], -1)
    Image.fromarray((m * 255 + 0.5).astype(np.uint8), "RGBA").save(A / f"{name}_Mask.png", optimize=True)
    materials[name] = {"kind": "authored", "base": ASSET + f"Authored/{name}_BaseMap.png", "normal": ASSET + f"Authored/{name}_Normal.png",
                       "mask": ASSET + f"Authored/{name}_Mask.png", "doubleSided": True}


# SD_Paper: 2x2 atlas (notice, yellowed form, blue ration slip, pink carbon copy); printed lines are abstract marks
S = 1024
paper = Image.new("RGB", (S, S))
ph_h = np.zeros((S, S), np.float32)
fib = noise(S, 3, 1) * 0.5 + noise(S, 24, 2) * 0.5
cols = [(222, 214, 196), (214, 196, 154), (184, 198, 206), (222, 188, 188)]
for q, col in enumerate(cols):
    x0, y0 = (q % 2) * S // 2, (q // 2) * S // 2
    tile = Image.new("RGB", (S // 2, S // 2), col)
    dr = ImageDraw.Draw(tile)
    ink = (58, 54, 50) if q != 2 else (40, 58, 90)
    r = random.Random(q)
    y = 42
    dr.rectangle([34, y, 34 + r.randint(160, 300), y + 22], fill=ink)       # heading bar
    if q == 0:
        dr.ellipse([400, 30, 470, 100], outline=(150, 40, 36), width=6)    # stamp
        dr.line([412, 86, 458, 44], fill=(150, 40, 36), width=6)
    y += 58
    while y < S // 2 - 50:
        x = 34
        while x < S // 2 - 60:
            w = r.randint(18, 70)
            if x + w > S // 2 - 34:
                break
            dr.rectangle([x, y, x + w, y + 7], fill=tuple(int(c * 0.9 + k * 0.1) for c, k in zip(ink, col)))
            x += w + r.randint(8, 14)
        y += r.choice([20, 20, 20, 34]) if q != 2 else 26
        if q == 2 and r.random() < 0.3:
            dr.line([34, y - 6, S // 2 - 34, y - 6], fill=ink, width=2)
    arr = np.asarray(tile).astype(np.float32) / 255
    # grime towards the edges, fibres, a few creases
    yy, xx = np.mgrid[0:S // 2, 0:S // 2] / (S // 2)
    edge = np.minimum(np.minimum(xx, 1 - xx), np.minimum(yy, 1 - yy))
    grime = np.clip(1 - edge / 0.12, 0, 1) * 0.35 + noise(S // 2, 40, 10 + q) * 0.12
    f = fib[y0:y0 + S // 2, x0:x0 + S // 2]
    arr = arr * (1 - grime[..., None] * np.array([0.55, 0.6, 0.75])) * (0.94 + 0.08 * f[..., None])
    h = f * 0.2
    for _ in range(3):
        a, b = r.uniform(0, 1), r.uniform(0, 1)
        dist = np.abs((xx - a) * math.cos(b * 6) + (yy - a) * math.sin(b * 6))
        crease = np.exp(-(dist / 0.004) ** 2)
        arr *= (1 - 0.18 * crease[..., None])
        h -= crease * 0.6
    paper.paste(Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8)), (x0, y0))
    ph_h[y0:y0 + S // 2, x0:x0 + S // 2] = h
save_set("SD_Paper", paper, ph_h, 3.0, 0.12)

# SD_Card: kraft carton (left: plain with tape and scuffs; right: stencilled stores mark and arrows), corrugation
card = Image.new("RGB", (S, S // 2), (160, 124, 82))
dc = ImageDraw.Draw(card)
dc.rectangle([0, 212, S // 2, 300], fill=(186, 170, 130))                  # tape band
st = (56, 44, 34)
dc.rectangle([S // 2 + 70, 60, S // 2 + 430, 90], fill=st)                  # stencil bars
dc.rectangle([S // 2 + 70, 110, S // 2 + 300, 132], fill=st)
for k, xa in enumerate((S // 2 + 90, S // 2 + 190)):                        # two "this way up" arrows
    dc.polygon([(xa, 300), (xa + 40, 250), (xa + 80, 300)], fill=st)
    dc.rectangle([xa + 28, 300, xa + 52, 360], fill=st)
dc.ellipse([S - 190, 300, S - 60, 430], outline=st, width=10)               # a ring mark with a W
dc.line([S - 160, 335, S - 140, 400, S - 125, 360, S - 110, 400, S - 90, 335], fill=st, width=9)
arr = np.asarray(card).astype(np.float32) / 255
yy, xx = np.mgrid[0:S // 2, 0:S] / (S // 2)
corr = 0.5 + 0.5 * np.sin(xx * S / 2 / 7.0 * 2 * math.pi)
n1 = noise(S, 20, 5)[:S // 2, :] * 0.5 + noise(S, 4, 6)[:S // 2, :] * 0.5
arr *= (0.9 + 0.12 * n1[..., None]) * (0.97 + 0.03 * corr[..., None])
water = np.clip((noise(S, 90, 7)[:S // 2, :] - 0.62) / 0.2, 0, 1)                 # old water stains
arr *= 1 - 0.22 * water[..., None]
card = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))
card_sq = Image.new("RGB", (S, S), (150, 118, 80)); card_sq.paste(card, (0, 0)); card_sq.paste(card.transpose(Image.FLIP_TOP_BOTTOM), (0, S // 2))
hh = np.zeros((S, S), np.float32); hh[:S // 2] = corr * 0.25 + n1 * 0.1; hh[S // 2:] = hh[:S // 2][::-1]
save_set("SD_Card", card_sq, hh, 2.0, 0.08)

# SD_Tin: two faded label bands (left red, right green) over tinned steel with rust spots; bare steel is metallic
tin = np.zeros((512, 512, 3), np.float32)
metal = np.zeros((512, 512), np.float32)
steel = np.array([0.62, 0.62, 0.6])
yy, xx = np.mgrid[0:512, 0:512] / 512
for half, lab in ((0, np.array([0.55, 0.2, 0.16])), (1, np.array([0.28, 0.42, 0.26]))):
    sl = slice(half * 256, half * 256 + 256)
    band = (yy[:, sl] > 0.18) & (yy[:, sl] < 0.82)
    tin[:, sl] = np.where(band[..., None], lab * 1.15, steel)
    metal[:, sl] = np.where(band, 0.0, 0.9)
    tin[(yy > 0.46) & (yy < 0.5) & (xx > half * 0.5) & (xx < half * 0.5 + 0.5)] *= 0.5     # a thin printed rule
rust = np.clip((noise(512, 12, 9) - 0.6) / 0.25, 0, 1) * np.clip((noise(512, 60, 10) - 0.35) / 0.3, 0, 1)
tin = tin * (1 - rust[..., None]) + np.array([0.36, 0.2, 0.1]) * rust[..., None]
metal *= 1 - rust
fade = noise(512, 50, 11)
tin = tin * (0.85 + 0.2 * fade[..., None]) + 0.06
smooth = np.clip(0.55 - rust * 0.45 - (1 - metal) * 0.2, 0.05, 0.8)
save_set("SD_Tin", Image.fromarray((np.clip(tin, 0, 1) * 255).astype(np.uint8)), rust * 0.6 + fade * 0.1, 2.0, smooth, metal)

# ------------------------------------------------------------------ tiling textures for the authored sacks, tarp, rope, skip
for tid, names in (("rough_linen", ["SD_Sack", "SD_SackPale", "SD_Tarp", "SD_Rope", "SD_Rag"]),
                   ("rusty_painted_metal", ["SD_SkipSteel"]), ("green_metal_rust", ["SD_ScrapSheet"])):
    d = TEX / tid
    d.mkdir(exist_ok=True)
    src = PH / "textures" / tid
    files = {p.name: p for p in src.iterdir()}
    diff = next(p for n, p in files.items() if "diff" in n.lower())
    nor = next(p for n, p in files.items() if "nor_gl" in n.lower())
    arm = next(p for n, p in files.items() if "arm" in n.lower())
    shutil.copyfile(diff, d / diff.name); shutil.copyfile(nor, d / nor.name)
    mask_from_arm(arm, d / f"{tid}_Mask.png", 1024)
    for n in names:
        materials[n] = {"kind": "tiling", "texture": tid, "base": ASSET + f"{tid}/{diff.name}", "normal": ASSET + f"{tid}/{nor.name}",
                        "mask": ASSET + f"{tid}/{tid}_Mask.png", "doubleSided": n in ("SD_Tarp", "SD_Rag")}
# per-material tints (multiplied over the base map in Unity)
TINTS = {"SD_Sack": [0.74, 0.55, 0.33], "SD_SackPale": [0.98, 0.8, 0.54], "SD_Tarp": [0.66, 0.6, 0.42], "SD_Rope": [0.9, 0.78, 0.55],
         "SD_Rag": [0.75, 0.32, 0.26], "SD_SkipSteel": [1.0, 1.0, 1.0], "SD_ScrapSheet": [1.0, 1.0, 1.0]}
for n, t in TINTS.items():
    materials[n]["tint"] = t

(TEX / "materials.json").write_text(json.dumps(materials, indent=1))
print(len(materials), "materials;", sum(1 for p in TEX.rglob("*") if p.is_file()), "texture files")
