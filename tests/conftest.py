"""Shared fixtures: a small EDGAR companyfacts document in the SEC's real format."""

from typing import Any

import pandas as pd
import pytest

from stockstudy.edgar import parse_company_facts


def _fact(**fields: Any) -> dict[str, Any]:
    return {"fy": None, "fp": None, "form": "10-K", "frame": None, **fields}


# Fiscal 2022 revenue is reported as 100 in the 2022 annual report, then restated to 98 in
# the 2023 annual report alongside fiscal 2023 revenue of 120. Filing dates are Fridays,
# so each figure becomes available the following Monday.
ACME: dict[str, Any] = {
    "cik": 1234,
    "entityName": "Acme Corp",
    "facts": {
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        _fact(
                            start="2021-10-01",
                            end="2022-09-30",
                            val=100,
                            accn="0000001234-22-000010",
                            fy=2022,
                            fp="FY",
                            filed="2022-11-04",
                        ),
                        _fact(
                            start="2021-10-01",
                            end="2022-09-30",
                            val=98,
                            accn="0000001234-23-000012",
                            fy=2023,
                            fp="FY",
                            filed="2023-11-03",
                        ),
                        _fact(
                            start="2022-10-01",
                            end="2023-09-30",
                            val=120,
                            accn="0000001234-23-000012",
                            fy=2023,
                            fp="FY",
                            filed="2023-11-03",
                        ),
                        _fact(
                            start="2022-10-01",
                            end="2022-12-31",
                            val=27,
                            form="10-Q",
                            accn="0000001234-23-000002",
                            fy=2023,
                            fp="Q1",
                            filed="2023-02-03",
                        ),
                    ]
                }
            },
            "Assets": {
                "units": {
                    "USD": [
                        _fact(
                            end="2022-09-30",
                            val=500,
                            accn="0000001234-22-000010",
                            fy=2022,
                            fp="FY",
                            filed="2022-11-04",
                        ),
                    ]
                }
            },
        },
        "dei": {
            "EntityCommonStockSharesOutstanding": {
                "units": {
                    "shares": [
                        _fact(
                            end="2022-10-28",
                            val=1_000_000,
                            accn="0000001234-22-000010",
                            fy=2022,
                            fp="FY",
                            filed="2022-11-04",
                        ),
                    ]
                }
            }
        },
    },
}

# A second company whose first annual report arrives later than Acme's.
BOLT: dict[str, Any] = {
    "cik": 5678,
    "entityName": "Bolt Inc",
    "facts": {
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        _fact(
                            start="2022-01-01",
                            end="2022-12-31",
                            val=40,
                            accn="0000005678-23-000001",
                            fy=2022,
                            fp="FY",
                            filed="2023-03-03",
                        ),
                    ]
                }
            }
        }
    },
}


@pytest.fixture
def facts() -> pd.DataFrame:
    return pd.concat([parse_company_facts(ACME), parse_company_facts(BOLT)], ignore_index=True)


@pytest.fixture
def acme() -> dict[str, Any]:
    return ACME
