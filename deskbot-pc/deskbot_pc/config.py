"""Gerenciamento de configurações e variáveis de ambiente do agente PC."""
import os
import sys


def carregar_env(caminho_env=None):
    """Carrega variáveis de um arquivo .env para os.environ caso ainda não definidas."""
    if caminho_env is None:
        dir_script = os.path.dirname(os.path.abspath(__file__))
        candidatos = [
            os.path.join(dir_script, ".env"),
            os.path.join(os.path.dirname(dir_script), ".env"),
            os.path.join(os.path.dirname(os.path.dirname(dir_script)), ".env"),
            os.path.join(os.getcwd(), ".env"),
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

WINDOWS = sys.platform == "win32"
BROKER = os.environ.get("DESKBOT_BROKER", "192.168.0.5")
SEGUNDOS_AUSENTE = 300  # sem teclado/mouse por 5 min = ausente (só Windows)


def obter_nome_pc(argv=None):
    """Resolve o identificador único deste computador."""
    args = argv if argv is not None else sys.argv
    padrao = "windows" if WINDOWS else "cachyos"
    if len(args) > 1 and not args[1].startswith("-"):
        return args[1]
    return os.environ.get("DESKBOT_NOME", padrao)


def obter_topico(nome=None):
    """Retorna o tópico MQTT de telemetria do PC."""
    nome_resolvido = nome or obter_nome_pc()
    return f"desk/pc/{nome_resolvido}/activity"


NOME = obter_nome_pc()
TOPICO = obter_topico(NOME)
