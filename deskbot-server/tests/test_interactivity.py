"""Testes unitários dos novos serviços de interatividade: Clima, Tempo e Touch."""
import os
import sys
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

# Garante import do pacote deskbot-server
_DIR_SERVER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _DIR_SERVER not in sys.path:
    sys.path.insert(0, _DIR_SERVER)

from deskbot_server.core.weather import ServicoClima, descrever_weather_code
from deskbot_server.core.time_service import ServicoTempo
from deskbot_server.core.humor import Cerebro
from deskbot_server.core.decision import escolher_expressao


class TestServicoClima(unittest.TestCase):
    def test_descrever_weather_code(self):
        """Verifica a tradução de códigos WMO padrão."""
        self.assertEqual(descrever_weather_code(0), "Céu limpo")
        self.assertEqual(descrever_weather_code(1), "Predom. ensolarado")
        self.assertEqual(descrever_weather_code(3), "Encoberto")
        self.assertEqual(descrever_weather_code(61), "Chuva fraca")
        self.assertEqual(descrever_weather_code(95), "Tempestade")
        self.assertEqual(descrever_weather_code(999), "Tempo instável")

    @patch.object(ServicoClima, "_fazer_requisicao")
    def test_obter_clima_sucesso_e_cache(self, mock_req):
        """Valida parsing e funcionamento do cache com intervalo."""
        mock_req.return_value = {
            "current": {
                "temperature_2m": 25.4,
                "apparent_temperature": 26.1,
                "relative_humidity_2m": 60,
                "weather_code": 2,
                "is_day": 1,
                "precipitation": 0.0,
                "wind_speed_10m": 14.2,
            }
        }

        servico = ServicoClima(cidade="Campinas", intervalo_cache=900)
        res1 = servico.obter_clima(agora_ts=1000.0)

        self.assertEqual(res1["city"], "Campinas")
        self.assertEqual(res1["temp"], 25.4)
        self.assertEqual(res1["apparent_temp"], 26.1)
        self.assertEqual(res1["humidity"], 60)
        self.assertEqual(res1["condition"], "Parcialm. nublado")
        self.assertTrue(res1["online"])
        self.assertEqual(mock_req.call_count, 1)

        # Segunda chamada dentro do intervalo de 900s deve usar o cache sem chamar _fazer_requisicao de novo
        res2 = servico.obter_clima(agora_ts=1500.0)
        self.assertEqual(res2["temp"], 25.4)
        self.assertEqual(mock_req.call_count, 1)

        # Terceira chamada após o intervalo deve renovar
        res3 = servico.obter_clima(agora_ts=2000.0)
        self.assertEqual(mock_req.call_count, 2)

    @patch.object(ServicoClima, "_fazer_requisicao")
    def test_obter_clima_fallback_erro(self, mock_req):
        """Valida resiliência graciosa quando a API falha."""
        mock_req.side_effect = TimeoutError("Conexão expirou")
        servico = ServicoClima(cidade="São Paulo")

        res = servico.obter_clima(agora_ts=1000.0)
        self.assertFalse(res["online"])
        self.assertEqual(res["condition"], "Indisponível")
        self.assertIn("error", res)


class TestServicoTempo(unittest.TestCase):
    def setUp(self):
        self.tempo = ServicoTempo(nome_usuario="Arthur")

    def test_saudacoes_contextuais_madrugada(self):
        """Madrugada com CODING vs OFFLINE."""
        dt_madrugada = datetime(2026, 11, 13, 3, 30)

        saudacao_coding = self.tempo.gerar_saudacao(dt_madrugada, estado_pc="CODING")
        self.assertEqual(saudacao_coding, "Noite adentro no código")

        saudacao_offline = self.tempo.gerar_saudacao(dt_madrugada, estado_pc="OFFLINE")
        self.assertEqual(saudacao_offline, "Madrugada silenciosa... Zzz")

    def test_saudacoes_contextuais_dia_e_tarde(self):
        """Manhã, Almoço e Tarde."""
        dt_manha = datetime(2026, 11, 13, 9, 0)
        self.assertIn("Bom dia, Arthur!", self.tempo.gerar_saudacao(dt_manha, "OFFLINE"))

        dt_almoco = datetime(2026, 11, 13, 12, 30)
        self.assertIn("almoço", self.tempo.gerar_saudacao(dt_almoco, "AWAY").lower())

        dt_tarde = datetime(2026, 11, 13, 15, 30)
        self.assertEqual(self.tempo.gerar_saudacao(dt_tarde, "CODING"), "Tarde focada no código!")

    def test_obter_status_tempo_payload(self):
        """Verifica payload completo para MQTT."""
        dt = datetime(2026, 11, 13, 14, 45)  # Sexta-feira
        res = self.tempo.obter_status_tempo(dt, "CODING")

        self.assertEqual(res["time"], "14:45")
        self.assertEqual(res["date"], "13/11/2026")
        self.assertEqual(res["day_of_week"], "Sexta-feira")
        self.assertEqual(res["period"], "tarde")
        self.assertEqual(res["greeting"], "Tarde focada no código!")


