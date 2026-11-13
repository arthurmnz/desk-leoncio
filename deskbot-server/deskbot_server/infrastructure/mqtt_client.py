"""Gerenciamento de conexão MQTT resiliente e despacho de mensagens para o DeskBot."""
import json
from deskbot_server.infrastructure.config import BROKER, T_PC_WILDCARD, T_PC_LEGACY, T_BOT

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None


class ClienteMQTT:
    """Cliente MQTT resiliente para comunicação entre o Cérebro, PCs e ESP32."""

    def __init__(self, cerebro, broker=BROKER, porta=1883, client_id="deskbot-cerebro"):
        if mqtt is None:
            raise RuntimeError(
                "A biblioteca 'paho-mqtt' é necessária para executar o servidor MQTT. "
                "Instale com 'pip install paho-mqtt'."
            )
        self.cerebro = cerebro
        self.broker = broker
        self.porta = porta
        self.client_id = client_id

        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.client_id)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        falha = reason_code.is_failure if hasattr(reason_code, "is_failure") else (reason_code != 0)

        if not falha:
            print(f"✓ Cérebro conectado ao MQTT em {self.broker}:{self.porta} (código: {reason_code})")
            client.subscribe([(T_PC_WILDCARD, 0), (T_PC_LEGACY, 0)])
            print(f"  Inscrito nos tópicos: '{T_PC_WILDCARD}' e '{T_PC_LEGACY}'")
        else:
            print(f"✗ Falha ao conectar ao broker MQTT: {reason_code}")

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None):
        falha = reason_code.is_failure if hasattr(reason_code, "is_failure") else (reason_code != 0)
        if falha:
            print(f"⚠ Cérebro desconectado do MQTT ({self.broker}): {reason_code}. Tentando reconectar...")
        else:
            print("Cérebro desconectado do MQTT normalmente.")

    def _on_message(self, client, userdata, msg):
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

            self.cerebro.atualizar_pc(nome_pc, estado)
        except Exception as e:
            print(f"mensagem inválida no tópico '{msg.topic}':", e)

    def iniciar(self):
        """Conecta ao broker e inicia o loop assíncrono de eventos."""
        print("Iniciando cérebro do DeskBot com Ciclo Circadiano...")
        print(f"Conectando ao broker MQTT em {self.broker}:{self.porta}...")

        try:
            self._client.connect(self.broker, self.porta, 60)
        except Exception as e:
            print(f"✗ Não foi possível conectar de imediato ao broker {self.broker}:{self.porta}: {e}")
            print("  Tentando conexão assíncrona em segundo plano...")
            try:
                self._client.connect_async(self.broker, self.porta, 60)
            except Exception as e_async:
                print(f"  Erro ao iniciar conexão assíncrona: {e_async}")

        self._client.loop_start()

    def publicar_estado(self, expr, energia, fase):
        """Publica o estado e fase circadiana do DeskBot para o ESP32."""
        payload = {
            "expr": expr,
            "energy": round(energia, 2),
            "phase": fase,
        }
        self._client.publish(T_BOT, json.dumps(payload), retain=True)

    def parar(self):
        """Finaliza o loop de eventos e desconecta do broker."""
        self._client.loop_stop()
        self._client.disconnect()
        print("Cérebro finalizado.")
