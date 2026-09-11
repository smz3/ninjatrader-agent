"""Shared day/session rules for every setup, as a Nautilus Strategy.

Timing: a bar (UTC open-time index, ts_init = close) reaches on_bar at its close
t = start + 1 min. Orders act at once (venue use_message_queue=False): a market
order fills at that close, which is the next bar's open time. Resting orders are
matched by Nautilus on the following bars. So a fill's bar index = last bar
seen by on_bar + 1, for fills inside a bar and fills at a close alike.

At each bar close t (minutes ET):
- t >= flat_by, or the day's last fed bar -> cancel all + flatten, day over
  (reason flat / eod).
- t inside a news block [E - before, E + after) -> cancel all + flatten (news).
- all-day event (elections) -> no trading that day.
- entries only if the bar starting at t is inside entry_window, not blocked,
  side allowed, trades < max_trades_per_day, planned risk <= max_stop_pts.
  Pending entries are canceled at the first close t >= entry_window end.
Orders = Nautilus brackets: entry + OUO stop-market SL / limit TP, priced from
the planned entry; TP is a plain limit (tp_post_only=False - the bracket helper
defaults to post-only, CME has no such thing for us). The first entry fill
cancels every other pending entry. Exit reason = the filled order's tag.
Trade P/L = Nautilus fill prices x $50 - Nautilus commissions. R uses the
planned risk (what the size is based on). peak_r = best bar high/low from the
entry bar to the exit bar.
"""
from nautilus_trader.core.uuid import UUID4
from nautilus_trader.model.enums import ContingencyType, OrderSide, OrderType, TimeInForce, TriggerType
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.model.orders import OrderList, StopMarketOrder
from nautilus_trader.trading.strategy import Strategy

from ..data import PT_USD, TICK, hm
from ..sim import Trade, tick

KINDS = {"market": OrderType.MARKET, "limit": OrderType.LIMIT, "stop": OrderType.STOP_MARKET}


