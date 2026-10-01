# City paving + texture streaming — progress (1 Oct 2026)

Brief: /home/teknetik/.local/state/ward-programme/prompts/05-city-paving-and-texture-streaming.md
Evidence: unity/evidence/city-paving/20261001/README.md · Unity pass: Assets/AthenHill/Editor/CityPavingPass.cs

## State: WRAPPED UP (14:5x) — installed and verified; frame-time record + city loop pending the orchestrator's combined test

## Done
- Diagnosis (`diag`, native probe): paving held at mip 2 by chunk UV metric 1 (all 87 chunks); non-streamed textures
  4399 MB > 4096 budget pinned every streamed texture at mip 2; old normal map = albedo file. Joints already not drawn;
  the "rail" = 4 Avenue service bands.
- Fixes: `StaticRenderChunksEditor.Rebuild` recalculates UV distribution metrics; PC budget 4096 -> 5632 MB.
- New ground: author_paving.py (4 m tile, 0.5 m courses, worn_rock_natural_01 flags, sanded joints) -> 2k BC7,
  non-streamed, 17.3 MB; shader Athen Hill/Ward Paving Lit (world-mapped, course shuffle, per-flag tone, macro tint/dust,
  grain, far-joint lift, course axis); PV_CityFlags (floor) + PV_CityFlags_Band (plaza insets, north-south).
- Installed (install.json, install-bands.json), Paving Joints + service bands inactive, chunks rebuilt, rollback copy.
- Native iterations after1..after3, runtime tuning sweep (tune-v1/v2), final tuning in tuning*.json applied (`assets,bandmat`).
- Preliminary A/B: material +0.31 ms at cam_pv_north_lane, ~0 at cam_hill; budget no measurable cost.
- Builds/cp-* deleted. Final verify 14:5x OK. READMEs + DOCS_SNIPPET written.

## Next (only if the orchestrator reports defects)
- Fix round from the combined test. Ideas parked: per-street course direction, flush duct covers where the service
  bands were, flag relief (parallax) if the noon look reads too clean.
