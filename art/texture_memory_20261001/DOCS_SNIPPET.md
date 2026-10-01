# Docs snippet — texture memory pass (1 Oct 2026)

## For unity/EDITING.md

### Texture compression and memory

- **Embedded glTF/glb images are compressed at import.** `Editor/GltfTextureCompression.cs` is a glTFast import add-on
  that compresses power-of-two embedded PNG/JPEG images to BC7.
  - It keeps the same channels, sRGB/linear flag, mips and sub-asset IDs, so references don't change.
  - It acts whenever a .glb is (re)imported; `ATHEN_GLTF_COMPRESS=0` turns it off for one Unity run.
  - Don't switch it off permanently: a reimport would bring back about 2.6 GB of uncompressed textures.
  - Embedded textures are **not** mipmap-streamed. NPOT embedded images stay uncompressed, so export power-of-two maps
    from Blender.
- **TextureImporter textures must be power-of-two to compress.** Unity 6000.6 leaves a non-power-of-two texture with
  mipmaps uncompressed (RGBA32) even with CompressedHQ or an explicit BC7 override. Either author power-of-two maps,
  or set `npotScale = ToLarger` together with a Standalone BC7 (colour/masks) or BC5 (normals) override, as
  `TextureMemoryPass.ApplyImporters` does.
  - Don't use ToLarger on normals created from a height map ("Create from Grayscale"): it weakens the bumps.
- **Check memory:** `TextureMemoryPass.RunBatch --steps inventory:<tag> -nographics` writes every texture the scene
  loads, with format, mips, streaming flag and MB, to `unity/evidence/texture-memory/20261001/inventory-<tag>.{json,md}`.
  Inactive objects count too. The run is heavy: about 12 GB plus 3 GB swap.
  - In a development player, `ATHEN_TEXSTREAM_PROBE=1` with `--athen-qa` logs the streaming counters
    (`art/texture_memory_20261001/native_probe.sh`). The probe hitches every 8 s, so never profile frame times with it.
- **Rollback:** `--steps revert` restores the original importer `.meta` files from the evidence folder.

## For the AGENTS.md baseline table

| Texture memory | 1 Oct 2026 (`art/texture_memory_20261001`). 434 scene textures compressed:<br>• 414 glTF-embedded → BC7 through a glTFast import add-on (`GltfTextureCompression`, on by default).<br>• 20 non-power-of-two TextureImporter maps → BC7/BC5, scaled up to a power of two (ToLarger) and streamed.<br>No source downsampled, no references changed.<br>Native, 3 views: non-streamed textures 4.0 → 1.6 GB, resident 4.7 → 2.2 GB, player VRAM 8.0 → 4.5 GB.<br>Streaming budget is still 5632 MB; 3584 MB is recommended (Carl decides). glTF textures are not streamed, and glTF meshes have UV distribution metric 1 (open). Not yet accepted by Carl. |
