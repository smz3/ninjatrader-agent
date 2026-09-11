# NautilusTrader as the backtest engine - notes (2026-09-11)

User decision 2026-09-11: stop trusting the home-made python fill engine, replace it
with NautilusTrader (open source, trusted), keep our data. Then test it, before NT8.

## Install

- `pip install nautilus_trader` -> 1.231.0 on Windows / Python 3.13 (wheel, no build).
- It pulled pandas 3.0.5, which broke global pins (freqtrade, streamlit, llama-index).
  Fixed: `pip install "pandas>=2.3.3,<3"` (Nautilus allows >=2.3.3,<4). ib-async's
  tzdata<2026 warning left as is (harmless).
- The .pyx source ships in `site-packages/nautilus_trader/` - read it there, no clone needed.

## How it fills on 1m bars (read from source, backtest/engine.pyx)

- bar_execution: each LAST bar -> 4 synthetic trades O, H, L, C, orders matched after
  each (~line 4850). Default order is always O-H-L-C (high first, even for shorts).
  `bar_adaptive_high_low_ordering=True` -> the extreme nearer the open goes first.
  Docs: "a deterministic heuristic, not a reconstruction of the actual trade sequence".
- Trade bars set bid = ask = last (L1 book).
- LIMIT: fills when price TOUCHES it (buy: ask <= limit) - no 1-tick trade-through
  (execution/matching_core.pyx is_limit_marketable). `prob_fill_on_limit` (default 1.0)
  makes touch fills probabilistic. Optimistic for "first touch of a level" setups.
- STOP_MARKET: triggers when ask >= trigger (buy). Hit during H/L/C -> filled AT the
  trigger price; hit by the bar's open (gap) -> filled at the open (~line 6590).
- `prob_slippage` (default 0) moves EVERY fill 1 tick worse, limit fills too
  (apply_fills ~line 7382). Left at its default (0) - see Settings below.
- Fees: `PerContractFeeModel(Money(1.75, USD))` = per side per contract = $3.50 RT.
  (FixedFeeModel charges per order.)
- `use_message_queue=True` (default): strategy commands wait for the next data point,
  so a cancel sent from on_order_filled does NOT apply inside the same bar. Set
  `use_message_queue=False` -> processed immediately. Needed for ORB (two stop entries,
  cancel the other on first fill).
- Bars: ts_init must be the bar CLOSE or the strategy sees the bar a minute early:
  `BarDataWrangler(bar_type, instrument).process(df, ts_init_delta=60_000_000_000)`,
  df = open/high/low/close/volume with a UTC open-time index.
- `use_reduce_only=True`: a reduce-only order with no position gets canceled.

## API bits

- `engine.add_venue(venue, oms_type=NETTING, account_type=MARGIN, starting_balances,
  base_currency, fill_model, fee_model, bar_adaptive_high_low_ordering,
  use_message_queue, ...)`, `add_instrument`, `add_data(bars)`, `add_strategy`, `run()`.
- Grids: `engine.reset()` keeps data/instruments/venues AND strategies ->
  `engine.clear_strategies()` then `add_strategy(next combo)`. `dispose()` at the end.
- `FuturesContract(instrument_id, raw_symbol, asset_class, currency, price_precision=2,
  price_increment=Price(0.25), multiplier=Quantity(50), lot_size=Quantity(1),
  underlying, activation_ns, expiration_ns, ts_event, ts_init)`.
- `order_factory.bracket(instrument_id, order_side, quantity,
  entry_order_type=MARKET|LIMIT|STOP_MARKET, entry_price, entry_trigger_price,
  tp_price, sl_trigger_price, entry_tags/tp_tags/sl_tags)`; OUO children by default.
  Note `tp_post_only=True` default - check a marketable TP isn't rejected.
  `submit_order_list(order_list)`.
- Strategy: `subscribe_bars`, `cancel_order`, `cancel_all_orders(instrument_id)`,
  `close_all_positions(instrument_id, tags=[...])`, `on_order_filled(event)`.

## Build plan (agreed direction)

- Keep: data.py (sessions, roll-safe levels, ATR, news), metrics.py, prop.py,
  registry recording, CLI `python -m tools.backtest`.
- Replace sim.py + setups/*.py with Nautilus Strategy classes. One continuous
  instrument ES.XCME fed only main-contract bars 09:00 -> flat_by + 1 min (from
  data.sessions()); flat every day, so roll jumps between sessions don't matter.
  Day levels passed in by date.
- At each bar close t: t >= flat_by or t inside a news block [E-5, E+5) -> cancel all
  + flatten. Entries only if the next bar starts inside entry_window and isn't blocked.
- Orders = brackets (SL/TP priced from the planned entry). ORB = two STOP_MARKET
  brackets, cancel the other on first fill; break during a news block = no trade.
  Key-level-fade = LIMIT brackets per live level, cancel the rest while in a trade,
  re-arm untouched levels after. Range-mode / VWAP / gap = MARKET brackets at the
  signal bar's close.
- Trades built from fills (entry/exit px, exit reason via tags) into the same Trade
  fields, so metrics/prop don't change. Add "nautilus-1m" to
  tools/registry/schema.py ENGINES.
- Settings (user decision 2026-09-11): Nautilus DEFAULTS, no tweaks of our own -
  no prob_fill_on_limit change, no adaptive ordering, no extra slippage ticks. Only
  set what Nautilus can't know: the ES contract spec + fees 1.75/side. If a setting
  must change for a strategy to work at all (e.g. same-bar cancel for ORB - try an
  OCO order list first), ask the user before changing it.
- Old engine's ~$23/trade = $3.50 commission + 1 tick ($12.50) slippage on every
  market/stop fill (entry and non-target exit) - our own assumption, not Nautilus's.
  Real slippage to be checked against tick data (Databento), not guessed.
- Tests: synthetic days with known answers (target hit, stop hit, gap through stop,
  stop+target in one bar, news flatten, flat_by), then the 5 base combos, compare vs
  the old engine's trade files (data/backtests/r-*.parquet), hand-check ~10 trades vs
  raw bars, then full grids -> registry runs.

## Old engine reference (base combos, in-sample, for comparison)

| setup | real costs expR | zero costs expR |
|---|---|---|
| orb | -0.087 | -0.030 |
| range-mode | -0.223 | -0.051 |
| vwap-snap | -0.088 | -0.021 |
| key-level-fade | -0.177 | -0.115 |
| gap-fill | -0.031 | +0.058 |
