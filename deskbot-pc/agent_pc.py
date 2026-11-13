#!/usr/bin/env python3
"""Agente do PC (Linux e Windows): detecta o que você faz e avisa o homelab via MQTT.

Uso:  python agent_pc.py             -> nome automático: "windows" ou "cachyos"
      python agent_pc.py meu-nome    -> nome personalizado

Estados publicados: GAMING, CODING, MEDIA, IDLE, AWAY (só Windows) e OFFLINE.

Shim retrocompatível que delega para a arquitetura modular `deskbot_pc`.
"""
import os
import sys

# Garante deskbot-pc no sys.path mesmo se chamado diretamente
_DIR_PC = os.path.dirname(os.path.abspath(__file__))
if _DIR_PC not in sys.path:
    sys.path.insert(0, _DIR_PC)

from deskbot_pc.catalogs import CODANDO, JOGOS, MIDIA, NAO_JOGO
from deskbot_pc.classifier import detectar
from deskbot_pc.config import (
    BROKER,
    NOME,
    SEGUNDOS_AUSENTE,
    TOPICO,
    WINDOWS,
    carregar_env,
)
from deskbot_pc.platform import app_em_primeiro_plano, segundos_ocioso
from deskbot_pc.__main__ import main

__all__ = [
    "carregar_env",
    "BROKER",
    "WINDOWS",
    "NOME",
    "TOPICO",
    "SEGUNDOS_AUSENTE",
    "JOGOS",
    "CODANDO",
    "MIDIA",
    "NAO_JOGO",
    "segundos_ocioso",
    "app_em_primeiro_plano",
    "detectar",
    "main",
]

if __name__ == "__main__":
    main()
