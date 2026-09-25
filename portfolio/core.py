"""Portfolio tracking, screening, stress-testing and contribution planning.

Pure standard library so it runs anywhere Python 3.9+ is installed.
Data lives in ../data as CSV; see README.md for the file formats.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

NUMERIC = {
    "price", "pe_f1", "pe_f2", "peg", "beta", "div_yield", "ltg",
    "zacks_rank", "roe", "ytd_pct", "chg_52w_pct",
}


def _num(value: str):
    return float(value) if value not in ("", None) else None


def load_universe(path: Path = DATA_DIR / "universe.csv") -> dict[str, dict]:
    with open(path, newline="") as f:
        rows = {}
        for r in csv.DictReader(f):
            rows[r["ticker"]] = {k: (_num(v) if k in NUMERIC else v) for k, v in r.items()}
        return rows


def load_targets(path: Path = DATA_DIR / "target_portfolio.csv") -> dict[str, dict]:
    with open(path, newline="") as f:
        out = {}
        for r in csv.DictReader(f):
            r["target_weight"] = float(r["target_weight"])
            out[r["ticker"]] = r
    total = sum(t["target_weight"] for t in out.values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"target weights sum to {total:.4f}, expected 1.0")
    return out


def load_holdings(path: Path = DATA_DIR / "holdings.csv") -> dict[str, dict[str, float]]:
    """Returns {ticker: {account: shares}}."""
    out: dict[str, dict[str, float]] = {}
    if not path.exists():
        return out
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if not r.get("ticker"):
                continue
            acct = out.setdefault(r["ticker"], {})
            acct[r["account"]] = acct.get(r["account"], 0.0) + float(r["shares"])
    return out


def load_prices(universe: dict[str, dict], path: Path = DATA_DIR / "prices.csv") -> dict[str, float]:
    """Snapshot prices from the universe, overridden by data/prices.csv if present."""
    prices = {t: r["price"] for t, r in universe.items() if r["price"] is not None}
    if path.exists():
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                prices[r["ticker"]] = float(r["price"])
    return prices


# ---------------------------------------------------------------- analytics

def weighted_metrics(weights: dict[str, float], universe: dict[str, dict]) -> dict[str, float]:
    """Weight-averaged fundamentals. Earnings yield is averaged (not P/E) so the
    result is the portfolio's true aggregate P/E, and missing values are
    renormalised over the names that have them."""
    out = {}
    for key in ("beta", "div_yield", "ltg"):
        pairs = [(w, universe[t][key]) for t, w in weights.items() if universe[t][key] is not None]
        wsum = sum(w for w, _ in pairs)
        out[key] = sum(w * v for w, v in pairs) / wsum if wsum else float("nan")
    for key in ("pe_f1", "pe_f2"):
        pairs = [(w, universe[t][key]) for t, w in weights.items() if universe[t][key]]
        wsum = sum(w for w, _ in pairs)
        ey = sum(w / v for w, v in pairs) / wsum if wsum else float("nan")
        out[key] = 1 / ey
        out[f"earnings_yield_{key[-2:]}"] = ey * 100
    return out


def exposure(weights: dict[str, float], universe: dict[str, dict], key: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for t, w in weights.items():
        out[universe[t][key]] = out.get(universe[t][key], 0.0) + w
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


# Scenario shocks by factor, in percent. These are judgement calls calibrated
# loosely on 2000-02, 2008 and 2022 drawdowns, not forecasts.
SCENARIOS: dict[str, dict] = {
    "ai_capex_digestion": {
        "desc": "Hyperscalers cut capex; 2022-style tech de-rating",
        "factor": {"ai_semis": -55, "ai_platform": -35, "software": -40, "financials": -12,
                   "insurance": -5, "staples": 0, "energy": -10, "conglomerate": -8, "healthcare": -5},
        "ticker": {},
    },
    "stagflation_rate_shock": {
        "desc": "10y to 6%, Brent $130, Fed keeps hiking",
        "factor": {"ai_semis": -35, "ai_platform": -30, "software": -35, "financials": -25,
                   "insurance": -8, "staples": -12, "energy": 20, "conglomerate": -12, "healthcare": -10},
        "ticker": {},
    },
    "gfc_recession": {
        "desc": "2008-style credit recession",
        "factor": {"ai_semis": -50, "ai_platform": -40, "software": -45, "financials": -55,
                   "insurance": -25, "staples": -15, "energy": -40, "conglomerate": -30, "healthcare": -20},
        "ticker": {},
    },
    "taiwan_strait": {
        "desc": "Blockade of Taiwan; foundry supply halted",
        "factor": {"ai_semis": -40, "ai_platform": -25, "software": -20, "financials": -15,
                   "insurance": -10, "staples": -10, "energy": 10, "conglomerate": -12, "healthcare": -10},
        "ticker": {"TSM": -70},
    },
}


def stress(weights: dict[str, float], universe: dict[str, dict]) -> dict[str, float]:
    results = {}
    for name, sc in SCENARIOS.items():
        total = 0.0
        for t, w in weights.items():
            shock = sc["ticker"].get(t, sc["factor"].get(universe[t]["factor"], 0.0))
            total += w * shock
        results[name] = total
    return results


# ---------------------------------------------------------------- screening

def _pct_rank(values: dict[str, float | None], higher_is_better: bool) -> dict[str, float]:
    present = {k: v for k, v in values.items() if v is not None}
    ordered = sorted(present, key=lambda k: present[k], reverse=not higher_is_better)
    n = len(ordered)
    ranks = {k: (i / (n - 1) if n > 1 else 1.0) for i, k in enumerate(ordered)}
    return {k: ranks.get(k, 0.5) for k in values}  # missing data scores neutral


SCREEN_WEIGHTS = {
    "quality": {"roe": 0.30, "pe_f2": 0.25, "peg": 0.15, "beta": 0.15, "zacks_rank": 0.15},
    "growth": {"ltg": 0.25, "pe_f2": 0.25, "peg": 0.25, "zacks_rank": 0.15, "roe": 0.10},
}
HIGHER_BETTER = {"roe": True, "ltg": True, "pe_f2": False, "peg": False, "beta": False, "zacks_rank": False}


def screen(universe: dict[str, dict]) -> dict[str, list[tuple[str, float]]]:
    """Score each sleeve's candidates 0-100 on a percentile composite."""
    out = {}
    for sleeve, wts in SCREEN_WEIGHTS.items():
        names = [t for t, r in universe.items() if r["sleeve"] == sleeve]
        score = {t: 0.0 for t in names}
        for metric, w in wts.items():
            ranks = _pct_rank({t: universe[t][metric] for t in names}, HIGHER_BETTER[metric])
            for t in names:
                score[t] += w * ranks[t]
        out[sleeve] = sorted(((t, 100 * s) for t, s in score.items()), key=lambda kv: -kv[1])
    return out


