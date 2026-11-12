# DeskBot

Robô de mesa feito com **ESP32 + tela TFT ILI9341**. Ele mostra um rosto (olhos animados) que reage ao que você faz nos seus PCs e tem um **humor interno** que muda com o tempo. O cérebro roda 24/7 no homelab, então o robô fica sempre ligado e "vivo", mesmo com os PCs desligados.

---

## Arquitetura

```
┌────────────────────┐
│ PC CachyOS         │   MQTT     ┌───────────────────────────┐   MQTT    ┌────────────────┐
│ agent_pc.py        │ ─────────▶ │ Homelab (Umbrel / Docker) │ ────────▶ │ ESP32 + ILI9341│
└────────────────────┘            │ Mosquitto + cerebro.py    │           │ deskbot.ino    │
┌────────────────────┐   MQTT     │                           │           └────────────────┘
│ PC Windows 10      │ ─────────▶ └───────────────────────────┘
│ agent_pc.py        │             combina os PCs, guarda o       só desenha, mas tem a
└────────────────────┘             humor e escolhe a expressão    camada "viva" local
```

| Peça | Onde roda | Função |
|---|---|---|
| `agent_pc.py` | CachyOS **e** Windows 10 | Detecta o que você faz e publica o estado do PC |
| Mosquitto | Homelab (Docker) | Broker MQTT. Guarda a última mensagem de cada tópico (retain) |
| `cerebro.py` | Homelab (Docker) | Combina os PCs, mantém energia/tédio/felicidade, escolhe a expressão e grava o log |
| `deskbot.ino` | ESP32 | Recebe a expressão e a desenha. Pisca, olha em volta e "respira" sozinho |

### Tópicos MQTT

| Tópico | Quem publica | Exemplo |
|---|---|---|
| `desk/pc/cachyos/activity` | PC CachyOS | `{"state": "CODING"}` |
| `desk/pc/windows/activity` | PC Windows | `{"state": "GAMING"}` |
| `desk/bot/state` | Cérebro | `{"expr": "jogando", "energy": 0.74}` |

- Cada PC publica ao mudar de estado e a cada 10 s. Se ele cair ou desligar sem avisar, o broker publica `OFFLINE` por ele (Last Will).
- O cérebro publica ao mudar de expressão e a cada 15 s (batimento: o ESP32 sabe que o cérebro está vivo).
- O `client_id` de cada agente é único (`deskbot-windows`, `deskbot-cachyos`). Com ids iguais, o broker derrubaria um dos dois.

### Estados de um PC

| Estado | Significado | Como detecta |
|---|---|---|
| `GAMING` | Jogando | Windows: app em primeiro plano em tela cheia (ou listado em `JOGOS`). Linux: processos da lista `JOGOS` |
| `CODING` | Programando | Processos da lista `CODANDO` abertos |
| `MEDIA` | Música/vídeo | Processos da lista `MIDIA` |
| `IDLE` | Ligado, sem atividade conhecida | Nenhum dos anteriores |
| `AWAY` | Ligado, mas você saiu | Windows: 5 min sem teclado/mouse (e sem jogo) |
| `OFFLINE` | Desligado ou sem conexão | Last Will do MQTT |

### Combinando os dois PCs

O cérebro fica com o estado **mais forte** entre os PCs:

`GAMING` > `CODING` > `MEDIA` > `IDLE` > `AWAY` > `OFFLINE`

Exemplos: jogando no Windows e com a IDE aberta no CachyOS, vale `GAMING`. Windows desligado e CachyOS ocioso, vale `IDLE`. Os dois desligados ou ausentes, ele age como se você tivesse saído (`AWAY` e `OFFLINE` contam como ausente).

---

## Resumo das expressões

