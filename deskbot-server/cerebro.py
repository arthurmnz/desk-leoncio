"""Cérebro do DeskBot: roda 24/7 no homelab.

Recebe o estado do PC, mantém o humor interno (energia, tédio, felicidade),
escolhe a expressão e publica pro ESP32. Também grava um CSV pra treinar
uma rede neural no futuro.
"""
import csv
import json
import os
import time
from datetime import datetime

import paho.mqtt.client as mqtt


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

BROKER = os.environ.get("BROKER", "localhost")
T_PC_WILDCARD = "desk/pc/+/activity"
T_PC_LEGACY = "desk/pc/activity"
T_BOT = "desk/bot/state"
LOG = os.environ.get("LOG", "deskbot_log.csv")

# Hierarquia de prioridade entre múltiplos PCs:
# GAMING > CODING > MEDIA > IDLE > AWAY > OFFLINE
PRIORIDADE = ["GAMING", "CODING", "MEDIA", "IDLE", "AWAY", "OFFLINE"]
ORDEM_PRIORIDADE = {estado: i for i, estado in enumerate(PRIORIDADE)}


def clamp(v):
    return max(0.0, min(1.0, v))


class Cerebro:
    def __init__(self):
        self.pcs = {}                # nome -> estado (ex: {"cachyos": "CODING", "windows": "OFFLINE"})
        self.pc = "OFFLINE"          # GAMING, CODING, MEDIA, IDLE, AWAY, OFFLINE (estado consolidado)
        self.desde = time.time()     # quando o estado consolidado do PC mudou
        self.energia = 0.8
        self.tedio = 0.0
        self.felicidade = 0.5
        self.ev_expr = None          # expressão temporária (reação a evento)
        self.ev_ate = 0.0

    def evento(self, expr, segundos):
        self.ev_expr, self.ev_ate = expr, time.time() + segundos

    def consolidar_estado(self):
        """Retorna o estado de maior prioridade entre todos os PCs monitorados."""
        if not self.pcs:
            return "OFFLINE"
        return min(self.pcs.values(), key=lambda est: ORDEM_PRIORIDADE.get(est, 99))

    def atualizar_pc(self, nome, estado):
        """Atualiza o estado de um PC específico e recalcula o estado consolidado."""
        estado = (estado or "").upper()
        if estado not in ORDEM_PRIORIDADE:
            print(f"Aviso: estado desconhecido '{estado}' recebido do PC '{nome}'")

        estado_anterior_pc = self.pcs.get(nome)
        self.pcs[nome] = estado

        novo_consolidado = self.consolidar_estado()
        antigo_consolidado = self.pc

        if novo_consolidado != antigo_consolidado:
            self.pc = novo_consolidado
            self.desde = time.time()
            if antigo_consolidado in ("OFFLINE", "AWAY") and novo_consolidado not in ("OFFLINE", "AWAY"):
                self.felicidade = clamp(self.felicidade + 0.2)
                self.evento("feliz", 6)              # "você voltou!"
            elif novo_consolidado in ("GAMING", "CODING", "MEDIA"):
                self.evento("curioso", 2.5)          # notou algo novo
            print(f"PC '{nome}' ({estado_anterior_pc} -> {estado}) | Consolidado: {antigo_consolidado} -> {novo_consolidado}")
        else:
            if estado_anterior_pc != estado:
                print(f"PC '{nome}': {estado_anterior_pc} -> {estado} (Consolidado mantido: {self.pc})")

    def novo_estado_pc(self, novo, nome="default"):
        """Método de compatibilidade para receber novo estado."""
        self.atualizar_pc(nome, novo)

    def tick(self, dt):
        hora = datetime.now().hour
        ativo = self.pc in ("GAMING", "CODING")

        # Energia: gasta em ~4h de uso, recupera em ~30 min de descanso
        if ativo:
            self.energia -= dt / (4 * 3600)
        elif self.pc in ("IDLE", "AWAY", "OFFLINE"):
            self.energia += dt / 1800
        teto = 0.5 if 0 <= hora < 6 else 1.0     # madrugada cansa
        self.energia = clamp(min(self.energia, teto))

        # Tédio: sobe quando nada acontece, some rápido quando há atividade
        if self.pc in ("IDLE", "AWAY", "OFFLINE"):
            self.tedio = clamp(self.tedio + dt / 900)
        else:
            self.tedio = clamp(self.tedio - dt / 60)

        # Felicidade: volta pro meio aos poucos; música ajuda
        self.felicidade += (0.5 - self.felicidade) * dt / 600
        if self.pc == "MEDIA":
            self.felicidade += dt / 300
        self.felicidade = clamp(self.felicidade)

    def escolher(self):
        agora = time.time()
        hora = datetime.now().hour
        if agora < self.ev_ate and self.ev_expr:
            return self.ev_expr

        if self.pc in ("OFFLINE", "AWAY"):
            noite = hora >= 23 or hora < 6
            if self.energia < 0.5 or noite:
                return "dormindo" if agora - self.desde > 600 else "sonolento"
            return "entediado" if self.tedio > 0.6 else "neutro"

        if self.energia < 0.25:
            return "sonolento"
        if self.pc == "GAMING":
            return "jogando"
        if self.pc == "CODING":
            return "codando"
        if self.pc == "MEDIA":
            return "feliz"
        return "curioso" if self.tedio > 0.5 else "neutro"


