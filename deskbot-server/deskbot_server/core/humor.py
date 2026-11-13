"""Modelo de humor interno e consolidação de múltiplos PCs do DeskBot."""
import threading
import time
from datetime import datetime

from deskbot_server.core.circadian import clamp, fator_circadiano
from deskbot_server.core.decision import escolher_expressao

# Hierarquia de prioridade entre múltiplos PCs:
# GAMING > CODING > MEDIA > IDLE > AWAY > OFFLINE
PRIORIDADE = ["GAMING", "CODING", "MEDIA", "IDLE", "AWAY", "OFFLINE"]
ORDEM_PRIORIDADE = {estado: i for i, estado in enumerate(PRIORIDADE)}
MAX_PCS = 16
MIN_TOUCH_INTERVAL = 0.2  # 200ms entre toques processados


class Cerebro:
    """Núcleo cognitivo e de humor do DeskBot."""

    def __init__(self):
        self._lock = threading.RLock()
        self.MAX_PCS = MAX_PCS
        self.MIN_TOUCH_INTERVAL = MIN_TOUCH_INTERVAL
        self._ultimo_toque_ts = 0.0

        self.pcs = {}                # nome -> estado (ex: {"cachyos": "CODING", "windows": "OFFLINE"})
        self.pc = "OFFLINE"          # GAMING, CODING, MEDIA, IDLE, AWAY, OFFLINE (estado consolidado)
        self.desde = time.time()     # quando o estado consolidado do PC mudou
        self.energia = 0.8
        self.tedio = 0.0
        self.felicidade = 0.5
        self.ev_expr = None          # expressão temporária (reação a evento)
        self.ev_ate = 0.0
        self.despertou_hoje = False  # rastreia se o bot já comemorou o despertar matinal
        self.ultimo_dia_despertar = None
        self.ultima_fase = None
        self.soneca_forcada = False  # ativado via long-press do touch na tela

    def evento(self, expr, segundos, agora_ts=None):
        with self._lock:
            ts = time.time() if agora_ts is None else agora_ts
            self.ev_expr, self.ev_ate = expr, ts + segundos

    def consolidar_estado(self):
        """Retorna o estado de maior prioridade entre todos os PCs monitorados."""
        with self._lock:
            if not self.pcs:
                return "OFFLINE"
            return min(self.pcs.values(), key=lambda est: ORDEM_PRIORIDADE.get(est, 99))

    def atualizar_pc(self, nome, estado, agora_dt=None, agora_ts=None):
        """Atualiza o estado de um PC específico e recalcula o estado consolidado."""
        with self._lock:
            if agora_dt is None:
                agora_dt = datetime.now()
            if agora_ts is None:
                agora_ts = time.time()

            hora = agora_dt.hour
            minuto = agora_dt.minute
            dia_atual = agora_dt.date()

            estado = (estado or "").upper()
            if estado not in ORDEM_PRIORIDADE:
                print(f"Aviso: estado desconhecido '{estado}' recebido do PC '{nome}'")
                return

            # Mitiga esgotamento de memória limitando quantidade de máquinas
            if nome not in self.pcs and len(self.pcs) >= self.MAX_PCS:
                chave_remover = None
                for k, v in self.pcs.items():
                    if v == "OFFLINE":
                        chave_remover = k
                        break
                if chave_remover is None:
                    chave_remover = next(iter(self.pcs))
                del self.pcs[chave_remover]
                print(f"Aviso: limite de {self.MAX_PCS} PCs atingido. PC '{chave_remover}' descartado da memória.")

            estado_anterior_pc = self.pcs.get(nome)
            self.pcs[nome] = estado

            novo_consolidado = self.consolidar_estado()
            antigo_consolidado = self.pc

            if novo_consolidado != antigo_consolidado:
                self.pc = novo_consolidado
                self.desde = agora_ts

                if antigo_consolidado in ("OFFLINE", "AWAY") and novo_consolidado not in ("OFFLINE", "AWAY"):
                    self.soneca_forcada = False
                    # Reações circadianas especiais ao retorno do usuário:
                    if 1 <= hora < 5:
                        # Alta madrugada: bot se espanta com o usuário acordado a essa hora
                        self.evento("surpreso", 6.0, agora_ts=agora_ts)
                        print(f"🌙 [Circadiano] Alta madrugada ({hora:02d}:{minuto:02d}): "
                              f"Usuário ativo! DeskBot espantado (surpreso).")
                    elif 6 <= hora < 12 and not self.despertou_hoje:
                        # Manhã: primeira atividade matinal comemora o despertar
                        self.despertou_hoje = True
                        self.ultimo_dia_despertar = dia_atual
                        self.felicidade = clamp(self.felicidade + 0.3)
                        self.evento("feliz", 8.0, agora_ts=agora_ts)
                        print(f"☀️ [Circadiano] Manhã ({hora:02d}:{minuto:02d}): "
                              f"Bom dia! DeskBot despertou com a primeira atividade matinal.")
                    else:
                        self.felicidade = clamp(self.felicidade + 0.2)
                        self.evento("feliz", 6.0, agora_ts=agora_ts)              # "você voltou!"
                elif novo_consolidado in ("GAMING", "CODING", "MEDIA"):
                    self.evento("curioso", 2.5, agora_ts=agora_ts)          # notou algo novo

                print(f"PC '{nome}' ({estado_anterior_pc} -> {estado}) | "
                      f"Consolidado: {antigo_consolidado} -> {novo_consolidado}")
            else:
                if estado_anterior_pc != estado:
                    print(f"PC '{nome}': {estado_anterior_pc} -> {estado} (Consolidado mantido: {self.pc})")

    def novo_estado_pc(self, novo, nome="default", agora_dt=None, agora_ts=None):
        """Método de compatibilidade para receber novo estado."""
        self.atualizar_pc(nome, novo, agora_dt=agora_dt, agora_ts=agora_ts)

    def processar_toque(self, evento: str, dados: dict = None, agora_ts: float = None) -> dict:
        """Processa interações diretas por toque enviadas pelo ESP32/TFT."""
        with self._lock:
            if agora_ts is None:
                agora_ts = time.time()

            # Rate limit interno de 200ms entre eventos de toque processados
            if (agora_ts - self._ultimo_toque_ts) < self.MIN_TOUCH_INTERVAL:
                return {"acao": "rate_limited", "evento": evento}
            self._ultimo_toque_ts = agora_ts

            dados = dados or {}
            ev = (evento or "").lower().strip()

            if ev in ("tap", "touch"):
                if self.soneca_forcada:
                    # Toque acorda o bot da soneca forçada
                    self.soneca_forcada = False
                    self.energia = max(self.energia, 0.5)
                    self.felicidade = clamp(self.felicidade + 0.1)
                    self.evento("curioso", 3.0, agora_ts=agora_ts)
                    print("👆 [Touch] DeskBot acordou da soneca com um toque suave!")
                    return {"acao": "despertar", "energia": self.energia, "expr": "curioso"}

                # Carinho na tela! Eleva a felicidade em +0.15 e dispara expressão feliz
                self.felicidade = clamp(self.felicidade + 0.15)
                self.tedio = clamp(self.tedio - 0.2)
                self.evento("feliz", 4.0, agora_ts=agora_ts)
                print(f"💖 [Touch] Carinho recebido na tela! Felicidade={self.felicidade:.2f}")
                return {"acao": "carinho", "felicidade": self.felicidade, "expr": "feliz"}

            elif ev in ("long_press", "longpress"):
                if self.soneca_forcada or self.energia <= 0.2:
                    # Acorda da soneca e recupera energia
                    self.soneca_forcada = False
                    self.energia = 0.85
                    self.felicidade = clamp(self.felicidade + 0.2)
                    self.evento("feliz", 4.0, agora_ts=agora_ts)
                    print("⏰ [Touch] Toque longo acordou o DeskBot! Energia revigorada.")
                    return {"acao": "despertar", "energia": self.energia, "expr": "feliz"}
                else:
                    # Força modo soneca
                    self.soneca_forcada = True
                    self.energia = 0.05
                    self.evento("dormindo", 4.0, agora_ts=agora_ts)
                    print("💤 [Touch] Toque longo colocou o DeskBot em modo soneca.")
                    return {"acao": "soneca", "energia": self.energia, "expr": "dormindo"}

            return {"acao": "ignorado", "evento": evento}

    def tick(self, dt=1.0, agora_dt=None):
        """Atualiza humores e ritmos circadianos do DeskBot."""
        with self._lock:
            if agora_dt is None:
                agora_dt = datetime.now()

            hora = agora_dt.hour
            minuto = agora_dt.minute
            dia_atual = agora_dt.date()

            # Reseta flag de despertar matinal ao entrar na madrugada
            if hora < 6:
                self.despertou_hoje = False
            elif self.ultimo_dia_despertar != dia_atual and hora >= 12:
                self.ultimo_dia_despertar = dia_atual

            ritmo = fator_circadiano(hora, minuto)
            self.ultima_fase = ritmo["fase"]

            ativo = self.pc in ("GAMING", "CODING")

            # Energia: modulada pelas taxas circadianas
            if ativo:
                # Gasto padrão em ~4h multiplicado pelo ritmo (ex: 1.6x na madrugada)
                taxa = (dt / (4 * 3600)) * ritmo["taxa_drenagem"]
                self.energia -= taxa
            elif self.pc == "MEDIA":
                taxa = (dt / (6 * 3600)) * ritmo["taxa_drenagem"]
                self.energia -= taxa
            elif self.pc in ("IDLE", "AWAY", "OFFLINE"):
                # Recuperação base de ~30 min modulada pelo ritmo
                taxa = (dt / 1800) * ritmo["taxa_recuperacao"]
                self.energia += taxa

            teto = ritmo["teto_energia"]
            self.energia = clamp(min(self.energia, teto))

            # Tédio: sobe quando inativo, desce rápido na atividade
            if self.pc in ("IDLE", "AWAY", "OFFLINE"):
                multiplicador_tedio = 1.3 if ritmo["fase"] == "slump_tarde" else 1.0
                self.tedio = clamp(self.tedio + (dt / 900) * multiplicador_tedio)
            else:
                self.tedio = clamp(self.tedio - dt / 60)

            # Felicidade: homeostase em direção ao 0.5; mídia anima
            self.felicidade += (0.5 - self.felicidade) * dt / 600
            if self.pc == "MEDIA":
                self.felicidade += dt / 300
            self.felicidade = clamp(self.felicidade)

            return ritmo

    def escolher(self, agora_dt=None, agora_ts=None):
        """Seleciona a expressão facial correspondente ao humor, PC e ciclo circadiano."""
        with self._lock:
            return escolher_expressao(self, agora_dt=agora_dt, agora_ts=agora_ts)
