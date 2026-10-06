"""Tests for stockstudy.edgar. No test touches the network beyond localhost."""

import json
import logging
import threading
import time
from collections.abc import Iterator, Mapping
from http.server import BaseHTTPRequestHandler, HTTPServer
from itertools import pairwise
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from stockstudy.edgar import (
    SEC_USER_AGENT_ENV,
    EdgarClient,
    _urllib_fetch,
    main,
    parse_company_facts,
    read_snapshot,
)
from stockstudy.pit import FACT_COLUMNS

AGENT = "Test Researcher test@example.com"
TICKERS = {"0": {"cik_str": 1234, "ticker": "ACME", "title": "Acme Corp"}}


class FakeSec:
    """Stands in for the SEC: serves fixed documents and records each request."""

    def __init__(self, company_facts: Mapping[str, Any]) -> None:
        self.company_facts = company_facts
        self.requests: list[tuple[str, dict[str, str], float]] = []

    def __call__(self, url: str, headers: Mapping[str, str]) -> bytes:
        self.requests.append((url, dict(headers), time.monotonic()))
        document = TICKERS if url.endswith("company_tickers.json") else self.company_facts
        return json.dumps(document).encode()


# --- Parsing -------------------------------------------------------------------


def test_parse_produces_the_point_in_time_schema(acme: dict[str, Any]) -> None:
    facts = parse_company_facts(acme)
    assert list(facts.columns) == FACT_COLUMNS
    assert set(facts["cik"]) == {"0000001234"}
    assert facts["value"].dtype == float
    assert str(facts["fiscal_year"].dtype) == "Int64"


def test_facts_become_available_the_business_day_after_filing(acme: dict[str, Any]) -> None:
    facts = parse_company_facts(acme)
    friday = facts[facts["filed"] == pd.Timestamp("2023-11-03")]
    assert set(friday["available_at"]) == {pd.Timestamp("2023-11-06")}  # the next Monday


def test_instant_facts_have_no_period_start(acme: dict[str, Any]) -> None:
    facts = parse_company_facts(acme)
    assets = facts[facts["concept"] == "Assets"]
    assert assets["period_start"].isna().all()


def test_restated_versions_are_kept_side_by_side(acme: dict[str, Any]) -> None:
    facts = parse_company_facts(acme)
    fy2022 = facts[(facts["concept"] == "Revenues") & (facts["period_end"] == "2022-09-30")]
    assert sorted(fy2022["value"]) == [98.0, 100.0]


# --- Client ----------------------------------------------------------------------


@pytest.mark.parametrize("agent", ["", "StockStudy research"])
def test_client_requires_a_contact_email(agent: str) -> None:
    with pytest.raises(ValueError, match=SEC_USER_AGENT_ENV):
        EdgarClient(agent)


def test_client_reads_the_contact_from_the_environment(
    monkeypatch: pytest.MonkeyPatch, acme: dict[str, Any]
) -> None:
    sec = FakeSec(acme)
    monkeypatch.setenv(SEC_USER_AGENT_ENV, AGENT)
    EdgarClient(fetch=sec).company_facts(1234)
    assert sec.requests[0][1] == {"User-Agent": AGENT}

    monkeypatch.delenv(SEC_USER_AGENT_ENV)
    with pytest.raises(ValueError, match=SEC_USER_AGENT_ENV):
        EdgarClient(fetch=sec)


def test_company_facts_are_recorded_and_can_be_replayed(
    tmp_path: Path, acme: dict[str, Any]
) -> None:
    sec = FakeSec(acme)
    facts = EdgarClient(AGENT, cache_dir=tmp_path, fetch=sec).company_facts("1234")

    assert sec.requests[0][0] == "https://data.sec.gov/api/xbrl/companyfacts/CIK0000001234.json"
    [recorded] = (tmp_path / "CIK0000001234").glob("*.json.gz")
    pd.testing.assert_frame_equal(read_snapshot(recorded), facts)


def test_snapshot_carries_retrieval_time_and_hash(acme: dict[str, Any]) -> None:
    client = EdgarClient(AGENT, fetch=FakeSec(acme))
    _, snapshot = client.get_json("https://example.test/doc.json", name="doc")
    assert snapshot.path is None
    assert len(snapshot.sha256) == 64
    assert snapshot.retrieved_at.tzinfo is not None


def test_tickers_map_to_padded_ciks(acme: dict[str, Any]) -> None:
    assert EdgarClient(AGENT, fetch=FakeSec(acme)).tickers() == {"ACME": "0000001234"}


def test_requests_are_spaced_out(acme: dict[str, Any]) -> None:
    sec = FakeSec(acme)
    client = EdgarClient(AGENT, fetch=sec, min_interval=0.05)
    for _ in range(3):
        client.get_json("https://example.test/doc.json", name="doc")
    times = [stamp for _, _, stamp in sec.requests]
    assert all(later - earlier >= 0.05 for earlier, later in pairwise(times))


# --- HTTP transport, against a local server ----------------------------------------


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        status = {"/ok": 200, "/forbidden": 403}.get(self.path, 404)
        body = self.headers["User-Agent"].encode()
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:  # keep test output quiet
        pass


@pytest.fixture
def server() -> Iterator[str]:
    httpd = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()
    httpd.server_close()


def test_transport_sends_headers_and_returns_the_body(server: str) -> None:
    assert _urllib_fetch(f"{server}/ok", {"User-Agent": AGENT}) == AGENT.encode()


def test_transport_explains_an_sec_refusal(server: str) -> None:
    with pytest.raises(PermissionError, match=SEC_USER_AGENT_ENV):
        _urllib_fetch(f"{server}/forbidden", {"User-Agent": AGENT})


def test_transport_passes_other_http_errors_through(server: str) -> None:
    with pytest.raises(OSError, match="404"):
        _urllib_fetch(f"{server}/missing", {"User-Agent": AGENT})


def test_transport_refuses_non_http_urls() -> None:
    with pytest.raises(ValueError, match="non-HTTP"):
        _urllib_fetch("file:///etc/passwd", {})


# --- Command line ------------------------------------------------------------------


def test_main_records_facts_for_tickers_and_ciks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    acme: dict[str, Any],
) -> None:
    monkeypatch.setenv(SEC_USER_AGENT_ENV, AGENT)
    monkeypatch.setattr("stockstudy.edgar._urllib_fetch", FakeSec(acme))
    with caplog.at_level(logging.INFO, logger="stockstudy.edgar"):
        assert main(["acme", "1234", "NOPE", "--cache-dir", str(tmp_path)]) == 0

    assert "acme (CIK 0000001234): 6 facts across 3 concepts" in caplog.text
    assert "NOPE: not in the SEC's current ticker list" in caplog.text
    assert len(list((tmp_path / "CIK0000001234").glob("*.json.gz"))) == 2
