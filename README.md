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
| `deskbot-pc` (`agent_pc.py`) | CachyOS **e** Windows 10 | Detecta o que você faz e publica o estado do PC |
| Mosquitto | Homelab (Docker) | Broker MQTT. Guarda a última mensagem de cada tópico (retain) |
| `deskbot-server` (`cerebro.py`) | Homelab (Docker) | Combina os PCs, mantém energia/tédio/felicidade, escolhe a expressão e grava o log |
| `deskbot` (`deskbot.ino`) | ESP32 | Recebe a expressão e a desenha. Pisca, olha em volta e "respira" sozinho |

### Tópicos MQTT

| Tópico | Quem publica | Exemplo |
|---|---|---|
| `desk/pc/cachyos/activity` | PC CachyOS | `{"state": "CODING"}` |
| `desk/pc/windows/activity` | PC Windows | `{"state": "GAMING"}` |
| `desk/bot/state` | Cérebro | `{"expr": "jogando", "energy": 0.74, "phase": "tarde_noite"}` |
| `desk/bot/weather` | Cérebro | `{"temp": 24.2, "apparent_temp": 25.0, "humidity": 65, "condition": "Predom. ensolarado", "city": "São Paulo"}` |
| `desk/bot/time` | Cérebro | `{"time": "14:35", "date": "13/11/2026", "greeting": "Tarde focada no código!", "period": "tarde"}` |
| `desk/bot/touch` | ESP32 | `{"event": "tap", "x": 160, "y": 120, "mode": 0, "duration_ms": 110}` |

- Cada PC publica ao mudar de estado e a cada 10 s. Se ele cair ou desligar sem avisar, o broker publica `OFFLINE` por ele (Last Will).
- O cérebro publica estado facial ao mudar e a cada 15 s (batimento: o ESP32 sabe que o cérebro está vivo).
- O cérebro sincroniza clima a cada 60 s (com cache interno de 15 min na API Open-Meteo) e relógio/saudações a cada 15 s.
- O ESP32 envia eventos táteis (toque curto / longo) com rate-limit e debounce via `desk/bot/touch`.
- O `client_id` de cada agente é único (`deskbot-windows`, `deskbot-cachyos`, `deskbot-cerebro`).


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
| **feliz** | Amarelo | Olhos com bochechas subindo (sorrindo) | Ouvindo música/vídeo (`MEDIA`); despertar matinal (06h às 12h); por 6 s ao voltar |
| **jogando** | Vermelho | Olhos com sobrancelha inclinada (focado) | `GAMING` |
| **codando** | Verde | Olhos achatados com pálpebra levemente baixa | `CODING` |
| **sonolento** | Roxo claro | Pálpebra caída e cantos para baixo | Energia < 20%; na madrugada se energia < 40%; ausente com pouca energia ou pré-sono |
| **dormindo** | Roxo escuro | Olhos fechados (só uma linha) | Ausente/idle: na madrugada após 2,5 min; pré-sono após 5 min; dia após 10 a 20 min |
| **curioso** | Ciano | Olhos altos e estreitos, olha bastante em volta | Por 2,5 s ao começar jogo/IDE/mídia; ocioso com tédio acima de 50% |
| **entediado** | Azul-acinzentado | Pálpebra pela metade, olhar vagando | Ausente com tédio acima de 60% |
| **offline** | Cinza | Olhos meio caídos, olhar perdido | **Local no ESP32:** 90 s sem nada do cérebro (homelab/Wi-Fi caiu) |
| **surpreso** | Branco | Olhos bem abertos e altos | Por 6 s se o usuário ligar o PC na alta madrugada (01h às 05h) |

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

> ### Ciclo Circadiano (Curva Biológica 24h)
O cérebro calcula continuamente a fase do dia e ajusta tetos biológicos e comportamentos:
- **Madrugada (00h00 - 05h59):** Teto biológico de energia mínimo (0.35 a 0.45), drenagem acelerada (1.6x), recuperação lenta (0.5x), dorme em 2.5 min de ausência/idle. Ao ligar o PC entre 01h e 05h, o DeskBot reage espantado (`surpreso`).
- **Manhã / Despertar (06h00 - 11h59):** Energia subindo em direção a 1.0, recuperação revigorante (1.3x). Primeira atividade celebra o bom dia (`feliz` por 8 s, +0.3 felicidade).
- **Slump pós-almoço (12h00 - 14h29):** Moleza digestiva/circadiana (teto 0.85, recuperação 0.7x, maior propensão ao tédio).
- **Tarde / Noite produtiva (14h30 - 21h59):** Pico biológico (teto 1.0, taxas nominais 1.0x).
- **Pré-sono / Desaceleração (22h00 - 23h59):** Fadiga acumulada (teto caindo gradualmente de 1.0 para 0.45, dorme com 5 min ausente).

