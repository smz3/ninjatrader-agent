// Opening Range Breakout - vanilla (step 1, no ATR yet).
//
// Source of truth for the rules: registry/strategies/orb.json (spec/params)
// and tools/backtest/nautilus/setups/orb.py (reference implementation this
// mirrors). Keep the three in sync if the rule ever changes.
//
// Range = high/low of [RangeStartTime, RangeEndTime]. Two resting stop
// entries (buy 1 tick above the high, sell 1 tick below the low) are armed
// once the range closes; the first fill cancels the other side (OCO is done
// by hand in OnOrderUpdate - NinjaScript's managed Enter* methods have no
// native OCO id for two *opposite* entries, only for exit brackets). Stop =
// other side of the range (default) or the range middle; target = TargetR x
// stop distance. One trade per day. Flat by FlatByTime. A resting entry
// order that a red-folder USD news window would otherwise let through is
// cancelled/flattened for [NewsBufferBeforeMin, NewsBufferAfterMin] around
// the event; if price crosses the breakout level while blocked, the whole
// day is skipped (matches orb.py's `watch()`).
//
// Two things to verify once this compiles inside NT8 (can't be checked from
// here - no headless NT8 compiler):
//   1. Bar timestamp convention. This assumes NinjaTrader labels an intraday
//      bar with its CLOSE time (a 08:30-08:31 CT bar prints Time[0]=08:31),
//      matching the reference engine's `t = bar start + 1 min`. Check the
//      "Orb: session start" print on the first log line of a day - it
//      should read the first RTH minute *after* RangeStartTime.
//   2. All times below are Central (CT) = ET minus 1 hour (CME session
//      templates + our imported bars are Central; both CT and ET follow the
//      same US DST rules so the 1h offset never drifts). Defaults are
//      09:30-09:45 ET / 09:30-11:00 ET / 11:30 ET flat, i.e. 830/845/830/
//      1000/1030 here. Confirm Tools > Options > General > Time Zone in NT8
//      is America/Chicago before trusting any of this (see
//      ninjascript/deploy.ps1 and tools/nt_export).
//
// News filter reads <NinjaTrader 8 folder>\news_usd_high.csv, built by
// `python -m tools.nt_export --news` from data/news/usd_high.csv and copied
// into place by ninjascript/deploy.ps1. Missing file = no news filter at
// all (logged once), not a crash - don't backtest funded-style days without
// checking that log line first.

