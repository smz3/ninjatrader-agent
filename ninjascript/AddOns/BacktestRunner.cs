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
// First build of this kind of thing - untested against NT8's actual runtime
// behavior (no headless compiler here to check it). Expect compile/runtime
// errors on the first few tries; paste them back and we fix forward, same
// as Orb.cs.

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

        private void ProcessJobSafe(string path)
        {
            string jobId = Path.GetFileNameWithoutExtension(path);
            try
            {
                // File may still be mid-write when Created fires.
                string text = ReadFileWithRetry(path);
                RunJob(jobId, text);
            }
            catch (Exception ex)
            {
                WriteResult(jobId, "ERROR\n" + ex);
            }
            finally
            {
                try
                {
                    string dst = Path.Combine(doneDir, Path.GetFileName(path));
                    if (File.Exists(dst))
                        File.Delete(dst);
                    if (File.Exists(path))
                        File.Move(path, dst);
                }
                catch
                {
                    // Leave it in place if the move itself fails - not fatal.
                }
            }
        }

        private static string ReadFileWithRetry(string path)
        {
            Exception last = null;
            for (int i = 0; i < 10; i++)
            {
                try
                {
                    return File.ReadAllText(path);
                }
                catch (IOException ex)
                {
                    last = ex;
                    System.Threading.Thread.Sleep(200);
                }
            }
            throw last ?? new IOException("Could not read " + path);
        }

        private void RunJob(string jobId, string text)
        {
            var lines = text.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);
            var fields = new Dictionary<string, string>();
            var props = new List<KeyValuePair<string, string>>();
            foreach (var raw in lines)
            {
                var line = raw.Trim();
                if (line.Length == 0 || line.StartsWith("#"))
                    continue;
                int eq = line.IndexOf('=');
                if (eq < 0)
                    continue;
                string key = line.Substring(0, eq).Trim();
                string val = line.Substring(eq + 1).Trim();
                if (key.StartsWith("prop."))
                    props.Add(new KeyValuePair<string, string>(key.Substring(5), val));
                else
                    fields[key] = val;
            }

            string strategyName = Require(fields, "strategy");
            string instrumentName = Require(fields, "instrument");
            int barsMinutes = fields.ContainsKey("bars_minutes") ? int.Parse(fields["bars_minutes"]) : 1;
            DateTime from = DateTime.Parse(Require(fields, "from"), CultureInfo.InvariantCulture);
            DateTime to = DateTime.Parse(Require(fields, "to"), CultureInfo.InvariantCulture);

            Type strategyType = FindStrategyType(strategyName);
            if (strategyType == null)
                throw new Exception("Strategy type not found (not compiled yet?): " + strategyName);

            Instrument instrument = Instrument.GetInstrument(instrumentName);
            if (instrument == null)
                throw new Exception("Instrument not found in NT8: " + instrumentName);

            var strategyObj = (StrategyBase)Activator.CreateInstance(strategyType);
            strategyObj.Instrument = instrument;
            strategyObj.BarsPeriod = new BarsPeriod { BarsPeriodType = BarsPeriodType.Minute, Value = barsMinutes };
            strategyObj.From = from;
            strategyObj.To = to;

            foreach (var kv in props)
                SetProperty(strategyObj, strategyType, kv.Key, kv.Value);

            strategyObj.RunBacktest();

            WriteResult(jobId, FormatPerformance(strategyObj));
        }

        private static void SetProperty(object target, Type type, string name, string rawValue)
        {
            PropertyInfo pi = type.GetProperty(name, BindingFlags.Public | BindingFlags.Instance)
                ?? typeof(StrategyBase).GetProperty(name, BindingFlags.Public | BindingFlags.Instance);
            if (pi == null || !pi.CanWrite)
                throw new Exception("No writable property '" + name + "' on " + type.Name);

            object value;
            if (pi.PropertyType.IsEnum)
                value = Enum.Parse(pi.PropertyType, rawValue, true);
            else if (pi.PropertyType == typeof(bool))
                value = bool.Parse(rawValue);
            else if (pi.PropertyType == typeof(DateTime))
                value = DateTime.Parse(rawValue, CultureInfo.InvariantCulture);
            else
                value = Convert.ChangeType(rawValue, pi.PropertyType, CultureInfo.InvariantCulture);

            pi.SetValue(target, value, null);
        }

        private static Type FindStrategyType(string shortName)
        {
            string fullName = "NinjaTrader.NinjaScript.Strategies." + shortName;
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                Type t;
                try { t = asm.GetType(fullName); }
                catch { continue; }
                if (t != null)
                    return t;
            }
            return null;
        }

        private static string Require(Dictionary<string, string> fields, string key)
        {
            string v;
            if (!fields.TryGetValue(key, out v) || string.IsNullOrEmpty(v))
                throw new Exception("Missing required job field: " + key);
            return v;
        }

        private static string FormatPerformance(StrategyBase strategy)
        {
            var perf = strategy.SystemPerformance;
            var sb = new StringBuilder();
            sb.AppendLine("OK");
            int totalTrades = perf.AllTrades.Count;
            double percentProfitable = totalTrades > 0 ? 100.0 * perf.AllTrades.WinningTrades.Count / totalTrades : 0.0;
            sb.AppendLine("NetProfit=" + perf.AllTrades.TradesPerformance.NetProfit.ToString(CultureInfo.InvariantCulture));
            sb.AppendLine("TotalTrades=" + totalTrades.ToString(CultureInfo.InvariantCulture));
            sb.AppendLine("PercentProfitable=" + percentProfitable.ToString(CultureInfo.InvariantCulture));
            sb.AppendLine("ProfitFactor=" + perf.AllTrades.TradesPerformance.ProfitFactor.ToString(CultureInfo.InvariantCulture));
            sb.AppendLine("AvgTrade=" + perf.AllTrades.TradesPerformance.Currency.AverageProfit.ToString(CultureInfo.InvariantCulture));
            sb.AppendLine("MaxDrawdown=" + perf.AllTrades.TradesPerformance.Currency.Drawdown.ToString(CultureInfo.InvariantCulture));
            sb.AppendLine();
            sb.AppendLine("# entryTime,exitTime,entryPrice,exitPrice,qty,pnl");
            foreach (Trade trade in perf.AllTrades)
            {
                sb.AppendLine(string.Join(",", new[]
                {
                    trade.Entry.Time.ToString("o", CultureInfo.InvariantCulture),
                    trade.Exit.Time.ToString("o", CultureInfo.InvariantCulture),
                    trade.Entry.Price.ToString(CultureInfo.InvariantCulture),
                    trade.Exit.Price.ToString(CultureInfo.InvariantCulture),
                    trade.Quantity.ToString(CultureInfo.InvariantCulture),
                    trade.ProfitCurrency.ToString(CultureInfo.InvariantCulture),
                }));
            }
            return sb.ToString();
        }

        private void WriteResult(string jobId, string content)
        {
            string path = Path.Combine(resultsDir, jobId + ".result.txt");
            File.WriteAllText(path, content);
        }
    }
}