def main():
    cerebro = Cerebro()

    def on_connect(client, userdata, flags, reason_code, properties=None):
        if hasattr(reason_code, "is_failure"):
            falha = reason_code.is_failure
        else:
            falha = (reason_code != 0)

        if not falha:
            print(f"✓ Cérebro conectado ao MQTT em {BROKER}:1883 (código: {reason_code})")
            client.subscribe([(T_PC_WILDCARD, 0), (T_PC_LEGACY, 0)])
            print(f"  Inscrito nos tópicos: '{T_PC_WILDCARD}' e '{T_PC_LEGACY}'")
        else:
            print(f"✗ Falha ao conectar ao broker MQTT: {reason_code}")

    def on_disconnect(client, userdata, disconnect_flags, reason_code, properties=None):
        if hasattr(reason_code, "is_failure"):
            falha = reason_code.is_failure
        else:
            falha = (reason_code != 0)
        if falha:
            print(f"⚠ Cérebro desconectado do MQTT ({BROKER}): {reason_code}. Tentando reconectar...")
        else:
            print("Cérebro desconectado do MQTT normalmente.")

    def on_message(client, userdata, msg):
        try:
            payload_str = msg.payload.decode("utf-8") if isinstance(msg.payload, (bytes, bytearray)) else msg.payload
            dados = json.loads(payload_str)
            estado = dados.get("state")
            if not estado:
                return

            partes = msg.topic.split("/")
            if len(partes) >= 4 and partes[0] == "desk" and partes[1] == "pc" and partes[3] == "activity":
                nome_pc = partes[2]
            else:
                nome_pc = "default"

            cerebro.atualizar_pc(nome_pc, estado)
        except Exception as e:
            print(f"mensagem inválida no tópico '{msg.topic}':", e)

    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="deskbot-cerebro")
    c.on_connect = on_connect
    c.on_disconnect = on_disconnect
    c.on_message = on_message

    print(f"Iniciando cérebro do DeskBot...")
    print(f"Conectando ao broker MQTT em {BROKER}:1883...")

    try:
        c.connect(BROKER, 1883, 60)
    except Exception as e:
        print(f"✗ Não foi possível conectar de imediato ao broker {BROKER}:1883: {e}")
        print("  Tentando conexão assíncrona em segundo plano...")
        try:
            c.connect_async(BROKER, 1883, 60)
        except Exception as e_async:
            print(f"  Erro ao iniciar conexão assíncrona: {e_async}")

    c.loop_start()

    log_dir = os.path.dirname(os.path.abspath(LOG))
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
        except Exception as e:
            print(f"Aviso: não foi possível criar diretório de log '{log_dir}': {e}")

    ultima_expr, t_pub, t_log = None, 0.0, 0.0
    novo_arquivo = not os.path.exists(LOG)
    with open(LOG, "a", newline="") as f:
        w = csv.writer(f)
        if novo_arquivo:
            w.writerow(["hora", "pc", "energia", "tedio", "felicidade", "expressao"])
            f.flush()
        try:
            while True:
                cerebro.tick(1.0)
                expr = cerebro.escolher()
                agora = time.time()

                # Publica ao mudar e a cada 15 s (heartbeat: o ESP32 sabe que o cérebro vive)
                if expr != ultima_expr or agora - t_pub > 15:
                    payload = {"expr": expr, "energy": round(cerebro.energia, 2)}
                    c.publish(T_BOT, json.dumps(payload), retain=True)
                    if expr != ultima_expr:
                        print("expressão:", expr)
                    ultima_expr, t_pub = expr, agora

                if agora - t_log >= 60:
                    w.writerow([datetime.now().isoformat(timespec="seconds"), cerebro.pc,
                                round(cerebro.energia, 2), round(cerebro.tedio, 2),
                                round(cerebro.felicidade, 2), expr])
                    f.flush()
                    t_log = agora
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nEncerrando cérebro do DeskBot...")
        finally:
            c.loop_stop()
            c.disconnect()
            print("Cérebro finalizado.")


if __name__ == "__main__":
    main()