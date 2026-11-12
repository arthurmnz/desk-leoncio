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


def carregar_env(caminho_env=None):
    """Carrega variáveis de um arquivo .env para os.environ caso ainda não definidas."""
    if caminho_env is None:
        dir_script = os.path.dirname(os.path.abspath(__file__))
        candidatos = [
            os.path.join(dir_script, ".env"),
            os.path.join(os.getcwd(), ".env"),
            os.path.join(os.path.dirname(dir_script), ".env"),
        ]
        for c in candidatos:
            if os.path.isfile(c):
                caminho_env = c
                break

    if not caminho_env or not os.path.isfile(caminho_env):
        return

    try:
        with open(caminho_env, "r", encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if not linha or linha.startswith("#"):
                    continue
                if linha.startswith("export "):
                    linha = linha[7:].strip()
                if "=" not in linha:
                    continue
                chave, valor = linha.split("=", 1)
                chave = chave.strip()
                valor = valor.strip()
                if len(valor) >= 2 and ((valor[0] == '"' and valor[-1] == '"') or (valor[0] == "'" and valor[-1] == "'")):
                    valor = valor[1:-1]
                if chave and chave not in os.environ:
                    os.environ[chave] = valor
    except Exception as e:
        print(f"Aviso: erro ao carregar {caminho_env}: {e}")


carregar_env()

BROKER = os.environ.get("DESKBOT_BROKER", "192.168.0.5")  # <- IP do homelab
WINDOWS = sys.platform == "win32"
padrao_nome = "windows" if WINDOWS else "cachyos"
NOME = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DESKBOT_NOME", padrao_nome)
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


def on_connect(client, userdata, flags, reason_code, properties=None):
    if hasattr(reason_code, "is_failure"):
        falha = reason_code.is_failure
    else:
        falha = (reason_code != 0)

    if not falha:
        print(f"✓ Broker conectado com sucesso em {BROKER}:1883 (tópico: {TOPICO})")
    else:
        print(f"✗ Falha ao conectar ao broker MQTT em {BROKER}:1883 - Código: {reason_code}")
        print("  Dicas para resolução:")
        print(f"  1. Verifique se o IP informado em DESKBOT_BROKER ({BROKER}) no seu .env está correto.")
        print("  2. Verifique se o broker Mosquitto está ativo no homelab.")
        print("  3. Verifique se a porta 1883 está liberada no firewall do homelab e do PC.")


def on_disconnect(client, userdata, disconnect_flags, reason_code, properties=None):
    if hasattr(reason_code, "is_failure"):
        falha = reason_code.is_failure
    else:
        falha = (reason_code != 0)

    if falha:
        print(f"⚠ Conexão perdida com o broker MQTT ({BROKER}:1883) - Motivo: {reason_code}")
        print("  Dicas para resolução:")
        print(f"  1. Verifique se o homelab ({BROKER}) está ligado e conectado na mesma rede.")
        print("  2. Verifique se o serviço Mosquitto permanece ativo.")
        print("  3. Verifique se a porta 1883 não está sendo bloqueada.")
        print("  Tentando reconectar automaticamente...")
    else:
        print(f"Desconectado do broker MQTT ({BROKER}:1883) normalmente.")


def main():
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"deskbot-{NOME}")
    c.on_connect = on_connect
    c.on_disconnect = on_disconnect

    # Se este PC cair/desligar sem avisar, o broker publica isso por nós
    c.will_set(TOPICO, json.dumps({"state": "OFFLINE"}), retain=True)

    print(f"Iniciando agente DeskBot '{NOME}'...")
    print(f"Conectando ao broker MQTT em {BROKER}:1883 (tópico: {TOPICO})...")

    try:
        c.connect(BROKER, 1883, 60)
    except Exception as e:
        print(f"✗ Não foi possível conectar de imediato ao broker {BROKER}:1883")
        print(f"  Erro: {e}")
        print("  Dicas para resolução:")
        print(f"  1. Confirme se o IP configurado em DESKBOT_BROKER ({BROKER}) no seu arquivo .env está correto.")
        print("  2. Verifique se o Mosquitto está em execução no homelab e se a porta 1883 está acessível.")
        print("  3. Verifique se regras de firewall no homelab ou no PC estão bloqueando a porta 1883.")
        print("  O agente continuará tentando conectar em segundo plano...")
        try:
            c.connect_async(BROKER, 1883, 60)
        except Exception as e_async:
            print(f"  Erro ao iniciar conexão assíncrona: {e_async}")

    c.loop_start()

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
    except KeyboardInterrupt:
        print(f"\nEncerrando agente '{NOME}'...")
    finally:
        try:
            c.publish(TOPICO, json.dumps({"state": "OFFLINE"}), retain=True).wait_for_publish(timeout=3)
        except Exception:
            pass
        c.loop_stop()
        c.disconnect()
        print(f"Agente '{NOME}' finalizado.")


if __name__ == "__main__":
    main()