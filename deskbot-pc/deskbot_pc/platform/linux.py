"""Provedor de métricas para Linux."""
from deskbot_pc.platform.base import BasePlatformDetector


class LinuxPlatformDetector(BasePlatformDetector):
    """Detecta atividade para Linux (process-based)."""

    def segundos_ocioso(self) -> float:
        return 0.0

    def app_em_primeiro_plano(self) -> tuple[str, bool]:
        return "", False
