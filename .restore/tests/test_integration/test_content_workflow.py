"""Integration tests for ugc-marketplace workflows."""

import pytest
from fastapi.testclient import TestClient


class TestContentLicensingWorkflow:
    """Test complete content licensing workflow."""

    def test_content_creation_to_license(self, client: TestClient):
        """Test content creation to license purchase."""
        # 1. Create creator
        creator_response = client.post("/api/creators", json={
            "name": "Test Creator",
            "email": "creator@example.com",
        })
        assert creator_response.status_code == 201
        creator_id = creator_response.json()["id"]

        # 2. Create content
        content_response = client.post("/api/content", json={
            "title": "Test Video",
            "description": "Test content",
            "creator_id": creator_id,
        })
        assert content_response.status_code == 201
        content_id = content_response.json()["id"]

        # 3. Create license
        license_response = client.post("/api/licenses", json={
            "content_id": content_id,
            "license_type": "standard",
            "price": 99.99,
        })
        assert license_response.status_code == 201

    def test_content_monetization_flow(self, client: TestClient):
        """Test content monetization workflow."""
        # Create content
        content_response = client.post("/api/content", json={
            "title": "Premium Content",
            "description": "Premium",
        })
        assert content_response.status_code == 201
        content_id = content_response.json()["id"]

        # Purchase license
        purchase_response = client.post("/api/purchases", json={
            "content_id": content_id,
            "buyer_id": 1,
        })
        assert purchase_response.status_code == 201


class TestRightsManagementWorkflow:
    """Test rights management workflow."""

    def test_content_rights_flow(self, client: TestClient):
        """Test content rights management."""
        # Create content
        content_response = client.post("/api/content", json={
            "title": "Licensed Content",
            "description": "Licensed",
        })
        assert content_response.status_code == 201
        content_id = content_response.json()["id"]

        # Check rights
        rights_response = client.get(f"/api/content/{content_id}/rights")
        assert rights_response.status_code == 200
