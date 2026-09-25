"""Executable check that a time-series transform never uses future information.

Look-ahead bias makes worthless signals look brilliant, and it is hard to see in review:
``shift(-1)``, a full-sample z-score, a centred rolling window and a backward fill all read
the future while looking innocent. :func:`assert_no_lookahead` turns the rule *an output
stamped at time t may depend only on inputs stamped at or before t* into a test that fails
loudly.

At several cut-off times *t* it runs two complementary probes, and every output at or
before *t* must survive both unchanged:

* **truncation** drops the input rows after *t* and re-runs the transform;
* **perturbation** randomly rescales every numeric input after *t*, keeping the length of
  the data, and re-runs the transform.

Truncation catches dependence on whether later rows exist at all (negative shifts,
full-sample statistics, centred windows, backward fills). Perturbation catches dependence
on later *values* where truncation happens to agree, such as a full-sample maximum that
was reached before *t*.

The check is only as strong as the data it is given: use enough rows to fill the
transform's windows, and include missing values if the transform fills them.

Example:
    >>> import numpy as np
    >>> import pandas as pd
    >>> prices = pd.Series(
    ...     np.linspace(100.0, 120.0, 60), index=pd.bdate_range("2024-01-01", periods=60)
    ... )
    >>> assert_no_lookahead(lambda p: p.pct_change(), prices)  # trailing return: passes
    >>> assert_no_lookahead(lambda p: p.pct_change().shift(-1), prices)  # forward return
    Traceback (most recent call last):
    LookAheadError: ...
"""

from __future__ import annotations

from collections.abc import Callable, Hashable
from typing import Any, Literal

import numpy as np
import numpy.typing as npt
import pandas as pd

__all__ = ["LookAheadError", "assert_no_lookahead"]

type Frame = pd.Series[Any] | pd.DataFrame
type Probe = Literal["dropped", "perturbed"]

# Perturbed values are multiplied by exp(N(0, sigma^2)). A positive factor preserves signs,
# so prices and volumes stay valid inputs; sigma = 0.5 moves a typical value by about 50%.
_NOISE_SIGMA = 0.5


class LookAheadError(AssertionError):
    """An output at or before time *t* changed when only inputs after *t* changed."""


def assert_no_lookahead[T: (pd.Series[Any], pd.DataFrame)](
    transform: Callable[[T], Frame],
    data: T,
    *,
    n_cutoffs: int = 8,
    n_perturbations: int = 2,
    level: int | str = 0,
    seed: int = 0,
    rtol: float = 1e-9,
    atol: float = 1e-12,
) -> None:
    """Assert that no output of ``transform`` depends on later inputs.

    Args:
        transform: Deterministic function from time-indexed data to time-indexed output,
            such as a feature or signal constructor. It receives a private copy of the
            data on every call.
        data: Input indexed by time, or by a ``MultiIndex`` with a time level such as a
            ``(date, ticker)`` panel. Any sortable index type works as time.
        n_cutoffs: Number of cut-off times, spread evenly from the first timestamp to the
            second-to-last. More cut-offs are more thorough and slower.
        n_perturbations: Random perturbations per cut-off. Use ``0`` to run the
            truncation probe only, which is required when ``data`` has no numeric values.
        level: The ``MultiIndex`` level that holds time, for the input and the output.
            Ignored for a flat index.
        seed: Seed for the perturbations, so that any failure is reproducible.
        rtol: Relative tolerance when comparing numeric outputs.
        atol: Absolute tolerance when comparing numeric outputs.

    Raises:
        LookAheadError: An output at or before some cut-off changed when the inputs after
            that cut-off were dropped or perturbed.
        ValueError: The arguments or the data cannot support a meaningful check.
        TypeError: ``transform`` did not return a time-indexed Series or DataFrame.
    """
    if n_cutoffs < 1:
        raise ValueError(f"n_cutoffs must be at least 1, got {n_cutoffs}")
    if n_perturbations < 0:
        raise ValueError(f"n_perturbations must be non-negative, got {n_perturbations}")
    if n_perturbations and not _numeric_columns(_as_frame(data)):
        raise ValueError(
            "data has no numeric values to perturb; pass n_perturbations=0 to run the "
            "truncation probe only"
        )

    times = _times(data.index, level)
    rng = np.random.default_rng(seed)
    baseline = _run(transform, data)
    for cutoff in _cutoffs(times, n_cutoffs):
        past = np.asarray(times <= cutoff)
        _compare(baseline, _run(transform, data[past]), cutoff, level, "dropped", rtol, atol)
        for _ in range(n_perturbations):
            probe = _run(transform, _perturb(data, ~past, rng))
            _compare(baseline, probe, cutoff, level, "perturbed", rtol, atol)


def _run[T: (pd.Series[Any], pd.DataFrame)](
    transform: Callable[[T], Frame], data: T
) -> pd.DataFrame:
    """Apply ``transform`` to a copy of ``data`` and return its output as a DataFrame."""
    output: object = transform(data.copy())
    if isinstance(output, pd.Series | pd.DataFrame):
        return _as_frame(output)
    raise TypeError(
        f"transform must return a pandas Series or DataFrame, got {type(output).__name__}"
    )


def _as_frame(data: Frame) -> pd.DataFrame:
    return data.to_frame() if isinstance(data, pd.Series) else data