### Camada "viva" (roda no ESP32, sempre)

- **Piscar** em intervalos aleatórios de 2,5 a 6 s, às vezes duplo (15% das vezes).
- **Olhar pelos lados** com movimentos aleatórios (menos frequentes com energia baixa).
- **Respiração:** o olho cresce e encolhe cerca de 2,5% bem devagar.
- **Transições suaves** entre expressões (forma e cor).
- Continua animado mesmo que o homelab caia.

### Touch Screen Nativo & Máquina de Estados da Tela (XPT2046)

A tela TFT ILI9341 conta com controlador de toque integrado **XPT2046** via SPI compartilhado (`TOUCH_CS` no pino GPIO 5). O firmware implementa uma máquina de estados visual intuitiva:

- **Modo 0: Olhos Expressivos (Padrão 30 fps):**
  - **Carinho nos Olhos:** Tocar suavemente na região central dos olhos aciona reflexo carinhoso imediato (piscada feliz) e eleva a felicidade interna em **+0.15**.
  - **Soneca Forçada / Despertar:** Manter o toque por mais de **1.5 s (Long Press)** coloca o DeskBot em modo soneca (`dormindo`, energia=0.05). Outro toque longo ou toque suave acorda o bot revigorado.
  - **Navegação:** Toque na barra superior ou inferior avança para o Modo 1.
- **Modo 1: Dashboard Clima & Relógio:**
  - Mostra horário de alta precisão, data e saudação contextual baseada na rotina (ex: *"Bom dia, Arthur!"*, *"Noite adentro no código"*).
  - Exibe cartão meteorológico obtido da API **Open-Meteo** no homelab (temperatura, sensação térmica, umidade e condição).
  - Qualquer toque na tela avança para o Modo 2.
- **Modo 2: Status do PC & Vitalidade do Robô:**
  - Exibe o estado consolidado dos PCs (`CODING`, `GAMING`, `MEDIA`, etc.).
  - Barra de bateria cognitiva / energia do DeskBot e fase circadiana ativa.
  - Qualquer toque na tela retorna ao Modo 0.
- **Retorno Automático por Inatividade:** Após 30 segundos sem interação nos modos de dashboard, a tela retorna automaticamente aos Olhos Expressivos.
- **Debounce & Rate-Limit:** Processamento não-bloqueante com debounce de 40 ms e rate-limit de 250 ms para publicações em `desk/bot/touch`, evitando sobrecarga no MQTT.

> ℹ️ **Nota de Hardware (Servos Pan/Tilt):** A implementação de movimentação mecânica de cabeça via servomotores Pan/Tilt foi **formalmente reclassificada para o Backlog / Fase Futura Opcional de Hardware**, priorizando a rica interatividade tátil nativa da tela, o conhecimento de clima e o ecossistema cognitivo local.

---

## Arquivos

O projeto está organizado em três componentes modulares:

