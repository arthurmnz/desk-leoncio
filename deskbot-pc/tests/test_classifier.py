"""Testes unitários para a máquina de inferência e classificação de estados do PC."""
import os
import sys
import unittest

# Garante path de importação para deskbot-pc
_DIR_PC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _DIR_PC not in sys.path:
    sys.path.insert(0, _DIR_PC)

from deskbot_pc.classifier import classificar_atividade
import agent_pc
import deskbot_pc


class TestClassificadorEstados(unittest.TestCase):
    def test_linux_gaming_detectado(self):
        """No Linux, a presença de um processo de jogo na lista infere GAMING."""
        processos = {"bash", "gamescope", "pulseaudio"}
        estado, primeiro = classificar_atividade(
            nomes_processos=processos,
            primeiro_plano="",
            tela_cheia=False,
            is_windows=False,
        )
        self.assertEqual(estado, "GAMING")

    def test_linux_coding_detectado(self):
        """No Linux, processos como 'code' ou 'nvim' inferem CODING."""
        processos = {"bash", "nvim", "kitty"}
        estado, _ = classificar_atividade(
            nomes_processos=processos,
            primeiro_plano="",
            tela_cheia=False,
            is_windows=False,
        )
        self.assertEqual(estado, "CODING")

    def test_linux_media_detectado(self):
        """No Linux, processos de mídia (spotify, mpv, vlc) inferem MEDIA."""
        processos = {"bash", "spotify", "waybar"}
        estado, _ = classificar_atividade(
            nomes_processos=processos,
            primeiro_plano="",
            tela_cheia=False,
            is_windows=False,
        )
        self.assertEqual(estado, "MEDIA")

    def test_linux_idle_quando_sem_atividades_especiais(self):
        """Sem processos categorizados, deve inferir IDLE."""
        processos = {"bash", "systemd", "gnome-terminal"}
        estado, _ = classificar_atividade(
            nomes_processos=processos,
            primeiro_plano="",
            tela_cheia=False,
            is_windows=False,
        )
        self.assertEqual(estado, "IDLE")

    def test_windows_tela_cheia_jogo(self):
        """No Windows, aplicativo em tela cheia que não esteja na lista de exceções infere GAMING."""
        processos = {"explorer.exe", "eldenring.exe"}
        estado, primeiro = classificar_atividade(
            nomes_processos=processos,
            primeiro_plano="eldenring.exe",
            tela_cheia=True,
            is_windows=True,
        )
        self.assertEqual(estado, "GAMING")
        self.assertEqual(primeiro, "eldenring.exe")

    def test_windows_tela_cheia_app_nao_jogo(self):
        """No Windows, tela cheia de apps como chrome.exe não deve ser classificada como GAMING."""
        processos = {"explorer.exe", "chrome.exe"}
        estado, _ = classificar_atividade(
            nomes_processos=processos,
            primeiro_plano="chrome.exe",
            tela_cheia=True,
            is_windows=True,
        )
        self.assertEqual(estado, "IDLE")

    def test_windows_away_quando_ocioso(self):
        """No Windows, inatividade de periféricos superior a 300 s infere AWAY se não houver mídia."""
        processos = {"explorer.exe"}
        estado, _ = classificar_atividade(
            nomes_processos=processos,
            primeiro_plano="explorer.exe",
            tela_cheia=False,
            segundos_ocioso=350.0,
            segundos_ausente=300.0,
            is_windows=True,
        )
        self.assertEqual(estado, "AWAY")

    def test_windows_media_quando_ocioso(self):
        """No Windows, inatividade de periféricos superior a 300 s infere MEDIA se houver spotify ativo."""
        processos = {"explorer.exe", "spotify.exe"}
        estado, _ = classificar_atividade(
            nomes_processos=processos,
            primeiro_plano="explorer.exe",
            tela_cheia=False,
            segundos_ocioso=350.0,
            segundos_ausente=300.0,
            is_windows=True,
        )
        self.assertEqual(estado, "MEDIA")

    def test_prioridade_gaming_sobre_coding_e_media(self):
        """GAMING tem prioridade sobre CODING e MEDIA mesmo com todos ativos."""
        processos = {"gamescope", "code", "spotify"}
        estado, _ = classificar_atividade(
            nomes_processos=processos,
            primeiro_plano="",
            is_windows=False,
        )
        self.assertEqual(estado, "GAMING")

    def test_compatibilidade_exports_agent_pc(self):
        """Garante que o shim agent_pc e o pacote deskbot_pc exportam as funções esperadas."""
        self.assertTrue(callable(agent_pc.detectar))
        self.assertTrue(callable(deskbot_pc.detectar))
        self.assertTrue(callable(deskbot_pc.classificar_atividade))
        self.assertTrue(hasattr(agent_pc, "JOGOS"))
        self.assertTrue(hasattr(agent_pc, "CODANDO"))
        self.assertTrue(hasattr(agent_pc, "MIDIA"))


if __name__ == "__main__":
    unittest.main()
