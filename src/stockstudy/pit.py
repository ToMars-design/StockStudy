"""Point-in-time facts: what was reported, and from when an investor could know it.

Every fact carries two clocks:

* the **period** it describes (``period_start``, ``period_end``), such as fiscal 2023;
* its **availability** (``available_at``): the first trading session in which an
  investor could have acted on it.

A later filing can report a different value for the same period, for example after a
restatement. Both versions are kept, and :func:`as_of` returns whichever was the latest
*known* on a date, so a backtest sees the figure investors actually had rather than
today's corrected one.

Facts follow the :data:`FACT_COLUMNS` schema. ``period_start`` is missing for instant
facts such as total assets, which describe a single date rather than an interval.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

__all__ = ["FACT_COLUMNS", "Period", "as_of", "latest_value"]

FACT_COLUMNS = [
    "cik",
    "taxonomy",
    "concept",
    "unit",
    "period_start",
    "period_end",
    "value",
    "fiscal_year",
    "fiscal_period",
    "form",
    "accession",
    "filed",
    "available_at",
]

type Period = Literal["annual", "quarterly", "instant"]

# One fact per company, concept, unit and period; versions differ only in availability.
_KEY = ["cik", "taxonomy", "concept", "unit", "period_start", "period_end"]

# Allowed period lengths in days. Generous, because fiscal years run 52 or 53 weeks.
_DURATION_DAYS: dict[Period, tuple[int, int]] = {"annual": (350, 380), "quarterly": (80, 100)}

_OUTPUT_COLUMNS = ["value", "period_end", "available_at", "accession"]


def as_of(facts: pd.DataFrame, when: pd.Timestamp) -> pd.DataFrame:
    """Return the facts as they were known on the session ``when``.

    Args:
        facts: Facts in the :data:`FACT_COLUMNS` schema, possibly with several versions
            of the same fact from different filings.
        when: Session date. Facts with ``available_at`` after it are invisible.

    Returns:
        One row per company, concept, unit and period: the most recently available
        version, with ties broken by accession number.
    """
    known = facts[facts["available_at"] <= when]
    newest_last = known.sort_values(["available_at", "accession"], kind="stable")
    return newest_last.drop_duplicates(_KEY, keep="last").reset_index(drop=True)


def latest_value(
    facts: pd.DataFrame,
    dates: pd.DatetimeIndex,
    *,
    concept: str,
    period: Period,
    unit: str = "USD",
    taxonomy: str = "us-gaap",
) -> pd.DataFrame:
    """For each date and company, the most recent period's value as known on that date.

    This is how a fundamental becomes a daily feature without look-ahead: on each date,
    only facts already available count, and among them the latest period wins, in the
    version known at the time.

    Args:
        facts: Facts in the :data:`FACT_COLUMNS` schema.
        dates: Session dates to evaluate on.
        concept: Concept name, such as ``"Revenues"`` or ``"Assets"``.
        period: ``"annual"`` or ``"quarterly"`` for flows, ``"instant"`` for stocks.
        unit: Unit of measure.
        taxonomy: Taxonomy of the concept.

    Returns:
        A frame indexed by ``(date, cik)`` with the value, its period end, its
        availability date and the accession number of the filing it came from. A company
        appears only from the first date on which one of its values is known.
    """
    selected = facts[
        (facts["concept"] == concept) & (facts["unit"] == unit) & (facts["taxonomy"] == taxonomy)
    ]
    selected = _with_period(selected, period)

    # The answer only changes when a new fact becomes available, so compute it at those
    # moments and carry it forward to the requested dates.
    snapshots = []
    for event in np.sort(selected["available_at"].unique()):
        known = as_of(selected, pd.Timestamp(event))
        newest = known.sort_values("period_end", kind="stable").drop_duplicates("cik", keep="last")
        snapshots.append(newest.assign(event=event))
    if not snapshots:
        empty = pd.MultiIndex.from_arrays([pd.DatetimeIndex([]), pd.Index([], dtype=str)])
        return pd.DataFrame(columns=_OUTPUT_COLUMNS, index=empty.set_names(["date", "cik"]))

    history = pd.concat(snapshots).sort_values("event", kind="stable")
    grid = pd.MultiIndex.from_product(
        [dates.sort_values(), history["cik"].unique()], names=["date", "cik"]
    ).to_frame(index=False)
    merged = pd.merge_asof(
        grid,
        history[["cik", "event", *_OUTPUT_COLUMNS]],
        left_on="date",
        right_on="event",
        by="cik",
        direction="backward",
    )
    known_rows = merged[merged["event"].notna()]
    return known_rows.set_index(["date", "cik"])[_OUTPUT_COLUMNS]


def _with_period(facts: pd.DataFrame, period: Period) -> pd.DataFrame:
    """Keep the facts whose period matches ``period``."""
    if period == "instant":
        return facts[facts["period_start"].isna()]
    shortest, longest = _DURATION_DAYS[period]
    days = (facts["period_end"] - facts["period_start"]).dt.days
    return facts[days.between(shortest, longest)]