```
desk-bot/
├── docs/                        # Documentação e planos de arquitetura
│   └── PLANO_DESKBOT_INTERATIVIDADE.md # Especificação completa de hardware, IA e roadmap
│
├── deskbot/                     # Firmware do ESP32 (Arduino / PlatformIO)
│   ├── deskbot.ino              # Ponto de entrada do sketch Arduino
│   ├── platformio.ini           # Configuração de build e dependências PlatformIO
│   ├── config.h                 # Pinos, timeouts e parâmetros visuais
│   ├── secrets.h.example        # Modelo de credenciais Wi-Fi e broker MQTT
│   ├── User_Setup.h             # Mapeamento de pinos SPI do TFT_eSPI (Display e Touch CS no GPIO 5)
│   ├── expressions.h / .cpp     # Catálogo e geometria das 10 expressões faciais
│   ├── display_renderer.h / .cpp# Renderização gráfica na tela ILI9341 (Modos 0, 1 e 2)
│   ├── animation.h / .cpp       # Camada "viva" (piscar, respiração, olhar e reação a carinho)
│   ├── touch_manager.h / .cpp   # Driver de toque XPT2046 com debounce, tap e long-press
│   └── network_manager.h / .cpp # Wi-Fi, cliente MQTT e despacho de clima/tempo/touch
│
├── deskbot-server/              # Cérebro do robô (Homelab / Docker)
│   ├── docker-compose.yml       # Stack Mosquitto + Cérebro (Umbrel)
│   ├── mosquitto.conf           # Configuração do broker MQTT
│   ├── requirements.txt         # Dependências Python (paho-mqtt)
│   ├── cerebro.py               # Shim retrocompatível de execução
│   ├── deskbot_server/          # Pacote modular do Cérebro
│   │   ├── __main__.py          # Ponto de entrada modular (python -m deskbot_server)
│   │   ├── core/                # Regras de negócio e modelos biológicos
│   │   │   ├── circadian.py     # Ciclo circadiano 24h e curvas biológicas
│   │   │   ├── decision.py      # Prioridade e máquina de estados de expressão
│   │   │   ├── humor.py         # Modelo dinâmico (energia, tédio, felicidade e touch)
│   │   │   ├── weather.py       # Integração com Open-Meteo REST API (cache e fallback)
│   │   │   └── time_service.py  # Relógio e saudações contextuais por atividade/horário
│   │   └── infrastructure/      # Conectores externos
│   │       ├── config.py        # Leitura de variáveis de ambiente (.env)
│   │       ├── mqtt_client.py   # Conexão MQTT resiliente (tópicos state, weather, time, touch)
│   │       └── telemetry.py     # Persistência do log em CSV
│   └── tests/                   # Testes unitários do Cérebro
│       ├── test_cerebro.py      # Testes da curva circadiana e consolidação
│       └── test_interactivity.py# Testes de clima, relógio contextual e eventos de toque
│
├── deskbot-pc/                  # Agente monitor de atividade dos PCs
│   ├── requirements.txt         # Dependências Python (paho-mqtt, psutil)
│   ├── agent_pc.py              # Shim retrocompatível de execução
│   ├── deskbot_pc/              # Pacote modular do Agente PC
│   │   ├── __main__.py          # Ponto de entrada modular (python -m deskbot_pc)
│   │   ├── catalogs.py          # Listas de processos (jogos, código, mídia)
│   │   ├── classifier.py        # Heurísticas de detecção e classificação
│   │   ├── config.py            # Carregamento de argumentos e ambiente
│   │   ├── mqtt_client.py       # Publicador MQTT com Last Will
│   │   └── platform/            # Abstrações de sistema operacional
│   │       ├── base.py          # Interface abstrata de monitoramento
│   │       ├── linux.py         # Backend Wayland/X11 para Linux
│   │       └── windows.py       # Backend Win32 (tela cheia e inatividade)
│   └── tests/                   # Testes unitários do Agente PC
│       └── test_classifier.py   # Testes de classificação e regras de prioridade
│
├── .env.example                 # Modelo global de variáveis de ambiente
└── .gitignore                   # Mantém .env, secrets.h, dados e venvs fora do repo
```

No homelab, a pasta do servidor fica em `/home/umbrel/umbrel/my-apps/desk-bot/deskbot-server`.

## Hardware e ligações (ILI9341 + Touch XPT2046 → ESP32)

O display ILI9341 e o controlador de toque resistivo XPT2046 compartilham o mesmo barramento SPI de alta velocidade:

