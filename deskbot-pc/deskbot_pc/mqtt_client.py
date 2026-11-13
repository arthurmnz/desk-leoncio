"""Cliente MQTT resiliente para envio de telemetria do DeskBot PC."""
import json

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None


class AgenteMQTT:
    """Gerencia a conexão MQTT e publicação de estados do agente local."""

    def __init__(self, broker: str, topico: str, nome: str, porta: int = 1883):
        if mqtt is None:
            raise RuntimeError(
                "A biblioteca 'paho-mqtt' é necessária para executar o cliente MQTT. "
                "Instale com 'pip install paho-mqtt'."
            )
        self.broker = broker
        self.topico = topico
        self.nome = nome
        self.porta = porta

        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"deskbot-{self.nome}",
        )
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

        # Se o PC desligar abruptamente, o broker publica OFFLINE automaticamente
        self._client.will_set(
            self.topico,
            json.dumps({"state": "OFFLINE"}),
            retain=True,
        )

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        falha = reason_code.is_failure if hasattr(reason_code, "is_failure") else (reason_code != 0)

        if not falha:
            print(f"✓ Broker conectado com sucesso em {self.broker}:{self.porta} (tópico: {self.topico})")
        else:
            print(f"✗ Falha ao conectar ao broker MQTT em {self.broker}:{self.porta} - Código: {reason_code}")
            print("  Dicas para resolução:")
            print(f"  1. Verifique se o IP informado em DESKBOT_BROKER ({self.broker}) no seu .env está correto.")
            print("  2. Verifique se o broker Mosquitto está ativo no homelab.")
            print("  3. Verifique se a porta 1883 está liberada no firewall do homelab e do PC.")

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None):
        falha = reason_code.is_failure if hasattr(reason_code, "is_failure") else (reason_code != 0)

        if falha:
            print(f"⚠ Conexão perdida com o broker MQTT ({self.broker}:{self.porta}) - Motivo: {reason_code}")
            print("  Dicas para resolução:")
            print(f"  1. Verifique se o homelab ({self.broker}) está ligado e conectado na mesma rede.")
            print("  2. Verifique se o serviço Mosquitto permanece ativo.")
            print("  3. Verifique se a porta 1883 não está sendo bloqueada.")
            print("  Tentando reconectar automaticamente...")
        else:
            print(f"Desconectado do broker MQTT ({self.broker}:{self.porta}) normalmente.")

    def iniciar(self):
        """Conecta ao broker e inicia o loop de rede em segundo plano."""
        print(f"Iniciando agente DeskBot '{self.nome}'...")
        print(f"Conectando ao broker MQTT em {self.broker}:{self.porta} (tópico: {self.topico})...")

        try:
            self._client.connect(self.broker, self.porta, 60)
        except Exception as e:
            print(f"✗ Não foi possível conectar de imediato ao broker {self.broker}:{self.porta}")
            print(f"  Erro: {e}")
            print("  Dicas para resolução:")
            print(f"  1. Confirme se o IP configurado em DESKBOT_BROKER ({self.broker}) no seu arquivo .env está correto.")
            print("  2. Verifique se o Mosquitto está em execução no homelab e se a porta 1883 está acessível.")
            print("  3. Verifique se regras de firewall no homelab ou no PC estão bloqueando a porta 1883.")
            print("  O agente continuará tentando conectar em segundo plano...")
            try:
                self._client.connect_async(self.broker, self.porta, 60)
            except Exception as e_async:
                print(f"  Erro ao iniciar conexão assíncrona: {e_async}")

        self._client.loop_start()

    def publicar_estado(self, estado: str):
        """Publica o estado de atividade atual no tópico do PC."""
        self._client.publish(
            self.topico,
            json.dumps({"state": estado}),
            retain=True,
        )

    def parar(self):
        """Publica OFFLINE e desconecta graciosamente."""
        try:
            self._client.publish(
                self.topico,
                json.dumps({"state": "OFFLINE"}),
                retain=True,
            ).wait_for_publish(timeout=3)
        except Exception:
            pass
        self._client.loop_stop()
        self._client.disconnect()
        print(f"Agente '{self.nome}' finalizado.")
