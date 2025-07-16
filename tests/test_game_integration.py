"""Integration tests for memes-ranker game flow."""

import asyncio
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.database import Database
from app.main import app


class TestGameIntegration:
    """Integration tests for the complete game flow."""

    def setup_method(self):
        """Set up test environment."""
        # Create temporary database
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.test_db.close()

        # Set environment variables for testing
        os.environ["DATABASE_PATH"] = self.test_db.name
        os.environ["ADMIN_PASSWORD"] = "test_admin_password"
        os.environ["JWT_SECRET_KEY"] = "test_jwt_secret_key"

        # Initialize database
        from setup_db import create_database

        create_database(self.test_db.name)

        # Create test client
        self.client = TestClient(app)

        # Create database instance for direct access
        self.db = Database(self.test_db.name)

    def teardown_method(self):
        """Clean up test environment."""
        # Remove temporary database
        if os.path.exists(self.test_db.name):
            os.unlink(self.test_db.name)

    def test_user_registration_and_session_creation(self):
        """Test that users are automatically registered with unique names."""
        # First request should create a new user
        response = self.client.get("/")
        assert response.status_code == 200

        # Check that session cookie is set
        assert "session_token" in response.cookies

        # Extract user name from response
        content = response.text
        assert "badge" in content  # User name should be displayed in badge

        # Second request with same session should return same user
        session_token = response.cookies["session_token"]
        response2 = self.client.get("/", cookies={"session_token": session_token})
        assert response2.status_code == 200

        # Should have same session token
        assert response2.cookies.get("session_token") == session_token

    def test_complete_game_flow(self):
        """Test complete game flow: user registration, meme rating, completion."""
        # Step 1: User visits site and gets registered
        response = self.client.get("/")
        assert response.status_code == 200
        session_token = response.cookies["session_token"]

        # Step 2: Admin populates memes
        admin_login = self.client.post(
            "/admin/login", data={"password": "test_admin_password"}
        )
        assert admin_login.status_code == 302
        # Admin token is set in cookies for authentication

        # Create some test memes in database
        asyncio.run(self._create_test_memes())

        # Step 3: User rates memes
        memes_response = self.client.get("/api/memes")
        memes = memes_response.json()["memes"]
        assert len(memes) > 0

        # Rate first meme
        rating_response = self.client.post(
            "/rank",
            json={"meme_id": memes[0]["id"], "score": 8},
            cookies={"session_token": session_token},
        )
        assert rating_response.status_code == 200

        # Rate second meme
        rating_response2 = self.client.post(
            "/rank",
            json={"meme_id": memes[1]["id"], "score": 5},
            cookies={"session_token": session_token},
        )
        assert rating_response2.status_code == 200

        # Step 4: Check stats
        stats_response = self.client.get("/api/stats")
        stats = stats_response.json()["stats"]

        # Should have statistics for rated memes
        rated_stats = [s for s in stats if s["ranking_count"] > 0]
        assert len(rated_stats) >= 2

    def test_multiple_users_rating_same_meme(self):
        """Test multiple users rating the same meme."""
        # Create test memes
        asyncio.run(self._create_test_memes())

        # User 1 rates meme
        response1 = self.client.get("/")
        session_token1 = response1.cookies["session_token"]

        memes_response = self.client.get("/api/memes")
        memes = memes_response.json()["memes"]

        self.client.post(
            "/rank",
            json={"meme_id": memes[0]["id"], "score": 9},
            cookies={"session_token": session_token1},
        )

        # User 2 rates same meme
        response2 = self.client.get("/")
        session_token2 = response2.cookies["session_token"]
        assert session_token2 != session_token1  # Different users

        self.client.post(
            "/rank",
            json={"meme_id": memes[0]["id"], "score": 6},
            cookies={"session_token": session_token2},
        )

        # Check that average is calculated correctly
        stats_response = self.client.get("/api/stats")
        stats = stats_response.json()["stats"]

        meme_stat = next(s for s in stats if s["id"] == memes[0]["id"])
        assert meme_stat["ranking_count"] == 2
        assert meme_stat["average_score"] == 7.5  # (9 + 6) / 2

    def test_user_updates_rating(self):
        """Test that user can update their rating for a meme."""
        # Create test memes
        asyncio.run(self._create_test_memes())

        # User rates meme
        response = self.client.get("/")
        session_token = response.cookies["session_token"]

        memes_response = self.client.get("/api/memes")
        memes = memes_response.json()["memes"]

        # Initial rating
        self.client.post(
            "/rank",
            json={"meme_id": memes[0]["id"], "score": 7},
            cookies={"session_token": session_token},
        )

        # Updated rating
        self.client.post(
            "/rank",
            json={"meme_id": memes[0]["id"], "score": 4},
            cookies={"session_token": session_token},
        )

        # Check that rating was updated, not duplicated
        stats_response = self.client.get("/api/stats")
        stats = stats_response.json()["stats"]

        meme_stat = next(s for s in stats if s["id"] == memes[0]["id"])
        assert meme_stat["ranking_count"] == 1  # Still only one rating
        assert meme_stat["average_score"] == 4.0  # Updated score

    def test_admin_session_management(self):
        """Test admin session creation and management."""
        # Admin login
        admin_login = self.client.post(
            "/admin/login", data={"password": "test_admin_password"}
        )
        assert admin_login.status_code == 302
        # Admin token is set in cookies for authentication

        # Access admin dashboard
        dashboard_response = self.client.get(
            "/admin/dashboard",
            cookies={"admin_token": admin_login.cookies["admin_token"]},
        )
        assert dashboard_response.status_code == 200

        # Create new session
        session_response = self.client.post(
            "/admin/session",
            json={"name": "Test Session"},
            cookies={"admin_token": admin_login.cookies["admin_token"]},
        )
        assert session_response.status_code == 200

        # Verify session was created
        session_data = session_response.json()
        assert session_data["status"] == "success"
        assert "session_id" in session_data

    def test_rating_validation(self):
        """Test that rating validation works correctly."""
        # Create test memes
        asyncio.run(self._create_test_memes())

        # User registration
        response = self.client.get("/")
        session_token = response.cookies["session_token"]

        memes_response = self.client.get("/api/memes")
        memes = memes_response.json()["memes"]

        # Test invalid scores
        invalid_scores = [-1, 11, 15, -5]

        for score in invalid_scores:
            rating_response = self.client.post(
                "/rank",
                json={"meme_id": memes[0]["id"], "score": score},
                cookies={"session_token": session_token},
            )
            assert rating_response.status_code == 400

        # Test valid scores
        valid_scores = [0, 1, 5, 10]

        for score in valid_scores:
            rating_response = self.client.post(
                "/rank",
                json={"meme_id": memes[0]["id"], "score": score},
                cookies={"session_token": session_token},
            )
            assert rating_response.status_code == 200

    def test_qr_code_generation(self):
        """Test QR code generation endpoint."""
        response = self.client.get("/qr-code")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert len(response.content) > 0

    def test_unauthenticated_access(self):
        """Test behavior with unauthenticated requests."""
        # Test rating without session
        rating_response = self.client.post("/rank", json={"meme_id": 1, "score": 5})
        assert rating_response.status_code == 401

        # Test admin endpoints without auth
        admin_response = self.client.get("/admin/dashboard")
        assert admin_response.status_code == 401

        session_response = self.client.post(
            "/admin/session", json={"name": "Test Session"}
        )
        assert session_response.status_code == 401

    async def _create_test_memes(self):
        """Helper method to create test memes in database."""
        test_memes = [
            ("test-meme-1.png", "/static/memes/test-meme-1.png"),
            ("test-meme-2.png", "/static/memes/test-meme-2.png"),
            ("test-meme-3.png", "/static/memes/test-meme-3.png"),
        ]

        for filename, path in test_memes:
            await self.db.create_meme(filename, path)


# Run tests directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
