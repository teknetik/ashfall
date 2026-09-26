# Ward tree Inspector candidate

Prepared outside Assets during native build/timing. **Not imported or compiled.** No live source, shader registration, material or scene was changed by this preparation.

The existing shader uses URP17.6's normal Lit inspector, which draws an explicit list of standard fields and therefore hides all four Ward wind/transmission controls. The installed `LitShader` and `LitDetailGUI` classes are internal, so an external derived LitShader class cannot compile. This candidate derives from public ShaderGUI and delegates standard drawing, material validation, shader assignment, preview and close callbacks to the pinned installed LitShader instance. It then appends the four existing MaterialProperty sliders with explanatory tooltips. Range attributes on WardTree.shader supply the limits; MaterialEditor handles mixed values, property drawers and Undo. No default values or material assignments change on installation.

This small wrapper uses reflection only to instantiate the internal LitShader class. It does not reflect individual methods/fields or reproduce URP keyword logic. The dependency is explicit and limited to the pinned editor package; a pipeline/package migration must revalidate it. It is Editor-only and adds no native player rendering cost. A longer alternative would duplicate the Lit inspector plus its internal detail GUI; this candidate avoids maintaining that copy.

After native timing finishes, place WardTreeShaderGUI.cs at Assets/AthenHill/Editor/WardTreeShaderGUI.cs and apply the one-line shader-registration.diff after comparing the current shader hash with manifest.json. Do not overwrite newer shader changes with the staged whole-file candidate. Unity should generate the script meta on import; preserve that GUID afterward.

Verify the standard Lit Surface/Inputs/Details/Advanced sections remain present, plus Ward Tree crown sway0–0.3m, flutter0–0.04m, sun transmission0–0.5 and ambient transmission0–0.5. Open leaves and bark without changing values; verify texture/custom values are unchanged. Test multi-material mixed-value edits and Undo/redo, then recheck alpha/normal/metallic/detail keyword behavior. Preserve direct0.22 and ambient0 unless a separate visual decision changes them. Native performance/rebuild is not needed solely for an Editor UI registration, but do not combine its import with an active timing run.

## Applied checkpoint

The root agent imported the staged Editor class and shader registration after GPU timing. Live Unity resolves the GUI and preserves Lit keywords. Clone-based multi-edit and Undo checks passed; scene remains clean. The saved leaf ambient value is .15 after the independent native comparison. Pointer-level inspection remains unverified while the desktop is locked; see manifest and dated evidence.
