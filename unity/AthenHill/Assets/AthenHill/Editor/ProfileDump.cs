using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEditor;
using UnityEditor.Profiling;
using UnityEditorInternal;

namespace AthenHill.Editor
{
    /// Reads a player profiler capture (.raw from `-profiler-enable -profiler-log-file X.raw`) and writes the markers
    /// with the most self time per thread, averaged over the captured frames:
    ///   -executeMethod AthenHill.Editor.ProfileDump.DumpBatch --raw X.raw --out X.json [--skip 60 | --last 600]
    public static class ProfileDump
    {
        public static void DumpBatch()
        {
            var args = Environment.GetCommandLineArgs();
            string Arg(string n, string d = null) { int i = Array.IndexOf(args, n); return i >= 0 && i + 1 < args.Length ? args[i + 1] : d; }
            string raw = Arg("--raw"), output = Arg("--out"); int skip = int.Parse(Arg("--skip", "60")), lastN = int.Parse(Arg("--last", "0"));
            int code = 0;
            try
            {
                if (!ProfilerDriver.LoadProfile(raw, false)) throw new Exception("Could not load " + raw);
                int last = ProfilerDriver.lastFrameIndex; int first = lastN > 0 ? Math.Max(ProfilerDriver.firstFrameIndex, last - lastN + 1) : ProfilerDriver.firstFrameIndex + skip;
                var threads = new Dictionary<string, Dictionary<string, double>>();
                var frameMs = new List<double>();
                int frames = 0;
                for (int f = first; f <= last; f++)
                {
                    frames++;
                    for (int t = 0; t < 64; t++)
                    {
                        using (var view = ProfilerDriver.GetHierarchyFrameDataView(f, t, HierarchyFrameDataView.ViewModes.MergeSamplesWithTheSameName, HierarchyFrameDataView.columnSelfTime, false))
                        {
                            if (view == null || !view.valid) { if (t > 2) break; continue; }
                            string thread = view.threadName;
                            if (thread != "Main Thread" && thread != "Render Thread" && !thread.StartsWith("Worker")) continue;
                            if (t == 0) frameMs.Add(view.frameTimeMs);
                            if (thread.StartsWith("Worker")) thread = "Workers";
                            if (!threads.TryGetValue(thread, out var totals)) threads[thread] = totals = new Dictionary<string, double>();
                            var stack = new Stack<int>(); stack.Push(view.GetRootItemID());
                            var children = new List<int>();
                            while (stack.Count > 0)
                            {
                                int id = stack.Pop();
                                if (id != view.GetRootItemID())
                                {
                                    string name = view.GetItemName(id); double self = view.GetItemColumnDataAsDouble(id, HierarchyFrameDataView.columnSelfTime);
                                    totals[name] = (totals.TryGetValue(name, out var v) ? v : 0) + self;
                                }
                                children.Clear(); view.GetItemChildren(id, children); foreach (var c in children) stack.Push(c);
                            }
                        }
                    }
                }
                var result = new
                {
                    raw, frames, firstFrame = first, lastFrame = last,
                    frameMs = frameMs.Count > 0 ? new { mean = frameMs.Average(), p95 = frameMs.OrderBy(x => x).ElementAt((int)(frameMs.Count * .95)), max = frameMs.Max() } : null,
                    threads = threads.ToDictionary(kv => kv.Key, kv => kv.Value.OrderByDescending(x => x.Value).Take(40).Select(x => new { marker = x.Key, msPerFrame = Math.Round(x.Value / Math.Max(1, frames), 3) }))
                };
                File.WriteAllText(output, JsonConvert.SerializeObject(result, Formatting.Indented));
                UnityEngine.Debug.Log("PROFILE_DUMP " + frames + " frames -> " + output);
            }
            catch (Exception e) { UnityEngine.Debug.LogException(e); code = 1; }
            EditorApplication.Exit(code);
        }
    }
}
