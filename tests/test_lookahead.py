"""Tests for stockstudy.lookahead.

Each leaky transform below is a classic source of look-ahead bias in research code, and
the causal transforms show the idiomatic alternatives: the file doubles as a catalogue.
"""

import math
from collections.abc import Callable
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd
import pytest

from stockstudy.lookahead import LookAheadError, assert_no_lookahead

type Series = pd.Series[Any]

N_DAYS = 120
TICKERS = ["AAA", "BBB", "CCC"]


def _random_walk(rng: np.random.Generator, n: int) -> npt.NDArray[np.float64]:
    return 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, n)))


@pytest.fixture
def prices() -> Series:
    rng = np.random.default_rng(42)
    index = pd.bdate_range("2024-01-01", periods=N_DAYS, name="date")
    return pd.Series(_random_walk(rng, N_DAYS), index=index, name="close")


@pytest.fixture
def gappy_prices(prices: Series) -> Series:
    """Prices with every other value missing, as in an illiquid or sparsely sampled series."""
    return prices.where(np.arange(len(prices)) % 2 == 0)


@pytest.fixture
def panel() -> pd.DataFrame:
    """Long-format (date, ticker) panel of closing prices."""
    rng = np.random.default_rng(7)
    dates = pd.bdate_range("2024-01-01", periods=N_DAYS)
    index = pd.MultiIndex.from_product([dates, TICKERS], names=["date", "ticker"])
    close = np.column_stack([_random_walk(rng, N_DAYS) for _ in TICKERS]).ravel()
    return pd.DataFrame({"close": close}, index=index)


# --- Single series -------------------------------------------------------------

CAUSAL: dict[str, Callable[[Series], Series]] = {
    "trailing return": lambda p: p.pct_change(),
    "lag": lambda p: p.shift(1),
    "trailing rolling mean": lambda p: p.rolling(20).mean(),
    "exponential moving average": lambda p: p.ewm(span=10).mean(),
    "expanding z-score": lambda p: (p - p.expanding().mean()) / p.expanding().std(),
    "right-labelled weekly bars": lambda p: p.resample("W").last(),
}

LEAKY: dict[str, Callable[[Series], Series]] = {
    "negative shift": lambda p: p.shift(-1),
    "forward return used as a feature": lambda p: p.pct_change().shift(-1),
    "full-sample z-score": lambda p: (p - p.mean()) / p.std(),
    "full-sample percentile rank": lambda p: p.rank(pct=True),
    "full-sample min-max scaling": lambda p: (p - p.min()) / (p.max() - p.min()),
    "centred rolling window": lambda p: p.rolling(5, center=True).mean(),
    "left-labelled weekly bars": lambda p: p.resample("W", label="left").last(),
}


@pytest.mark.parametrize("transform", CAUSAL.values(), ids=CAUSAL.keys())
def test_causal_transform_passes(transform: Callable[[Series], Series], prices: Series) -> None:
    assert_no_lookahead(transform, prices)


@pytest.mark.parametrize("transform", LEAKY.values(), ids=LEAKY.keys())
def test_leaky_transform_fails(transform: Callable[[Series], Series], prices: Series) -> None:
    with pytest.raises(LookAheadError):
        assert_no_lookahead(transform, prices)


def test_forward_fill_is_causal_but_backward_fill_leaks(gappy_prices: Series) -> None:
    assert_no_lookahead(lambda p: p.ffill(), gappy_prices)
    with pytest.raises(LookAheadError):
        assert_no_lookahead(lambda p: p.bfill(), gappy_prices)


def test_interpolation_leaks(gappy_prices: Series) -> None:
    with pytest.raises(LookAheadError):
        assert_no_lookahead(lambda p: p.interpolate(), gappy_prices)


def test_perturbation_catches_what_truncation_misses(prices: Series) -> None:
    """A full-sample maximum reached on day one looks causal to truncation alone."""
    peaked = prices.copy()
    peaked.iloc[0] = 1.2 * prices.max()

    def drawdown_from_full_sample_peak(p: Series) -> Series:
        return p.div(p.max()) - 1

    assert_no_lookahead(drawdown_from_full_sample_peak, peaked, n_perturbations=0)
    with pytest.raises(LookAheadError, match="perturbed"):
        assert_no_lookahead(drawdown_from_full_sample_peak, peaked)


# --- Panels and frames ---------------------------------------------------------

PANEL_CAUSAL: dict[str, Callable[[pd.DataFrame], Series]] = {
    "per-ticker trailing return": lambda df: df.groupby(level="ticker")["close"].pct_change(),
    "cross-sectional rank per date": lambda df: df.groupby(level="date")["close"].rank(pct=True),
}

PANEL_LEAKY: dict[str, Callable[[pd.DataFrame], Series]] = {
    "per-ticker negative shift": lambda df: df.groupby(level="ticker")["close"].shift(-1),
    "per-ticker full-sample z-score": lambda df: df.groupby(level="ticker")["close"].transform(
        lambda p: (p - p.mean()) / p.std()
    ),
}


@pytest.mark.parametrize("transform", PANEL_CAUSAL.values(), ids=PANEL_CAUSAL.keys())
def test_causal_panel_transform_passes(
    transform: Callable[[pd.DataFrame], Series], panel: pd.DataFrame
) -> None:
    assert_no_lookahead(transform, panel)


