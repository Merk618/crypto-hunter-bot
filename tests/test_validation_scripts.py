"""Validation script import tests."""

import importlib


def test_validation_scripts_import_safely_without_trades() -> None:
    """Scripts import without running validation or trading."""
    for module in ["scripts.validate_real_data_phase22", "scripts.validate_kraken_public", "scripts.validate_moomoo_readonly"]:
        imported = importlib.import_module(module)
        assert hasattr(imported, "main")