#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using System.Linq;
using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.Gui.SuperDom;
using NinjaTrader.Gui.Tools;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.Core.FloatingPoint;
using NinjaTrader.NinjaScript.Indicators;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class Orb : Strategy
    {
        private const int Qty = 1;

        private struct NewsEvent
        {
            public DateTime Date;
            public int Hhmm;
            public bool AllDay;
        }

        private struct BlockWindow
        {
            public int Start;
            public int End;
        }

        private List<NewsEvent> newsEvents = new List<NewsEvent>();
        private List<BlockWindow> todayBlocks = new List<BlockWindow>();

        private int rangeStartMin, rangeEndMin, entryWindowStartMin, entryWindowEndMin, flatByMin;

        private DateTime currentSessionDate = DateTime.MinValue;
        private bool rangeSet, doneForDay, pendingPlaced, tradedToday;
        private double rangeHigh, rangeLow, breakoutUp, breakoutDn;
        private Order longEntryOrder, shortEntryOrder;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "Opening Range Breakout - vanilla stop-entry OCO, other-side stop, R target. See registry/strategies/orb.json.";
                Name = "Orb";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = false;
                IsFillLimitOnTouch = false;
                MaximumBarsLookBack = MaximumBarsLookBack.TwoHundredFiftySix;
                Slippage = 0;
                StartBehavior = StartBehavior.WaitUntilFlat;
                TimeInForce = TimeInForce.Gtc;
                TraceOrders = false;
                RealtimeErrorHandling = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade = 1;
                IsInstantiatedOnEachOptimizationIteration = true;

                RangeStartTime = 830;        // 08:30 CT = 09:30 ET
                RangeEndTime = 845;          // 08:45 CT = 09:45 ET
                EntryWindowStartTime = 830;  // 08:30 CT = 09:30 ET
                EntryWindowEndTime = 1000;   // 10:00 CT = 11:00 ET
                FlatByTime = 1030;           // 10:30 CT = 11:30 ET
                StopAtMiddle = false;        // false = other-side (registry default)
                TargetR = 0.5;
                MaxStopPoints = 20;
                NewsBufferBeforeMin = 5;
                NewsBufferAfterMin = 5;
            }
            else if (State == State.Configure)
            {
            }
            else if (State == State.DataLoaded)
            {
                rangeStartMin = ToMinutes(RangeStartTime);
                rangeEndMin = ToMinutes(RangeEndTime);
                entryWindowStartMin = ToMinutes(EntryWindowStartTime);
                entryWindowEndMin = ToMinutes(EntryWindowEndTime);
                flatByMin = ToMinutes(FlatByTime);
                LoadNewsEvents();
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < 1)
                return;

            DateTime bt = Time[0];
            DateTime sessionDate = bt.Date;
            int barMin = bt.Hour * 60 + bt.Minute;

            if (sessionDate != currentSessionDate)
                NewSessionReset(sessionDate);

            if (doneForDay)
                return;

            if (!rangeSet && barMin > rangeStartMin && barMin <= rangeEndMin)
            {
                rangeHigh = Math.Max(rangeHigh, High[0]);
                rangeLow = Math.Min(rangeLow, Low[0]);
            }

            if (barMin >= flatByMin)
            {
                FlattenAndCancel();
                doneForDay = true;
                return;
            }

            if (!rangeSet && barMin > rangeEndMin)
            {
                if (rangeHigh <= rangeLow)
                {
                    doneForDay = true; // no bars printed inside the range window
                    return;
                }
                rangeSet = true;
                breakoutUp = RoundToTick(rangeHigh + TickSize);
                breakoutDn = RoundToTick(rangeLow - TickSize);
                Print(string.Format("Orb {0:yyyy-MM-dd}: range {1:F2}-{2:F2}, breakout {3:F2}/{4:F2}, session-start bar Time[0]={5:HH:mm}",
                    sessionDate, rangeLow, rangeHigh, breakoutUp, breakoutDn, bt));
            }

            if (!rangeSet)
                return;

            if (IsBlocked(barMin))
            {
                bool wouldBreak = !tradedToday && (High[0] >= breakoutUp || Low[0] <= breakoutDn);
                FlattenAndCancel();
                if (wouldBreak)
                    doneForDay = true;
                return;
            }

            if (tradedToday)
                return;

            if (barMin > entryWindowEndMin)
            {
                FlattenAndCancel();
                doneForDay = true;
                return;
            }

            int entryStart = Math.Max(rangeEndMin, entryWindowStartMin);
            if (barMin < entryStart)
                return;

            if (!pendingPlaced)
                ArmEntries();
        }

        protected override void OnOrderUpdate(Order order, double limitPrice, double stopPrice, int quantity,
            int filled, double averageFillPrice, OrderState orderState, DateTime time, ErrorCode error, string comment)
        {
            if (order.Name == "OrbLong")
                longEntryOrder = order;
            else if (order.Name == "OrbShort")
                shortEntryOrder = order;

            if (orderState != OrderState.Filled)
                return;

            if (order.Name == "OrbLong")
            {
                tradedToday = true;
                CancelIfWorking(shortEntryOrder);
            }
            else if (order.Name == "OrbShort")
            {
                tradedToday = true;
                CancelIfWorking(longEntryOrder);
            }
        }

        private void ArmEntries()
        {
            double mid = RoundToTick((rangeHigh + rangeLow) / 2.0);
            double stopForLong = StopAtMiddle ? mid : breakoutDn;
            double stopForShort = StopAtMiddle ? mid : breakoutUp;

            double riskLong = breakoutUp - stopForLong;
            double riskShort = stopForShort - breakoutDn;
            bool longOk = riskLong > 0 && riskLong <= MaxStopPoints;
            bool shortOk = riskShort > 0 && riskShort <= MaxStopPoints;

            if (longOk)
            {
                double target = RoundToTick(breakoutUp + TargetR * riskLong);
                EnterLongStopMarket(Qty, breakoutUp, "OrbLong");
                SetStopLoss("OrbLong", CalculationMode.Price, RoundToTick(stopForLong), false);
                SetProfitTarget("OrbLong", CalculationMode.Price, target);
            }
            if (shortOk)
            {
                double target = RoundToTick(breakoutDn - TargetR * riskShort);
                EnterShortStopMarket(Qty, breakoutDn, "OrbShort");
                SetStopLoss("OrbShort", CalculationMode.Price, RoundToTick(stopForShort), false);
                SetProfitTarget("OrbShort", CalculationMode.Price, target);
            }

            pendingPlaced = longOk || shortOk;
            if (!pendingPlaced)
                doneForDay = true; // neither side fits MaxStopPoints today
        }

        private void CancelIfWorking(Order order)
        {
            if (order != null && (order.OrderState == OrderState.Accepted || order.OrderState == OrderState.Working))
                CancelOrder(order);
        }

        private void FlattenAndCancel()
        {
            CancelIfWorking(longEntryOrder);
            CancelIfWorking(shortEntryOrder);
            pendingPlaced = false;

            if (Position.MarketPosition == MarketPosition.Long)
                ExitLong("OrbFlat", "OrbLong");
            else if (Position.MarketPosition == MarketPosition.Short)
                ExitShort("OrbFlat", "OrbShort");
        }

        private void NewSessionReset(DateTime sessionDate)
        {
            currentSessionDate = sessionDate;
            rangeSet = false;
            doneForDay = false;
            pendingPlaced = false;
            tradedToday = false;
            rangeHigh = double.MinValue;
            rangeLow = double.MaxValue;
            breakoutUp = 0;
            breakoutDn = 0;
            longEntryOrder = null;
            shortEntryOrder = null;

            todayBlocks.Clear();
            foreach (NewsEvent ev in newsEvents)
            {
                if (ev.Date != sessionDate)
                    continue;
                if (ev.AllDay)
                {
                    doneForDay = true;
                    continue;
                }
                int center = ToMinutes(ev.Hhmm);
                todayBlocks.Add(new BlockWindow { Start = center - NewsBufferBeforeMin, End = center + NewsBufferAfterMin });
            }
        }

        private bool IsBlocked(int barMin)
        {
            for (int i = 0; i < todayBlocks.Count; i++)
                if (barMin >= todayBlocks[i].Start && barMin < todayBlocks[i].End)
                    return true;
            return false;
        }

        private void LoadNewsEvents()
        {
            newsEvents.Clear();
            string path = Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "news_usd_high.csv");
            if (!File.Exists(path))
            {
                Print("Orb: news_usd_high.csv not found at " + path + " - running with NO news filter. Run `python -m tools.nt_export --news` and ninjascript/deploy.ps1 first.");
                return;
            }
            foreach (string line in File.ReadAllLines(path))
            {
                if (string.IsNullOrWhiteSpace(line))
                    continue;
                string[] f = line.Split(',');
                if (f.Length < 3)
                    continue;
                newsEvents.Add(new NewsEvent
                {
                    Date = DateTime.ParseExact(f[0], "yyyyMMdd", CultureInfo.InvariantCulture),
                    Hhmm = int.Parse(f[1], CultureInfo.InvariantCulture),
                    AllDay = f[2].Trim() == "1",
                });
            }
        }

        private double RoundToTick(double price)
        {
            return Instrument.MasterInstrument.RoundToTickSize(price);
        }

        private static int ToMinutes(int hhmm)
        {
            return (hhmm / 100) * 60 + (hhmm % 100);
        }

        #region Properties
        [NinjaScriptProperty]
        [Range(0, 2359)]
        [Display(Name = "Range start (CT, HHMM)", Description = "09:30 ET default = 830 CT", Order = 1, GroupName = "ORB - range")]
        public int RangeStartTime { get; set; }

        [NinjaScriptProperty]
        [Range(0, 2359)]
        [Display(Name = "Range end (CT, HHMM)", Description = "09:45 ET default = 845 CT", Order = 2, GroupName = "ORB - range")]
        public int RangeEndTime { get; set; }

        [NinjaScriptProperty]
        [Range(0, 2359)]
        [Display(Name = "Entry window start (CT, HHMM)", Description = "09:30 ET default = 830 CT", Order = 3, GroupName = "ORB - entries")]
        public int EntryWindowStartTime { get; set; }

        [NinjaScriptProperty]
        [Range(0, 2359)]
        [Display(Name = "Entry window end (CT, HHMM)", Description = "11:00 ET default = 1000 CT - pending entries cancelled after this", Order = 4, GroupName = "ORB - entries")]
        public int EntryWindowEndTime { get; set; }

        [NinjaScriptProperty]
        [Range(0, 2359)]
        [Display(Name = "Flat by (CT, HHMM)", Description = "11:30 ET default = 1030 CT - force flat + cancel", Order = 5, GroupName = "ORB - entries")]
        public int FlatByTime { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Stop at range middle", Description = "false (default) = other side of range; true = range middle", Order = 6, GroupName = "ORB - risk")]
        public bool StopAtMiddle { get; set; }

        [NinjaScriptProperty]
        [Range(0.01, double.MaxValue)]
        [Display(Name = "Target (x stop distance, R)", Description = "0.5 default", Order = 7, GroupName = "ORB - risk")]
        public double TargetR { get; set; }

        [NinjaScriptProperty]
        [Range(0.01, double.MaxValue)]
        [Display(Name = "Max stop (points)", Description = "20 default - skip a side whose stop distance exceeds this", Order = 8, GroupName = "ORB - risk")]
        public double MaxStopPoints { get; set; }

        [NinjaScriptProperty]
        [Range(0, 120)]
        [Display(Name = "News buffer before (min)", Description = "5 default", Order = 9, GroupName = "ORB - news")]
        public int NewsBufferBeforeMin { get; set; }

        [NinjaScriptProperty]
        [Range(0, 120)]
        [Display(Name = "News buffer after (min)", Description = "5 default", Order = 10, GroupName = "ORB - news")]
        public int NewsBufferAfterMin { get; set; }
        #endregion
    }
}
