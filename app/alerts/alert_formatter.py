"""Alert report formatting helpers."""

from __future__ import annotations

from app.alerts.alert_models import AlertReport


class AlertFormatter:
    """Format alert reports for console, Markdown, and compact summaries."""

    def format_console_report(self, alert_report: AlertReport) -> str:
        """Return a clean plain-text report."""
        return self._format(alert_report, markdown=False)

    def format_markdown_report(self, alert_report: AlertReport) -> str:
        """Return a Markdown report."""
        return self._format(alert_report, markdown=True)

    def format_compact_summary(self, alert_report: AlertReport) -> str:
        """Return a compact one-screen summary."""
        return (
            f"{alert_report.title}: "
            f"{len(alert_report.crypto_candidates)} crypto, "
            f"{len(alert_report.stock_candidates)} stock, "
            f"{len(alert_report.option_candidates)} option candidates"
        )

    def _format(self, report: AlertReport, markdown: bool) -> str:
        """Format sections."""
        heading = f"# {report.title}" if markdown else report.title
        lines = [heading, f"Generated: {report.generated_at}", ""]
        lines.extend(self._section("Top Crypto Candidates", report.crypto_candidates, markdown))
        lines.extend(self._section("Top Stock Candidates", report.stock_candidates, markdown))
        lines.extend(self._section("Top Options Candidates", report.option_candidates, markdown))
        if report.risk_summary:
            lines.extend(["", "## Risk Status" if markdown else "Risk Status", self._dict_line(report.risk_summary)])
        if report.safety_summary:
            lines.extend(["", "## Safety Status" if markdown else "Safety Status", self._dict_line(report.safety_summary)])
        if report.warnings:
            lines.extend(["", "## Warnings" if markdown else "Warnings"])
            lines.extend([f"- {warning}" for warning in report.warnings])
        return "\n".join(lines)

    def _section(self, title: str, candidates: list[dict], markdown: bool) -> list[str]:
        """Format one candidate section."""
        lines = ["", f"## {title}" if markdown else title]
        if not candidates:
            lines.append("- None")
            return lines
        for candidate in candidates:
            lines.append(f"- {candidate.get('symbol')} | {candidate.get('score')} | {candidate.get('category')} | {candidate.get('title')}")
            warnings = candidate.get("warnings") or []
            blockers = candidate.get("blockers") or []
            if warnings:
                lines.append(f"  warnings: {', '.join(warnings[:3])}")
            if blockers:
                lines.append(f"  blockers: {', '.join(blockers[:3])}")
        return lines

    def _dict_line(self, value: dict) -> str:
        """Format a small dictionary."""
        return ", ".join(f"{key}={item}" for key, item in value.items() if key not in {"source", "generated_at"})
