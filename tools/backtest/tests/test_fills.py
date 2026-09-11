"""Synthetic days with known answers: does the Nautilus engine fill the way
engine.py / base.py / the setup docstrings say? No market data needed.

  python -m pytest tools/backtest/tests -q

Each day is flat at BASE from 09:00 to 16:00; a test overrides a few bars.
Costs: $3.50 RT, no slippage, so pnl_usd = points x $50 - 3.50.
"""
import numpy as np

from tools.backtest.data import Day, hm
from tools.backtest.nautilus import Engine

BASE = 5000.0
FEE = 3.5
SPEC = dict(sides="both", entry_window=["09:30", "11:00"], flat_by="11:30",
            max_trades_per_day=1, max_stop_pts=20, news_buffer_min=[5, 5],
            stop={"type": "points", "value": 2}, target={"type": "r", "value": 1})
GAP = dict(gap_unit="points", min_gap=1, max_gap=10, entry_delay_min=0)
ORB = dict(range_window="09:30-09:45", stop_at="other-side", atr_mode="off",
           range_max_atr=0.35, atr_stop=0.1)
KLF = dict(levels=["pdh", "pdl", "onh", "onl"], touch_ticks=0, first_touch_only=True)
RANGE = {"09:31": (5000, 5004, 5000, 5000), "09:32": (5000, 5000, 4996, 5000)}   # ORB 4996-5004


def day(bars=None, date="2024-01-02", **kw) -> Day:
    """Flat day; bars = {"HH:MM": (open, high, low, close)}."""
    mins = np.arange(540, 960)
    o, h, l, c = (np.full(len(mins), BASE) for _ in range(4))
    for t, (bo, bh, bl, bc) in (bars or {}).items():
        k = hm(t) - 540
        o[k], h[k], l[k], c[k] = bo, bh, bl, bc
    f = dict(rth_open=float(o[30]), atr=10.0, prev_close=None, prev_high=None, prev_low=None,
             on_high=None, on_low=None, news=(), news_all_day=False)
    return Day(date, mins, o, h, l, c, np.full(len(mins), 100.0), **{**f, **kw})


def run(sid, days, params, **spec_kw):
    sp = {**SPEC, **spec_kw}
    eng = Engine(sid, days, hm(sp["flat_by"]))
    try:
        trades, skipped, _ = eng.backtest(sp, params)
    finally:
        eng.close()
    return trades, skipped, eng.rejected


def gap_day(bars=None, date="2024-01-02", **kw):
    """Gap down 5 pts under prior close 5005 -> long at the 09:29 close 5000,
    stop 4998, target 5005."""
    return day(bars, date, prev_close=5005.0, **kw)


def check(t, side, entry, entry_min, exit, exit_min, reason):
    assert (t.side, t.entry, t.entry_min, t.exit, t.exit_min, t.reason) == (
        side, entry, hm(entry_min), exit, hm(exit_min), reason)
    assert t.pnl_usd == round((exit - entry) * side * 50 - FEE, 2)


def test_market_entry_then_target_and_stop_on_two_days():
    days = [gap_day({"09:40": (5000, 5006, 5000, 5006)}),
            gap_day({"09:40": (5000, 5000, 4997, 4997)}, date="2024-01-03")]
    trades, _, rejected = run("gap-fill", days, GAP)
    assert len(trades) == 2 and not rejected
    check(trades[0], 1, 5000, "09:30", 5005, "09:40", "target")
    assert trades[0].r == (5 * 50 - FEE) / (2 * 50)
    check(trades[1], 1, 5000, "09:30", 4998, "09:40", "stop")      # stop fills at its trigger


def test_gap_through_stop_fills_at_open():
    trades, _, _ = run("gap-fill", [gap_day({"09:40": (4995, 4996, 4994, 4995)})], GAP)
    check(trades[0], 1, 5000, "09:30", 4995, "09:40", "stop")


def test_stop_and_target_in_one_bar_nearer_extreme_first():
    low_first = gap_day({"09:40": (4999, 5006, 4997, 5003)})
    high_first = gap_day({"09:40": (5004, 5006, 4997, 5000)}, date="2024-01-03")
    trades, _, _ = run("gap-fill", [low_first, high_first], GAP)
    check(trades[0], 1, 5000, "09:30", 4998, "09:40", "stop")
    check(trades[1], 1, 5000, "09:30", 5005, "09:40", "target")


def test_gap_filled_before_entry_time_skips():
    d = gap_day({"09:30": (5000, 5005, 5000, 5000)})
    trades, _, _ = run("gap-fill", [d], {**GAP, "entry_delay_min": 5})
    assert trades == []


def test_news_flattens_at_close_before_block():
    # event 10:00, buffer 5/5 -> the 09:54 bar closes at 09:55 = block start
    d = gap_day({"09:54": (5000, 5001, 5000, 5001)}, news=(hm("10:00"),))
    trades, _, _ = run("gap-fill", [d], GAP)
    check(trades[0], 1, 5000, "09:30", 5001, "09:55", "news")


def test_news_blocks_entry():
    d = gap_day(news=(hm("09:30"),))                 # block 09:25-09:35 covers the entry
    trades, skipped, _ = run("gap-fill", [d], GAP)
    assert trades == [] and skipped == 1


def test_flat_by_flattens_at_close():
    d = gap_day({"09:59": (5000, 5001, 4999, 4999)})
    trades, _, _ = run("gap-fill", [d], GAP, flat_by="10:00")
    check(trades[0], 1, 5000, "09:30", 4999, "10:00", "flat")


def test_orb_stop_entry_fills_at_trigger_then_target():
    # range 4996-5004 -> buy stop 5004.25, stop 4995.75 (other side), 0.5R target 5008.5
    d = day({**RANGE, "09:50": (5000, 5005, 5000, 5005), "09:51": (5005, 5005, 5005, 5005),
             "09:55": (5005, 5009, 5005, 5009)})
    trades, _, rejected = run("orb", [d], ORB, target={"type": "r", "value": 0.5})
    assert len(trades) == 1 and not rejected
    check(trades[0], 1, 5004.25, "09:50", 5008.5, "09:55", "target")


def test_orb_bar_breaking_both_sides_takes_first_on_path_only():
    # high nearer the open -> long fills first, same bar's low stops it out; short never fills
    d = day({**RANGE, "09:50": (5001, 5005, 4995, 5000)})
    trades, _, _ = run("orb", [d], ORB, target={"type": "r", "value": 0.5})
    assert len(trades) == 1
    check(trades[0], 1, 5004.25, "09:50", 4995.75, "09:50", "stop")


def test_key_level_limit_fills_at_level():
    # prior-day high 5010 above the open -> sell limit 5010, stop 5012, 1R target 5008
    d = day({"09:45": (5000, 5010, 5000, 5009.5), "09:46": (5009.5, 5009.5, 5007, 5007)},
            prev_high=5010.0)
    trades, _, _ = run("key-level-fade", [d], KLF)
    assert len(trades) == 1
    check(trades[0], -1, 5010, "09:45", 5008, "09:46", "target")
