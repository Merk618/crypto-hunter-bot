"""Safe operator command summaries."""

from __future__ import annotations

from app.operator.operator_models import CommandSummary


class CommandSummaryBuilder:
    """Build local PowerShell command summaries for operators."""

    def build(self) -> CommandSummary:
        """Return safe local commands."""
        commands = [
            {"label": "Run tests", "command": r".\.venv\Scripts\python.exe -m pytest"},
            {"label": "Start backend", "command": r".\.venv\Scripts\python.exe -m uvicorn app.main:app --reload"},
            {"label": "Safety audit", "command": r'Invoke-RestMethod -Uri "http://127.0.0.1:8000/system/safety-audit"'},
            {"label": "Unified summary", "command": r'Invoke-RestMethod -Uri "http://127.0.0.1:8000/reports/unified-summary"'},
            {"label": "Alerts preview", "command": r'Invoke-RestMethod -Uri "http://127.0.0.1:8000/alerts/preview"'},
            {"label": "Operator status", "command": r'Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/status"'},
            {"label": "Paper-trade approval review", "command": r'Invoke-RestMethod -Uri "http://127.0.0.1:8000/operator/paper-trade-approval-review"'},
            {"label": "Controlled paper status", "command": r'Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/status"'},
            {"label": "Controlled paper audit", "command": r'Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/audit"'},
            {"label": "Controlled paper preflight", "command": r'Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/preflight"'},
            {"label": "Controlled paper decision", "command": r'Invoke-RestMethod -Uri "http://127.0.0.1:8000/observation/controlled-paper/decision"'},
            {"label": "MooMoo status", "command": r'Invoke-RestMethod -Uri "http://127.0.0.1:8000/moomoo/status"'},
            {"label": "Stock candidates", "command": r'Invoke-RestMethod -Uri "http://127.0.0.1:8000/stock-hunter/top-candidates"'},
            {"label": "Options scanner top", "command": r'Invoke-RestMethod -Uri "http://127.0.0.1:8000/options-scanner/top"'},
        ]
        return CommandSummary(
            title="Crypto Hunter Standalone Operator Commands",
            commands=commands,
            notes=["Run these from the crypto-hunter-bot repo root.", "Stop the uvicorn server with Ctrl+C in its terminal."],
            warnings=["All commands are read-only or local test commands; none place real orders."],
        )
