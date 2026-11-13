"""Loop principal de pooling e despacho do DeskBot PC."""
import sys
import time

from deskbot_pc.classifier import detectar
from deskbot_pc.config import BROKER, obter_nome_pc, obter_topico
from deskbot_pc.mqtt_client import AgenteMQTT


def main(argv=None):
    nome = obter_nome_pc(argv)
    topico = obter_topico(nome)

    agente = AgenteMQTT(broker=BROKER, topico=topico, nome=nome)
    agente.iniciar()

    ultimo, t_pub = None, 0.0
    try:
        while True:
            estado, janela = detectar()
            agora = time.time()
            if estado != ultimo or agora - t_pub > 10:
                agente.publicar_estado(estado)
                if estado != ultimo:
                    print(f"estado: {estado}   (janela em foco: {janela or '-'})")
                ultimo, t_pub = estado, agora
            time.sleep(2)
    except KeyboardInterrupt:
        print(f"\nEncerrando agente '{nome}'...")
    finally:
        agente.parar()


if __name__ == "__main__":
    main()
