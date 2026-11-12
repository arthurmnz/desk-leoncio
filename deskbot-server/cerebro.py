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

BROKER = os.environ.get("BROKER", "localhost")
T_PC = "desk/pc/activity"
T_BOT = "desk/bot/state"
LOG = os.environ.get("LOG", "deskbot_log.csv")


def clamp(v):
    return max(0.0, min(1.0, v))


class Cerebro:
    def __init__(self):
        self.pc = "OFFLINE"          # GAMING, CODING, MEDIA, IDLE, OFFLINE
        self.desde = time.time()     # quando o estado do PC mudou
        self.energia = 0.8
        self.tedio = 0.0
        self.felicidade = 0.5
        self.ev_expr = None          # expressão temporária (reação a evento)
        self.ev_ate = 0.0

    def evento(self, expr, segundos):
        self.ev_expr, self.ev_ate = expr, time.time() + segundos

    def novo_estado_pc(self, novo):
        if novo == self.pc:
            return
        antigo = self.pc
        self.pc, self.desde = novo, time.time()
        if antigo == "OFFLINE" and novo != "OFFLINE":
            self.felicidade = clamp(self.felicidade + 0.2)
            self.evento("feliz", 6)              # "você voltou!"
        elif novo in ("GAMING", "CODING", "MEDIA"):
            self.evento("curioso", 2.5)          # notou algo novo
        print(f"PC: {antigo} -> {novo}")

    def tick(self, dt):
        hora = datetime.now().hour
        ativo = self.pc in ("GAMING", "CODING")

        # Energia: gasta em ~4h de uso, recupera em ~30 min de descanso
        if ativo:
            self.energia -= dt / (4 * 3600)
        elif self.pc in ("IDLE", "OFFLINE"):
            self.energia += dt / 1800
        teto = 0.5 if 0 <= hora < 6 else 1.0     # madrugada cansa
        self.energia = clamp(min(self.energia, teto))

        # Tédio: sobe quando nada acontece, some rápido quando há atividade
        if self.pc in ("IDLE", "OFFLINE"):
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

        if self.pc == "OFFLINE":
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

    def on_connect(client, userdata, flags, reason_code, properties):
        print("MQTT conectado:", reason_code)
        client.subscribe(T_PC)

    def on_message(client, userdata, msg):
        try:
            cerebro.novo_estado_pc(json.loads(msg.payload)["state"])
        except Exception as e:
            print("mensagem inválida:", e)

    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="deskbot-cerebro")
    c.on_connect, c.on_message = on_connect, on_message
    c.connect(BROKER, 1883, 60)
    c.loop_start()

    ultima_expr, t_pub, t_log = None, 0.0, 0.0
    novo_arquivo = not os.path.exists(LOG)
    with open(LOG, "a", newline="") as f:
        w = csv.writer(f)
        if novo_arquivo:
            w.writerow(["hora", "pc", "energia", "tedio", "felicidade", "expressao"])
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


if __name__ == "__main__":
    main()