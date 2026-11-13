"""Classificador de estados do PC (GAMING, CODING, MEDIA, IDLE, AWAY, OFFLINE)."""
import sys
import psutil

from deskbot_pc.catalogs import obter_catalogos
from deskbot_pc.config import SEGUNDOS_AUSENTE, WINDOWS
from deskbot_pc.platform import detector as default_detector


def classificar_atividade(
    nomes_processos: set,
    primeiro_plano: str = "",
    tela_cheia: bool = False,
    segundos_ocioso: float = 0.0,
    is_windows: bool = False,
    segundos_ausente: float = SEGUNDOS_AUSENTE,
    catalogos: tuple = None,
) -> tuple[str, str]:
    """Classifica o estado do usuário com base em processos, ociosidade e tela cheia.

    Função pura e determinística, ideal para testes unitários com mocks.
    """
    if catalogos is None:
        jogos, codando, midia_set, nao_jogo = obter_catalogos(is_windows)
    else:
        jogos, codando, midia_set, nao_jogo = catalogos

    primeiro_lower = (primeiro_plano or "").lower()

    if is_windows:
        jogando = primeiro_lower in jogos or bool(
            tela_cheia and primeiro_lower and primeiro_lower not in nao_jogo
        )
    else:
        jogando = bool(nomes_processos & jogos)

    midia = bool(nomes_processos & midia_set)

    if jogando:
        estado = "GAMING"  # Controle de jogo não conta como "input", por isso tem prioridade
    elif segundos_ocioso > segundos_ausente:
        estado = "MEDIA" if midia else "AWAY"
    elif nomes_processos & codando:
        estado = "CODING"
    elif midia:
        estado = "MEDIA"
    else:
        estado = "IDLE"

    return estado, primeiro_plano


def detectar(detector_inst=None, is_windows=None, segundos_ausente=SEGUNDOS_AUSENTE) -> tuple[str, str]:
    """Inspeciona o sistema operacional e processos ativos para determinar o estado atual."""
    inst = detector_inst or default_detector
    win = WINDOWS if is_windows is None else is_windows

    nomes = set()
    for p in psutil.process_iter(["name"]):
        try:
            nome = (p.info["name"] or "").lower()
            if nome:
                nomes.add(nome)
        except psutil.Error:
            pass

    primeiro, cheia = inst.app_em_primeiro_plano()
    ocioso = inst.segundos_ocioso()

    return classificar_atividade(
        nomes_processos=nomes,
        primeiro_plano=primeiro,
        tela_cheia=cheia,
        segundos_ocioso=ocioso,
        is_windows=win,
        segundos_ausente=segundos_ausente,
    )
