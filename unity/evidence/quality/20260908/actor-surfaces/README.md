# Supplied actor surface fidelity recovery

Prepared 8 September 2026. **Installer authored; Unity execution and native visual
acceptance remain pending.** Root owns integration, scene save, chunk rebuild and
Linux builds. This task has not changed the shared scene or source assets.

Standalone Roslyn compilation against the installed Unity6000.6 assemblies and
current project assemblies succeeded with no code errors. [Compiler output](compile.log)
contains one netstandard2.0→2.1 reference-assumption warning; [response file](compile.rsp)
records the exact references. This static compile does not execute the installer or
replace the required Unity Console and native checks.

Installer: [`ActorSurfaceFidelityPass.cs`](../../../../AthenHill/Assets/AthenHill/Editor/ActorSurfaceFidelityPass.cs).
It has two explicit entry points:

```csharp
AthenHill.Editor.ActorSurfaceFidelityPass.Prepare();
AthenHill.Editor.ActorSurfaceFidelityPass.Install();
```

The corresponding menus are `Athen Hill/Characters/Prepare supplied surface fidelity
assets` and `Athen Hill/Characters/Install supplied surface fidelity`. `Install`
runs preparation itself. It assigns only nine existing SkinnedMeshRenderers, keeps
their prefab links, records overrides and leaves the scene dirty for the caller to
save. It does not open/reload a scene, rebuild chunks, replace prefabs, alter motion
scripts, sample poses or run a player build.

## Planned changes and strict limits

| Family | Before | Prepared recovery |
| --- | --- | --- |
| Player | Full 4K albedo also emits at factor1; metallic factor1 without a mask; no tangents/shadows | Original embedded albedo in URP Lit; emission off, nonmetal0 and smoothness0.25; compatible tangent clone and cast/receive shadows |
| Mira / Torr / Linn | 2K albedo only, green-grey tint, no tangent/PBR/shadow support | Original guard 2K albedo/normal/metallic/roughness, white tint; correct packed channels, tangent clone and shadows |
| Vex | Recovered original 2K PBR and tangent clone | Same supplied maps through validated shared guard recovery; preserves vertex/index/rig data and shadows |
| Three travelers | Original4096 albedo imports2048; packed map2048 derived from4096 originals; shadows off | Original4096 albedo plus newly packed exact4096 metallic/smoothness; tangent clone and shadows |
| Yard mechanic | Supplied2K PBR, shadows on | Preserve original maps with exact channel checks and compatible tangent clone; shadows retained |

All maps in [source-map-checks.json](source-map-checks.json) were verified against
retained source PNGs. Guard, mechanic and traveler source/runtime PNGs are
byte-identical. Guard/mechanic existing packed maps are exact; traveler's existing
2048 packed map loses half the linear source resolution. The new pack preserves
metallic in R and stores `255 - roughness` in A, with G/B zero. The installer decodes
the original PNG bytes independently of import resampling, then checks **every
output pixel** before binding a linear data texture to URP Lit.

Player source GLBs provide only the original albedo, and travelers have no retained
normal texture. The installer does not manufacture those maps or claim full PBR
recovery where none exists. Player cyan accents remain visible in albedo, but are
not made emissive without a reviewed semantic mask. Source anatomy, armour shapes,
visor detail, finger/face animation and source texture softness remain art work.

The measured 12-texture allowlist restores source dimensions with NPOTScale.None
and sufficient maxTextureSize: wall, gunmetal, paving normal/albedo pairs, Karaveen
poster, Ward banner, courtyard canvas, hill soil, sandstone and traveler albedo.
Existing mip, wrap, compression, anisotropy and normal color-space settings are
preserved. Original PNGs, UI assets and rejected shop candidates are untouched.
An explicit platform override that still reduces dimensions causes a clear failure
for review instead of silently removing the override.

## Preservation and repeat behavior

Preparation refuses unexpected actor assignments/topology. It hashes semantic mesh
buffers before/after: positions, normals, UV0–7, colors, indices/submeshes/base
vertices, index format, all bone weights, bind poses and every blendshape frame.
Only the tangent channel may change. All tangent vectors are checked for finiteness,
unit length, orthogonality to normals and valid handedness. Unity-owned bone-weight
arrays are read without disposal, following the [Unity API ownership guidance](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Mesh.GetBonesPerVertex.html).

Original meshes are retained. Four new mesh/material families live in
`Assets/AthenHill/Art/ActorSurfaceFidelity`. Existing recovery assets are validated
on repeats, not overwritten. Deliberately changed artist buffers/bindings stop the
installer for review. Original importer metadata is backed up once. Skeleton paths,
root bones, every actor transform, culling bounds and offscreen settings must remain
identical through installation. Existing animation clips/controllers and route or
gameplay tuning are never assigned by this code.

Successful preparation writes `prepared.json` with mesh equivalence, channels,
import dimensions and renderer before-state. Successful installation writes
`installed.json`. These reports do not exist until Unity actually runs the methods;
the authored checks are not being passed off as executed verification.

## Integration and visual evidence still required

1. Compile in the connected saved Unity project and inspect Console errors.
2. Run Prepare, inspect `prepared.json`, then Install. Check all nine actor bindings.
3. Save the scene; save asset state before recomputing render-source fingerprint.
   Rebuild chunks through the normal workflow if other source/material work changed.
4. Reopen the scene and build native Linux. Check the same source hashes and bindings.
5. Capture Vex face/body/conversation and all nine actors in sun and shade, plus
   native moving views, third-person/first-person camera transitions and shadows.
   Existing useful cameras: `cam_p1_vex_face`, `cam_fidelity_guard`, `cam_terminal`,
   `cam_salvage_general`, `cam_hill`. These do not provide complete individual
   coverage; see [review requests](native-review-requests.json).
6. Independent critic must inspect source identity, cloth/skin/armour separation,
   excessive specular response, visor readability, contact shadows and foot motion.
   Source fidelity recovery is not a claim of AAA quality or final acceptance.
# Interrupted install recovery

The first actual integration completed `Prepare` but was interrupted after renderer assignments, before `installed.json`. The original preparation evidence is retained as `prepared-first.json`. Unity may reset `SkinnedMeshRenderer.localBounds` when `sharedMesh` is assigned; the installer now captures and restores those bounds explicitly, records them in renderer evidence, and rolls all assigned mesh/material/bounds/shadow properties back if a subsequent check fails. Detailed rig-signature differences are written on a failed preservation check.

The next actual install's preservation check found only floating-point AABB roundoff, with unchanged bones/rootBone/transforms. Bounds are now checked to **0.1 mm in world space**, using the maximum displacement of all eight corresponding AABB corners transformed through the renderer's actual matrix. This is not a tolerance on mesh buffers, UVs, weights, bindposes or transforms; those remain exact. `culling-bounds-check.json` and `installed.json` record each local center/size delta and world maximum. Exceeding the tolerance still rejects and rolls back. Repeated installs avoid reassigning the same mesh/bounds, preventing cumulative setter roundoff. After bounds recovery has already run, retry only `Install()`.

For this specific interrupted run, root can call `ActorSurfaceFidelityPass.RecoverInterruptedInstallBounds()` followed by `ActorSurfaceFidelityPass.Install()`. Recovery requires the exact frozen `before-scene.unity` SHA256 and confirms that its supplied prefab instances contain no AABB overrides. It verifies live mesh equivalence, then restores only the original supplied prefab renderer's local culling bounds for each actor and records `bounds-recovery.json`. It does not load, save or replace the shared scene. If the baseline check fails, it stops before applying inferred bounds. This code correction was compiled without operating Unity; the root owns its actual execution and acceptance.
