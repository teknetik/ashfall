using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using NUnit.Framework;
using UnityEngine;
namespace AthenHill.Tests
{
    /// The Steady Hands bench job as a model (20 Nov 2026): the step graph of art/steady_hands_bench_20261120/data/steps.json,
    /// faults and recoveries, leaving and resuming, quality, and the blob the crafting system saves. No scene.
    public class AssemblyJobTests
    {
        static string Repo => Path.GetFullPath(Path.Combine(Application.dataPath, "../../.."));
        static AssemblyRecipeData Table() => AssemblyRecipeData.FromJson(File.ReadAllText(Path.Combine(Repo, "art/steady_hands_bench_20261120/data/steps.json")));

        /// A small job with every feature: two stages, a free step, an optional step, a recovery that replaces an action,
        /// a deferred recovery in the next stage, a step that spends an input, and a leave step.
        static AssemblyRecipeData Small()
        {
            AssemblyActionDef A(string key, params AssemblyFaultDef[] faults) => new AssemblyActionDef { key = key, verb = AssemblyVerbKind.Seat, faults = faults };
            var data = new AssemblyRecipeData
            {
                id = "small",
                stages = new[]
                {
                    new AssemblyStageDef { id = "a", steps = new[]
                    {
                        new AssemblyStepDef { id = "a.one", actions = new[] { A("x"), A("y") } },
                        new AssemblyStepDef { id = "a.two", requires = new[] { "a.one" }, free = true, spends = new[] { "scrap_alloy" },
                            actions = new[] { A("l"), A("r", new AssemblyFaultDef { kind = "stripped", penalty = .1f, after = 2, recovery = "a.two.r" }, new AssemblyFaultDef { kind = "frayed", penalty = .05f, recovery = "b.fix" }) } },
                        new AssemblyStepDef { id = "a.two.r", recovery = true, replaces = new[] { "a.two:r" }, actions = new[] { A("pliers") } },
                        new AssemblyStepDef { id = "a.opt", optional = true, actions = new[] { A("o") } },
                    } },
                    new AssemblyStageDef { id = "b", steps = new[]
                    {
                        new AssemblyStepDef { id = "b.fix", recovery = true, actions = new[] { A("restrip") } },
                        new AssemblyStepDef { id = "b.one", requires = new[] { "b.fix" }, actions = new[] { A("z") } },
                        new AssemblyStepDef { id = "b.leave", requires = new[] { "b.one" }, onLeave = true, actions = new[] { A("holster") } },
                    } },
                },
            };
            data.Normalise();
            Assert.That(data.Validate(), Is.Empty);
            return data;
        }

        static void FinishByFirstOpen(AssemblyJob job, float precision = 1)
        {
            for (int guard = 0; guard < 3000 && !job.Complete; guard++)
            {
                var open = job.OpenActions.ToList();
                if (open.Count > 0) { Assert.That(job.CompleteAction(open[0].step.id, open[0].action.key, precision).ok, Is.True, open[0].Id); continue; }
                var empty = job.OpenSteps.FirstOrDefault(s => s.actions.Length == 0);
                Assert.That(empty, Is.Not.Null, "stuck at stage " + job.StageIndex);
                job.CompleteStep(empty.id, precision);
            }
            Assert.That(job.Complete, Is.True);
        }

