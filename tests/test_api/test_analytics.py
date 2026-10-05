"""Comprehensive API tests for the Analytics endpoints.

Tests cover:
- GET /api/v1/analytics
- GET /api/v1/analytics/creators
- GET /api/v1/analytics/content
- GET /api/v1/analytics/revenue
"""

import pytest
from fastapi.testclient import TestClient
from httpx import Response


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    """Return a FastAPI TestClient for the application."""
    from ugc_marketplace.main import app

    return TestClient(app)


@pytest.fixture
def analytics_base_url() -> str:
    """Base URL for analytics endpoints."""
    return "/api/v1/analytics"


@pytest.fixture
def sample_analytics_response() -> dict:
    """Sample response payload for GET /api/v1/analytics."""
    return {
        "total_creators": 150,
        "total_content": 3200,
        "total_revenue": 125000.50,
        "active_creators": 89,
        "published_content": 2800,
        "period": "last_30_days",
    }


@pytest.fixture
def sample_creator_analytics_response() -> dict:
    """Sample response payload for GET /api/v1/analytics/creators."""
    return {
        "creators": [
            {
                "creator_id": "creator-001",
                "username": "alice",
                "content_count": 45,
                "total_views": 12000,
                "total_revenue": 5200.00,
                "engagement_rate": 0.085,
            },
            {
                "creator_id": "creator-002",
                "username": "bob",
                "content_count": 30,
                "total_views": 8500,
                "total_revenue": 3100.00,
                "engagement_rate": 0.072,
            },
        ],
        "total": 2,
        "page": 1,
        "page_size": 50,
    }


@pytest.fixture
def sample_content_analytics_response() -> dict:
    """Sample response payload for GET /api/v1/analytics/content."""
    return {
        "content": [
            {
                "content_id": "content-001",
                "title": "Summer Campaign",
                "creator_id": "creator-001",
                "views": 5000,
                "likes": 320,
                "shares": 45,
                "revenue": 1200.00,
            },
            {
                "content_id": "content-002",
                "title": "Winter Collection",
                "creator_id": "creator-002",
                "views": 3500,
                "likes": 210,
                "shares": 30,
                "revenue": 800.00,
            },
        ],
        "total": 2,
        "page": 1,
        "page_size": 50,
    }


@pytest.fixture
def sample_revenue_analytics_response() -> dict:
    """Sample response payload for GET /api/v1/analytics/revenue."""
    return {
        "total_revenue": 125000.50,
        "currency": "USD",
        "period": "last_30_days",
        "breakdown": [
            {"date": "2026-09-01", "revenue": 4200.00},
            {"date": "2026-09-02", "revenue": 3800.50},
            {"date": "2026-09-03", "revenue": 5100.00},
        ],
        "top_earners": [
            {"creator_id": "creator-001", "revenue": 5200.00},
            {"creator_id": "creator-002", "revenue": 3100.00},
        ],
    }


# ---------------------------------------------------------------------------
# GET /api/v1/analytics
# ---------------------------------------------------------------------------


class TestGetAnalytics:
    """Tests for GET /api/v1/analytics."""

    def test_get_analytics_success(
        self, client: TestClient, analytics_base_url: str, sample_analytics_response: dict
    ) -> None:
        """GET /api/v1/analytics returns 200 with valid analytics data."""
        response: Response = client.get(analytics_base_url)

        assert response.status_code == 200
        data = response.json()
        assert "total_creators" in data
        assert "total_content" in data
        assert "total_revenue" in data
        assert "active_creators" in data
        assert "published_content" in data
        assert "period" in data

    def test_get_analytics_response_structure(
        self, client: TestClient, analytics_base_url: str
    ) -> None:
        """GET /api/v1/analytics response has correct types for all fields."""
        response: Response = client.get(analytics_base_url)

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["total_creators"], int)
        assert isinstance(data["total_content"], int)
        assert isinstance(data["total_revenue"], (int, float))
        assert isinstance(data["active_creators"], int)
        assert isinstance(data["published_content"], int)
        assert isinstance(data["period"], str)

    def test_get_analytics_content_type(
        self, client: TestClient, analytics_base_url: str
    ) -> None:
        """GET /api/v1/analytics returns JSON content type."""
        response: Response = client.get(analytics_base_url)

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_get_analytics_values_non_negative(
        self, client: TestClient, analytics_base_url: str
    ) -> None:
        """GET /api/v1/analytics returns non-negative numeric values."""
        response: Response = client.get(analytics_base_url)

        assert response.status_code == 200
        data = response.json()

        assert data["total_creators"] >= 0
        assert data["total_content"] >= 0
        assert data["total_revenue"] >= 0
        assert data["active_creators"] >= 0
        assert data["published_content"] >= 0

    def test_get_analytics_active_creators_lte_total(
        self, client: TestClient, analytics_base_url: str
    ) -> None:
        """Active creators count does not exceed total creators count."""
        response: Response = client.get(analytics_base_url)

        assert response.status_code == 200
        data = response.json()

        assert data["active_creators"] <= data["total_creators"]

    def test_get_analytics_published_lte_total(
        self, client: TestClient, analytics_base_url: str
    ) -> None:
        """Published content count does not exceed total content count."""
        response: Response = client.get(analytics_base_url)

        assert response.status_code == 200
        data = response.json()

        assert data["published_content"] <= data["total_content"]


