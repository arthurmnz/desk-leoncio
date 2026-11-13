// DeskBot - ESP32 + ILI9341 (TFT_eSPI)
// Bibliotecas necessárias: TFT_eSPI, PubSubClient (Nick O'Leary), ArduinoJson (v7)

#include <Arduino.h>
#include "config.h"
#include "display_renderer.h"
#include "animation.h"
#include "network_manager.h"
#include "touch_manager.h"

static unsigned long ultimoFrame = 0;
static unsigned long ultimoRenderDashboard = 0;
static DisplayMode modoAnterior = MODE_EYES;

void setup() {
  Serial.begin(115200);

  // Inicializa o display TFT e aloca sprite de tela dupla
  inicializar_display();

  // Inicializa controlador de toque XPT2046 (SPI compartilhado, CS no GPIO 5)
  inicializar_touch();

  // Inicia conexão Wi-Fi e configura broker MQTT
  inicializar_rede();
}

void loop() {
  // 1. Mantém conexão de rede e processa mensagens MQTT recebidas
  atualizar_rede();

  // 2. Processa toque capacitivo/resistivo XPT2046 com debounce e rate-limit
  atualizar_touch(enviar_evento_toque_mqtt);

  DisplayMode modoAtual = obter_modo_atual();

  // Limpa a tela caso o modo tenha acabado de mudar
  if (modoAtual != modoAnterior) {
    tft.fillScreen(BG);
    modoAnterior = modoAtual;
    ultimoRenderDashboard = 0; // Força renderização imediata do novo dashboard
  }

  // 3. Renderização conforme a máquina de estados visual
  unsigned long agora = millis();

  switch (modoAtual) {
    case MODE_EYES:
      // Renderiza quadro de animação dos olhos a ~30 fps (33 ms)
      if (agora - ultimoFrame >= 33) {
        ultimoFrame = agora;
        atualizar_frame_animacao();
      }
      break;

    case MODE_WEATHER:
      // Renderiza dashboard de clima e relógio a cada 1000 ms (1 Hz)
      if (agora - ultimoRenderDashboard >= 1000) {
        ultimoRenderDashboard = agora;
        const DadosTempo& dt = obter_dados_tempo();
        const DadosClima& dc = obter_dados_clima();
        desenhar_dashboard_clima(
          dt.hora,
          dt.data,
          dt.saudacao,
          dc.temp,
          dc.sensacao,
          dc.umidade,
          dc.condicao,
          dc.cidade
        );
      }
      break;

    case MODE_PC_STATUS:
      // Renderiza dashboard de status do PC e vitalidade a cada 1000 ms (1 Hz)
      if (agora - ultimoRenderDashboard >= 1000) {
        ultimoRenderDashboard = agora;
        const DadosBotState& ds = obter_dados_estado();
        desenhar_status_pc(
          ds.estadoPc,
          ds.energia,
          ds.fase,
          "Homelab"
        );
      }
      break;

    default:
      definir_modo_atual(MODE_EYES);
      break;
  }
}