        [Test] public void TheStepTableIsSoundAndKeepsTheDesignsStepIds()
        {
            var data = Table();
            Assert.That(data.Validate(), Is.Empty);
            Assert.That(data.id, Is.EqualTo("assembly_grip_stabilised_pistol")); Assert.That(data.craftRecipeId, Is.EqualTo("recipe_grip_stabilised_pistol"));
            var rows = data.stages.Select(s => s.steps.Count(st => !st.recovery)).ToArray();
            Assert.That(rows, Is.EqualTo(new[] { 6, 10, 11, 16, 6, 9, 5, 4 }), "DESIGN.md section 7: 67 step rows in 8 stages");
            foreach (var id in new[] { "s0.pistol", "s0.card_before", "s0.cell", "s1.clamp", "s1.screw_b", "s1.inspect", "s2.swap", "s2.winding", "s3.bath", "s3.strap", "s4.press", "s5.damp", "s6.slide", "s6.cell", "s7.card_after", "s7.leave" })
                Assert.That(data.Steps.Any(s => s.id == id), Is.True, id);
            foreach (var stage in data.stages) foreach (var step in stage.steps) Assert.That(step.id, Does.StartWith(stage.id + "."), step.id);
            // the slice: stages 0, 1, 6 and 7 have work to do by hand
            foreach (var id in new[] { "s0", "s1", "s6", "s7" }) Assert.That(data.stages.Single(s => s.id == id).steps.All(st => st.actions.Length > 0), Is.True, id);
            Assert.That(data.Steps.Single(s => s.id == "s7.leave").onLeave, Is.True);
            Assert.That(data.byproducts.Single().itemId, Is.EqualTo("copper_filament"));
        }

        [Test] public void NothingIsAvailableBeforeItsPrerequisites()
        {
            foreach (var data in new[] { Small(), Table() })
            {
                var job = new AssemblyJob(data); var stageOf = new Dictionary<string, int>();
                for (int i = 0; i < data.stages.Length; i++) foreach (var s in data.stages[i].steps) stageOf[s.id] = i;
                var rng = new System.Random(7);
                for (int guard = 0; guard < 3000 && !job.Complete; guard++)
                {
                    foreach (var step in data.Steps)
                    {
                        var state = job.State(step.id);
                        if (state != AssemblyStepState.Available && state != AssemblyStepState.Active) continue;
                        Assert.That(stageOf[step.id], Is.LessThanOrEqualTo(job.StageIndex), step.id + " is open ahead of its stage");
                        foreach (var r in step.requires) Assert.That(job.State(r), Is.EqualTo(AssemblyStepState.Done).Or.EqualTo(AssemblyStepState.Dormant), step.id + " is open before " + r);
                    }
                    // a locked step's action is refused
                    var locked = data.Steps.FirstOrDefault(s => job.State(s.id) == AssemblyStepState.Locked && s.actions.Length > 0);
                    if (locked != null) Assert.That(job.CompleteAction(locked.id, locked.actions[0].key, 1).ok, Is.False, locked.id);
                    var open = job.OpenActions.ToList();
                    if (open.Count > 0) { var pick = open[rng.Next(open.Count)]; foreach (var k in pick.action.after) Assert.That(job.ActionDone(pick.step.id, k), Is.True); job.CompleteAction(pick.step.id, pick.action.key, 1); }
                    else job.CompleteStep(job.OpenSteps.First(s => s.actions.Length == 0).id);
                }
                Assert.That(job.Complete, Is.True, data.id);
            }
        }

        [Test] public void EveryStepIsReachableAndTheJobCompletesInAnyOrder()
        {
            var data = Table();
            for (int seed = 0; seed < 12; seed++)
            {
                var job = new AssemblyJob(data); var rng = new System.Random(seed); var done = new HashSet<string>();
                for (int guard = 0; guard < 3000 && !job.Complete; guard++)
                {
                    var open = job.OpenActions.ToList(); var empty = job.OpenSteps.Where(s => s.actions.Length == 0).ToList();
                    Assert.That(open.Count + empty.Count, Is.GreaterThan(0), $"seed {seed}: stuck at stage {job.StageIndex}");
                    int pick = rng.Next(open.Count + empty.Count);
                    if (pick < open.Count) { var p = job.CompleteAction(open[pick].step.id, open[pick].action.key, 1); if (p.stepDone) done.Add(open[pick].step.id); }
                    else { job.CompleteStep(empty[pick - open.Count].id); done.Add(empty[pick - open.Count].id); }
                }
                Assert.That(job.Complete, Is.True);
                foreach (var step in data.Steps.Where(s => !s.recovery && !s.optional)) Assert.That(job.IsDone(step.id), Is.True, step.id);
                Assert.That(job.Score, Is.EqualTo(1).Within(1e-4f)); Assert.That(job.Quality, Is.EqualTo(CraftQuality.Fine));
                foreach (var step in data.Steps.Where(s => s.recovery)) Assert.That(job.State(step.id), Is.EqualTo(AssemblyStepState.Dormant), step.id + " ran without its fault");
            }
        }

