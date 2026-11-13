"""Camada de infraestrutura: configurações, MQTT e telemetria."""
from deskbot_server.infrastructure.config import (
    BROKER,
    LOG,
    T_BOT,
    T_PC_LEGACY,
    T_PC_WILDCARD,
    carregar_env,
)
from deskbot_server.infrastructure.mqtt_client import ClienteMQTT
from deskbot_server.infrastructure.telemetry import Telemetria

__all__ = [
    "BROKER",
    "LOG",
    "T_BOT",
    "T_PC_LEGACY",
    "T_PC_WILDCARD",
    "carregar_env",
    "ClienteMQTT",
    "Telemetria",
]