@pytest.mark.parametrize("transform", PANEL_LEAKY.values(), ids=PANEL_LEAKY.keys())
def test_leaky_panel_transform_fails(
    transform: Callable[[pd.DataFrame], Series], panel: pd.DataFrame
) -> None:
    with pytest.raises(LookAheadError):
        assert_no_lookahead(transform, panel)


def test_time_level_can_be_chosen_by_name(panel: pd.DataFrame) -> None:
    ticker_first = panel.reorder_levels(["ticker", "date"]).sort_index()
    assert_no_lookahead(
        lambda df: df.groupby(level="ticker")["close"].pct_change(), ticker_first, level="date"
    )


def test_non_numeric_columns_are_carried_through(prices: Series) -> None:
    frame = pd.DataFrame({"close": prices, "sector": "tech", "halted": False})
    assert_no_lookahead(lambda df: df.assign(ret=df["close"].pct_change()), frame)


def test_output_may_drop_rows(prices: Series) -> None:
    assert_no_lookahead(lambda p: p.pct_change().dropna(), prices)


# --- Diagnostics ---------------------------------------------------------------


def test_error_names_the_cutoff_probe_and_first_difference(prices: Series) -> None:
    first_day = prices.index[0].date().isoformat()
    with pytest.raises(LookAheadError) as caught:
        assert_no_lookahead(lambda p: p.shift(-1), prices)
    message = str(caught.value)
    assert f"outputs at or before {first_day} changed" in message
    assert "inputs after it were dropped" in message
    assert f"first difference at {first_day}, column 'close'" in message


@pytest.mark.parametrize(
    ("transform", "message"),
    [
        (lambda p: p.iloc[: len(p) // 2], "row\\(s\\) disappeared"),
        (lambda p: p.iloc[-(len(p) // 2) :], "row\\(s\\) appeared"),
        (lambda p: p.iloc[::-1] if len(p) % 2 else p, "reordered"),
    ],
    ids=["rows disappear", "rows appear", "rows reorder"],
)
def test_error_describes_changed_rows(
    transform: Callable[[Series], Series], message: str, prices: Series
) -> None:
    with pytest.raises(LookAheadError, match=message):
        assert_no_lookahead(transform, prices)


def test_error_describes_changed_columns(prices: Series) -> None:
    with pytest.raises(LookAheadError, match="columns changed"):
        assert_no_lookahead(lambda p: p.to_frame(f"close_{len(p)}"), prices)


def test_labels_are_compared_exactly(prices: Series) -> None:
    def regime(p: Series) -> Series:
        return (p > p.median()).map({True: "high", False: "low"})

    with pytest.raises(LookAheadError, match=r"'high'|'low'"):
        assert_no_lookahead(regime, prices)


# --- Guard rails ---------------------------------------------------------------


def test_does_not_mutate_input(prices: Series) -> None:
    before = prices.copy()
    assert_no_lookahead(lambda p: p.pct_change(), prices)
    pd.testing.assert_series_equal(prices, before)


def test_transform_that_mutates_its_input_cannot_corrupt_the_check(prices: Series) -> None:
    def in_place_return(df: pd.DataFrame) -> Series:
        df["close"] = df["close"].pct_change()
        return df["close"]

    frame = prices.to_frame()
    assert_no_lookahead(in_place_return, frame)
    pd.testing.assert_frame_equal(frame, prices.to_frame())


def test_differences_within_tolerance_are_ignored(prices: Series) -> None:
    def length_dependent_rounding(p: Series) -> Series:
        return p.pct_change() * (1 + 1e-13 * math.sin(len(p)))

    assert_no_lookahead(length_dependent_rounding, prices)
    with pytest.raises(LookAheadError):
        assert_no_lookahead(length_dependent_rounding, prices, rtol=0.0, atol=0.0)


def test_truncation_only_mode_for_non_numeric_data(prices: Series) -> None:
    moves = pd.Series(np.where(prices.diff() > 0, "up", "down"), index=prices.index)
    with pytest.raises(ValueError, match="n_perturbations=0"):
        assert_no_lookahead(lambda s: s.shift(1), moves)
    assert_no_lookahead(lambda s: s.shift(1), moves, n_perturbations=0)
    with pytest.raises(LookAheadError):
        assert_no_lookahead(lambda s: s.shift(-1), moves, n_perturbations=0)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [({"n_cutoffs": 0}, "n_cutoffs"), ({"n_perturbations": -1}, "n_perturbations")],
)
def test_rejects_invalid_arguments(prices: Series, kwargs: dict[str, int], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        assert_no_lookahead(lambda p: p, prices, **kwargs)


def test_rejects_data_without_a_future(prices: Series) -> None:
    with pytest.raises(ValueError, match="two distinct timestamps"):
        assert_no_lookahead(lambda p: p, prices.iloc[:1])


def test_rejects_output_that_is_not_pandas(prices: Series) -> None:
    with pytest.raises(TypeError, match="Series or DataFrame"):
        assert_no_lookahead(lambda p: p.to_numpy(), prices)  # type: ignore[arg-type, return-value]


def test_rejects_output_not_indexed_by_time(prices: Series) -> None:
    with pytest.raises(TypeError, match="indexed by time"):
        assert_no_lookahead(lambda p: p.reset_index(drop=True), prices)