class SetupStrategy(Strategy):
    def bind(self, bar_type, where: dict, n_fed: dict, spec: dict, params: dict):
        self.bar_type, self.iid = bar_type, bar_type.instrument_id
        self.where, self.n_fed = where, n_fed
        self.spec, self.p = spec, params
        self.sides = {"long": (1,), "short": (-1,), "both": (1, -1)}[spec["sides"]]
        self.win_from, self.win_to = (hm(x) for x in spec["entry_window"])
        self.flat = hm(spec["flat_by"])
        self.max_trades, self.max_stop = spec["max_trades_per_day"], spec["max_stop_pts"]
        self.buffer = spec["news_buffer_min"]
        self.trades, self.news_skipped, self.rejected = [], 0, []   # rejected: (date, t, tag, reason)
        self.d, self.pos, self.pending = None, None, {}
        return self

    def on_start(self):
        self.subscribe_bars(self.bar_type)

    # -- hooks for setups -------------------------------------------------
    def start_day(self, d): ...
    def watch(self, i): ...            # every bar, flat or not
    def step(self, i, t): ...          # only when flat, not on the bar of an exit
    def on_entry(self, oid): ...

    # -- helpers ----------------------------------------------------------
    def blocked(self, t: int) -> bool:
        return any(a <= t < b for a, b in self.blocks)

    def can_enter(self, t: int, side: int, count: bool = True) -> bool:
        if (self.n_day >= self.max_trades or side not in self.sides
                or not self.win_from <= t < self.win_to or t >= self.flat):
            return False
        if self.blocked(t):
            self.news_skipped += count
            return False
        return True

    def dist(self, level: dict, risk: float | None = None, ref: float | None = None) -> float:
        """Points for a non-structure LEVEL (r needs risk, range needs ref)."""
        t, v = level["type"], level["value"]
        pts = {"points": lambda: v, "ticks": lambda: v * TICK, "r": lambda: v * risk,
               "atr": lambda: v * self.d.atr, "range": lambda: v * ref}[t]()
        return max(tick(pts), TICK)

    def enter(self, side: int, kind: str, entry: float, stop: float, target: float):
        """Submit a bracket; entry = planned price (market: the current close). -> entry id."""
        stop, target = tick(stop), tick(target)
        risk, reward = (entry - stop) * side, (target - entry) * side
        if risk <= 0 or reward <= 0 or (self.max_stop is not None and risk > self.max_stop):
            return None
        k = KINDS[kind]
        ol = self.order_factory.bracket(
            instrument_id=self.iid, order_side=OrderSide.BUY if side > 0 else OrderSide.SELL,
            quantity=Quantity.from_int(1),
            entry_order_type=OrderType.MARKET if k == OrderType.STOP_MARKET else k,
            entry_price=Price(entry, 2) if k == OrderType.LIMIT else None,
            tp_price=Price(target, 2), sl_trigger_price=Price(stop, 2), tp_post_only=False,
            entry_tags=["entry"], tp_tags=["target"], sl_tags=["stop"])
        if k == OrderType.STOP_MARKET:
            ol = self.stop_entry(ol, Price(entry, 2))
        oid = ol.first.client_order_id
        self.pending[oid] = (side, entry, stop, target, ol.orders)
        self.submit_order_list(ol)
        return oid

    def stop_entry(self, ol: OrderList, trigger: Price) -> OrderList:
        """bracket() has no STOP_MARKET entry: swap its (unsent) market entry for a
        stop-market one with the same id/list/links, as bracket() builds the others."""
        e = ol.first
        stop = StopMarketOrder(
            self.trader_id, self.id, e.instrument_id, e.client_order_id, e.side, e.quantity,
            trigger, TriggerType.DEFAULT, UUID4(), self.clock.timestamp_ns(), TimeInForce.GTC,
            contingency_type=ContingencyType.OTO, order_list_id=ol.id,
            linked_order_ids=e.linked_order_ids, tags=e.tags)
        return OrderList(ol.id, [stop, *ol.orders[1:]])

    def cancel_pending(self):
        for *_, orders in self.pending.values():
            for o in orders:
                if not self.cache.order(o.client_order_id).is_closed:
                    self.cancel_order(o)
        self.pending = {}

    def flatten(self, reason: str):
        self.pending = {}
        self.cancel_all_orders(self.iid)
        if self.pos is not None:
            self.close_all_positions(self.iid, tags=[reason])

    # -- engine callbacks -------------------------------------------------
    def new_day(self, d):
        if self.pos is not None or self.pending:
            raise RuntimeError(f"{d.date}: position/orders carried over from {self.d.date}")
        self.d, self.over, self.exit_i, self.n_day = d, d.news_all_day, -1, 0
        a, b = self.buffer
        self.blocks = [(e - a, e + b) for e in d.news]
        self.start_day(d)

    def on_bar(self, bar):
        d, i = self.where[bar.ts_event]
        if d is not self.d:
            self.new_day(d)
        self.i = i
        if self.over:
            return
        t = int(d.mins[i]) + 1
        self.watch(i)
        if t >= self.flat or i == self.n_fed[d.date] - 1:
            self.flatten("flat" if t >= self.flat else "eod")
            self.over = True
            return
        if self.blocked(t):
            self.flatten("news")
        elif self.pending and t >= self.win_to:
            self.cancel_pending()
        if self.pos is None and self.exit_i != i:
            self.step(i, t)

    def on_order_filled(self, e):
        tag = (self.cache.order(e.client_order_id).tags or [""])[0]
        px, fi, fee = e.last_px.as_double(), self.i + 1, e.commission.as_double()
        if tag == "entry":
            side, entry, stop, target, _ = self.pending.pop(e.client_order_id)
            self.cancel_pending()
            self.n_day += 1
            self.pos = dict(side=side, px=px, planned=entry, stop=stop, target=target, i=fi, fee=fee)
            self.on_entry(e.client_order_id)
        elif self.pos is not None:
            self.close_trade(tag, px, fi, fee)

    def on_order_rejected(self, e):
        tag = (self.cache.order(e.client_order_id).tags or [""])[0]
        self.rejected.append((self.d.date, int(self.d.mins[self.i]) + 1, tag, str(e.reason)))
        if tag == "entry":
            self.pending.pop(e.client_order_id, None)
        elif self.pos is not None:          # unprotected position -> get out
            self.flatten("rejected")

    def close_trade(self, reason: str, px: float, fi: int, fee: float):
        p, d = self.pos, self.d
        self.pos, self.exit_i = None, fi
        side, n = p["side"], len(d.mins)
        minute = lambda k: int(d.mins[k]) if k < n else int(d.mins[-1]) + 1
        a = min(p["i"], n - 1)
        b = max(a, min(fi if reason in ("target", "stop") else fi - 1, n - 1))
        mfe = d.h[a:b + 1].max() - p["px"] if side > 0 else p["px"] - d.l[a:b + 1].min()
        risk = (p["planned"] - p["stop"]) * side
        pts = (px - p["px"]) * side
        usd = pts * PT_USD - p["fee"] - fee
        self.trades.append(Trade(d.date, side, minute(p["i"]), p["px"], p["stop"], p["target"],
                                 minute(fi), px, reason, round(pts, 4), round(usd, 2), risk,
                                 usd / (risk * PT_USD), max(float(mfe), 0.0) / risk, fi))
