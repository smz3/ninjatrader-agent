"""Real backtest days -> tools.prop_sim, LucidDaily 50K rules.

Eval: $3k target, $2k EOD trailing, 50% consistency, $1,200 daily loss,
60 trading days (same config as docs/research/prop-firm-shortlist.md,
'Eval risk vs funded risk'). Funded: tools.prop_sim.funded PLANS['daily']
(intraday trailing incl. open-profit peaks, $2,100 buffer, $500 min payout),
60 trading days. Whole backtest days are resampled (engine.Empirical), so
no-trade days, real R per trade and real open peaks carry over. R x risk
assumes exact risk sizing (MES for the remainder).
"""
from tools.prop_sim import funded as F
from tools.prop_sim.engine import Empirical, Firm, run_many

EVAL = Firm(target=3_000, max_dd=2_000, dd_mode="eod", consistency=0.5, daily_loss=1_200,
            max_days=60)
FUNDED_DAYS = 60


def simulate(per_day: list, eval_risk: float, funded_risk: float, n: int) -> dict:
    e = run_many(EVAL, Empirical(per_day, eval_risk), n)
    f = F.run_many(F.PLANS["daily"], Empirical(per_day, funded_risk), FUNDED_DAYS, n=n)
    return {
        "risk_usd": eval_risk,
        "eval_pass_rate": round(e["pass_rate"], 4),
        "eval_median_days": e["median_days"],
        "funded_risk_usd": funded_risk,
        "funded_blown_rate": round(f["blown"], 4),
        "funded_got_paid_rate": round(f["got_paid"], 4),
        "funded_avg_paid_usd": round(f["avg_paid"], 2),
    }
