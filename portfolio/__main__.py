"""CLI: python -m portfolio <command>

  summary                     target-portfolio fundamentals, exposures and stress tests
  screen                      rank the candidate universe by sleeve
  drift                       current holdings vs targets (needs data/holdings.csv)
  contribute AMOUNT [--roth-room R] [--min-trade M]
                              plan buys for a new contribution, no selling
"""
from __future__ import annotations

import argparse
import sys

from . import core


def _pct(x: float) -> str:
    return f"{100 * x:5.1f}%"


def cmd_summary(_args) -> None:
    u, t = core.load_universe(), core.load_targets()
    w = {k: v["target_weight"] for k, v in t.items()}
    m = core.weighted_metrics(w, u)
    print(f"Holdings: {len(w)}   largest: {max(w.values()):.0%}")
    print(f"Forward P/E  F1 {m['pe_f1']:.1f}x (earnings yield {m['earnings_yield_f1']:.2f}%)"
          f"   F2 {m['pe_f2']:.1f}x (earnings yield {m['earnings_yield_f2']:.2f}%)")
    print(f"Beta {m['beta']:.2f}   dividend yield {m['div_yield']:.2f}%   "
          f"consensus long-term EPS growth {m['ltg']:.1f}%")
    for key in ("sleeve", "factor"):
        print(f"\nExposure by {key}:")
        for k, v in core.exposure(w, u, key).items():
            print(f"  {k:<14}{_pct(v)}")
    print("\nStress scenarios (instant shock, % of portfolio):")
    for name, loss in core.stress(w, u).items():
        print(f"  {name:<24}{loss:6.1f}%   {core.SCENARIOS[name]['desc']}")


def cmd_screen(_args) -> None:
    u, t = core.load_universe(), core.load_targets()
    for sleeve, rows in core.screen(u).items():
        print(f"\n{sleeve.upper()} sleeve (composite 0-100; * = in target portfolio)")
        for tk, s in rows:
            r = u[tk]
            f2 = f"{r['pe_f2']:.1f}" if r["pe_f2"] else "  n/a"
            print(f"  {'*' if tk in t else ' '} {tk:<6}{s:5.1f}   P/E F2 {f2:>5}   "
                  f"rank {int(r['zacks_rank'])}   {r['name']}")


def cmd_drift(_args) -> None:
    u, t = core.load_universe(), core.load_targets()
    h = core.load_holdings()
    if not h:
        sys.exit("data/holdings.csv is empty; add rows as: ticker,account,shares")
    pos = core.positions(h, t, core.load_prices(u))
    total = sum(p.value for p in pos)
    print(f"Portfolio value ${total:,.2f}\n")
    print(f"  {'ticker':<7}{'actual':>8}{'target':>8}{'drift pp':>10}")
    for tk, a, tg, d in core.drift(pos):
        flag = "  <-- rebalance band breached" if abs(d) >= 5 else ""
        print(f"  {tk:<7}{_pct(a):>8}{_pct(tg):>8}{d:10.1f}{flag}")


def cmd_contribute(args) -> None:
    u, t = core.load_universe(), core.load_targets()
    pos = core.positions(core.load_holdings(), t, core.load_prices(u))
    orders = core.plan_contribution(pos, t, args.amount, args.roth_room, args.min_trade)
    print(f"Plan for ${args.amount:,.2f} (Roth room ${args.roth_room:,.2f}):\n")
    for o in orders:
        print(f"  BUY {o['ticker']:<6} {o['account']:<8} ${o['dollars']:>9,.2f}  ~{o['shares']} sh")
    print(f"\n  total ${sum(o['dollars'] for o in orders):,.2f}")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="portfolio", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("summary").set_defaults(fn=cmd_summary)
    sub.add_parser("screen").set_defaults(fn=cmd_screen)
    sub.add_parser("drift").set_defaults(fn=cmd_drift)
    c = sub.add_parser("contribute")
    c.add_argument("amount", type=float)
    c.add_argument("--roth-room", type=float, default=0.0)
    c.add_argument("--min-trade", type=float, default=25.0)
    c.set_defaults(fn=cmd_contribute)
    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