| Pino da Tela | Função | ESP32 | Notas |
|---|---|---|---|
| **VCC / LED** | Alimentação e Backlight | 3V3 | Consumo nominal ~80-120mA |
| **GND** | Referência Elétrica | GND | Terra comum do sistema |
| **CS** | Chip Select do Display | **GPIO 15** | Linha exclusiva do display TFT |
| **RESET** | Reset por Hardware | **GPIO 4** | Pulso de inicialização do display |
| **DC** | Data / Command | **GPIO 2** | Seleciona modo de dados ou comandos |
| **SDI (MOSI)** | SPI Master Out Slave In | **GPIO 23** | Barramento compartilhado (Display + Touch) |
| **SCK** | SPI Clock | **GPIO 18** | Barramento compartilhado (Display + Touch) |
| **SDO (MISO)** | SPI Master In Slave Out | **GPIO 19** | Leitura de coordenadas do Touch XPT2046 |
| **T_CS** | Chip Select do Touch | **GPIO 5** | Ativação do controlador XPT2046 |
| **T_CLK** | Clock do Touch | **GPIO 18** | Compartilhado com SCK do display |
| **T_DIN** | Entrada de Dados Touch | **GPIO 23** | Compartilhado com SDI/MOSI do display |
| **T_DO** | Saída de Dados Touch | **GPIO 19** | Compartilhado com SDO/MISO do display |
| **T_IRQ** | Interrupção de Toque | *Não conectado* | Polling não bloqueante via TFT_eSPI (40ms) |

- **PlatformIO:** O projeto inclui `platformio.ini` pronto com gerenciamento automático de dependências (**TFT_eSPI**, **PubSubClient**, **ArduinoJson**). Para compilar e gravar: `pio run --target upload`.
- **Arduino IDE:** Bibliotecas necessárias: **TFT_eSPI**, **PubSubClient**, **ArduinoJson (v7)**. Os pinos e `#define TOUCH_CS 5` já estão integrados no `User_Setup.h`.


## Como rodar

### Homelab (Cérebro + Mosquitto)

**Via Docker Compose (recomendado no homelab):**
```bash
cd /home/umbrel/umbrel/my-apps/desk-bot/deskbot-server
docker compose up -d
docker logs -f deskbot-cerebro
```

**Diretamente em Python:**
```bash
cd deskbot-server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m deskbot_server
```
> *Nota de compatibilidade:* o shim `python cerebro.py` continua funcionando normalmente e delega para o pacote modular `deskbot_server`.

### PC CachyOS (Linux)

```fish
cd ~/code/desk-bot/deskbot-pc
source .venv/bin/activate.fish
pip install -r requirements.txt
python -m deskbot_pc
```
> *Nota de compatibilidade:* o comando legado `python agent_pc.py` continua disponível via shim retrocompatível.

### PC Windows 10 (PowerShell)

```powershell
cd C:\caminho\desk-bot\deskbot-pc
py -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m deskbot_pc
```
> *Nota de compatibilidade:* o comando `.\.venv\Scripts\python agent_pc.py` permanece suportado.

Para abrir sozinho com o Windows: Agendador de Tarefas, "Ao fazer logon", executando `.\.venv\Scripts\pythonw.exe -m deskbot_pc` ou `.\.venv\Scripts\pythonw.exe agent_pc.py` (o `pythonw` não abre janela de terminal).

### ESP32 (Firmware)

1. Copiar `deskbot/secrets.h.example` para `deskbot/secrets.h`.
2. Preencher `WIFI_SSID`, `WIFI_PASS` (rede 2.4 GHz) e `MQTT_HOST`.
3. Fazer o upload:
   - **Com PlatformIO (recomendado):**
     ```bash
     cd deskbot
     pio run --target upload
     pio device monitor
     ```
   - **Com Arduino IDE:** abrir `deskbot/deskbot.ino` e fazer o upload na placa `ESP32 Dev Module`.

## Testes automatizados

Cada componente Python possui sua própria suíte de testes unitários com o framework nativo `unittest`:

**Testes do Cérebro (`deskbot-server`):**
```bash
cd deskbot-server
python -m unittest discover tests
```
Valida a curva circadiana de 24 horas, transições contínuas de fase, limiares de humor e consolidação de prioridade entre múltiplos PCs.

**Testes do Agente PC (`deskbot-pc`):**
```bash
cd deskbot-pc
python -m unittest discover tests
```
Valida heurísticas de detecção de tela cheia, catálogos de processos (`GAMING`, `CODING`, `MEDIA`, `IDLE`, `AWAY`) e compatibilidade entre plataformas.

## Configuração (.env e secrets.h)

Nada de IP ou senha fica escrito no código. Os arquivos reais **não vão pro git** (estão no `.gitignore`); só os `.example` vão.