        [Test] public void EveryFaultCostsQualityAndEveryRecoveryIsNeededThenClears()
        {
            foreach (var data in new[] { Small(), Table() })
                foreach (var step in data.Steps) foreach (var a in step.actions) foreach (var f in a.faults)
                {
                    var job = new AssemblyJob(data);
                    for (int guard = 0; guard < 3000 && job.State(step.id) != AssemblyStepState.Available && job.State(step.id) != AssemblyStepState.Active; guard++)
                    {
                        var open = job.OpenActions.ToList();
                        if (open.Count > 0) { job.CompleteAction(open[0].step.id, open[0].action.key, 1); continue; }
                        var empty = job.OpenSteps.FirstOrDefault(s => s.actions.Length == 0); if (empty == null) break; job.CompleteStep(empty.id);
                    }
                    // a mistake inside a recovery step can only be made once another mistake has started that recovery: not reached on a clean run
                    if (job.State(step.id) != AssemblyStepState.Available && job.State(step.id) != AssemblyStepState.Active) { Assert.That(step.recovery, Is.True, step.id + " is never reached"); continue; }
                    string where = $"{data.id} {step.id}:{a.key} {f.kind}";
                    float before = job.Score; AssemblyFaultResult last = default;
                    for (int i = 0; i < Mathf.Max(1, f.after); i++)
                    {
                        if (i < f.after - 1 && !string.IsNullOrEmpty(f.recovery)) Assert.That(job.State(f.recovery), Is.EqualTo(AssemblyStepState.Dormant), where + ": the recovery starts too soon");
                        last = job.Fault(step.id, a.key, f.kind);
                        Assert.That(last.ok, Is.True, where); Assert.That(last.penalty, Is.EqualTo(f.penalty).Within(1e-5f), where); Assert.That(last.first, Is.EqualTo(i == 0), where);
                    }
                    Assert.That(job.FaultsOn(step.id, f.kind), Is.EqualTo(Mathf.Max(1, f.after)), where);
                    Assert.That(job.Faults, Is.EqualTo(Mathf.Max(1, f.after)));
                    if (f.penalty > 0 && job.ActionsDone(step.id) > 0) Assert.That(job.Score, Is.LessThan(before), where + ": a fault must cost quality");
                    Assert.That(job.Complete, Is.False, where + ": a fault never ends the job");
                    if (string.IsNullOrEmpty(f.recovery)) { Assert.That(last.recoveryStarted, Is.Null, where); FinishByFirstOpen(job); continue; }
                    Assert.That(last.recoveryStarted, Is.EqualTo(f.recovery), where);
                    var recovery = data.Steps.Single(s => s.id == f.recovery);
                    Assert.That(job.State(f.recovery), Is.Not.EqualTo(AssemblyStepState.Dormant), where);
                    foreach (var rep in recovery.replaces) { var parts = rep.Split(':'); if (!job.ActionDone(parts[0], parts[1])) Assert.That(job.Blocked(parts[0], parts[1]), Is.EqualTo("recovery:" + f.recovery), where + ": the botched action must wait for its recovery"); }
                    // a second fault does not start it twice
                    Assert.That(job.Fault(step.id, a.key, f.kind).recoveryStarted, Is.Null, where);
                    FinishByFirstOpen(job);
                    Assert.That(job.IsDone(f.recovery), Is.True, where + ": the recovery was needed to finish");
                    foreach (var rep in recovery.replaces) { var parts = rep.Split(':'); Assert.That(job.ActionDone(parts[0], parts[1]), Is.True, where); }
                    Assert.That(job.Score, Is.LessThan(1), where);
                }
        }

