"""Catálogos de identificadores de processos por plataforma (Windows / Linux)."""
import sys

# ---------------------------------------------------------------------------
# Windows: Listas de executáveis (em minúsculas)
# ---------------------------------------------------------------------------
WINDOWS_JOGOS = set()  # ex: {"eldenring.exe", "valorant-win64-shipping.exe"}
WINDOWS_CODANDO = {
    "code.exe",
    "cursor.exe",
    "devenv.exe",
    "pycharm64.exe",
    "idea64.exe",
    "nvim.exe",
    "arduino ide.exe",
}
WINDOWS_MIDIA = {"spotify.exe", "vlc.exe", "mpv.exe"}
WINDOWS_NAO_JOGO = {
    "explorer.exe",
    "chrome.exe",
    "firefox.exe",
    "msedge.exe",
    "brave.exe",
    "vlc.exe",
    "mpv.exe",
    "code.exe",
    "cursor.exe",
    "applicationframehost.exe",
    "searchhost.exe",
    "lockapp.exe",
    "logonui.exe",
}

# ---------------------------------------------------------------------------
# Linux: Listas de processos (em minúsculas)
# ---------------------------------------------------------------------------
LINUX_JOGOS = {"gamescope", "reaper", "lutris-wrapper"}
LINUX_CODANDO = {"code", "nvim", "vim", "arduino-ide", "idea", "pycharm", "zed"}
LINUX_MIDIA = {"spotify", "mpv", "vlc"}
LINUX_NAO_JOGO = set()


def obter_catalogos(is_windows=None):
    """Retorna os conjuntos de catálogo (jogos, codando, midia, nao_jogo) para a plataforma."""
    if is_windows is None:
        is_windows = (sys.platform == "win32")

    if is_windows:
        return WINDOWS_JOGOS, WINDOWS_CODANDO, WINDOWS_MIDIA, WINDOWS_NAO_JOGO
    return LINUX_JOGOS, LINUX_CODANDO, LINUX_MIDIA, LINUX_NAO_JOGO


# Aliases retrocompatíveis para o ambiente corrente
_is_win = (sys.platform == "win32")
JOGOS, CODANDO, MIDIA, NAO_JOGO = obter_catalogos(_is_win)