# ---------------------------------------------------------------------------
# GET /api/v1/analytics/creators
# ---------------------------------------------------------------------------


class TestGetCreatorAnalytics:
    """Tests for GET /api/v1/analytics/creators."""

    def test_get_creator_analytics_success(
        self,
        client: TestClient,
        analytics_base_url: str,
        sample_creator_analytics_response: dict,
    ) -> None:
        """GET /api/v1/analytics/creators returns 200 with creator analytics."""
        response: Response = client.get(f"{analytics_base_url}/creators")

        assert response.status_code == 200
        data = response.json()
        assert "creators" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    def test_get_creator_analytics_list_structure(
        self, client: TestClient, analytics_base_url: str
    ) -> None:
        """Each creator entry has required fields with correct types."""
        response: Response = client.get(f"{analytics_base_url}/creators")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["creators"], list)
        for creator in data["creators"]:
            assert "creator_id" in creator
            assert "username" in creator
            assert "content_count" in creator
            assert "total_views" in creator
            assert "total_revenue" in creator
            assert "engagement_rate" in creator

            assert isinstance(creator["creator_id"], str)
            assert isinstance(creator["username"], str)
            assert isinstance(creator["content_count"], int)
            assert isinstance(creator["total_views"], int)
            assert isinstance(creator["total_revenue"], (int, float))
            assert isinstance(creator["engagement_rate"], (int, float))

    def test_get_creator_analytics_pagination(
        self, client: TestClient, analytics_base_url: str
    ) -> None:
        """Creator analytics pagination fields are valid."""
        response: Response = client.get(f"{analytics_base_url}/creators")

        assert response.status_code == 200
        data = response.json()

        assert data["page"] >= 1
        assert data["page_size"] >= 1
        assert data["total"] >= 0

    def test_get_creator_analytics_content_type(
        self, client: TestClient, analytics_base_url: str
    ) -> None:
        """GET /api/v1/analytics/creators returns JSON content type."""
        response: Response = client.get(f"{analytics_base_url}/creators")

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_get_creator_analytics_engagement_rate_range(
        self, client: TestClient, analytics_base_url: str
    ) -> None:
        """Engagement rate is between 0 and 1 for all creators."""
        response: Response = client.get(f"{analytics_base_url}/creators")

        assert response.status_code == 200
        data = response.json()

        for creator in data["creators"]:
            assert 0 <= creator["engagement_rate"] <= 1

    def test_get_creator_analytics_non_negative_values(
        self, client: TestClient, analytics_base_url: str
    ) -> None:
        """Creator analytics numeric values are non-negative."""
        response: Response = client.get(f"{analytics_base_url}/creators")

        assert response.status_code == 200
        data = response.json()

        for creator in data["creators"]:
            assert creator["content_count"] >= 0
            assert creator["total_views"] >= 0
            assert creator["total_revenue"] >= 0


# ---------------------------------------------------------------------------
# GET /api/v1/analytics/content
# ---------------------------------------------------------------------------


class TestGetContentAnalytics:
    """Tests for GET /api/v1/analytics/content."""

    def test_get_content_analytics_success(
        self,
        client: TestClient,
        analytics_base_url: str,
        sample_content_analytics_response: dict,
    ) -> None:
        """GET /api/v1/analytics/content returns 200 with content analytics."""
        response: Response = client.get(f"{analytics_base_url}/content")

        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    def test_get_content_analytics_list_structure(
        self, client: TestClient, analytics_base_url: str
    ) -> None:
        """Each content entry has required fields with correct types."""
        response: Response = client.get(f"{analytics_base_url}/content")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["content"], list)
        for item in data["content"]:
            assert "content_id" in item
            assert "title" in item
            assert "creator_id" in item
            assert "views" in item
            assert "likes" in item
            assert "shares" in item
            assert "revenue" in item

            assert isinstance(item["content_id"], str)
            assert isinstance(item["title"], str)
            assert isinstance(item["creator_id"], str)
            assert isinstance(item["views"], int)
            assert isinstance(item["likes"], int)
            assert isinstance(item["shares"], int)
            assert isinstance(item["revenue"], (int, float))

    def test_get_content_analytics_pagination(
        self, client: TestClient, analytics_base_url: str
    ) -> None:
        """Content analytics pagination fields are valid."""
        response: Response = client.get(f"{analytics_base_url}/content")

        assert response.status_code == 200
        data = response.json()

        assert data["page"] >= 1
        assert data["page_size"] >= 1
        assert data["total"] >= 0

    def test_get_content_analytics_content_type(
        self, client: TestClient, analytics_base_url: str
    ) -> None:
        """GET /api/v1/analytics/content returns JSON content type."""
        response: Response = client.get(f"{analytics_base_url}/content")

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_get_content_analytics_non_negative_values(
        self, client: TestClient, analytics_base_url: str
    ) -> None:
        """Content analytics numeric values are non-negative."""
        response: Response = client.get(f"{analytics_base_url}/content")

        assert response.status_code == 200
        data = response.json()

        for item in data["content"]:
            assert item["views"] >= 0
            assert item["likes"] >= 0
            assert item["shares"] >= 0
            assert item["revenue"] >= 0

    def test_get_content_analytics_likes_lte_views(
        self, client: TestClient, analytics_base_url: str
    ) -> None:
        """Likes count does not exceed views count for each content item."""
        response: Response = client.get(f"{analytics_base_url}/content")

        assert response.status_code == 200
        data = response.json()

        for item in data["content"]:
            assert item["likes"] <= item["views"]

    def test_get_content_analytics_shares_lte_views(
        self, client: TestClient, analytics_base_url: str
    ) -> None:
        """Shares count does not exceed views count for each content item."""
        response: Response = client.get(f"{analytics_base_url}/content")

        assert response.status_code == 200
        data = response.json()

        for item in data["content"]:
            assert item["shares"] <= item["views"]


