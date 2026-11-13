"""Provedor de métricas Win32 via ctypes para Windows."""
import sys
import psutil

from deskbot_pc.platform.base import BasePlatformDetector

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


class WindowsPlatformDetector(BasePlatformDetector):
    """Detecta atividade, foco e tela cheia utilizando chamadas nativas Win32."""

    def segundos_ocioso(self) -> float:
        if sys.platform != "win32":
            return 0.0
        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(info)
        user32.GetLastInputInfo(ctypes.byref(info))
        return ((kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000.0

    def app_em_primeiro_plano(self) -> tuple[str, bool]:
        if sys.platform != "win32":
            return "", False
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return "", False
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        cheia = (rect.left <= 0 and rect.top <= 0
                 and rect.right >= user32.GetSystemMetrics(0)
                 and rect.bottom >= user32.GetSystemMetrics(1))
        try:
            nome = psutil.Process(pid.value).name().lower()
        except psutil.Error:
            nome = ""
        return nome, cheia
