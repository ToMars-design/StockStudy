"""Tests for stockstudy.pit, on the Acme and Bolt filings defined in conftest.py."""

import pandas as pd
import pytest

from stockstudy.lookahead import LookAheadError, assert_no_lookahead
from stockstudy.pit import as_of, latest_value

ACME, BOLT = "0000001234", "0000005678"
DATES = pd.bdate_range("2022-10-03", "2024-03-29")


def _revenue(facts: pd.DataFrame, when: str) -> list[float]:
    known = as_of(facts, pd.Timestamp(when))
    rows = known[(known["cik"] == ACME) & (known["concept"] == "Revenues")]
    return rows.sort_values("period_end")["value"].tolist()


def test_as_of_hides_facts_until_the_session_after_filing(facts: pd.DataFrame) -> None:
    assert _revenue(facts, "2022-11-04") == []  # filing day itself: not yet usable
    assert _revenue(facts, "2022-11-07") == [100.0]


def test_as_of_shows_the_original_figure_until_the_restatement_is_filed(
    facts: pd.DataFrame,
) -> None:
    assert _revenue(facts, "2023-11-03") == [100.0, 27.0]
    assert _revenue(facts, "2023-11-06") == [98.0, 27.0, 120.0]


def test_latest_annual_value_tracks_what_was_known(facts: pd.DataFrame) -> None:
    revenue = latest_value(facts, DATES, concept="Revenues", period="annual")["value"]

    assert pd.Timestamp("2022-11-04") not in revenue.index.get_level_values("date")
    assert revenue[(pd.Timestamp("2022-11-07"), ACME)] == 100.0
    assert revenue[(pd.Timestamp("2023-11-03"), ACME)] == 100.0  # restatement not yet filed
    assert revenue[(pd.Timestamp("2023-11-06"), ACME)] == 120.0  # newer fiscal year wins
    assert revenue[(pd.Timestamp("2024-03-29"), BOLT)] == 40.0


def test_companies_appear_only_once_something_is_known(facts: pd.DataFrame) -> None:
    revenue = latest_value(facts, DATES, concept="Revenues", period="annual")
    first_seen = revenue.reset_index().groupby("cik")["date"].min()
    assert first_seen[ACME] == pd.Timestamp("2022-11-07")
    assert first_seen[BOLT] == pd.Timestamp("2023-03-06")


def test_quarterly_and_instant_periods_are_selected_by_length(facts: pd.DataFrame) -> None:
    quarterly = latest_value(facts, DATES, concept="Revenues", period="quarterly")
    assert set(quarterly["value"]) == {27.0}

    assets = latest_value(facts, DATES, concept="Assets", period="instant")
    assert set(assets["value"]) == {500.0}

    shares = latest_value(
        facts,
        DATES,
        concept="EntityCommonStockSharesOutstanding",
        period="instant",
        unit="shares",
        taxonomy="dei",
    )
    assert set(shares["value"]) == {1_000_000.0}


def test_unknown_concept_gives_an_empty_frame(facts: pd.DataFrame) -> None:
    empty = latest_value(facts, DATES, concept="NoSuchConcept", period="annual")
    assert empty.empty
    assert list(empty.index.names) == ["date", "cik"]


def test_latest_value_has_no_lookahead(facts: pd.DataFrame) -> None:
    by_availability = facts.set_index(pd.DatetimeIndex(facts["available_at"], name="known"))
    assert_no_lookahead(
        lambda f: latest_value(f, DATES, concept="Revenues", period="annual"), by_availability
    )


def test_treating_period_end_as_availability_is_caught(facts: pd.DataFrame) -> None:
    """The classic fundamentals leak: using a figure from the day its period ended."""
    by_availability = facts.set_index(pd.DatetimeIndex(facts["available_at"], name="known"))

    def leaky(f: pd.DataFrame) -> pd.DataFrame:
        return latest_value(
            f.assign(available_at=f["period_end"]), DATES, concept="Revenues", period="annual"
        )

    with pytest.raises(LookAheadError):
        assert_no_lookahead(leaky, by_availability)
