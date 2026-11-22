"""Fetch curated SimReady Central packages from Hugging Face into raw/<id>/.

For each entry in catalog_defs.ASSETS (or a subset passed on the command line):
1. Downloads com.nvidia.simready.packaging.json and .metadata/com.nvidia.simready.packaging.bom.json
2. Downloads all USD layers (.usd, .usda, .usdc), texture images (.png, .jpg), one thumbnail,
   and any LICENSE/ATTRIBUTION/mechanism metadata files.
3. Skips duplicate source_assets/ copies and redundant .thumbs/ sizes to save bandwidth and disk.
4. Verifies file sizes against the BOM so interrupted downloads are automatically retried.

Usage:
    python3 fetch_simready.py [--workers 8] [asset_id ...]
"""
import argparse, concurrent.futures, json, sys, time, urllib.request
from pathlib import Path
from catalog_defs import ASSETS

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"


def fetch_url(url, dst, expected_size=None, retries=3):
    if dst.exists() and (expected_size is None or dst.stat().st_size == expected_size):
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".part")
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Ashfall-SimReady-Pipeline/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp, open(tmp, "wb") as f:
                while True:
                    chunk = resp.read(1024 * 256)
                    if not chunk:
                        break
                    f.write(chunk)
            if expected_size is not None and tmp.stat().st_size != expected_size:
                raise IOError(f"size mismatch for {url}: got {tmp.stat().st_size}, expected {expected_size}")
            tmp.replace(dst)
            return True
        except Exception as e:
            if attempt == retries - 1:
                raise RuntimeError(f"Failed to download {url}: {e}") from e
            time.sleep(1.0 * (attempt + 1))
    return False


def want_bom_item(rp):
    if "/source_assets/" in rp or rp.startswith("simready_usd/source_assets/"):
        return False
    if "/.thumbs/" in rp:
        return rp.endswith("_thumbnail.png") or ("/256x256/" in rp and not rp.endswith(("_light.png", "_transparent.png")) and "Textures/.thumbs" not in rp)
    if rp.endswith(".mdl"):
        return False
    return True


def pull_asset(entry, pool):
    aid = entry["id"]
    base = entry["url"].rstrip("/")
    adir = RAW / aid
    adir.mkdir(parents=True, exist_ok=True)

    pkg_path = adir / "com.nvidia.simready.packaging.json"
    bom_path = adir / ".metadata/com.nvidia.simready.packaging.bom.json"
    fetch_url(f"{base}/com.nvidia.simready.packaging.json", pkg_path)
    fetch_url(f"{base}/.metadata/com.nvidia.simready.packaging.bom.json", bom_path)

    bom = json.loads(bom_path.read_text())
    items = [i for i in bom.get("items", []) if want_bom_item(i["relative_path"])]
    futs = []
    for item in items:
        rp = item["relative_path"]
        sz = item.get("size")
        futs.append(pool.submit(fetch_url, f"{base}/{rp}", adir / rp, sz))
    downloaded = sum(1 for f in concurrent.futures.as_completed(futs) if f.result())
    total_mb = sum(i.get("size", 0) for i in items) / 1e6
    print(f"[{aid:42}] {len(items):2} files ({total_mb:5.1f} MB) | {downloaded:2} new", flush=True)
    return len(items), total_mb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("ids", nargs="*")
    args = ap.parse_args()

    want = set(args.ids) if args.ids else None
    targets = [a for a in ASSETS if not want or a["id"] in want]
    if not targets:
        sys.exit("No matching asset IDs found in catalog_defs.py")

    t0 = time.time()
    total_files = 0
    total_mb = 0.0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for entry in targets:
            nf, mb = pull_asset(entry, pool)
            total_files += nf
            total_mb += mb
    print(f"Done: {len(targets)} assets ({total_files} files, {total_mb:.1f} MB) in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
