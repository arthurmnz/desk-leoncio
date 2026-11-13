"""Testes unitários do Ciclo Circadiano e lógica do Cérebro (DeskBot)."""
import os
import sys
import unittest
from datetime import datetime

# Garante import do pacote deskbot-server
_DIR_SERVER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _DIR_SERVER not in sys.path:
    sys.path.insert(0, _DIR_SERVER)

# Testa imports tanto do módulo legado cerebro quanto do novo deskbot_server
from cerebro import Cerebro, fator_circadiano, calcular_ritmo_circadiano, clamp
import deskbot_server


class TestCicloCircadiano(unittest.TestCase):
    def test_curva_madrugada_03h00(self):
        """03:00 - Pico do repouso noturno: teto mínimo, drenagem acelerada, dormir rápido."""
        ritmo = fator_circadiano(3, 0)
        self.assertEqual(ritmo["fase"], "madrugada")
        self.assertEqual(ritmo["label"], "Madrugada")
        self.assertAlmostEqual(ritmo["teto_energia"], 0.35, places=2)
        self.assertGreaterEqual(ritmo["taxa_drenagem"], 1.5)
        self.assertLessEqual(ritmo["taxa_recuperacao"], 0.6)
        self.assertLessEqual(ritmo["tempo_para_dormir"], 180.0)

    def test_curva_manha_08h00(self):
        """08:00 - Despertar matinal: energia em ascensão rápida, recuperação revigorante."""
        ritmo = fator_circadiano(8, 0)
        self.assertEqual(ritmo["fase"], "manha")
        self.assertEqual(ritmo["label"], "Manhã / Despertar")
        self.assertGreaterEqual(ritmo["teto_energia"], 0.85)
        self.assertEqual(ritmo["taxa_drenagem"], 1.0)
        self.assertGreater(ritmo["taxa_recuperacao"], 1.0)
        self.assertEqual(ritmo["tempo_para_dormir"], 600.0)

    def test_curva_slump_13h30(self):
        """13:30 - Slump pós-almoço: queda de vitalidade digestiva, tédio facilitado."""
        ritmo = fator_circadiano(13, 30)
        self.assertEqual(ritmo["fase"], "slump_tarde")
        self.assertEqual(ritmo["label"], "Slump pós-almoço")
        self.assertAlmostEqual(ritmo["teto_energia"], 0.85, places=2)
        self.assertLess(ritmo["taxa_recuperacao"], 1.0)
        self.assertLess(ritmo["limiar_tedio"], 0.5)

    def test_curva_tarde_noite_19h00(self):
        """19:00 - Tarde / noite produtiva: vitalidade plena (teto 1.0)."""
        ritmo = fator_circadiano(19, 0)
        self.assertEqual(ritmo["fase"], "tarde_noite")
        self.assertEqual(ritmo["label"], "Tarde / Noite produtiva")
        self.assertEqual(ritmo["teto_energia"], 1.0)
        self.assertEqual(ritmo["taxa_drenagem"], 1.0)
        self.assertEqual(ritmo["taxa_recuperacao"], 1.0)
        self.assertEqual(ritmo["tempo_para_dormir"], 600.0)

    def test_curva_pre_sono_23h30(self):
        """23:30 - Pré-sono: desaceleração, energia caindo de 1.0 em direção ao teto noturno."""
        ritmo = fator_circadiano(23, 30)
        self.assertEqual(ritmo["fase"], "pre_sono")
        self.assertEqual(ritmo["label"], "Pré-sono / Desaceleração")
        self.assertGreater(ritmo["teto_energia"], 0.45)
        self.assertLess(ritmo["teto_energia"], 0.70)
        self.assertLessEqual(ritmo["tempo_para_dormir"], 360.0)

    def test_pre_sono_curva_descendente(self):
        """Verifica a desaceleração suave de 22:00 até 23:59."""
        teto_2200 = fator_circadiano(22, 0)["teto_energia"]
        teto_2300 = fator_circadiano(23, 0)["teto_energia"]
        teto_2330 = fator_circadiano(23, 30)["teto_energia"]
        teto_2359 = fator_circadiano(23, 59)["teto_energia"]

        self.assertAlmostEqual(teto_2200, 1.0, places=2)
        self.assertGreater(teto_2200, teto_2300)
        self.assertGreater(teto_2300, teto_2330)
        self.assertGreater(teto_2330, teto_2359)

    def test_transicao_continua_fronteiras(self):
        """Verifica se não há quebras abruptas nas fronteiras entre fases."""
        r_2359 = fator_circadiano(23, 59)
        r_0000 = fator_circadiano(0, 0)
        self.assertAlmostEqual(r_2359["teto_energia"], r_0000["teto_energia"], delta=0.05)

        r_0559 = fator_circadiano(5, 59)
        r_0600 = fator_circadiano(6, 0)
        self.assertAlmostEqual(r_0559["teto_energia"], r_0600["teto_energia"], delta=0.05)


