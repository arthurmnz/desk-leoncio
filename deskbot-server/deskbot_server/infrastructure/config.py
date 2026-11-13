"""Gerenciamento de configurações e carregamento de variáveis de ambiente do DeskBot."""
import os


def carregar_env(caminho_env=None):
    """Carrega variáveis de um arquivo .env para os.environ caso ainda não definidas."""
    if caminho_env is None:
        dir_script = os.path.dirname(os.path.abspath(__file__))
        # Sobe níveis para procurar na raiz do servidor e do projeto
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


# Executa o carregamento inicial por padrão
carregar_env()

BROKER = os.environ.get("BROKER", "localhost")
T_PC_WILDCARD = "desk/pc/+/activity"
T_PC_LEGACY = "desk/pc/activity"
T_BOT = "desk/bot/state"
LOG = os.environ.get("LOG", "deskbot_log.csv")
