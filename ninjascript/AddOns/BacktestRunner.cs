// No-click NT8 backtest runner (task t-b2d143).
//
// Watches ninjascript/jobs/ (this repo, not copied into NT8's folder - the
// AddOn reads it directly off disk) for *.job files. Each job = one
// backtest: which strategy, which instrument, date range, optional property
// overrides. Runs it via StrategyBase.RunBacktest() (public API, confirmed
// via reflection - see docs/research/nt8-automation-notes.md) and writes a
// result + trade list back to ninjascript/results/. No Strategy Analyzer
// clicks needed once this compiles and NT8 is left running.
//
// Job file format (plain key=value lines, NOT json - avoids depending on a
// json library that may not be in NinjaScript's default reference set):
//   strategy=Orb
//   instrument=ES 12-26
//   bars_minutes=1
//   from=2016-09-01
//   to=2024-12-31
//   prop.Slippage=0
//   prop.BarsRequiredToTrade=1
//   prop.IncludeCommission=true
// Any "prop.X=Y" line sets strategy property X via reflection (works for
// any public settable property on the strategy, including its own
// [NinjaScriptProperty] params like RangeStartTime).
//
// This class is ONLY the watcher (frozen at NT8 startup - changing it
// needs an NT8 restart). All job logic lives in BacktestJob.cs, which is
// picked up fresh after every recompile, no restart needed.

#region Using declarations
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Strategies;
#endregion

namespace NinjaTrader.NinjaScript.AddOns
{
    public class BacktestRunner : AddOnBase
    {
        // Fixed to this machine's repo checkout - single-user project, not
        // meant to be portable.
        private const string RepoRoot = @"C:\Users\User\Desktop\ninjatrader-agent";
        private string jobsDir;
        private string doneDir;
        private string resultsDir;
        private FileSystemWatcher watcher;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "BacktestRunner";
                Description = "Watches ninjascript/jobs for backtest job files, runs them, writes results.";
            }
            else if (State == State.Configure)
            {
                jobsDir = Path.Combine(RepoRoot, "ninjascript", "jobs");
                doneDir = Path.Combine(jobsDir, "done");
                resultsDir = Path.Combine(RepoRoot, "ninjascript", "results");
                Directory.CreateDirectory(jobsDir);
                Directory.CreateDirectory(doneDir);
                Directory.CreateDirectory(resultsDir);

                // Pick up any jobs dropped while NT8 wasn't running.
                foreach (var f in Directory.GetFiles(jobsDir, "*.job"))
                    ProcessJobSafe(f);

                watcher = new FileSystemWatcher(jobsDir, "*.job");
                watcher.Created += (s, e) => ProcessJobSafe(e.FullPath);
                watcher.EnableRaisingEvents = true;
            }
            else if (State == State.Terminated)
            {
                if (watcher != null)
                {
                    watcher.EnableRaisingEvents = false;
                    watcher.Dispose();
                    watcher = null;
                }
            }
        }

        // Thin on purpose - see BacktestJob.cs. Only this watcher is frozen
        // at NT8 startup; all job logic is looked up fresh per job.
        private void ProcessJobSafe(string path)
        {
            try
            {
                Type jobType = FindNewestType("NinjaTrader.NinjaScript.AddOns.BacktestJob");
                if (jobType == null)
                    throw new Exception("BacktestJob type not found - not compiled?");
                jobType.GetMethod("Process", BindingFlags.Public | BindingFlags.Static)
                    .Invoke(null, new object[] { path, doneDir, resultsDir });
            }
            catch (Exception ex)
            {
                try
                {
                    File.WriteAllText(Path.Combine(resultsDir, Path.GetFileNameWithoutExtension(path) + ".result.txt"),
                        "ERROR\n" + ex);
                }
                catch { }
            }
        }

        // Every recompile loads a NEW custom assembly into the same AppDomain
        // without unloading old ones - last-loaded match = newest build.
        private static Type FindNewestType(string fullName)
        {
            Type found = null;
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                Type t;
                try { t = asm.GetType(fullName); }
                catch { continue; }
                if (t != null)
                    found = t;
            }
            return found;
        }
    }
}
