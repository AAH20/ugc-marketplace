"""Pin correct API route paths: no doubled path segments, intended paths reachable.

Regression test for the bug where routers declared a prefix that already
included the mount path (e.g. APIRouter(prefix="/api/v1/payments") mounted
again at "/payments" under "/api/v1"), producing doubled segments such as
``/api/v1/payments/api/v1/payments``.
"""

from __future__ import annotations

import re

from ugc_marketplace.main import app

# A doubled segment: the same path component appearing twice in a row,
# e.g. /analytics/analytics or /payments/api/v1/payments.
_DOUBLED = re.compile(r"/([a-z0-9_-]+)/\1(/|$)")

# Baseline path count captured before the fix (see task spec).
_EXPECTED_TOTAL_PATHS = 167

# Representative intended paths (the single-segment form each route must serve).
_INTENDED_PATHS = [
    "/api/v1/payments",
    "/api/v1/analytics/audience/analyze",
    "/api/v1/discovery/search",
    "/api/v1/monetization/metrics",
    "/api/v1/rights/licenses",
    "/api/v1/curation/curate",
    "/api/v1/marketplace/listings",
    "/api/v1/quality/score",
    "/api/v1/fraud/analyze",
    "/api/v1/licensing/licenses",
    "/api/v1/creators",
    "/api/v1/content",
    "/api/v1/transactions",
    "/api/v1/notifications",
    "/api/v1/categories",
    "/api/v1/tags/",
    "/api/v1/reviews",
    "/api/v1/listings/",
]


def _paths() -> list[str]:
    return list(app.openapi()["paths"])


def test_no_doubled_path_segments() -> None:
    """No served path may contain a doubled path segment."""
    doubled = [p for p in _paths() if _DOUBLED.search(p)]
    assert doubled == [], f"{len(doubled)} paths have doubled segments: {doubled[:10]}"


def test_total_path_count_preserved() -> None:
    """The total number of served paths must not drop (routes must stay reachable)."""
    assert len(_paths()) == _EXPECTED_TOTAL_PATHS


def test_intended_paths_exist() -> None:
    """Every representative endpoint is served at its correct single-segment path."""
    paths = set(_paths())
    missing = [p for p in _INTENDED_PATHS if p not in paths]
    assert missing == [], f"missing intended paths: {missing}"
