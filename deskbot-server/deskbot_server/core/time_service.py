"""Serviço de tempo e saudações contextuais do DeskBot."""
from datetime import datetime

DIAS_SEMANA = [
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sábado",
    "Domingo",
]

MESES = [
    "",
    "Jan",
    "Fev",
    "Mar",
    "Abr",
    "Mai",
    "Jun",
    "Jul",
    "Ago",
    "Set",
    "Out",
    "Nov",
    "Dez",
]


class ServicoTempo:
    """Gera informações de tempo, calendário e saudações contextuais personalizadas."""

    def __init__(self, nome_usuario: str = "Arthur"):
        self.nome_usuario = nome_usuario

    def gerar_saudacao(self, agora_dt: datetime, estado_pc: str = "OFFLINE") -> str:
        """Gera uma saudação contextual baseada na hora do dia e no estado da máquina."""
        hora = agora_dt.hour
        pc = (estado_pc or "OFFLINE").upper()

        if 0 <= hora < 5:
            if pc == "CODING":
                return "Noite adentro no código"
            elif pc == "GAMING":
                return "Madrugada gamer!"
            elif pc in ("AWAY", "IDLE", "OFFLINE"):
                return "Madrugada silenciosa... Zzz"
            return f"Alta madrugada, {self.nome_usuario}!"

        if 5 <= hora < 12:
            if pc == "CODING":
                return f"Bom dia, {self.nome_usuario}! Foco no código!"
            return f"Bom dia, {self.nome_usuario}!"

        if 12 <= hora < 14:
            if pc in ("AWAY", "IDLE", "OFFLINE"):
                return "Pausa para o almoço!"
            return f"Boa tarde, {self.nome_usuario}! Almoçou?"

        if 14 <= hora < 18:
            if pc == "CODING":
                return "Tarde focada no código!"
            elif pc == "GAMING":
                return "Tarde de jogatina!"
            return f"Boa tarde, {self.nome_usuario}!"

        if 18 <= hora < 23:
            if pc == "GAMING":
                return "Noite de relaxar nos jogos!"
            elif pc == "CODING":
                return "Noite produtiva no código!"
            return f"Boa noite, {self.nome_usuario}!"

        # 23h
        if pc == "CODING":
            return "Noite adentro no código"
        return f"Boa noite, {self.nome_usuario}!"

    def obter_status_tempo(self, agora_dt: datetime = None, estado_pc: str = "OFFLINE") -> dict:
        """Retorna o payload completo de tempo para publicação via MQTT."""
        if agora_dt is None:
            agora_dt = datetime.now()

        hora = agora_dt.hour
        if 5 <= hora < 12:
            periodo = "manha"
        elif 12 <= hora < 18:
            periodo = "tarde"
        elif 18 <= hora < 23:
            periodo = "noite"
        else:
            periodo = "madrugada"

        dia_sem = DIAS_SEMANA[agora_dt.weekday()]
        mes_nome = MESES[agora_dt.month] if 1 <= agora_dt.month <= 12 else ""
        data_formatada = f"{agora_dt.day:02d} {mes_nome} {agora_dt.year}"

        saudacao = self.gerar_saudacao(agora_dt, estado_pc)

        return {
            "time": agora_dt.strftime("%H:%M"),
            "date": agora_dt.strftime("%d/%m/%Y"),
            "date_display": data_formatada,
            "day_of_week": dia_sem,
            "period": periodo,
            "greeting": saudacao,
        }
