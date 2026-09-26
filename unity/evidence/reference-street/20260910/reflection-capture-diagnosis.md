# Reflection capture diagnosis — 10 September 2026

The hour-16 failure in `iteration-02-native` has a concrete configuration defect: the selected PC quality tier disables realtime reflection probes, while `CityTimeReflections` changes individual probes to Realtime and calls `RenderProbe` without enabling the global capture switch. Unity documents that realtime probes are not baked when `QualitySettings.realtimeReflectionProbes` is disabled. The runtime fix enables that switch immediately before requesting a capture and restores its original value when the component is disabled.

## Retained failure evidence

- Unity 6000.6.0f1, URP 17.6.0, PC quality, OpenGLCore 4.5 on RTX 3060 / i9-10850K, native 1920 × 1080. These are the failed build's settings, not qualification of the changed source.
- `iteration-02-native/time-state.json` records hour 16, paused, one failed capture, zero completed captures, another capture pending, and empty realtime texture names on both the 128-pixel City sky probe and the 256-pixel Courtyard probe. Both use IndividualFaces slicing and have zero intensity while stale.
- That file's SHA-256 remains `1bef05b36cb1c48e2b95052d5c61ecf67fe54bfe96ecd343ba3c8d632c57187b`.
- `ProjectSettings/QualitySettings.asset` sets `realtimeReflectionProbes: 0` in both Mobile (line 28) and PC (line 82). `GameSettings.ApplyQuality` does not enable this property. Inspection of installed URP/core package sources found no managed override that enables it on the game's behalf. The URP Editor-only `SupportedRenderingFeatures.active.reflectionProbes` assignment is a separate support/Inspector flag and is not evidence that native runtime capture is unsupported.

## Scope of the fix

Changed only `Assets/AthenHill/Scripts/CityTimeReflections.cs`: retain the original global setting in `OnEnable`, set it true before `RenderProbe`, and restore it in `OnDisable`, alongside the component's existing state restoration. Project quality assets are unchanged. The one-capture-at-a-time queue, IndividualFaces slicing, resolutions, refresh interval, 10-second timeout, failure/completion counters and suppression of stale bright reflections are unchanged.

The official API establishes that this switch is a necessary precondition. It does not prove that no second platform-specific issue exists. Successful native capture still needs to be observed; increasing the timeout or changing slicing without that evidence would not fix the identified configuration defect.

## Checks and required native follow-up

- `git diff --check` for the changed runtime file passed.
- Offline compilation of the runtime source set passed with Unity 6000.6.0f1's bundled .NET SDK / Roslyn and the project's Unity assembly references. The first attempt used an older response file missing the newer `NativeVisualReview.cs` and `NativeAssetReview.cs`; adding those existing files to the temporary response file made compilation pass. No runtime source was altered to accommodate the compiler.
- Compile invocation, from `unity/AthenHill`: `/home/teknetik/Unity/Hub/Editor/6000.6.0f1/Editor/Data/DotNetSdk/dotnet /home/teknetik/Unity/Hub/Editor/6000.6.0f1/Editor/Data/DotNetSdk/sdk/8.0.318/Roslyn/bincore/csc.dll @/tmp/ward-reflection-quality-fix.rsp` (exit 0, no diagnostics).
- Checked source SHA-256: `e8d362ec260801977b6dcb45430954da185586a97c3e303c6bc582ad8985f1f5`. Temporary compiled assembly SHA-256: `f2a99f3649fbcf6dce6527b563a9ecf61bdc1a752e82fe2176e034ad90469e7d`.
- No Unity/Blender instance was launched or modified, and no input was sent to the currently running player during this diagnosis.

Native verification is pending a new build. Preserve `iteration-02-native` and capture a new evidence directory. At the same native settings, exercise noon → 16 → midnight → noon; at each changed hour require an increased completion count, zero failures, no pending capture for at least 1.2 seconds, and inspect the recorded probe textures/intensities. Reuse the unchanged gate in `art/reference_street_20260910/capture_asset_passes.py`. It observes completion counters and pending state; it does not expose or certify each probe's exact captured hour. Inspect actual nonempty realtime textures and the lit result as well. Record capture latency and traversal frame times because enabling previously blocked capture introduces actual rendering work. The second-lighting art review must use the completed new capture, not the failed hour-16 images.

## Primary references

- [Unity 6: QualitySettings.realtimeReflectionProbes](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/QualitySettings-realtimeReflectionProbes.html): disabled realtime probes are not baked.
- [Unity 6: ReflectionProbe.RenderProbe](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/ReflectionProbe.RenderProbe.html): requests a runtime probe render and returns an ID for completion checks.
- [Unity 6: ReflectionProbe.IsFinishedRendering](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/ReflectionProbe.IsFinishedRendering.html): tests completion of the requested render, including time-sliced work.
