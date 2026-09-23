// Backtest job logic for the BacktestRunner AddOn (task t-b2d143).
//
// Lives apart from BacktestRunner.cs on purpose: NT8 only instantiates
// AddOns at startup, so any logic inside the AddOn class needs an NT8
// restart (= re-login) to change. The AddOn is now a thin file watcher that,
// per job, looks up the NEWEST loaded copy of this class and calls Process()
// - so editing this file only needs a recompile (deploy.ps1 with the
// NinjaScript Editor open), never a restart. Job file format: see
// BacktestRunner.cs.

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
    public static class BacktestJob
    {
        public static void Process(string path, string doneDir, string resultsDir)
        {
            string jobId = Path.GetFileNameWithoutExtension(path);
            try
            {
                // File may still be mid-write when Created fires.
                string text = ReadFileWithRetry(path);
                RunJob(resultsDir, jobId, text);
            }
            catch (Exception ex)
            {
                WriteResult(resultsDir, jobId, "ERROR\n" + ex);
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

        private static void RunJob(string resultsDir, string jobId, string text)
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
            // Without this NT8 keeps no Trade objects during a backtest -
            // AllTrades stays empty (TotalTrades=0) even when orders fill.
            strategyObj.IncludeTradeHistoryInBacktest = true;

            foreach (var kv in props)
                SetProperty(strategyObj, strategyType, kv.Key, kv.Value);

            strategyObj.RunBacktest();

            WriteResult(resultsDir, jobId, FormatPerformance(strategyObj));
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
            // Every F5/auto-recompile loads a NEW custom assembly into the same
            // AppDomain without unloading the old one, so several assemblies
            // can define the same strategy type. Take the last-loaded match -
            // the first match is the stale build from NT8 startup.
            string fullName = "NinjaTrader.NinjaScript.Strategies." + shortName;
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
            sb.AppendLine("StrategyAssembly=" + strategy.GetType().Assembly.FullName);
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

        private static void WriteResult(string resultsDir, string jobId, string content)
        {
            string path = Path.Combine(resultsDir, jobId + ".result.txt");
            File.WriteAllText(path, content);
        }
    }
}
