"""V1 completion checklist tests."""

from app.audit.v1_completion_checklist import V1CompletionChecklistService


def test_v1_checklist_includes_required_backend_items() -> None:
    """Checklist includes required backend items."""
    report = V1CompletionChecklistService().build()
    names = {item["name"] for item in report["items"]}

    assert "backend starts locally" in names
    assert "pytest passes" in names
    assert "strategy checkpoint exists" in names
    assert "operator commands available" in names


def test_v1_checklist_marks_final_runbook_needed() -> None:
    """Final runbook remains missing before Phase 42."""
    report = V1CompletionChecklistService().build()

    assert "final runbook still needed" in report["missing_items"]


def test_v1_checklist_marks_freeze_package_needed() -> None:
    """Freeze package remains missing before Phase 43."""
    report = V1CompletionChecklistService().build()

    assert "v1 freeze package still needed" in report["missing_items"]
