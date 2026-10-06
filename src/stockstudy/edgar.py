"""Point-in-time company fundamentals from SEC EDGAR.

The SEC publishes every XBRL fact a US-listed company has filed, each tagged with the
filing that reported it. Because each version of a figure keeps its own filing date,
restated figures do not overwrite the originals, and the facts feed straight into
:mod:`stockstudy.pit`.

Availability: a filing's date does not say whether it arrived before or after the
market close, so a fact filed on day *D* becomes available at the next session, *D + 1*.
That costs at most one day and never lets an after-hours filing leak into day *D*.

Fair access: the SEC requires every automated request to identify a contact
(``"Name email@example.com"``) and to stay under 10 requests per second. The contact is
read from the ``SEC_USER_AGENT`` environment variable, never from code.

Every download is saved, gzipped and named by retrieval time and content hash, so the
project accumulates its own record of what the SEC published and when.

Run ``python -m stockstudy.edgar AAPL MSFT`` to download and record the facts for some
tickers.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import logging
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pandas as pd
from pandas.tseries.offsets import BDay

from stockstudy.pit import FACT_COLUMNS

__all__ = [
    "SEC_USER_AGENT_ENV",
    "EdgarClient",
    "Snapshot",
    "parse_company_facts",
    "read_snapshot",
]

SEC_USER_AGENT_ENV = "SEC_USER_AGENT"

_COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_MIN_INTERVAL_SECONDS = 0.125  # 8 requests per second, under the SEC's limit of 10

type Fetch = Callable[[str, Mapping[str, str]], bytes]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Snapshot:
    """A recorded download: what was fetched, when, and its content hash."""

    url: str
    retrieved_at: pd.Timestamp
    sha256: str
    path: Path | None


class EdgarClient:
    """Rate-limited EDGAR client that records every response it receives."""

    def __init__(
        self,
        user_agent: str | None = None,
        *,
        cache_dir: Path | None = None,
        fetch: Fetch | None = None,
        min_interval: float = _MIN_INTERVAL_SECONDS,
    ) -> None:
        """Configure the client.

        Args:
            user_agent: Contact identifying you to the SEC, such as
                ``"Jane Doe jane@example.com"``. Defaults to the ``SEC_USER_AGENT``
                environment variable.
            cache_dir: Directory for recorded downloads. ``None`` records nothing.
            fetch: Function performing the HTTP GET; replaceable for testing.
            min_interval: Minimum seconds between requests.

        Raises:
            ValueError: No contact email is configured.
        """
        agent = os.environ.get(SEC_USER_AGENT_ENV, "") if user_agent is None else user_agent
        if "@" not in agent:
            raise ValueError(
                f"set {SEC_USER_AGENT_ENV} to a contact name and email, such as "
                "'Jane Doe jane@example.com': the SEC refuses requests without one"
            )
        self._headers = {"User-Agent": agent}
        self._cache_dir = cache_dir
        self._fetch = fetch or _urllib_fetch
        self._min_interval = min_interval
        self._last_request = float("-inf")

    def company_facts(self, cik: str | int) -> pd.DataFrame:
        """Download every XBRL fact a company has filed, in the point-in-time schema."""
        padded = f"{int(cik):010d}"
        payload, _ = self.get_json(_COMPANY_FACTS_URL.format(cik=padded), name=f"CIK{padded}")
        return parse_company_facts(payload)

    def tickers(self) -> dict[str, str]:
        """Map tickers to zero-padded CIKs.

        The SEC publishes only the current mapping: tickers of delisted companies are
        missing and reused tickers point to their current owner. Use it to look up
        today's companies, never to build a historical universe.
        """
        payload, _ = self.get_json(_TICKERS_URL, name="company_tickers")
        return {row["ticker"]: f"{int(row['cik_str']):010d}" for row in payload.values()}

    def get_json(self, url: str, *, name: str) -> tuple[Any, Snapshot]:
        """Fetch and decode a JSON document, recording the raw response under ``name``."""
        wait = self._last_request + self._min_interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()
        raw = self._fetch(url, self._headers)
        snapshot = self._record(url, name, raw)
        return json.loads(raw), snapshot

    def _record(self, url: str, name: str, raw: bytes) -> Snapshot:
        retrieved_at = pd.Timestamp.now(tz="UTC")
        digest = hashlib.sha256(raw).hexdigest()
        path = None
        if self._cache_dir is not None:
            stamp = retrieved_at.strftime("%Y%m%dT%H%M%S%fZ")
            path = self._cache_dir / name / f"{stamp}-{digest[:12]}.json.gz"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(gzip.compress(raw))
        return Snapshot(url=url, retrieved_at=retrieved_at, sha256=digest, path=path)


def parse_company_facts(payload: Mapping[str, Any]) -> pd.DataFrame:
    """Flatten an EDGAR ``companyfacts`` document into the point-in-time schema.

    Args:
        payload: Decoded JSON from ``/api/xbrl/companyfacts/CIK##########.json``.

    Returns:
        One row per reported fact and filing, with columns :data:`FACT_COLUMNS`.
        ``available_at`` is the business day after the filing date.
    """
    cik = f"{int(payload['cik']):010d}"
    rows = [
        {
            "cik": cik,
            "taxonomy": taxonomy,
            "concept": concept,
            "unit": unit,
            "period_start": fact.get("start"),
            "period_end": fact["end"],
            "value": fact["val"],
            "fiscal_year": fact.get("fy"),
            "fiscal_period": fact.get("fp"),
            "form": fact.get("form"),
            "accession": fact["accn"],
            "filed": fact["filed"],
        }
        for taxonomy, concepts in payload.get("facts", {}).items()
        for concept, body in concepts.items()
        for unit, facts in body.get("units", {}).items()
        for fact in facts
    ]
    frame = pd.DataFrame(rows, columns=FACT_COLUMNS[:-1])
    for column in ("period_start", "period_end", "filed"):
        frame[column] = pd.to_datetime(frame[column])
    frame["value"] = frame["value"].astype(float)
    frame["fiscal_year"] = frame["fiscal_year"].astype("Int64")
    frame["available_at"] = frame["filed"] + BDay(1)
    return frame


def read_snapshot(path: Path) -> pd.DataFrame:
    """Parse a recorded ``companyfacts`` download, so analyses can rerun offline."""
    return parse_company_facts(json.loads(gzip.decompress(path.read_bytes())))


def _urllib_fetch(url: str, headers: Mapping[str, str]) -> bytes:
    if urlsplit(url).scheme not in {"http", "https"}:
        raise ValueError(f"refusing to fetch a non-HTTP URL: {url}")
    request = urllib.request.Request(url, headers=dict(headers))  # noqa: S310 (scheme checked)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 (scheme checked)
            body: bytes = response.read()
            return body
    except urllib.error.HTTPError as error:
        if error.code == 403:
            raise PermissionError(
                f"the SEC refused {url}: check that {SEC_USER_AGENT_ENV} holds a real contact "
                "name and email, and that requests stay under 10 per second"
            ) from error
        raise


def main(argv: list[str] | None = None) -> int:
    """Download and record the EDGAR facts for the given tickers or CIKs."""
    parser = argparse.ArgumentParser(prog="python -m stockstudy.edgar", description=main.__doc__)
    parser.add_argument("symbols", nargs="+", help="tickers (AAPL) or CIK numbers (320193)")
    parser.add_argument("--cache-dir", type=Path, default=Path("data/raw/edgar"))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    client = EdgarClient(cache_dir=args.cache_dir)
    symbols: list[str] = args.symbols
    tickers = client.tickers() if any(not s.isdigit() for s in symbols) else {}
    for symbol in symbols:
        cik = symbol if symbol.isdigit() else tickers.get(symbol.upper())
        if cik is None:
            logger.error("%s: not in the SEC's current ticker list", symbol)
            continue
        facts = client.company_facts(cik)
        logger.info(
            "%s (CIK %s): %d facts across %d concepts, filed %s to %s",
            symbol,
            f"{int(cik):010d}",
            len(facts),
            facts["concept"].nunique(),
            facts["filed"].min().date(),
            facts["filed"].max().date(),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