class TestInteracaoToqueHumor(unittest.TestCase):
    def setUp(self):
        self.cerebro = Cerebro()

    def test_toque_curto_carinho_eleva_felicidade(self):
        """Tocar nos olhos (tap) aciona reação de carinho e eleva felicidade (+0.15)."""
        self.cerebro.felicidade = 0.50
        self.cerebro.tedio = 0.40

        res = self.cerebro.processar_toque("tap", agora_ts=100.0)
        self.assertEqual(res["acao"], "carinho")
        self.assertAlmostEqual(self.cerebro.felicidade, 0.65, places=2)
        self.assertLess(self.cerebro.tedio, 0.40)
        self.assertEqual(self.cerebro.ev_expr, "feliz")
        self.assertEqual(self.cerebro.ev_ate, 104.0)

        # Testa clamp máximo em 1.0
        self.cerebro.felicidade = 0.95
        self.cerebro.processar_toque("tap", agora_ts=110.0)
        self.assertEqual(self.cerebro.felicidade, 1.0)

    def test_toque_longo_forca_soneca_e_desperta(self):
        """Toque longo (>1.5s) força soneca ou acorda o bot."""
        self.cerebro.energia = 0.90
        self.cerebro.soneca_forcada = False

        # 1. Long-press enquanto acordado -> força soneca
        res1 = self.cerebro.processar_toque("long_press", agora_ts=200.0)
        self.assertEqual(res1["acao"], "soneca")
        self.assertTrue(self.cerebro.soneca_forcada)
        self.assertAlmostEqual(self.cerebro.energia, 0.05, places=2)

        # Expressão agora deve ser 'dormindo'
        expr_dormindo = self.cerebro.escolher(
            agora_dt=datetime(2026, 11, 13, 14, 0),
            agora_ts=210.0,
        )
        self.assertEqual(expr_dormindo, "dormindo")

        # 2. Long-press enquanto em soneca -> desperta com energia recuperada
        res2 = self.cerebro.processar_toque("long_press", agora_ts=220.0)
        self.assertEqual(res2["acao"], "despertar")
        self.assertFalse(self.cerebro.soneca_forcada)
        self.assertAlmostEqual(self.cerebro.energia, 0.85, places=2)
        self.assertEqual(self.cerebro.ev_expr, "feliz")

    def test_toque_curto_desperta_de_soneca_forcada(self):
        """Toque curto (tap) suave também acorda o bot da soneca forçada."""
        self.cerebro.soneca_forcada = True
        self.cerebro.energia = 0.05

        res = self.cerebro.processar_toque("tap", agora_ts=300.0)
        self.assertEqual(res["acao"], "despertar")
        self.assertFalse(self.cerebro.soneca_forcada)
        self.assertGreaterEqual(self.cerebro.energia, 0.5)
        self.assertEqual(self.cerebro.ev_expr, "curioso")

    def test_atividade_pc_reseta_soneca_forcada(self):
        """Se o usuário sentar e começar a codar/jogar, cancela a soneca forçada."""
        self.cerebro.pc = "OFFLINE"
        self.cerebro.soneca_forcada = True

        self.cerebro.atualizar_pc("main_pc", "CODING", agora_dt=datetime(2026, 11, 13, 15, 0), agora_ts=400.0)
        self.assertFalse(self.cerebro.soneca_forcada)
        self.assertEqual(self.cerebro.pc, "CODING")


if __name__ == "__main__":
    unittest.main()
