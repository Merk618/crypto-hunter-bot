"""Phase 15 documentation regression tests."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_phase15_docs_exist() -> None:
    """Required Phase 15 docs are present."""
    docs = ROOT / "docs"

    assert (docs / "PHASE15_LOCAL_VALIDATION.md").exists()
    assert (docs / "STRATEGY_CALIBRATION.md").exists()
    assert (docs / "MOOMOO_CONNECTOR_PLAN.md").exists()
    assert (docs / "CONNECTOR_BOUNDARIES.md").exists()


def test_moomoo_plan_keeps_connector_separate() -> None:
    """MooMoo is documented as separate from Crypto Hunter core."""
    text = (ROOT / "docs" / "MOOMOO_CONNECTOR_PLAN.md").read_text(encoding="utf-8")

    assert "should not be added directly into the Crypto Hunter trading core" in text
    assert "Stock/Options Hunter" in text
    assert "MooMoo read-only feasibility spike" in text


def test_phase15_docs_do_not_add_live_execution_language() -> None:
    """Phase 15 docs keep live execution out of scope."""
    combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in (ROOT / "docs").glob("*.md"))

    assert "do not place a real order" in combined or "does not place a real order" in combined
    assert "read-only" in combined
    assert "no withdrawal" in combined