| Expressão | Cor | Visual | Quando aparece |
|---|---|---|---|
| **neutro** | Ciano | Olhos grandes e redondos, olhar livre | Ocioso sem tédio; ausente com energia boa e sem tédio |
| **feliz** | Amarelo | Olhos com bochechas subindo (sorrindo) | Ouvindo música/vídeo (`MEDIA`); por 6 s quando você volta |
| **jogando** | Vermelho | Olhos com sobrancelha inclinada (focado) | `GAMING` |
| **codando** | Verde | Olhos achatados com pálpebra levemente baixa | `CODING` |
| **sonolento** | Roxo claro | Pálpebra caída e cantos para baixo | Energia abaixo de 25% com PC ativo; ausente com pouca energia ou à noite (primeiros 10 min) |
| **dormindo** | Roxo escuro | Olhos fechados (só uma linha) | Ausente há mais de 10 min e (energia baixa ou entre 23h e 6h) |
| **curioso** | Ciano | Olhos altos e estreitos, olha bastante em volta | Por 2,5 s ao começar jogo/IDE/mídia; ocioso com tédio acima de 50% |
| **entediado** | Azul-acinzentado | Pálpebra pela metade, olhar vagando | Ausente com tédio acima de 60% |
| **offline** | Cinza | Olhos meio caídos, olhar perdido | **Local no ESP32:** 90 s sem nada do cérebro (homelab/Wi-Fi caiu) |
| **surpreso** | Branco | Olhos bem abertos e altos | Existe no firmware, mas o cérebro **ainda não usa** |

### Prioridade da escolha (no cérebro)

1. **Evento temporário** (feliz ao voltar, curioso ao abrir algo): vale por alguns segundos e passa na frente de tudo.
2. **Ausente** (`AWAY`/`OFFLINE`): dormindo, sonolento, entediado ou neutro, conforme energia, hora e tédio.
3. **Energia abaixo de 25%:** sonolento (mesmo com o PC ativo).
4. **Atividade:** jogando, codando ou feliz (mídia).
5. **Ocioso:** curioso se estiver entediado, senão neutro.

---

## Humor interno

Variáveis entre 0 e 1, atualizadas a cada segundo no `cerebro.py`:

| Variável | Sobe | Desce |
|---|---|---|
| **Energia** (começa em 0,8) | Descansando (ocioso, ausente ou desligado): cheia em cerca de 30 min | Jogando ou codando: esvazia em cerca de 4 h. Entre 0h e 6h nunca passa de 0,5 |
| **Tédio** | Ocioso, ausente ou desligado: cheio em cerca de 15 min | Com atividade: some em cerca de 1 min |
| **Felicidade** (começa em 0,5) | Quando você volta (+0,2); ouvindo mídia (cheia em cerca de 5 min) | Volta devagar para 0,5 (cerca de 10 min) |

> A felicidade já é calculada e gravada no log, mas **ainda não muda nenhuma expressão**.

### Camada "viva" (roda no ESP32, sempre)

- **Piscar** em intervalos aleatórios de 2,5 a 6 s, às vezes duplo (15% das vezes).
- **Olhar pelos lados** com movimentos aleatórios (menos frequentes com energia baixa).
- **Respiração:** o olho cresce e encolhe cerca de 2,5% bem devagar.
- **Transições suaves** entre expressões (forma e cor).
- Continua animado mesmo que o homelab caia.

---

## Arquivos

```
desk-bot/
├── docker-compose.yml   # Mosquitto + cérebro (homelab)
├── mosquitto.conf       # Config do broker (porta 1883, sem senha)
├── cerebro.py           # Humor e escolha da expressão (roda em container)
├── agent_pc.py          # Agente dos PCs (o mesmo arquivo serve pra Linux e Windows)
├── deskbot.ino          # Firmware do ESP32
├── secrets.h.example    # Modelo das credenciais do ESP32 (copiar para secrets.h)
├── .env.example         # Modelo da configuração (copiar para .env)
├── .gitignore           # Mantém .env, secrets.h, dados e venv fora do repo
└── dados/
    └── deskbot_log.csv  # Log (1 linha por minuto): hora, estado, humor, expressão, estado de cada PC
```

No homelab, a pasta fica em `/home/umbrel/umbrel/my-apps/desk-bot`.

## Hardware e ligações (ILI9341 → ESP32)

| TFT | ESP32 |
|---|---|
| VCC / LED | 3V3 |
| GND | GND |
| CS | GPIO 15 |
| RESET | GPIO 4 |
| DC | GPIO 2 |
| SDI (MOSI) | GPIO 23 |
| SCK | GPIO 18 |
| SDO (MISO) | GPIO 19 (opcional) |

Bibliotecas na Arduino IDE: **TFT_eSPI**, **PubSubClient**, **ArduinoJson (v7)**. Os pinos ficam no `User_Setup.h` do TFT_eSPI.

## Como rodar