        [Test] public void ARecoveryStandsInForWhatItReplacesAndADeferredOneWaitsForItsStage()
        {
            var data = Small(); var job = new AssemblyJob(data);
            job.CompleteAction("a.one", "x", 1); job.CompleteAction("a.one", "y", 1);
            job.CompleteAction("a.two", "l", .8f);
            job.Fault("a.two", "r", "stripped"); Assert.That(job.State("a.two.r"), Is.EqualTo(AssemblyStepState.Dormant));
            job.Fault("a.two", "r", "stripped"); Assert.That(job.State("a.two.r"), Is.EqualTo(AssemblyStepState.Available));
            Assert.That(job.CompleteAction("a.two", "r", 1).ok, Is.False, "the stripped screw cannot be done the normal way");
            var p = job.CompleteAction("a.two.r", "pliers", .9f);
            Assert.That(p.stepDone, Is.True); Assert.That(job.IsDone("a.two"), Is.True, "the recovery finished the step it stood in for");
            Assert.That(job.ActionReplaced("a.two", "r"), Is.True);
            Assert.That(job.DoneActions.Select(x => x.Id), Does.Not.Contain("a.two:r"), "a replaced action's own effects never happened");
            Assert.That(job.DoneActions.Select(x => x.Id), Does.Contain("a.two.r:pliers"));
            // a fault whose recovery sits in the next stage
            job = new AssemblyJob(data);
            job.CompleteAction("a.one", "x", 1); job.CompleteAction("a.one", "y", 1);
            Assert.That(job.Fault("a.two", "r", "frayed").recoveryStarted, Is.EqualTo("b.fix"));
            Assert.That(job.State("b.fix"), Is.EqualTo(AssemblyStepState.Locked), "it waits for its own stage");
            job.CompleteAction("a.two", "l", 1); job.CompleteAction("a.two", "r", 1);
            Assert.That(job.StageIndex, Is.EqualTo(1)); Assert.That(job.State("b.fix"), Is.EqualTo(AssemblyStepState.Available)); Assert.That(job.State("b.one"), Is.EqualTo(AssemblyStepState.Locked));
            job.CompleteAction("b.fix", "restrip", 1); Assert.That(job.State("b.one"), Is.EqualTo(AssemblyStepState.Available));
        }

        [Test] public void LeavingResetsAStepInProgressAndKeepsEverythingElse()
        {
            var data = Small(); var job = new AssemblyJob(data);
            job.CompleteAction("a.one", "x", 1); job.CompleteAction("a.one", "y", .6f);
            job.CompleteAction("a.two", "l", 1); job.Fault("a.two", "r", "frayed");
            Assert.That(job.State("a.two"), Is.EqualTo(AssemblyStepState.Active));
            job.Leave();
            Assert.That(job.IsDone("a.one"), Is.True); Assert.That(job.State("a.two"), Is.EqualTo(AssemblyStepState.Available));
            Assert.That(job.ActionDone("a.two", "l"), Is.False, "a step in progress resets (DESIGN.md rule 6)");
            Assert.That(job.FaultsOn("a.two", "frayed"), Is.EqualTo(1), "leaving is not a way to wash a fault off");
            Assert.That(job.State("b.fix"), Is.EqualTo(AssemblyStepState.Locked), "the recovery it started is still owed");
            // what a finished recovery stood in for is not undone by leaving
            job = new AssemblyJob(data);
            job.CompleteAction("a.one", "x", 1); job.CompleteAction("a.one", "y", 1);
            job.Fault("a.two", "r", "stripped"); job.Fault("a.two", "r", "stripped"); job.CompleteAction("a.two.r", "pliers", 1);
            Assert.That(job.State("a.two"), Is.EqualTo(AssemblyStepState.Active));
            job.Leave();
            Assert.That(job.ActionDone("a.two", "r"), Is.True); Assert.That(job.ActionReplaced("a.two", "r"), Is.True);
            job.CompleteAction("a.two", "l", 1); Assert.That(job.IsDone("a.two"), Is.True);
        }

