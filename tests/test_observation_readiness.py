"""Observation readiness tests."""

from app.observation.observation_readiness import ObservationReadinessChecker


class Safety:
    """Safety fake."""

    def __init__(self, passed=True):
        self.passed = passed

    def run(self):
        return Obj({"passed": self.passed, "live_trading_locked": self.passed, "no_add_order_detected": True, "no_withdrawal_methods_detected": True, "blockers": [] if self.passed else ["safety failed"], "warnings": []})


class Validator:
    """Validation fake."""

    def __init__(self, moomoo_status="disabled"):
        self.moomoo_status = moomoo_status

    def validate_kraken_public_data(self):
        return Obj({"passed": True, "blockers": []})

    def validate_crypto_signals(self):
        return Obj({"passed": True, "blockers": []})

    def validate_moomoo_health(self):
        return Obj({"passed": False, "status": self.moomoo_status, "warnings": ["MooMoo disabled"], "blockers": []})


class Paper:
    """Paper broker fake."""

    def get_account_summary(self):
        return {"equity": 10000}


class Journal:
    """Journal fake."""

    def get_recent_signals(self, limit=1):
        return []


class Reports:
    """Report fake."""

    def __init__(self, polluted=False):
        self.polluted = polluted

    def get_daily_briefing(self):
        reason = "fake signal" if self.polluted else "valid momentum"
        return {"top_candidates": {"crypto": [{"asset_class": "crypto", "symbol": "BTC/USD", "score": 90, "reasons": [reason]}], "stocks": [], "options": []}}


class Operator:
    """Operator fake."""

    def get_operator_status(self):
        return {"backend_healthy": True}


class Alerts:
    """Alert fake."""

    def get_alert_status(self):
        return {"read_only": True, "channels": {"email": False}}


class Obj:
    """Object with to_dict."""

    def __init__(self, data):
        self.data = data

    def to_dict(self):
        return self.data


def checker(**overrides):
    defaults = {
        "safety_audit": Safety(),
        "validator": Validator(),
        "paper_broker": Paper(),
        "trade_journal": Journal(),
        "report_service": Reports(),
        "operator_service": Operator(),
        "alert_service": Alerts(),
    }
    defaults.update(overrides)
    return ObservationReadinessChecker(**defaults)


def test_observation_readiness_passes_when_safe_checks_pass() -> None:
    """Safe checks produce readiness despite MooMoo disabled warning."""
    result = checker().check()

    assert result["ready"] is True
    assert result["warnings"]


def test_observation_readiness_blocks_when_safety_audit_fails() -> None:
    """Safety failure blocks readiness."""
    result = checker(safety_audit=Safety(passed=False)).check()

    assert result["ready"] is False
    assert "safety failed" in result["blockers"]


def test_observation_readiness_warns_when_moomoo_disabled_but_does_not_block_crypto_only() -> None:
    """MooMoo disabled is warning-only for crypto observation."""
    result = checker(validator=Validator(moomoo_status="disabled")).check()

    assert result["ready"] is True
    assert "MooMoo disabled" in result["warnings"]


def test_observation_readiness_blocks_polluted_reports() -> None:
    """Polluted daily briefing blocks observation."""
    result = checker(report_service=Reports(polluted=True)).check()

    assert result["ready"] is False
    assert "daily briefing contains fake/test/demo records" in result["blockers"]
