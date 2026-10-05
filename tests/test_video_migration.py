"""Integration tests for Alembic migrations."""
import os
import pytest
import subprocess
import tempfile


class TestAlembicMigration:
    """Tests that Alembic migrations work correctly."""

    def test_migration_generates_video_tables(self):
        """Migration creates all video-related tables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db_url = f"sqlite:///{db_path}"

            # Run alembic upgrade
            env = os.environ.copy()
            env["DATABASE_URL"] = db_url
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                env=env,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"Alembic upgrade failed: {result.stderr}"

            # Check tables exist
            from sqlalchemy import create_engine, inspect
            engine = create_engine(db_url)
            inspector = inspect(engine)
            tables = inspector.get_table_names()

            assert "video_generation_requests" in tables
            assert "video_generation_results" in tables
            assert "video_quality_metrics" in tables
            assert "video_templates" in tables

            engine.dispose()

    def test_migration_downgrade_removes_video_tables(self):
        """Downgrade removes video tables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db_url = f"sqlite:///{db_path}"

            # First upgrade
            env = os.environ.copy()
            env["DATABASE_URL"] = db_url
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                env=env,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0

            # Then downgrade
            result = subprocess.run(
                ["alembic", "downgrade", "base"],
                env=env,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"Downgrade failed: {result.stderr}"

            # Check tables are gone
            from sqlalchemy import create_engine, inspect
            engine = create_engine(db_url)
            inspector = inspect(engine)
            tables = inspector.get_table_names()

            assert "video_generation_requests" not in tables
            assert "video_generation_results" not in tables
            assert "video_quality_metrics" not in tables
            assert "video_templates" not in tables

            engine.dispose()

    def test_migration_upgrade_is_idempotent(self):
        """Running upgrade head twice does not fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            db_url = f"sqlite:///{db_path}"

            env = os.environ.copy()
            env["DATABASE_URL"] = db_url

            # First upgrade
            result1 = subprocess.run(
                ["alembic", "upgrade", "head"],
                env=env,
                capture_output=True,
                text=True,
            )
            assert result1.returncode == 0

            # Second upgrade should also succeed
            result2 = subprocess.run(
                ["alembic", "upgrade", "head"],
                env=env,
                capture_output=True,
                text=True,
            )
            assert result2.returncode == 0