        [Test] public void TheJobCanBeLeftAndResumedAtAnyPoint()
        {
            foreach (var data in new[] { Small(), Table() })
            {
                var job = new AssemblyJob(data); var rng = new System.Random(3); int points = 0;
                for (int guard = 0; guard < 3000 && !job.Complete; guard++)
                {
                    var open = job.OpenActions.ToList();
                    if (open.Count > 0) { var pick = open[rng.Next(open.Count)]; job.CompleteAction(pick.step.id, pick.action.key, .5f + .5f * (float)rng.NextDouble()); if (rng.Next(9) == 0 && pick.action.faults.Length > 0) job.Fault(pick.step.id, pick.action.key, pick.action.faults[0].kind); }
                    else job.CompleteStep(job.OpenSteps.First(s => s.actions.Length == 0).id, .9f);
                    job.Seconds += 7; job.Notes["card:s0.card_before"] = "0.01,0.02;" + guard;
                    // save here, load, and compare with stepping back from the same point
                    var resumed = AssemblyJob.FromBlob(data, job.ToBlob());
                    var left = AssemblyJob.FromBlob(data, job.ToBlob()); left.Leave();
                    foreach (var step in data.Steps)
                    {
                        Assert.That(resumed.State(step.id), Is.EqualTo(left.State(step.id)), step.id);
                        Assert.That(resumed.FaultsOn(step.id), Is.EqualTo(job.FaultsOn(step.id)), step.id);
                        if (job.IsDone(step.id)) Assert.That(resumed.IsDone(step.id), Is.True, step.id + " was finished and must stay finished");
                        Assert.That(resumed.State(step.id), Is.Not.EqualTo(AssemblyStepState.Active), step.id + ": a step in progress resets on returning");
                    }
                    Assert.That(resumed.Seconds, Is.EqualTo(job.Seconds).Within(1e-3f)); Assert.That(resumed.Penalty, Is.EqualTo(job.Penalty).Within(1e-5f));
                    Assert.That(resumed.Notes["card:s0.card_before"], Is.EqualTo(job.Notes["card:s0.card_before"]));
                    Assert.That(resumed.StageIndex, Is.LessThanOrEqualTo(job.StageIndex));
                    // and the resumed job can still be finished (checked at a spread of points; it is the slow part)
                    if (guard % (data.Steps.Count() > 20 ? 9 : 2) == 0) { FinishByFirstOpen(resumed); points++; }
                }
                Assert.That(job.Complete, Is.True); Assert.That(points, Is.GreaterThan(1));
            }
        }

        [Test] public void QualityIsTheWeightedMeanOfPrecisionLessCappedFaultPenalties()
        {
            var data = Small(); data.quality = new AssemblyQualityRules { rough = .55f, fine = .85f, faultPenalty = .02f, maxPenalty = .2f, replacedPrecision = .35f };
            data.stages[0].steps[0].actions[0].weight = 3; data.stages[0].steps[0].actions[1].weight = 1;
            var job = new AssemblyJob(data);
            Assert.That(job.Score, Is.EqualTo(1), "nothing done yet");
            job.CompleteAction("a.one", "x", 1); job.CompleteAction("a.one", "y", .2f);
            Assert.That(job.Score, Is.EqualTo((3 * 1 + 1 * .2f) / 4).Within(1e-5f));
            job.Fault("a.one", "x", "anything"); Assert.That(job.Score, Is.EqualTo(.8f - .02f).Within(1e-5f), "a fault without a definition costs the default");
            for (int i = 0; i < 30; i++) job.Fault("a.one", "x", "anything");
            Assert.That(job.Score, Is.EqualTo(.8f - .2f).Within(1e-5f), "penalties are capped");
            Assert.That(AssemblyJob.QualityFor(.549f, data.quality), Is.EqualTo(CraftQuality.Rough));
            Assert.That(AssemblyJob.QualityFor(.55f, data.quality), Is.EqualTo(CraftQuality.Standard));
            Assert.That(AssemblyJob.QualityFor(.85f, data.quality), Is.EqualTo(CraftQuality.Standard));
            Assert.That(AssemblyJob.QualityFor(.851f, data.quality), Is.EqualTo(CraftQuality.Fine));
            // time never lowers quality; an optional step counts only when done
            var a = new AssemblyJob(Small()); var b = new AssemblyJob(Small());
            foreach (var j in new[] { a, b }) { j.CompleteAction("a.one", "x", .9f); j.CompleteAction("a.one", "y", .9f); }
            b.Seconds = 5000; Assert.That(b.Score, Is.EqualTo(a.Score));
            a.CompleteAction("a.opt", "o", .1f); Assert.That(a.Score, Is.LessThan(b.Score));
            // a perfect run of the real table is Fine, a clumsy one Rough
            var fine = new AssemblyJob(Table()); FinishByFirstOpen(fine, 1); Assert.That(fine.Quality, Is.EqualTo(CraftQuality.Fine));
            var rough = new AssemblyJob(Table()); FinishByFirstOpen(rough, .5f); Assert.That(rough.Quality, Is.EqualTo(CraftQuality.Rough));
            var standard = new AssemblyJob(Table()); FinishByFirstOpen(standard, .7f); Assert.That(standard.Quality, Is.EqualTo(CraftQuality.Standard));
        }

