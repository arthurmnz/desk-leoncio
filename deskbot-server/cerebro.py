"""Cérebro do DeskBot: roda 24/7 no homelab.

Shim retrocompatível que importa os módulos da nova arquitetura `deskbot_server`.
Mantém compatibilidade total com comandos existentes, Docker Compose e suítes de testes.
"""
import sys
import os

# Garante que deskbot-server esteja no sys.path mesmo se executado diretamente
_DIR_SERVER = os.path.dirname(os.path.abspath(__file__))
if _DIR_SERVER not in sys.path:
    sys.path.insert(0, _DIR_SERVER)

from deskbot_server.core.circadian import (
    clamp,
    fator_circadiano,
    calcular_ritmo_circadiano,
)
from deskbot_server.core.decision import escolher, escolher_expressao
from deskbot_server.core.humor import (
    Cerebro,
    PRIORIDADE,
    ORDEM_PRIORIDADE,
)
from deskbot_server.infrastructure.config import (
    carregar_env,
    BROKER,
    LOG,
    T_BOT,
    T_PC_LEGACY,
    T_PC_WILDCARD,
)
from deskbot_server.__main__ import main

__all__ = [
    "Cerebro",
    "fator_circadiano",
    "calcular_ritmo_circadiano",
    "clamp",
    "escolher",
    "escolher_expressao",
    "PRIORIDADE",
    "ORDEM_PRIORIDADE",
    "carregar_env",
    "BROKER",
    "LOG",
    "T_BOT",
    "T_PC_LEGACY",
    "T_PC_WILDCARD",
    "main",
]

if __name__ == "__main__":
    main()
