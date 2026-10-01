# Texture memory pass (1 Oct 2026)

Compresses the scene's uncompressed textures without downsampling any source and without touching materials, prefabs,
scene references or GUIDs. Evidence and numbers: `unity/evidence/texture-memory/20261001/README.md`.

## How it works

- **glTF/glb embedded images** (glTFast 6.20 decodes them to uncompressed RGBA32/RGB24 sub-assets and has no
  compression setting). `Assets/AthenHill/Editor/GltfTextureCompression.cs` registers a glTFast import add-on
  (`GLTFast.Addons.ImportAddonRegistry`, `ITextureImageLoader`), which the editor importer also runs.
  - What it does: decodes each embedded PNG/JPEG exactly as glTFast does, then compresses power-of-two images to BC7.
    All four channels are kept, with the same sRGB/linear flag, mip chain, orientation and readability.
  - Why references survive: sub-asset names, types and file IDs are unchanged, so every material, prefab and scene
    reference stays valid.
  - What it leaves alone: NPOT images with mipmaps (Unity refuses to block-compress them) and meshes.
  - No mipmap streaming: flagging the in-memory import texture as streaming crashed Unity's TextureStreamingManager.
  - Default and override: `DefaultOn = true`; `ATHEN_GLTF_COMPRESS=0|1` overrides it for one Unity run. Import results
    only change when a .glb is (re)imported.
- **TextureImporter textures**. Every non-UI uncompressed texture in the scene was non-power-of-two with mipmaps, which
  Unity 6000.6 leaves uncompressed even with an explicit BC7 override. Each one now gets:
  - a Standalone override: BC7 for colour and packed masks, BC5 for normal maps, quality 50, max size never below the
    source;
  - `npotScale = ToLarger`, so the GPU copy is scaled *up* to the next power of two (the source file is untouched);
  - mipmap streaming on.

  The sRGB/linear flags and texture types are unchanged. Normals generated from a height source
  (`convertToNormalmap`) are skipped, because scaling the height changes the bump strength. The original `.meta` of
  every changed texture is copied to `unity/evidence/texture-memory/20261001/rollback/meta/` before the change.

## Run order (from the repo root; $O = /home/teknetik/.local/state/ward-programme)

```bash
L=$PWD/unity/evidence/texture-memory/20261001/logs; M=AthenHill.Editor.TextureMemoryPass.RunBatch
$O/unity.sh $L/inv.log $M --steps inventory:before -nographics          # scene texture inventory (heavy: ~12 GB + 3 GB swap)
$O/unity.sh $L/pb.log  $M --steps parity:a:before                         # isolated close-up captures (graphics; also parity:b)
$O/unity.sh $L/imp.log $M --steps importers -nographics                   # TextureImporter overrides (+ rollback .meta copies)
ATHEN_GLTF_COMPRESS=1 $O/unity.sh $L/g.log $M --steps "gltf:WardRetrofit/WardRetrofit.glb:retrofit,verifyglb:WardRetrofit/WardRetrofit.glb" -nographics
#   … then KaraveenMarket, then the rest (one .glb group per run; each followed by verifyglb)
$O/unity.sh $L/pa.log  $M --steps parity:a:after ; $O/unity.sh $L/pb2.log $M --steps parity:b:after,psnr,board
uv run --with pillow --with numpy python art/texture_memory_20261001/compare_parity.py unity/evidence/texture-memory/20261001
$O/unity.sh $L/inv2.log $M --steps inventory:after -nographics
$O/unity.sh $L/b.log   $M --steps build:after -nographics                 # own folder Builds/tm-after (delete after measuring)
art/texture_memory_20261001/native_probe.sh before-batch2 $PWD/unity/AthenHill/Builds/batch-batch2/AthenHill.x86_64
art/texture_memory_20261001/native_probe.sh after $PWD/unity/AthenHill/Builds/tm-after/AthenHill.x86_64
$O/unity.sh $L/cv.log  $M --steps cameras,verify -nographics              # review cameras + final check
```

Other steps:
- `plan[:filter]`: counts of the importer decisions.
- `revert[:filter]`: restores the saved `.meta` files and reimports.
- `gltfplain:<filter>`: reimport with the add-on off (needs `ATHEN_GLTF_COMPRESS=0`).
- `metrics:<glb+glb>`: UV distribution metrics of the meshes in those files.

Compile-check C# changes outside Unity first: `python3 art/night_life_20261001/check_compile.py editor <file.cs>`.

## Rollback

- **TextureImporter:** `--steps revert -nographics`. It copies the original `.meta` files back and reimports.
- **glTF:** set `GltfTextureCompression.DefaultOn = false`, or run with `ATHEN_GLTF_COMPRESS=0`, then
  `--steps gltfplain:all:restore` to force-reimport the 24 files listed in `inventory-before.json`.
- **Review cameras:** delete the root "Texture memory review cameras".

## Files

| File | Role |
| --- | --- |
| `vram_sampler.sh` | Total and player GPU memory every 2 s while a native run lasts (nvidia-smi). |
| `native_probe.sh` | One native lookbook (cam_hill, cam_avenue, cam_gate, 13:00) with `ATHEN_TEXSTREAM_PROBE=1` and the sampler. Memory only, never for frame times. |
| `compare_parity.py` | Before/after pairs, ×8 difference, worst-block crop and PSNR of the isolated editor captures. |
| `PROGRESS.md`, `DOCS_SNIPPET.md` | Progress log; text for EDITING.md and the AGENTS.md baseline table. |

No external assets; nothing to license.
