"""Candidate normalization for unified reporting."""

from __future__ import annotations

from app.alerts.alert_models import AlertCandidate


def candidate_from_crypto_signal(signal: dict) -> AlertCandidate:
    """Normalize a crypto signal record."""
    symbol = str(signal.get("symbol", "UNKNOWN"))
    score = float(signal.get("score", 0) or 0)
    return AlertCandidate(
        asset_class="crypto",
        symbol=symbol,
        title=f"{symbol} crypto signal",
        score=score,
        category=str(signal.get("category", "UNKNOWN")),
        risk_level=signal.get("risk_level"),
        reasons=list(signal.get("reasons") or signal.get("reasons_json") or []),
        warnings=list(signal.get("warnings") or signal.get("warnings_json") or []),
        blockers=list(signal.get("blockers") or signal.get("blockers_json") or []),
        metadata={"latest_price": signal.get("latest_price"), "timeframe": signal.get("timeframe")},
        source="crypto_signal_candidate_v1",
    )


def candidate_from_stock_result(result: dict) -> AlertCandidate:
    """Normalize a Stock Hunter scanner result."""
    signal = result.get("stock_signal") or result
    symbol = str(result.get("symbol") or signal.get("symbol") or "UNKNOWN")
    score = float(signal.get("score", result.get("opportunity_score", 0)) or 0)
    return AlertCandidate(
        asset_class="stock",
        symbol=symbol,
        title=f"{symbol} stock candidate",
        score=score,
        category=str(signal.get("category", result.get("action", "UNKNOWN"))),
        reasons=list(signal.get("reasons") or result.get("notes") or []),
        warnings=list(signal.get("warnings") or result.get("warnings") or []),
        blockers=list(signal.get("blockers") or result.get("blockers") or []),
        metadata={"opportunity_score": result.get("opportunity_score"), "rank": result.get("rank")},
        source="stock_signal_candidate_v1",
    )


def candidate_from_ranked_option(contract: dict) -> AlertCandidate:
    """Normalize a ranked option contract."""
    symbol = str(contract.get("symbol", "UNKNOWN"))
    return AlertCandidate(
        asset_class="option",
        symbol=symbol,
        title=f"{contract.get('underlying', 'UNKNOWN')} {contract.get('option_type', 'option')} research contract",
        score=float(contract.get("total_score", 0) or 0),
        category=str(contract.get("label", "UNKNOWN")),
        reasons=list(contract.get("reasons") or []),
        warnings=list(contract.get("warnings") or []),
        blockers=list(contract.get("blockers") or []),
        metadata={
            "rank": contract.get("rank"),
            "underlying": contract.get("underlying"),
            "expiration": contract.get("expiration"),
            "strike": contract.get("strike"),
            "dte": contract.get("dte"),
            "delta": contract.get("delta"),
            "spread_pct": contract.get("spread_pct"),
        },
        source="ranked_option_candidate_v1",
    )
