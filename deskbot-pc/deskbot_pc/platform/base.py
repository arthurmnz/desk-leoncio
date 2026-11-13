"""Interface base para detecção de foco e ociosidade de periféricos do SO."""


class BasePlatformDetector:
    """Contrato base para provedores de estado de sistema operacional."""

    def segundos_ocioso(self) -> float:
        """Retorna o tempo em segundos desde a última entrada de teclado/mouse."""
        return 0.0

    def app_em_primeiro_plano(self) -> tuple[str, bool]:
        """Retorna tupla com (nome_processo_minúsculo, esta_em_tela_cheia)."""
        return "", False
