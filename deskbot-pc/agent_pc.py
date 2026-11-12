#!/usr/bin/env python3
"""Agente do PC (Linux e Windows): detecta o que você faz e avisa o homelab via MQTT.

Uso:  python agent_pc.py             -> nome automático: "windows" ou "cachyos"
      python agent_pc.py meu-nome    -> nome personalizado

Estados publicados: GAMING, CODING, MEDIA, IDLE, AWAY (só Windows) e OFFLINE.
"""
import json
import os
import sys
import time

import paho.mqtt.client as mqtt
import psutil

BROKER = os.environ.get("DESKBOT_BROKER", "192.168.0.5")  # <- IP do homelab
WINDOWS = sys.platform == "win32"
NOME = sys.argv[1] if len(sys.argv) > 1 else ("windows" if WINDOWS else "cachyos")
TOPICO = f"desk/pc/{NOME}/activity"

SEGUNDOS_AUSENTE = 300  # sem teclado/mouse por 5 min = ausente (só Windows)

# ---------------------------------------------------------------------------
# Listas de programas. Ajuste pros seus. Nomes em minúsculas.
# ---------------------------------------------------------------------------
if WINDOWS:
    # Jogos que você quer forçar como "jogando" (a janela em primeiro plano é
    # esse exe). Jogos em tela cheia já são detectados sem precisar listar.
    JOGOS = set()  # exemplo: {"eldenring.exe", "valorant-win64-shipping.exe"}
    CODANDO = {"code.exe", "cursor.exe", "devenv.exe", "pycharm64.exe",
               "idea64.exe", "nvim.exe", "arduino ide.exe"}
    MIDIA = {"spotify.exe", "vlc.exe", "mpv.exe"}
    # Apps que podem ficar em tela cheia mas NÃO são jogo
    NAO_JOGO = {"explorer.exe", "chrome.exe", "firefox.exe", "msedge.exe",
                "brave.exe", "vlc.exe", "mpv.exe", "code.exe", "cursor.exe",
                "applicationframehost.exe", "searchhost.exe", "lockapp.exe",
                "logonui.exe"}
else:
    JOGOS = {"gamescope", "reaper", "lutris-wrapper"}
    CODANDO = {"code", "nvim", "vim", "arduino-ide", "idea", "pycharm", "zed"}
    MIDIA = {"spotify", "mpv", "vlc"}
    NAO_JOGO = set()

# ---------------------------------------------------------------------------
# Windows: janela em primeiro plano e tempo sem teclado/mouse (sem libs extras)
# ---------------------------------------------------------------------------
if WINDOWS:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

    def segundos_ocioso():
        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(info)
        user32.GetLastInputInfo(ctypes.byref(info))
        return ((kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000.0

    def app_em_primeiro_plano():
        """Retorna (nome do processo, está em tela cheia no monitor principal?)."""
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
else:
    def segundos_ocioso():
        return 0.0

    def app_em_primeiro_plano():
        return "", False


def detectar():
    nomes = set()
    for p in psutil.process_iter(["name"]):
        try:
            nomes.add((p.info["name"] or "").lower())
        except psutil.Error:
            pass

    primeiro, cheia = app_em_primeiro_plano()
    if WINDOWS:
        jogando = primeiro in JOGOS or bool(cheia and primeiro and primeiro not in NAO_JOGO)
    else:
        jogando = bool(nomes & JOGOS)
    midia = bool(nomes & MIDIA)

    if jogando:
        estado = "GAMING"            # controle de jogo não conta como "input", por isso vem primeiro
    elif segundos_ocioso() > SEGUNDOS_AUSENTE:
        estado = "MEDIA" if midia else "AWAY"
    elif nomes & CODANDO:
        estado = "CODING"
    elif midia:
        estado = "MEDIA"
    else:
        estado = "IDLE"
    return estado, primeiro


def main():
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"deskbot-{NOME}")
    # Se este PC cair/desligar sem avisar, o broker publica isso por nós
    c.will_set(TOPICO, json.dumps({"state": "OFFLINE"}), retain=True)
    c.connect(BROKER, 1883, 60)
    c.loop_start()
    print(f"Agente '{NOME}' -> {BROKER} ({TOPICO})")

    ultimo, t_pub = None, 0.0
    try:
        while True:
            estado, janela = detectar()
            agora = time.time()
            if estado != ultimo or agora - t_pub > 10:
                c.publish(TOPICO, json.dumps({"state": estado}), retain=True)
                if estado != ultimo:
                    print(f"estado: {estado}   (janela em foco: {janela or '-'})")
                ultimo, t_pub = estado, agora
            time.sleep(2)
    finally:
        c.publish(TOPICO, json.dumps({"state": "OFFLINE"}), retain=True).wait_for_publish()
        c.loop_stop()
        c.disconnect()


if __name__ == "__main__":
    main()