        [Test] public void TheBlobRoundTrips()
        {
            var data = Small(); var job = new AssemblyJob(data);
            job.CompleteAction("a.one", "x", .9f); job.CompleteAction("a.one", "y", .4f);
            job.Fault("a.two", "r", "stripped"); job.Fault("a.two", "r", "stripped"); job.Fault("a.two", "l", "odd");
            job.CompleteAction("a.two.r", "pliers", .7f); job.CompleteAction("a.two", "l", .6f);
            job.Seconds = 312.5f; job.Notes["k"] = "v;1,2";
            string blob = job.ToBlob();
            Assert.That(blob, Does.Contain("\"v\":2")); Assert.That(blob, Does.Contain("\"recipe\":\"small\""));
            var back = AssemblyJob.FromBlob(data, blob);
            foreach (var step in data.Steps) { Assert.That(back.State(step.id), Is.EqualTo(job.State(step.id)), step.id); Assert.That(back.FaultsOn(step.id), Is.EqualTo(job.FaultsOn(step.id)), step.id); }
            Assert.That(back.ActionReplaced("a.two", "r"), Is.True); Assert.That(back.Score, Is.EqualTo(job.Score).Within(1e-5f)); Assert.That(back.Faults, Is.EqualTo(3)); Assert.That(back.Penalty, Is.EqualTo(job.Penalty).Within(1e-5f));
            Assert.That(back.Seconds, Is.EqualTo(312.5f)); Assert.That(back.Notes["k"], Is.EqualTo("v;1,2"));
            Assert.That(back.ToBlob(), Is.EqualTo(blob), "saving again gives the same blob");
            Assert.That(back.Fault("a.two", "l", "odd").first, Is.False, "which fault kinds were already seen is kept (Brann speaks once)");
            Assert.That(back.SpentInputs(), Is.EqualTo(new[] { "scrap_alloy" }));
            // a finished step that has nothing to do (a design row not yet built) is kept too
            var table = Table(); var granted = new AssemblyJob(table); granted.Grant(new[] { "s0", "s1", "s2", "s3", "s4", "s5" }, .9f);
            var again = AssemblyJob.FromBlob(table, granted.ToBlob());
            Assert.That(again.StageIndex, Is.EqualTo(6)); Assert.That(again.IsDone("s2.swap"), Is.True); Assert.That(again.Score, Is.EqualTo(granted.Score).Within(1e-5f));
        }

