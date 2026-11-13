"""Ponto de entrada padrão executável do DeskBot Server."""
import time
from datetime import datetime

from deskbot_server.core.humor import Cerebro
from deskbot_server.infrastructure.config import LOG, carregar_env
from deskbot_server.infrastructure.mqtt_client import ClienteMQTT
from deskbot_server.infrastructure.telemetry import Telemetria


def main():
    carregar_env()
    cerebro = Cerebro()
    cliente_mqtt = ClienteMQTT(cerebro)
    cliente_mqtt.iniciar()

    telemetria = Telemetria(LOG)
    telemetria.abrir()

    ultima_expr, t_pub, t_log = None, 0.0, 0.0
    ultima_fase = None

    try:
        while True:
            agora_dt = datetime.now()
            agora = time.time()
            ritmo = cerebro.tick(1.0, agora_dt=agora_dt)
            expr = cerebro.escolher(agora_dt=agora_dt, agora_ts=agora)

            # Notifica mudança de fase circadiana no console
            if ritmo["fase"] != ultima_fase:
                print(f"⏰ [Circadiano] Nova fase do dia: {ritmo['label']} "
                      f"(teto={ritmo['teto_energia']:.2f}, drenagem={ritmo['taxa_drenagem']}x, "
                      f"recuperação={ritmo['taxa_recuperacao']}x, dormir_idle={ritmo['tempo_para_dormir']}s)")
                ultima_fase = ritmo["fase"]

            # Publica ao mudar e a cada 15 s (heartbeat: o ESP32 sabe que o cérebro vive)
            if expr != ultima_expr or agora - t_pub > 15:
                cliente_mqtt.publicar_estado(expr, cerebro.energia, ritmo["fase"])
                if expr != ultima_expr:
                    print(f"expressão: {expr} | energia: {cerebro.energia:.2f} | fase: {ritmo['label']}")
                ultima_expr, t_pub = expr, agora

            # Telemetria periódica em CSV e console a cada 60 s
            if agora - t_log >= 60:
                telemetria.registrar(
                    agora_dt=agora_dt,
                    pc=cerebro.pc,
                    energia=cerebro.energia,
                    tedio=cerebro.tedio,
                    felicidade=cerebro.felicidade,
                    expr=expr,
                    fase=ritmo["fase"],
                    label_fase=ritmo["label"],
                )
                t_log = agora

            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando cérebro do DeskBot...")
    finally:
        telemetria.fechar()
        cliente_mqtt.parar()


if __name__ == "__main__":
    main()
