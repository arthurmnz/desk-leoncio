"""DeskBot PC: Agente local de monitoramento de atividades."""
from deskbot_pc.catalogs import (
    CODANDO,
    JOGOS,
    MIDIA,
    NAO_JOGO,
    obter_catalogos,
)
from deskbot_pc.classifier import classificar_atividade, detectar
from deskbot_pc.config import (
    BROKER,
    NOME,
    SEGUNDOS_AUSENTE,
    TOPICO,
    WINDOWS,
    carregar_env,
    obter_nome_pc,
    obter_topico,
)
from deskbot_pc.mqtt_client import AgenteMQTT
from deskbot_pc.__main__ import main

__all__ = [
    "carregar_env",
    "BROKER",
    "WINDOWS",
    "NOME",
    "TOPICO",
    "SEGUNDOS_AUSENTE",
    "obter_nome_pc",
    "obter_topico",
    "JOGOS",
    "CODANDO",
    "MIDIA",
    "NAO_JOGO",
    "obter_catalogos",
    "detectar",
    "classificar_atividade",
    "AgenteMQTT",
    "main",
]
