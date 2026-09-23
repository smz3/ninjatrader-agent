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
        private Order longEntryOrder, shortEntryOrder, stopOrder, targetOrder;
        private double stopForLongPending, stopForShortPending, targetLongPending, targetShortPending;
        private string entryOcoId, exitOcoId;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "Opening Range Breakout - vanilla stop-entry OCO, other-side stop, R target. See registry/strategies/orb.json.";
                Name = "Orb";
                Calculate = Calculate.OnBarClose;
                IsExitOnSessionCloseStrategy = false;
                IsFillLimitOnTouch = false;
                MaximumBarsLookBack = MaximumBarsLookBack.TwoHundredFiftySix;
                Slippage = 0;
                StartBehavior = StartBehavior.WaitUntilFlat;
                TimeInForce = TimeInForce.Gtc;
                TraceOrders = false;
                RealtimeErrorHandling = RealtimeErrorHandling.StopCancelClose;
                BarsRequiredToTrade = 1;
                IncludeTradeHistoryInBacktest = true;
                IsInstantiatedOnEachOptimizationIteration = true;
                // Unmanaged: the Managed approach's "Internal Order Handling Rules
                // that Reduce Unwanted Positions" silently ignores BOTH entries
                // whenever a long-stop and short-stop are working at once (our
                // straddle OCO pattern) - confirmed in NT log, this is why every
                // backtest showed TotalTrades=0. Unmanaged bypasses that check and
                // lets us use a real OCO id to link the two opposite entries.
                IsUnmanaged = true;

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
                Dbg(string.Format("=== Orb run {0:o}: {1} {2} TickSize={3} PointValue={4} IsUnmanaged={5}",
                    DateTime.Now, Instrument.FullName, BarsPeriod, TickSize, Instrument.MasterInstrument.PointValue, IsUnmanaged));
                LoadNewsEvents();
            }
        }

        // Print() only reaches NT8's Output window, which nothing outside NT8
        // can read - mirror every debug line into a repo file so automated
        // backtests (ninjascript/jobs) can be diagnosed headlessly.
        private const string DebugLogPath = @"C:\Users\User\Desktop\ninjatrader-agent\ninjascript\results\orb_debug.log";

        private void Dbg(string msg)
        {
            Print(msg);
            try { File.AppendAllText(DebugLogPath, msg + Environment.NewLine); }
            catch { }
        }

        private static bool markerPrinted = false;

        protected override void OnBarUpdate()
        {
            if (!markerPrinted)
            {
                Dbg("ORB_BUILD_MARKER_9942");
                markerPrinted = true;
            }

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
                Dbg(string.Format("Orb {0:yyyy-MM-dd}: range {1:F2}-{2:F2}, breakout {3:F2}/{4:F2}, session-start bar Time[0]={5:HH:mm}",
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
            Dbg(string.Format("Orb DEBUG OnOrderUpdate: name={0} state={1} filled={2} avgFill={3:F2} stop={4:F2} error={5} comment={6} time={7:HH:mm:ss}",
                order.Name, orderState, filled, averageFillPrice, stopPrice, error, comment, time));

            if (order.Name == "OrbLong")
                longEntryOrder = order;
            else if (order.Name == "OrbShort")
                shortEntryOrder = order;
            else if (order.Name == "OrbStop")
                stopOrder = order;
            else if (order.Name == "OrbTarget")
                targetOrder = order;

            if (orderState != OrderState.Filled)
                return;

            // Entry OCO id already made NT cancel the other side's resting
            // entry order natively - CancelIfWorking here is just a safety net.
            if (order.Name == "OrbLong")
            {
                tradedToday = true;
                CancelIfWorking(shortEntryOrder);
                exitOcoId = "OrbExit" + currentSessionDate.ToString("yyyyMMdd");
                stopOrder = SubmitOrderUnmanaged(0, OrderAction.Sell, OrderType.StopMarket, Qty, 0, RoundToTick(stopForLongPending), exitOcoId, "OrbStop");
                targetOrder = SubmitOrderUnmanaged(0, OrderAction.Sell, OrderType.Limit, Qty, targetLongPending, 0, exitOcoId, "OrbTarget");
            }
            else if (order.Name == "OrbShort")
            {
                tradedToday = true;
                CancelIfWorking(longEntryOrder);
                exitOcoId = "OrbExit" + currentSessionDate.ToString("yyyyMMdd");
                stopOrder = SubmitOrderUnmanaged(0, OrderAction.BuyToCover, OrderType.StopMarket, Qty, 0, RoundToTick(stopForShortPending), exitOcoId, "OrbStop");
                targetOrder = SubmitOrderUnmanaged(0, OrderAction.BuyToCover, OrderType.Limit, Qty, targetShortPending, 0, exitOcoId, "OrbTarget");
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

            Dbg(string.Format("Orb DEBUG ArmEntries {0:HH:mm}: longOk={1} shortOk={2} breakoutUp={3:F2} breakoutDn={4:F2} stopLong={5:F2} stopShort={6:F2} riskLong={7:F2} riskShort={8:F2}",
                Time[0], longOk, shortOk, breakoutUp, breakoutDn, stopForLong, stopForShort, riskLong, riskShort));

            entryOcoId = "OrbEntry" + currentSessionDate.ToString("yyyyMMdd");
            stopForLongPending = stopForLong;
            stopForShortPending = stopForShort;

            if (longOk)
            {
                targetLongPending = RoundToTick(breakoutUp + TargetR * riskLong);
                Dbg(string.Format("Orb DEBUG submitting OrbLong: entry={0:F2} stop={1:F2} target={2:F2}", breakoutUp, stopForLong, targetLongPending));
                longEntryOrder = SubmitOrderUnmanaged(0, OrderAction.Buy, OrderType.StopMarket, Qty, 0, breakoutUp, entryOcoId, "OrbLong");
            }
            if (shortOk)
            {
                targetShortPending = RoundToTick(breakoutDn - TargetR * riskShort);
                Dbg(string.Format("Orb DEBUG submitting OrbShort: entry={0:F2} stop={1:F2} target={2:F2}", breakoutDn, stopForShort, targetShortPending));
                shortEntryOrder = SubmitOrderUnmanaged(0, OrderAction.SellShort, OrderType.StopMarket, Qty, 0, breakoutDn, entryOcoId, "OrbShort");
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
            CancelIfWorking(stopOrder);
            CancelIfWorking(targetOrder);
            pendingPlaced = false;

            if (Position.MarketPosition == MarketPosition.Long)
                SubmitOrderUnmanaged(0, OrderAction.Sell, OrderType.Market, Position.Quantity, 0, 0, "", "OrbFlat");
            else if (Position.MarketPosition == MarketPosition.Short)
                SubmitOrderUnmanaged(0, OrderAction.BuyToCover, OrderType.Market, Position.Quantity, 0, 0, "", "OrbFlat");
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
            stopOrder = null;
            targetOrder = null;
            entryOcoId = null;
            exitOcoId = null;

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
                Dbg("Orb: news_usd_high.csv not found at " + path + " - running with NO news filter. Run `python -m tools.nt_export --news` and ninjascript/deploy.ps1 first.");
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
