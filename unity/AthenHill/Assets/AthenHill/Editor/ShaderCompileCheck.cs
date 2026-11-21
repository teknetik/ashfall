using System;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.Rendering;
using UnityEngine;
using UnityEngine.Rendering;

namespace AthenHill.Editor
{
    /// Compiles every pass of the given shaders for the shipped player (Linux x86-64, OpenGL Core) with no keywords and
    /// reports errors, without a graphics device (21 Nov 2026, Gemini merge review: two terrain shaders it changed
    /// had a ShaderLab parse error that no batch step reported). A -nographics import only logs a parse error; HLSL
    /// errors in a pass appear only when a variant is compiled, which this does.
    /// Batch: -executeMethod AthenHill.Editor.ShaderCompileCheck.RunBatch -nographics --shaders A.shader,B.shader [--out file]
    public static class ShaderCompileCheck
    {
        public static void RunBatch()
        {
            var args = Environment.GetCommandLineArgs();
            string Arg(string name) { int i = Array.IndexOf(args, name); return i >= 0 && i + 1 < args.Length ? args[i + 1] : null; }
            try
            {
                var paths = (Arg("--shaders") ?? "").Split(',').Where(p => p.Length > 0).ToArray();
                if (paths.Length == 0) throw new Exception("--shaders is empty");
                var report = new StringBuilder(); int failures = 0;
                foreach (var path in paths)
                {
                    var shader = AssetDatabase.LoadAssetAtPath<Shader>(path);
                    if (!shader) { report.AppendLine($"MISSING {path}"); failures++; continue; }
                    var parse = ShaderUtil.GetShaderMessages(shader).Where(m => m.severity == ShaderCompilerMessageSeverity.Error).ToArray();
                    foreach (var m in parse) report.AppendLine($"ERROR {path} (import) line {m.line}: {m.message}");
                    failures += parse.Length;
                    var data = ShaderUtil.GetShaderData(shader);
                    int compiled = 0;
                    for (int s = 0; s < data.SubshaderCount; s++)
                    {
                        var sub = data.GetSubshader(s);
                        for (int p = 0; p < sub.PassCount; p++)
                        {
                            var pass = sub.GetPass(p);
                            foreach (var stage in new[] { ShaderType.Vertex, ShaderType.Fragment })
                            {
                                if (!pass.HasShaderStage(stage)) continue;
                                var info = pass.CompileVariant(stage, new string[0], ShaderCompilerPlatform.OpenGLCore, BuildTarget.StandaloneLinux64, false);
                                compiled++;
                                foreach (var m in info.Messages.Where(m => m.severity == ShaderCompilerMessageSeverity.Error))
                                { report.AppendLine($"ERROR {path} pass {s}.{p} '{pass.Name}' {stage} line {m.line}: {m.message}"); failures++; }
                                if (!info.Success && !info.Messages.Any(m => m.severity == ShaderCompilerMessageSeverity.Error))
                                { report.AppendLine($"ERROR {path} pass {s}.{p} '{pass.Name}' {stage}: compile failed without a message"); failures++; }
                            }
                        }
                    }
                    report.AppendLine($"{(parse.Length == 0 ? "OK" : "FAIL")} {path} ({shader.name}): {compiled} stage compiles, hasError={ShaderUtil.ShaderHasError(shader)}");
                }
                var text = report.ToString();
                var outPath = Arg("--out");
                if (!string.IsNullOrEmpty(outPath)) { Directory.CreateDirectory(Path.GetDirectoryName(outPath)); File.WriteAllText(outPath, text); }
                Debug.Log("ShaderCompileCheck " + (failures == 0 ? "PASS" : $"FAIL {failures}") + "\n" + text);
                EditorApplication.Exit(failures == 0 ? 0 : 1);
            }
            catch (Exception e) { Debug.LogException(e); EditorApplication.Exit(1); }
        }
    }
}
