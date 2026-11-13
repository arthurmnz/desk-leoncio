"""Módulo de abstração de plataforma do DeskBot PC."""
import sys
from deskbot_pc.platform.base import BasePlatformDetector
from deskbot_pc.platform.linux import LinuxPlatformDetector
from deskbot_pc.platform.windows import WindowsPlatformDetector


def obter_detector(is_windows=None) -> BasePlatformDetector:
    """Retorna a instância do detector de plataforma apropriado."""
    if is_windows is None:
        is_windows = (sys.platform == "win32")
    if is_windows:
        return WindowsPlatformDetector()
    return LinuxPlatformDetector()


detector = obter_detector()


def segundos_ocioso() -> float:
    return detector.segundos_ocioso()


def app_em_primeiro_plano() -> tuple[str, bool]:
    return detector.app_em_primeiro_plano()


__all__ = [
    "BasePlatformDetector",
    "LinuxPlatformDetector",
    "WindowsPlatformDetector",
    "obter_detector",
    "detector",
    "segundos_ocioso",
    "app_em_primeiro_plano",
]