# ---------------------------------------------------------------- holdings & contributions

@dataclass
class Position:
    ticker: str
    shares: float
    price: float
    target: float
    accounts: dict[str, float] = field(default_factory=dict)

    @property
    def value(self) -> float:
        return self.shares * self.price


def positions(holdings, targets, prices) -> list[Position]:
    tickers = list(targets) + [t for t in holdings if t not in targets]
    out = []
    for t in tickers:
        accts = holdings.get(t, {})
        if t not in prices:
            raise KeyError(f"no price for {t}; add it to data/prices.csv")
        out.append(Position(t, sum(accts.values()), prices[t],
                            targets.get(t, {}).get("target_weight", 0.0), dict(accts)))
    return out


def drift(pos: list[Position]) -> list[tuple[str, float, float, float]]:
    """(ticker, actual weight, target weight, drift in percentage points)."""
    total = sum(p.value for p in pos)
    rows = []
    for p in pos:
        actual = p.value / total if total else 0.0
        rows.append((p.ticker, actual, p.target, 100 * (actual - p.target)))
    return sorted(rows, key=lambda r: r[3])


def plan_contribution(pos: list[Position], targets: dict[str, dict], amount: float,
                      roth_room: float = 0.0, min_trade: float = 25.0) -> list[dict]:
    """Allocate new cash toward the most underweight names without selling.

    Rebalancing with contributions keeps turnover (and taxes in the taxable
    account) at zero. Buys smaller than `min_trade` are dropped and their cash
    redistributed. Roth-preferred names fill the Roth first; any Roth room left
    after that is filled with other buys, because Roth space that goes unused in a
    tax year is lost.
    """
    total_after = sum(p.value for p in pos) + amount
    active = [p for p in pos if p.target > 0]
    while True:
        deficits = {p.ticker: max(0.0, p.target * total_after - p.value) for p in active}
        dsum = sum(deficits.values())
        if dsum == 0:
            deficits = {p.ticker: p.target for p in active}
            dsum = sum(deficits.values())
        buys = {t: amount * d / dsum for t, d in deficits.items() if d > 0}
        small = [t for t, v in buys.items() if v < min_trade]
        if not small or len(small) == len(buys):
            break
        active = [p for p in active if p.ticker not in small]

    price = {p.ticker: p.price for p in pos}
    room = roth_room
    orders = []
    ordered = sorted(buys.items(), key=lambda kv: targets[kv[0]]["account_pref"] != "roth")
    for t, dollars in ordered:
        to_roth = min(dollars, room)
        room -= to_roth
        for acct, d in (("roth", to_roth), ("taxable", dollars - to_roth)):
            if d > 0.005:
                orders.append({"ticker": t, "account": acct, "dollars": round(d, 2),
                               "shares": round(d / price[t], 4)})
    return orders
