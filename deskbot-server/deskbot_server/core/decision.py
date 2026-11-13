"""Lógica de decisão e seleção de expressões faciais do DeskBot."""
import time
from datetime import datetime

from deskbot_server.core.circadian import fator_circadiano


def escolher_expressao(cerebro, agora_dt=None, agora_ts=None):
    """Seleciona a expressão facial correspondente ao humor, PC e ciclo circadiano."""
    if agora_dt is None:
        agora_dt = datetime.now()
    if agora_ts is None:
        agora_ts = time.time()

    hora = agora_dt.hour
    minuto = agora_dt.minute
    ritmo = fator_circadiano(hora, minuto)

    # 1. Expressão temporária (evento) tem prioridade absoluta
    if agora_ts < cerebro.ev_ate and cerebro.ev_expr:
        return cerebro.ev_expr

    tempo_ausente = agora_ts - cerebro.desde
    limiar_dormir = ritmo["tempo_para_dormir"]

    # 2. Quando o PC está OFFLINE ou AWAY (usuário ausente)
    if cerebro.pc in ("OFFLINE", "AWAY"):
        if ritmo["fase"] in ("madrugada", "pre_sono"):
            # Na noite/madrugada dorme com tolerância curta (ex: 2.5 min na madrugada)
            return "dormindo" if tempo_ausente > limiar_dormir else "sonolento"

        # Durante o dia / slump:
        if cerebro.energia < 0.35 and tempo_ausente > limiar_dormir:
            return "dormindo"
        if tempo_ausente > 1200 and cerebro.energia < 0.6:  # Mais de 20 min ausente de dia
            return "dormindo"

        if cerebro.energia < 0.35:
            return "sonolento"
        return "entediado" if cerebro.tedio > ritmo["limiar_tedio"] else "neutro"

    # 3. Quando o PC está em IDLE (ligado, mas sem interação)
    if cerebro.pc == "IDLE":
        if ritmo["fase"] == "madrugada" and tempo_ausente > limiar_dormir:
            return "dormindo"
        if cerebro.energia < 0.35:
            return "sonolento"
        if cerebro.tedio > ritmo["limiar_tedio"]:
            return "entediado"
        return "curioso" if cerebro.tedio > 0.4 else "neutro"

    # 4. Quando o PC está em atividade (GAMING, CODING, MEDIA)
    # Se for na madrugada, o cansaço biológico se impõe (vai para sonolento)
    if ritmo["fase"] == "madrugada" and cerebro.energia < 0.40:
        return "sonolento"

    # Se a energia estiver em esgotamento crítico em qualquer horário
    if cerebro.energia < 0.20:
        return "sonolento"

    if cerebro.pc == "GAMING":
        return "jogando"
    if cerebro.pc == "CODING":
        return "codando"
    if cerebro.pc == "MEDIA":
        return "feliz"

    return "curioso" if cerebro.tedio > 0.5 else "neutro"


escolher = escolher_expressao
