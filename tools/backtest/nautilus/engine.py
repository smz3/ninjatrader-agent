"""NautilusTrader backtest engine for the registry setups.

One BacktestEngine per strategy run: venue XCME (netting, margin, $1M so margin
never binds), one continuous ES.XCME FuturesContract (tick 0.25, x50), fed each
session's main-contract 1m bars from 09:00 up to and incl. the bar starting at
flat_by (data.sessions()). Flat every day, so contract rolls between sessions
never touch a position. Bars: UTC open-time index, ts_init = bar close
(BarDataWrangler ts_init_delta 60s), so a strategy sees a bar when it closes.

Venue = Nautilus defaults, except (user decisions 2026-09-11):
- fee_model PerContractFeeModel $1.75/side = $3.50 RT (Lucid ES) - Nautilus can't know it;
- use_message_queue=False - orders/cancels act instantly (real OCO), needed when
  one of 2+ pending entries fills.
So: default FillModel (no slippage), default O-H-L-C bar path, limits fill on touch.
Grid: engine.reset() + clear_strategies() between combos, data stays loaded.
"""
import numpy as np
import pandas as pd
from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.backtest.models import PerContractFeeModel
from nautilus_trader.config import LoggingConfig
from nautilus_trader.model.currencies import USD
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import AccountType, AssetClass, OmsType
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.instruments import FuturesContract
from nautilus_trader.model.objects import Money, Price, Quantity
from nautilus_trader.persistence.wranglers import BarDataWrangler

from .setups import SETUPS

VENUE = Venue("XCME")
BAR_TYPE = BarType.from_str("ES.XCME-1-MINUTE-LAST-EXTERNAL")
FEE_PER_SIDE_USD = 1.75
COSTS = {"commission_rt_usd": 2 * FEE_PER_SIDE_USD, "slippage_ticks": 0}


def instrument() -> FuturesContract:
    return FuturesContract(
        InstrumentId.from_str("ES.XCME"), Symbol("ES"), AssetClass.INDEX, USD, 2,
        Price.from_str("0.25"), Quantity.from_int(50), Quantity.from_int(1), "ES",
        0, 4_102_444_800_000_000_000, 0, 0)          # expiry 2100 - one continuous contract


def feed(days: list, flat: int, inst) -> tuple[list, dict, dict]:
    """(nautilus bars, {ts_event ns: (Day, bar index)}, {date: bars fed})."""
    refs, idx, dates, mins, cols = [], [], [], [], {k: [] for k in "ohlcv"}
    n_fed = {}
    for d in days:
        k = int(np.searchsorted(d.mins, flat, side="right"))
        n_fed[d.date] = k
        refs += [d] * k
        idx.append(np.arange(k))
        dates.append(np.repeat(d.date, k))
        mins.append(d.mins[:k])
        for c in "ohlcv":
            cols[c].append(getattr(d, c)[:k])
    et = pd.to_datetime(np.concatenate(dates)) + pd.to_timedelta(np.concatenate(mins), unit="min")
    ts = pd.DatetimeIndex(et).tz_localize("America/New_York").tz_convert("UTC")
    df = pd.DataFrame({name: np.concatenate(cols[c]) for c, name in
                       zip("ohlcv", ("open", "high", "low", "close", "volume"))}, index=ts)
    bars = BarDataWrangler(BAR_TYPE, inst).process(df, ts_init_delta=60_000_000_000)
    where = dict(zip(ts.asi8.tolist(), zip(refs, np.concatenate(idx).tolist())))
    return bars, where, n_fed


class Engine:
    def __init__(self, sid: str, days: list, flat: int):
        self.cls, self.days = SETUPS[sid], days
        self.engine = BacktestEngine(BacktestEngineConfig(logging=LoggingConfig(log_level="ERROR")))
        self.engine.add_venue(VENUE, OmsType.NETTING, AccountType.MARGIN, [Money(1_000_000, USD)],
                              base_currency=USD,
                              fee_model=PerContractFeeModel(Money(FEE_PER_SIDE_USD, USD)),
                              use_message_queue=False)
        inst = instrument()
        self.engine.add_instrument(inst)
        bars, self.where, self.n_fed = feed(days, flat, inst)
        self.engine.add_data(bars)

    def backtest(self, spec: dict, params: dict):
        """(trades, news_skipped, per-day [(r, peak_r), ...] incl. empty days)."""
        s = self.cls().bind(BAR_TYPE, self.where, self.n_fed, spec, params)
        self.engine.add_strategy(s)
        self.engine.run()
        if s.rejected:
            print(f"  note: {s.rejected} orders rejected by Nautilus")
        self.engine.reset()
        self.engine.clear_strategies()
        by = {}
        for t in s.trades:
            by.setdefault(t.date, []).append((t.r, t.peak_r))
        return s.trades, s.news_skipped, [by.get(d.date, []) for d in self.days]

    def close(self):
        self.engine.dispose()
