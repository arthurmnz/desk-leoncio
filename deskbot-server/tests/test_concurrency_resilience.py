"""Testes de concorrência, rate limiting e resiliência dos serviços do DeskBot."""
import json
import os
import sys
import threading
import time
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

_DIR_SERVER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _DIR_SERVER not in sys.path:
    sys.path.insert(0, _DIR_SERVER)

from deskbot_server.core.humor import Cerebro, MAX_PCS
from deskbot_server.core.weather import ServicoClima
from deskbot_server.infrastructure.mqtt_client import ClienteMQTT


class TestCerebroConcorrenciaERateLimit(unittest.TestCase):
    def setUp(self):
        self.cerebro = Cerebro()

    def test_rate_limit_toque(self):
        """Eventos de toque com intervalo inferior a 200ms são rate-limited."""
        t0 = 100.0
        res1 = self.cerebro.processar_toque("tap", agora_ts=t0)
        self.assertEqual(res1["acao"], "carinho")

        # Toque 100ms depois (< 200ms): deve ser ignorado com acao=rate_limited
        res2 = self.cerebro.processar_toque("tap", agora_ts=t0 + 0.10)
        self.assertEqual(res2["acao"], "rate_limited")

        # Toque 250ms depois do t0 (>= 200ms): deve ser aceito normalmente
        res3 = self.cerebro.processar_toque("tap", agora_ts=t0 + 0.25)
        self.assertEqual(res3["acao"], "carinho")

    def test_limite_max_pcs_e_descarte(self):
        """Ao ultrapassar MAX_PCS (16), chaves antigas/offline são descartadas."""
        for i in range(MAX_PCS):
            self.cerebro.atualizar_pc(f"pc_{i}", "OFFLINE")

        self.assertEqual(len(self.cerebro.pcs), MAX_PCS)

        # Adiciona o 17º PC
        self.cerebro.atualizar_pc("pc_extra", "CODING")
        self.assertEqual(len(self.cerebro.pcs), MAX_PCS)
        self.assertIn("pc_extra", self.cerebro.pcs)

    def test_thread_safety_cerebro(self):
        """Executa múltiplas threads simultâneas sem deadlocks ou inconsistências."""
        erros = []

        def worker_touch():
            for i in range(50):
                try:
                    self.cerebro.processar_toque("tap", agora_ts=1000.0 + (i * 0.25))
                except Exception as e:
                    erros.append(e)

        def worker_pc(pc_id):
            estados = ["CODING", "GAMING", "IDLE", "OFFLINE"]
            for i in range(50):
                try:
                    self.cerebro.atualizar_pc(f"pc_thread_{pc_id}", estados[i % len(estados)])
                except Exception as e:
                    erros.append(e)

        def worker_tick():
            for _ in range(50):
                try:
                    self.cerebro.tick(0.1)
                    self.cerebro.escolher()
                except Exception as e:
                    erros.append(e)

        threads = [
            threading.Thread(target=worker_touch),
            threading.Thread(target=worker_pc, args=(1,)),
            threading.Thread(target=worker_pc, args=(2,)),
            threading.Thread(target=worker_tick),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(erros), 0, f"Ocorreram erros de concorrência: {erros}")


class TestServicoClimaResiliencia(unittest.TestCase):
    def test_validacao_latitude_longitude_limites(self):
        """Latitude deve estar em [-90, 90] e Longitude em [-180, 180]."""
        # Valores válidos não devem lançar exceção
        servico = ServicoClima(latitude=0.0, longitude=0.0)
        self.assertEqual(servico.latitude, 0.0)
        self.assertEqual(servico.longitude, 0.0)

        # Latitude fora dos limites
        with self.assertRaises(ValueError):
            ServicoClima(latitude=91.0, longitude=0.0)
        with self.assertRaises(ValueError):
            ServicoClima(latitude=-90.5, longitude=0.0)

        # Longitude fora dos limites
        with self.assertRaises(ValueError):
            ServicoClima(latitude=0.0, longitude=180.5)
        with self.assertRaises(ValueError):
            ServicoClima(latitude=0.0, longitude=-181.0)

    @patch.object(ServicoClima, "_fazer_requisicao")
    def test_cooldown_apos_falha_nao_sobrecarrega(self, mock_req):
        """Falha de rede deve impor cooldown de 5 minutos (300s)."""
        mock_req.side_effect = TimeoutError("Serviço indisponível")
        servico = ServicoClima(intervalo_cache=900)

        # Primeira chamada falha
        res1 = servico.obter_clima(agora_ts=1000.0)
        self.assertFalse(res1["online"])
        self.assertEqual(mock_req.call_count, 1)

        # Chamada 60s depois deve estar em cooldown e NÃO tentar nova requisição
        res2 = servico.obter_clima(agora_ts=1060.0)
        self.assertEqual(mock_req.call_count, 1)
        self.assertFalse(res2["online"])

        # Chamada após 305s (passado o cooldown de 300s) deve tentar novamente
        res3 = servico.obter_clima(agora_ts=1305.0)
        self.assertEqual(mock_req.call_count, 2)

    @patch.object(ServicoClima, "_fazer_requisicao")
    def test_nao_vaza_detalhes_internos_erro(self, mock_req):
        """Erros de rede não devem vazar URLs sensíveis ou stack traces no MQTT."""
        mock_req.side_effect = Exception("Database credentials at postgres://user:secret@internal:5432")
        servico = ServicoClima()

        res = servico.obter_clima(agora_ts=1000.0)
        self.assertEqual(res["error"], "Falha ao obter dados meteorológicos")
        self.assertNotIn("credentials", res["error"])
        self.assertNotIn("secret", res["error"])


class TestMqttClientValidacao(unittest.TestCase):
    def setUp(self):
        self.cerebro = Cerebro()
        mock_mqtt = MagicMock()
        with patch("deskbot_server.infrastructure.mqtt_client.mqtt", mock_mqtt):
            self.cliente = ClienteMQTT(self.cerebro)
        self.cliente.publicar_estado = MagicMock()

    def test_on_message_payload_invalido_ignorado(self):
        """Payloads que não sejam dicts ou campos não-string são ignorados com segurança."""
        msg_invalida = MagicMock()
        msg_invalida.topic = "desk/bot/touch"
        # Payload com lista em vez de dict
        msg_invalida.payload = json.dumps(["nao_um_dict"]).encode("utf-8")
        self.cliente._on_message(None, None, msg_invalida)
        self.cliente.publicar_estado.assert_not_called()

        # Touch com event que não é string
        msg_touch_err = MagicMock()
        msg_touch_err.topic = "desk/bot/touch"
        msg_touch_err.payload = json.dumps({"event": 12345}).encode("utf-8")
        self.cliente._on_message(None, None, msg_touch_err)
        self.cliente.publicar_estado.assert_not_called()

        # PC activity com state que não é string
        msg_pc_err = MagicMock()
        msg_pc_err.topic = "desk/pc/activity"
        msg_pc_err.payload = json.dumps({"state": ["invalido"]}).encode("utf-8")
        self.cliente._on_message(None, None, msg_pc_err)
        self.assertEqual(self.cerebro.pc, "OFFLINE")


if __name__ == "__main__":
    unittest.main()