**Homelab**
```bash
cd /home/umbrel/umbrel/my-apps/desk-bot
docker compose up -d
docker logs -f deskbot-cerebro
```

**PC CachyOS**
```fish
cd ~/code/desk-bot
source .venv/bin/activate.fish
python agent_pc.py
```

**PC Windows 10** (PowerShell)
```powershell
cd C:\caminho\desk-bot
py -m venv .venv
.\.venv\Scripts\pip install paho-mqtt psutil
.\.venv\Scripts\python agent_pc.py
```
Para abrir sozinho com o Windows: Agendador de Tarefas, "Ao fazer logon", executando `.\.venv\Scripts\pythonw.exe agent_pc.py` (o `pythonw` não abre janela de terminal).

**ESP32:** copiar `secrets.h.example` para `secrets.h` (na mesma pasta do `deskbot.ino`), preencher `WIFI_SSID`, `WIFI_PASS` (rede 2.4 GHz) e `MQTT_HOST`, e fazer o upload.

## Configuração (.env e secrets.h)

Nada de IP ou senha fica escrito no código. Os arquivos reais **não vão pro git** (estão no `.gitignore`); só os `.example` vão.

| Arquivo de exemplo | Copie para | Onde fica | O que configura |
|---|---|---|---|
| `.env.example` | `.env` | Cada PC (ao lado do `agent_pc.py`) | `DESKBOT_BROKER` (IP do homelab), `DESKBOT_NOME` (opcional) |
| `.env.example` | `.env` | Homelab (ao lado do `docker-compose.yml`) | `TZ` (fuso horário do cérebro) |
| `secrets.h.example` | `secrets.h` | Pasta do `deskbot.ino` | Wi-Fi e IP do broker no ESP32 |

## Testes rápidos

Forçar uma expressão direto no robô:
```bash
mosquitto_pub -h IP_DO_HOMELAB -t desk/bot/state -m '{"expr":"feliz","energy":1}'
```

Fingir que o Windows está com um jogo aberto:
```bash
mosquitto_pub -h IP_DO_HOMELAB -t desk/pc/windows/activity -m '{"state":"GAMING"}'
```

Ao rodar, cada agente imprime o estado detectado e a janela em foco. Use isso para ajustar as listas de programas.

---

## Estado atual

**Montado**
- Broker MQTT e cérebro em containers no homelab
- Agente único para CachyOS e Windows, com tópico por PC e combinação dos estados no cérebro
- Windows: detecção de jogo pela janela em tela cheia e de ausência por tempo sem teclado/mouse
- Firmware com olhos animados, camada viva e 10 expressões
- Log do humor em CSV (base para a rede neural)

**Para ajustar e validar**
- Listas `JOGOS`, `CODANDO`, `MIDIA` e `NAO_JOGO` do `agent_pc.py` (a detecção de tela cheia é uma heurística)
- Valores visuais de cada expressão na tabela `EXPRS` do `deskbot.ino`
- Tempos do humor (4 h de energia, 15 min de tédio etc.) conforme a sua rotina

## Limitações conhecidas

- O broker está **sem senha** (aceitável só na rede local).
- A detecção de tela cheia olha só o **monitor principal** e pode confundir um app maximizado sem barra de tarefas com um jogo. O controle de jogo não conta como teclado/mouse, por isso o jogo é checado antes da ausência.
- No CachyOS (Wayland), ainda não há detecção de `AWAY`: "ocioso" significa só "nenhum app conhecido aberto".
- Se o MQTT cair, a animação do ESP32 trava por cerca de 2 s a cada tentativa de reconexão (a cada 4 s).
- O IP do homelab precisa ser fixo (reserva de DHCP no roteador).
- Os agentes dos PCs precisam ser iniciados (no Windows, via Agendador de Tarefas).

## Próximos passos

1. Usar a **felicidade** e a expressão **surpreso** no cérebro.
2. **Brilho do backlight** menor à noite (o cérebro manda o valor).
3. Serviço **systemd de usuário** para o agente do CachyOS iniciar sozinho.
4. Detecção de **ausência no CachyOS**.
5. Reações a **eventos**: `git push`, erro de compilação, CPU em 100%, chamada em andamento.
6. **Sons** com buzzer e, mais adiante, **microfone** (Whisper no homelab).
7. **Rede neural** treinada com o `deskbot_log.csv` para aprender a sua rotina.
8. Senha no Mosquitto.