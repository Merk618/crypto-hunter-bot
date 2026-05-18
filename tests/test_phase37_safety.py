"""Phase 37 safety regression tests."""

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
