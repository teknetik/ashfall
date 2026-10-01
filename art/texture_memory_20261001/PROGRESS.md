# Texture memory pass — progress (1 Oct 2026)

Brief: /home/teknetik/.local/state/ward-programme/prompts/15-texture-compression.md
Editor code: unity/AthenHill/Assets/AthenHill/Editor/TextureMemoryPass.cs (+ GltfTextureCompression.cs)
Evidence: unity/evidence/texture-memory/20261001/README.md

## State 17:05: DONE (pending the orchestrator's combined batch-3 test)

## Done
- 15:58 inventory-before: 1501 textures, 9345 MB; not streamed 4733 MB; uncompressed 4720 MB (glTF 3900, importer 818).
- 16:05 add-on probe (WorkerDroid). **Crashed at shutdown (rc 139)**, cause found later.
- 16:11–16:13 parity before (isolated scene, 12 views).
- 16:14 importers: 22 NPOT → BC7/BC5 + ToLarger + streaming (landed just before the batch-2 build; the orchestrator
  kept them).
- 16:29 WardRetrofit with the add-on **crashed (rc 139)**. Both core dumps are in TextureStreamingManager
  (m_StreamingMipmaps set through SerializedObject on the in-memory texture). 16:31 restored with a plain reimport and
  verified. The add-on was fixed: compress only, POT only, no streaming flag, no SerializedObject.
- 16:33–16:41 fixed add-on: WorkerDroid + SteelTargetPlate, WardRetrofit, KaraveenMarket, then the other 20. All
  rc 0, verified (1785 renderers, 0 missing). glTF 3745 → 1160 MB. DefaultOn = true.
- 16:43–16:46 parity after + importer PSNR. 16:49 compile error for about a minute (night-facade job failed; the
  orchestrator told that agent to rerun). Since then every C# change is compile-checked offline first.
- 16:50 reverted Gunmetal/WallStone NormalSource (normals made from height; scaling would flatten them); board tiles.
- 16:52 inventory-after: 6287 MB; not streamed 1744 MB; uncompressed 167 MB.
- 16:54 build tm-after. 16:56/16:58 native probe: batch-2 4033/4692 MB (not streamed/resident) → 1573/2238 MB;
  player VRAM 8012 → 4538 MiB. Builds/tm-after deleted.
- 17:01 review cameras (cam_tm_* ×6) + verify OK. README, DOCS_SNIPPET written.

## Next (only if the orchestrator reports defects)
- Optional follow-ups (decisions): streaming budget 5632 → 3584; UV distribution metrics for glTF meshes (separate
  A/B); streaming flag on 96 compressed, non-streamed importer textures (437 MB).
