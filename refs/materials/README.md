# Material reference freeze

These six original imagegen closeups were displayed and visually inspected before their unchanged PNG bytes were copied into `public/assets/textures/`. Exact prompts, source paths, dimensions, hashes, reviews and foliage UV regions are recorded in `textures-provenance.json`.

The hero bark target was 2048×2048; the built-in generator returned 1254×1254, retained without upscaling. All six delivered images are native 1254×1254.

The foliage atlas has a genuine alpha channel. Start with `alphaTest: 0.35` and verify the leaves at gameplay distance. Use the recorded unequal atlas rectangles to avoid clipping the broad upper-left spray. The holographic atlas uses an intentionally opaque dark backing for emissive use.

Accepted material references must not be overwritten. Any revised generator output should use a versioned filename. Live mesh tiling, mipmaps and final shading remain integration checks.