        [Test] public void OlderAndBrokenBlobsLoadSafely()
        {
            var data = Small();
            foreach (var bad in new[] { null, "", "   ", "not json", "{", "[]", "{\"v\":2,\"recipe\":\"another_recipe\",\"steps\":[{\"id\":\"a.one\",\"state\":3,\"done\":[\"x\",\"y\"]}]}", "{\"v\":2,\"steps\":null}" })
            {
                AssemblyJob job = null;
                Assert.DoesNotThrow(() => job = AssemblyJob.FromBlob(data, bad), bad ?? "null");
                Assert.That(job.StageIndex, Is.EqualTo(0), bad ?? "null"); Assert.That(job.State("a.one"), Is.EqualTo(AssemblyStepState.Available), bad ?? "null");
            }
            // layout 1: finished step ids only
            var old = AssemblyJob.FromBlob(data, "{\"v\":1,\"recipe\":\"small\",\"seconds\":40,\"done\":[\"a.one\",\"gone.step\"],\"faults\":2}");
            Assert.That(old.IsDone("a.one"), Is.True); Assert.That(old.State("a.two"), Is.EqualTo(AssemblyStepState.Available)); Assert.That(old.Seconds, Is.EqualTo(40));
            Assert.That(old.Faults, Is.EqualTo(2)); Assert.That(old.Penalty, Is.EqualTo(2 * data.quality.faultPenalty).Within(1e-5f));
            FinishByFirstOpen(old);
            // steps and actions that no longer exist are dropped; a half-done step is reset; a step claimed done without its actions is not done
            var odd = AssemblyJob.FromBlob(data, "{\"v\":2,\"recipe\":\"small\",\"steps\":[{\"id\":\"a.one\",\"state\":3,\"done\":[\"x\",\"y\",\"zz\"],\"precision\":[0.5]},{\"id\":\"nope\",\"state\":3,\"done\":[\"q\"]},{\"id\":\"a.two\",\"state\":3,\"done\":[\"l\"],\"faultKinds\":[\"stripped\"],\"faultCounts\":[2]},{\"id\":\"a.two.r\",\"state\":1}]}");
            Assert.That(odd.IsDone("a.one"), Is.True); Assert.That(odd.State("a.two"), Is.EqualTo(AssemblyStepState.Available)); Assert.That(odd.ActionDone("a.two", "l"), Is.False);
            Assert.That(odd.FaultsOn("a.two", "stripped"), Is.EqualTo(2)); Assert.That(odd.State("a.two.r"), Is.EqualTo(AssemblyStepState.Available), "a recovery that was owed is still owed");
            FinishByFirstOpen(odd);
            // a blob from a longer table (steps this build does not have) still opens
            var real = new AssemblyJob(Table()); FinishByFirstOpen(real);
            Assert.DoesNotThrow(() => AssemblyJob.FromBlob(data, real.ToBlob().Replace("assembly_grip_stabilised_pistol", "small")));
        }

        [Test] public void GrantSpentInputsAndTheLeaveStep()
        {
            var data = Table(); var job = new AssemblyJob(data);
            Assert.That(job.LeaveStep, Is.Null);
            Assert.That(job.Grant(new[] { "s0", "s1" }, .9f).Count, Is.EqualTo(16)); Assert.That(job.StageIndex, Is.EqualTo(2));
            Assert.That(job.SpentInputs(), Is.Empty);
            job.Grant(new[] { "s2", "s3", "s4", "s5" }, .9f);
            Assert.That(job.StageIndex, Is.EqualTo(6));
            Assert.That(job.SpentInputs(), Is.EqualTo(new[] { "component:servo", "nanite:tier1", "scrap_alloy" }), "what is cut, opened or fused is lost on abandoning");
            job.Grant(new[] { "s6" }, .9f);
            job.CompleteAction("s7.shake", "shake", 1); Assert.That(job.LeaveStep, Is.Null, "the card is still to shoot");
            job.CompleteAction("s7.card_after", "pulses", 1);
            Assert.That(job.LeaveStep?.id, Is.EqualTo("s7.leave"), "stepping back now finishes the job");
            job.CompleteStep("s7.leave"); Assert.That(job.Complete, Is.True); Assert.That(job.LeaveStep, Is.Null);
        }
    }
}
