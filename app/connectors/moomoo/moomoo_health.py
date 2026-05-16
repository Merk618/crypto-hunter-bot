"""MooMoo package and OpenD health checks."""

from __future__ import annotations

import importlib.util
import socket
from collections.abc import Callable

from app.config import Settings, get_settings
from app.connectors.moomoo.moomoo_config import get_moomoo_config
from app.connectors.moomoo.moomoo_models import MooMooHealthStatus


class MooMooHealth:
    """Read-only health checker for MooMoo feasibility."""

    def __init__(
        self,
        settings: Settings | None = None,
        import_checker: Callable[[str], bool] | None = None,
        socket_checker: Callable[[str, int], bool] | None = None,
    ) -> None:
        """Initialize health checker with injectable test seams."""
        self.settings = settings or get_settings()
        self.import_checker = import_checker or self._default_import_checker
        self.socket_checker = socket_checker or self._default_socket_checker

    def check(self) -> MooMooHealthStatus:
        """Return MooMoo package/OpenD health without performing any trading action."""
        config = get_moomoo_config(self.settings)
        warnings: list[str] = []
        import_available = self.import_checker("moomoo")
        if not import_available:
            warnings.append("moomoo-api package is not importable")

        connected = False
        if config.enabled:
            try:
                connected = self.socket_checker(config.host, config.port)
                if not connected:
                    warnings.append("OpenD socket is not reachable")
            except Exception:
                warnings.append("OpenD socket check failed")
                connected = False
        else:
            warnings.append("MooMoo connector is disabled; OpenD socket check skipped")

        if not config.read_only or config.trading_enabled or config.paper_trading_enabled or config.unlock_trade_context:
            warnings.append("Unsafe MooMoo trading flag detected; connector must remain read-only")

        return MooMooHealthStatus(
            enabled=config.enabled,
            configured=bool(config.host and config.port),
            import_available=import_available,
            connected=connected,
            host=config.host,
            port=config.port,
            read_only=config.read_only,
            trading_enabled=config.trading_enabled,
            paper_trading_enabled=config.paper_trading_enabled,
            unlock_trade_context=config.unlock_trade_context,
            warnings=warnings,
        )

    def _default_import_checker(self, module_name: str) -> bool:
        """Return whether a module can be imported."""
        return importlib.util.find_spec(module_name) is not None

    def _default_socket_checker(self, host: str, port: int) -> bool:
        """Return whether OpenD host/port accepts a socket connection."""
        with socket.create_connection((host, port), timeout=2):
            return True