| Arquivo de exemplo | Copie para | Onde fica | O que configura |
|---|---|---|---|
| `.env.example` | `.env` | `deskbot-pc/` (ao lado de `agent_pc.py`) | `DESKBOT_BROKER` (IP do homelab), `DESKBOT_NOME` (opcional) |
| `.env.example` | `.env` | `deskbot-server/` (ao lado do `docker-compose.yml`) | `TZ` (fuso horário do cérebro) |
| `secrets.h.example` | `secrets.h` | `deskbot/` (ao lado de `deskbot.ino`) | Wi-Fi e IP do broker no ESP32 |

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
- Listas `JOGOS`, `CODANDO`, `MIDIA` e `NAO_JOGO` do `deskbot-pc` (`deskbot_pc/catalogs.py`)
- Valores visuais de cada expressão no `deskbot` (`deskbot/expressions.cpp`)
- Tempos do humor (4 h de energia, 15 min de tédio etc.) conforme a sua rotina

## Limitações conhecidas

- O broker está **sem senha** (aceitável só na rede local).
- A detecção de tela cheia olha só o **monitor principal** e pode confundir um app maximizado sem barra de tarefas com um jogo. O controle de jogo não conta como teclado/mouse, por isso o jogo é checado antes da ausência.
- No CachyOS (Wayland), ainda não há detecção de `AWAY`: "ocioso" significa só "nenhum app conhecido aberto".
- Se o MQTT cair, a animação do ESP32 trava por cerca de 2 s a cada tentativa de reconexão (a cada 4 s).
- O IP do homelab precisa ser fixo (reserva de DHCP no roteador).
- Os agentes dos PCs precisam ser iniciados (no Windows, via Agendador de Tarefas).

---

## 🚀 Evolução & Plano de Hiper-Interatividade

Para transformar o DeskBot em um companheiro de mesa verdadeiramente vivo, tátil, sonoro e adaptativo com aprendizado contínuo, foi elaborado um plano arquitetural completo sem restrições de hardware:

👉 **Consulte a especificação detalhada:** [docs/PLANO_DESKBOT_INTERATIVIDADE.md](docs/PLANO_DESKBOT_INTERATIVIDADE.md)

### Destaques do Plano:
- **Benchmark & Inspiração da Robótica de Mesa:** Lições de expressividade de referências globais como **EMO**, **Vector & Cozmo** (Pixar), **LOONA** e **AIBI Pocket**.
- **Hardware Sensorial & Atuadores:**
  - *Tato & Movimento:* Toque capacitivo no topo para carinho/acordar, IMU 6DoF (MPU6050) para tontura/reação ao ser levantado da mesa.
  - *Presença Real:* Radar mmWave 24 GHz (HLK-LD2410) para detectar presença estática (respiração na cadeira) e sensor ToF para gestos no ar (high-five virtual).
  - *Expressividade Mecânica:* Pescoço articulado Pan & Tilt (2 servos micro) para assentir, negar e acompanhar o monitor ativo onde você digita.
  - *Áudio & Iluminação:* Sons procedurais estilo Wall-E/R2-D2 via amplificador I2S (MAX98357A) e aura luminosa de humor com anel de LEDs RGB WS2812B.
- **Inteligência Artificial & Aprendizado Contínuo:**
  - *Memória Multicamada:* Memória de Trabalho (RAM), Memória Episódica (ChromaDB vetorial) e Grafo de Conhecimento Semântico do Arthur.
  - *Sleep Consolidation (03:00):* Consolidação noturna automática via LLM local (Ollama / Llama 3) no homelab minerando a rotina do dia.
  - *Modelo VAD & Contextual Bandits:* Equilíbrio psicológico (Valence-Arousal-Dominance) com reforço implícito para proatividade não-invasiva.
- **Roadmap em 4 Fases:** Cronograma incremental dividindo entregas de firmware, eletrônica e backend Docker.

---

## Próximos passos

1. ~~Usar a **felicidade** e a expressão **surpreso** no cérebro~~ *(Concluído: Ciclo Circadiano implementado)*.
2. **Brilho do backlight** menor à noite (o cérebro manda o valor).
3. Serviço **systemd de usuário** para o agente do CachyOS iniciar sozinho.
4. Detecção de **ausência no CachyOS**.
5. Reações a **eventos**: `git push`, erro de compilação, CPU em 100%, chamada em andamento.
6. **Sons** com buzzer e, mais adiante, **microfone** (Whisper no homelab).
7. **Rede neural** treinada com o `deskbot_log.csv` para aprender a sua rotina.
8. Senha no Mosquitto.