"""Phase 43 route tests."""

from pathlib import Path

from app.main import app


ROOT = Path(__file__).resolve().parents[1]


def test_phase43_routes_exist() -> None:
    """Freeze, handoff, roadmap, and next-project routes exist."""
    paths = {route.path for route in app.routes}

    assert "/audit/v1-freeze-report" in paths
    assert "/operator/v1-handoff-package" in paths
    assert "/operator/future-roadmap" in paths
    assert "/operator/next-project-plan" in paths


def test_phase43_routes_do_not_expose_secrets() -> None:
    """Route paths do not expose secret-bearing names."""
    paths = " ".join(route.path.lower() for route in app.routes if route.path.startswith("/audit") or route.path.startswith("/operator"))

    assert "secret" not in paths
    assert "api_key" not in paths
    assert "webhook" not in paths


def test_sol_meme_doc_remains_future_read_only() -> None:
    """SOL meme module doc remains future and read-only."""
    text = (ROOT / "docs" / "SOL_MEME_HUNTER_FUTURE_MODULE.md").read_text(encoding="utf-8").lower()

    assert "future read-only module" in text
    assert "solana meme coins only" in text
    assert "trading" in text
    assert "not in scope yet" in text

