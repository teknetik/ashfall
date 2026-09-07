# U4 — sound, rendering and editability — 7 September 2026

Technical port accepted; final concept likeness remains open.

Audio output was captured from Unity's isolated PulseAudio stream, including a
13-second ambience loop, footsteps, spatial hum and UI confirmation. Pause/mute
produce silence and unmuting restores output. See audio/report.json and WAVs.
The supplied mixes and provenance are retained; no music or voices were invented.

Render sources remain modular prefab instances. Static meshes are grouped by
material and spatial cells with explicit Show Sources/Rebuild controls. The
edit-roundtrip.json check preserves source visibility, transforms, prefab linkage
and colliders. World/actor materials are native editable variants, original imports
are unchanged, and stale chunks fail the build rather than overwriting edits.

URP 17.6.0, Forward, OpenGL Core, 1920×1080, render scale 1, 4× MSAA,
one 4096 shadow cascade / 50 m, one shadowed sun, unshadowed fill, sky reflection,
no SSAO or postprocessing. All eight actors, shadows and HUD are included.
Standalone route timing is recorded in ../U5/native/qualification.json. This is
an RTX 3060 / i9-10850K desktop, not a medium laptop qualification. Draw/Batches
recorders and GPU timings returned no usable samples; zero is not a measured
cost. Independent OpenGL API tracing supplies actual draw counts in gl-trace/.
The attempted GPU trace replay did not return usable timings and is rejected.

## Fixed-camera scorecard (0–5)

Compared actual native cam_hill/cam_avenue/cam_gate captures in ../U5/native with
frozen refs/01–03; cameras preserve imported compositions rather than matching
the painting exactly. Scores are an explicit visual review, not an image metric.

| Trait | Hill | Avenue | Gate |
| --- | ---: | ---: | ---: |
| Palette | 3 | 3 | 3 |
| Sky / haze | 2 | 2 | 2 |
| Silhouette | 2 | 2 | 3 |
| Light direction | 3 | 3 | 3 |
| Roughness | 3 | 3 | 3 |
| Density | 2 | 2 | 2 |
| Scale | 4 | 4 | 4 |
| HUD integration | 3 | 3 | 3 |

The warm stone/gunmetal/red/cyan palette reads, but stone is too yellow and evenly
lit. The sky lacks the reference's clouds and depth. The imported V-shaped tree
and flat square grass bed need authored silhouette/mound work. Shop and canyon
masses remain simple and streets lack reference clutter. Gate arches are readable
but too regular. Material detail is noisy at distance. The character is still more
stylized than the bearded-armour target; NPCs retain the supplied primitive bodies.

The required 4/5 palette/silhouette/light threshold is NOT met. This milestone
accepts the sound and faithful editable technical port, as permitted by the handover;
it does not mark final visual work finished or lower its target.

Final trace: maximum 78 GL draw submissions across follow/three hero cameras,
shop, Lattice transition/overlay and pause. See phases.json for actual states.
The final route averages 490 FPS. Raw ProfilerRecorder data includes one zero
triangle/SetPass sample followed by an exact double (370,796 / 38), then
185,398 / 19: a counter aggregation anomaly, retained without silently filtering.
The separate API trace counts real triangle submissions. One walking frame was
66.6 ms; p99 was 5.10 ms. Therefore the strict every-frame 58 FPS floor is not
claimed. The earlier route had a worst walking frame of 8.52 ms, but it is not
substituted for the final run. GPU timing and medium-laptop qualification remain open.