# ---------------------------------------------------------------------------
# GET /api/v1/analytics/revenue
# ---------------------------------------------------------------------------


class TestGetRevenueAnalytics:
    """Tests for GET /api/v1/analytics/revenue."""

    def test_get_revenue_analytics_success(
        self,
        client: TestClient,
        analytics_base_url: str,
        sample_revenue_analytics_response: dict,
    ) -> None:
        """GET /api/v1/analytics/revenue returns 200 with revenue analytics."""
        response: Response = client.get(f"{analytics_base_url}/revenue")

        assert response.status_code == 200
        data = response.json()
        assert "total_revenue" in data
        assert "currency" in data
        assert "period" in data
        assert "breakdown" in data
        assert "top_earners" in data

    def test_get_revenue_analytics_response_structure(
        self, client: TestClient, analytics_base_url: str
    ) -> None:
        """Revenue analytics response has correct types for all fields."""
        response: Response = client.get(f"{analytics_base_url}/revenue")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["total_revenue"], (int, float))
        assert isinstance(data["currency"], str)
        assert isinstance(data["period"], str)
        assert isinstance(data["breakdown"], list)
        assert isinstance(data["top_earners"], list)

    def test_get_revenue_analytics_breakdown_structure(
        self, client: TestClient, analytics_base_url: str
    ) -> None:
        """Each breakdown entry has date and revenue fields."""
        response: Response = client.get(f"{analytics_base_url}/revenue")

        assert response.status_code == 200
        data = response.json()

        for entry in data["breakdown"]:
            assert "date" in entry
            assert "revenue" in entry
            assert isinstance(entry["date"], str)
            assert isinstance(entry["revenue"], (int, float))

    def test_get_revenue_analytics_top_earners_structure(
        self, client: TestClient, analytics_base_url: str
    ) -> None:
        """Each top earner entry has creator_id and revenue fields."""
        response: Response = client.get(f"{analytics_base_url}/revenue")

        assert response.status_code == 200
        data = response.json()

        for earner in data["top_earners"]:
            assert "creator_id" in earner
            assert "revenue" in earner
            assert isinstance(earner["creator_id"], str)
            assert isinstance(earner["revenue"], (int, float))

    def test_get_revenue_analytics_content_type(
        self, client: TestClient, analytics_base_url: str
    ) -> None:
        """GET /api/v1/analytics/revenue returns JSON content type."""
        response: Response = client.get(f"{analytics_base_url}/revenue")

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_get_revenue_analytics_total_non_negative(
        self, client: TestClient, analytics_base_url: str
    ) -> None:
        """Total revenue is non-negative."""
        response: Response = client.get(f"{analytics_base_url}/revenue")

        assert response.status_code == 200
        data = response.json()

        assert data["total_revenue"] >= 0

    def test_get_revenue_analytics_breakdown_non_negative(
        self, client: TestClient, analytics_base_url: str
    ) -> None:
        """All breakdown revenue values are non-negative."""
        response: Response = client.get(f"{analytics_base_url}/revenue")

        assert response.status_code == 200
        data = response.json()

        for entry in data["breakdown"]:
            assert entry["revenue"] >= 0

    def test_get_revenue_analytics_top_earners_non_negative(
        self, client: TestClient, analytics_base_url: str
    ) -> None:
        """All top earner revenue values are non-negative."""
        response: Response = client.get(f"{analytics_base_url}/revenue")

        assert response.status_code == 200
        data = response.json()

        for earner in data["top_earners"]:
            assert earner["revenue"] >= 0

    def test_get_revenue_analytics_currency_format(
        self, client: TestClient, analytics_base_url: str
    ) -> None:
        """Currency is a non-empty string (ISO 4217 format)."""
        response: Response = client.get(f"{analytics_base_url}/revenue")

        assert response.status_code == 200
        data = response.json()

        assert len(data["currency"]) == 3
        assert data["currency"].isalpha()
        assert data["currency"].isupper()
