"""Trade list -> registry METRICS (per 1 ES, after costs)."""
from statistics import mean


def compute(trades: list, days: int, news_skipped: int) -> dict:
    n = len(trades)
    pnl = [t.pnl_usd for t in trades]
    wins = [x for x in pnl if x > 0]
    losses = [x for x in pnl if x <= 0]
    avg_w = mean(wins) if wins else 0.0
    avg_l = mean(losses) if losses else 0.0
    eq = peak = dd = 0.0
    for x in pnl:
        eq += x
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    by_day = {}
    for t in trades:
        by_day[t.date] = by_day.get(t.date, 0.0) + t.pnl_usd
    gross_loss = -sum(losses)
    return {
        "trades": n,
        "days": days,
        "trades_per_day": round(n / days, 3) if days else 0.0,
        "win_rate": round(len(wins) / n, 4) if n else 0.0,
        "avg_win_usd": round(avg_w, 2),
        "avg_loss_usd": round(avg_l, 2),
        "rr": round(avg_w / -avg_l, 3) if avg_l < 0 else 0.0,
        "expectancy_usd": round(mean(pnl), 2) if n else 0.0,
        "expectancy_r": round(mean(t.r for t in trades), 4) if n else 0.0,
        "avg_risk_pts": round(mean(t.risk_pts for t in trades), 2) if n else 0.0,
        "profit_factor": round(sum(wins) / gross_loss, 3) if gross_loss > 0 else None,
        "net_usd": round(sum(pnl), 2),
        "max_dd_usd": round(dd, 2),
        "worst_day_usd": round(min(0.0, *by_day.values()), 2),
        "news_skipped": news_skipped,
    }
