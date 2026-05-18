"""Phase 38 safety regression tests."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_python(paths: list[str]) -> str:
    """Read Python files under selected paths."""
    chunks: list[str] = []
    for rel in paths:
        path = ROOT / rel
        if path.is_file():
            chunks.append(path.read_text(encoding="utf-8"))
        elif path.exists():
            for file_path in path.rglob("*.py"):
                chunks.append(file_path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def test_no_kraken_addorder_added() -> None:
    """Kraken live order token remains absent."""
    assert "AddOrder" not in read_python(["app", "scripts"])


def test_no_moomoo_order_cancel_unlock_added() -> None:
    """MooMoo remains read-only."""
    text = read_python(["app/connectors/moomoo"])

    assert "def place_order" not in text
    assert "def cancel_order" not in text
    assert "def unlock_trade" not in text


def test_no_options_withdrawal_or_live_execution_added() -> None:
    """No prohibited execution surfaces were added."""
    text = read_python(["app", "scripts"]).lower()

    assert "def withdraw" not in text
    assert "def transfer" not in text
    assert "def funding" not in text
    assert "def staking" not in text
    assert "execute_option" not in text
    assert "options_execution" not in text


def test_no_paper_trading_enabled_by_default() -> None:
    """Controlled paper and paper-trade observation remain disabled by default."""
    from app.config import Settings

    settings = Settings(_env_file=None)

    assert settings.controlled_paper_observation_enabled is False
    assert settings.controlled_paper_observation_allow_buys is False
    assert settings.paper_trade_observation_enabled is False
    assert settings.paper_trade_observation_allow_enable is False