class TestReacoesCircadianas(unittest.TestCase):
    def setUp(self):
        self.cerebro = Cerebro()

    def test_reacao_alta_madrugada_surpreso_para_sonolento(self):
        """Às 03:00, retorno do PC deve disparar 'surpreso' e depois ir para 'sonolento'."""
        dt_madrugada = datetime(2026, 11, 13, 3, 0)
        ts_inicial = 1000.0

        # Bot inicializa em repouso de madrugada
        self.cerebro.energia = 0.35
        self.cerebro.pc = "OFFLINE"

        # Usuário liga PC e começa a codar
        self.cerebro.atualizar_pc("main_pc", "CODING", agora_dt=dt_madrugada, agora_ts=ts_inicial)

        # Durante o evento (t = 1001), bot está surpreso por ver o usuário acordado
        expr_evento = self.cerebro.escolher(agora_dt=dt_madrugada, agora_ts=ts_inicial + 1.0)
        self.assertEqual(expr_evento, "surpreso", "DeskBot deveria reagir 'surpreso' na alta madrugada")

        # Após expirar o evento (6s depois, t = 1008), cansaço da madrugada domina -> sonolento
        expr_pos_evento = self.cerebro.escolher(agora_dt=dt_madrugada, agora_ts=ts_inicial + 8.0)
        self.assertEqual(expr_pos_evento, "sonolento", "Após surpresa, DeskBot de madrugada deve ficar sonolento")

    def test_reacao_despertar_matinal_feliz(self):
        """Às 08:00, primeira atividade matinal deve celebrar com 'feliz' (bom dia)."""
        dt_manha = datetime(2026, 11, 13, 8, 0)
        ts_inicial = 2000.0

        self.cerebro.pc = "OFFLINE"
        self.cerebro.despertou_hoje = False

        # Primeira atividade do dia
        self.cerebro.atualizar_pc("main_pc", "CODING", agora_dt=dt_manha, agora_ts=ts_inicial)
        self.assertTrue(self.cerebro.despertou_hoje)

        expr_evento = self.cerebro.escolher(agora_dt=dt_manha, agora_ts=ts_inicial + 1.0)
        self.assertEqual(expr_evento, "feliz", "DeskBot deveria comemorar bom dia com 'feliz'")

        # Segunda atividade não deve re-disparar o despertar do dia se já despertou
        self.cerebro.pc = "OFFLINE"
        self.cerebro.atualizar_pc("main_pc", "CODING", agora_dt=dt_manha, agora_ts=ts_inicial + 10.0)
        self.assertTrue(self.cerebro.despertou_hoje)

    def test_reset_despertar_madrugada(self):
        """Ao entrar na madrugada, flag despertou_hoje é resetada para o próximo dia."""
        dt_manha = datetime(2026, 11, 13, 9, 0)
        self.cerebro.tick(dt=1.0, agora_dt=dt_manha)
        self.cerebro.despertou_hoje = True

        # Virou a noite para madrugada do dia seguinte (02:00)
        dt_madrugada = datetime(2026, 11, 14, 2, 0)
        self.cerebro.tick(dt=1.0, agora_dt=dt_madrugada)
        self.assertFalse(self.cerebro.despertou_hoje, "Flag despertou_hoje deve ser resetada na madrugada")

    def test_madrugada_dorme_rapido_em_ausencia(self):
        """De madrugada, tempo de tolerância para dormir deve ser ~2.5 min (150s)."""
        dt_madrugada = datetime(2026, 11, 13, 3, 0)
        ts_inicial = 3000.0

        self.cerebro.pc = "OFFLINE"
        self.cerebro.desde = ts_inicial
        self.cerebro.energia = 0.35

        # Antes de 150s: sonolento
        expr_cedo = self.cerebro.escolher(agora_dt=dt_madrugada, agora_ts=ts_inicial + 60.0)
        self.assertEqual(expr_cedo, "sonolento")

        # Após 150s (ex: 180s): dormindo
        expr_dormindo = self.cerebro.escolher(agora_dt=dt_madrugada, agora_ts=ts_inicial + 180.0)
        self.assertEqual(expr_dormindo, "dormindo")

    def test_slump_propensao_ao_tedio(self):
        """No slump da tarde (13:30), tédio acima de 0.40 já deixa o bot entediado."""
        dt_slump = datetime(2026, 11, 13, 13, 30)
        ts = 4000.0

        self.cerebro.pc = "IDLE"
        self.cerebro.desde = ts
        self.cerebro.energia = 0.8
        self.cerebro.tedio = 0.45

        expr = self.cerebro.escolher(agora_dt=dt_slump, agora_ts=ts + 30.0)
        self.assertEqual(expr, "entediado")

    def test_recuperacao_manha_vs_slump(self):
        """Recuperação no repouso pela manhã deve ser mais rápida que no slump pós-almoço."""
        dt_manha = datetime(2026, 11, 13, 9, 0)
        dt_slump = datetime(2026, 11, 13, 13, 30)

        c_manha = Cerebro()
        c_manha.pc = "IDLE"
        c_manha.energia = 0.50
        c_manha.tick(dt=600, agora_dt=dt_manha)
        ganho_manha = c_manha.energia - 0.50

        c_slump = Cerebro()
        c_slump.pc = "IDLE"
        c_slump.energia = 0.50
        c_slump.tick(dt=600, agora_dt=dt_slump)
        ganho_slump = c_slump.energia - 0.50

        self.assertGreater(ganho_manha, ganho_slump, "Recuperação matinal deve ser superior à do slump da tarde")

    def test_drenagem_acelerada_madrugada_vs_dia(self):
        """Drenagem de energia de madrugada deve ser maior que a taxa de dia para mesmo dt."""
        dt_madrugada = datetime(2026, 11, 13, 3, 0)
        dt_dia = datetime(2026, 11, 13, 15, 0)

        c_madrugada = Cerebro()
        c_madrugada.pc = "GAMING"
        c_madrugada.energia = 0.35
        c_madrugada.tick(dt=3600, agora_dt=dt_madrugada)
        gasto_madrugada = 0.35 - c_madrugada.energia

        c_dia = Cerebro()
        c_dia.pc = "GAMING"
        c_dia.energia = 0.90
        c_dia.tick(dt=3600, agora_dt=dt_dia)
        gasto_dia = 0.90 - c_dia.energia

        self.assertGreater(gasto_madrugada, gasto_dia, "Gasto na madrugada deve ser maior devido à fadiga biológica")

    def test_consolidacao_multiplos_pcs(self):
        """Verifica se prioridade de múltiplos PCs respeita GAMING > CODING > IDLE > OFFLINE."""
        c = Cerebro()
        c.atualizar_pc("note", "CODING")
        self.assertEqual(c.pc, "CODING")

        c.atualizar_pc("desktop", "GAMING")
        self.assertEqual(c.pc, "GAMING", "GAMING deve ter prioridade sobre CODING")

        c.atualizar_pc("desktop", "OFFLINE")
        self.assertEqual(c.pc, "CODING", "Deve retroceder para CODING quando desktop desligar")

    def test_estado_desconhecido_ignorado_e_nao_persistido(self):
        """Hardening: estado não mapeado deve ser descartado sem persistir em self.pcs."""
        c = Cerebro()
        c.atualizar_pc("pc_teste", "INVALID_STATE")
        self.assertNotIn("pc_teste", c.pcs, "Estado desconhecido não deve ser salvo em self.pcs")
        self.assertEqual(c.pc, "OFFLINE", "Consolidado não deve ser alterado por estado inválido")

    def test_modulo_package_exports(self):
        """Garante integridade dos exports públicos de deskbot_server."""
        self.assertTrue(hasattr(deskbot_server, "Cerebro"))
        self.assertTrue(hasattr(deskbot_server, "fator_circadiano"))
        self.assertTrue(hasattr(deskbot_server, "ClienteMQTT"))
        self.assertTrue(hasattr(deskbot_server, "Telemetria"))


if __name__ == "__main__":
    unittest.main()