def _times(index: pd.Index, level: int | str) -> pd.Index:
    """The timestamp of each row: the index itself, or one level of a MultiIndex."""
    return index.get_level_values(level) if isinstance(index, pd.MultiIndex) else index


def _cutoffs(times: pd.Index, n_cutoffs: int) -> pd.Index:
    """Evenly spaced distinct times, excluding the last so that each has a future."""
    distinct = times.unique().sort_values()
    if len(distinct) < 2:
        raise ValueError("data must span at least two distinct timestamps")
    positions = np.linspace(0, len(distinct) - 2, num=n_cutoffs).round().astype(int)
    return distinct[np.unique(positions)]


def _perturb[T: (pd.Series[Any], pd.DataFrame)](
    data: T, future: npt.NDArray[np.bool_], rng: np.random.Generator
) -> T:
    """Return a copy of ``data`` whose numeric values in ``future`` rows are rescaled.

    Each value gets its own random factor, so relative magnitudes, ranks and extremes
    among the future values all change, while signs and zeros are preserved.
    """
    frame = _as_frame(data).copy()
    for column in _numeric_columns(frame):
        values = frame.iloc[:, column].to_numpy(dtype=float, na_value=np.nan, copy=True)
        values[future] *= rng.lognormal(0.0, _NOISE_SIGMA, size=int(future.sum()))
        frame.isetitem(column, values)
    if isinstance(data, pd.Series):
        series: pd.Series[Any] = frame.iloc[:, 0]
        series.name = data.name
        return series
    return frame


def _numeric_columns(frame: pd.DataFrame) -> list[int]:
    """Positions of columns holding numbers (booleans excluded)."""
    return [i for i in range(frame.shape[1]) if _is_numeric(frame.iloc[:, i])]


def _is_numeric(series: pd.Series[Any]) -> bool:
    return pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series)


def _compare(
    baseline: pd.DataFrame,
    probe: pd.DataFrame,
    cutoff: Hashable,
    level: int | str,
    how: Probe,
    rtol: float,
    atol: float,
) -> None:
    """Raise LookAheadError if ``probe`` differs from ``baseline`` at or before ``cutoff``."""
    difference = _first_difference(
        _up_to(baseline, cutoff, level), _up_to(probe, cutoff, level), how, rtol, atol
    )
    if difference is not None:
        raise LookAheadError(
            f"outputs at or before {_fmt(cutoff)} changed when the inputs after it were "
            f"{how}: {difference}"
        )


def _up_to(frame: pd.DataFrame, cutoff: Hashable, level: int | str) -> pd.DataFrame:
    try:
        return frame[np.asarray(_times(frame.index, level) <= cutoff)]
    except TypeError as error:
        raise TypeError(
            "transform output must be indexed by time like its input, so that outputs "
            f"can be compared with the cut-off {_fmt(cutoff)}"
        ) from error


def _first_difference(
    expected: pd.DataFrame, actual: pd.DataFrame, how: Probe, rtol: float, atol: float
) -> str | None:
    """Describe the earliest difference between two outputs, or return None if they match."""
    if not expected.index.equals(actual.index):
        missing = expected.index.difference(actual.index, sort=False)
        extra = actual.index.difference(expected.index, sort=False)
        if len(missing):
            return f"{len(missing)} output row(s) disappeared, first at {_fmt(missing[0])}"
        if len(extra):
            return f"{len(extra)} output row(s) appeared, first at {_fmt(extra[0])}"
        return "output rows were reordered or duplicated"
    if not expected.columns.equals(actual.columns):
        return f"output columns changed from {list(expected.columns)} to {list(actual.columns)}"

    differs = ~_same_values(expected, actual, rtol, atol)
    if not differs.any():
        return None
    row, column = np.argwhere(differs)[0]
    before, after = _scalar(expected.iloc[row, column]), _scalar(actual.iloc[row, column])
    return (
        f"first difference at {_fmt(expected.index[row])}, column {expected.columns[column]!r}: "
        f"{before!r} originally, {after!r} when {how}"
    )


def _same_values(
    expected: pd.DataFrame, actual: pd.DataFrame, rtol: float, atol: float
) -> npt.NDArray[np.bool_]:
    """Element-wise equality of two equally shaped frames; numbers within tolerance."""
    same = np.ones(expected.shape, dtype=bool)
    for i in range(expected.shape[1]):
        left, right = expected.iloc[:, i], actual.iloc[:, i]
        missing = left.isna().to_numpy() & right.isna().to_numpy()
        if _is_numeric(left) and _is_numeric(right):
            equal = np.isclose(
                left.to_numpy(dtype=float, na_value=np.nan),
                right.to_numpy(dtype=float, na_value=np.nan),
                rtol=rtol,
                atol=atol,
            )
        else:
            equal = left.eq(right).to_numpy(dtype=bool, na_value=False)
        same[:, i] = equal | missing
    return same


def _scalar(value: object) -> object:
    """Unwrap numpy scalars so that messages show ``1.5`` rather than ``np.float64(1.5)``."""
    return value.item() if isinstance(value, np.generic) else value


def _fmt(label: object) -> str:
    """Render an index label compactly: dates without a midnight time, tuples flattened."""
    if isinstance(label, tuple):
        return "(" + ", ".join(_fmt(part) for part in label) + ")"
    if isinstance(label, pd.Timestamp) and label == label.normalize():
        return label.date().isoformat()
    return str(label)
