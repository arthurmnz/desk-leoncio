#include "touch_manager.h"
#include "display_renderer.h"
#include "animation.h"
#include <TFT_eSPI.h>

static DisplayMode modoAtual = MODE_EYES;
static unsigned long ultimoToqueTs = 0;
static unsigned long inicioPressionamento = 0;
static unsigned long ultimoEnvioMqtt = 0;
static bool pressionando = false;
static bool longPressDisparado = false;
static uint16_t ultX = 0, ultY = 0;

DisplayMode obter_modo_atual() {
  return modoAtual;
}

void definir_modo_atual(DisplayMode novoModo) {
  if (novoModo != modoAtual) {
    modoAtual = (DisplayMode)((int)novoModo % MODE_MAX);
    tft.fillScreen(BG);
    solicitar_redesenho_completo();
    ultimoToqueTs = millis();
    Serial.printf("🖥 [Touch] Modo de exibição alterado para: %d\n", (int)modoAtual);
  }
}

void alternar_proximo_modo() {
  definir_modo_atual((DisplayMode)(((int)modoAtual + 1) % MODE_MAX));
}

void inicializar_touch() {
  // Configuração padrão de calibração para display ILI9341 320x240 com XPT2046
  // Calibração típica: [xMin, xMax, yMin, yMax, rot]
  uint16_t calData[5] = { 275, 3620, 264, 3532, 1 };
  tft.setTouch(calData);
  ultimoToqueTs = millis();
  Serial.println("✓ Touch XPT2046 inicializado (GPIO 5)");
}

void atualizar_touch(TouchEventHandler handler) {
  unsigned long agora = millis();
  uint16_t tx = 0, ty = 0;
  bool tocando = tft.getTouch(&tx, &ty, 400);

  // 1. Início de uma pressão na tela
  if (tocando && !pressionando) {
    pressionando = true;
    inicioPressionamento = agora;
    longPressDisparado = false;
    ultX = tx;
    ultY = ty;
  }
  // 2. Mantendo a tela pressionada (detecção de Long Press > 1.5s)
  else if (tocando && pressionando) {
    ultX = tx;
    ultY = ty;
    unsigned long duracao = agora - inicioPressionamento;

    if (!longPressDisparado && duracao >= TOUCH_LONG_PRESS_MS) {
      longPressDisparado = true;
      ultimoToqueTs = agora;
      Serial.printf("⏰ [Touch] Long Press detectado (%lu ms)!\n", duracao);

      if (handler && (agora - ultimoEnvioMqtt >= TOUCH_RATE_LIMIT_MS)) {
        handler("long_press", tx, ty, (int)modoAtual, duracao);
        ultimoEnvioMqtt = agora;
      }
    }
  }
  // 3. Liberação do toque (Touch Up)
  else if (!tocando && pressionando) {
    pressionando = false;
    unsigned long duracao = agora - inicioPressionamento;
    ultimoToqueTs = agora;

    // Se não foi long press e respeitou o debounce mínimo de 40ms, é um TAP
    if (!longPressDisparado && duracao >= TOUCH_DEBOUNCE_MS) {
      Serial.printf("👆 [Touch] Tap em (%d, %d) no modo %d (duracao: %lu ms)\n", ultX, ultY, (int)modoAtual, duracao);

      if (modoAtual == MODE_EYES) {
        // Área central dos olhos (Y entre 40 e 190): Carinho!
        if (ultY >= 40 && ultY <= 190) {
          Serial.println("💖 [Touch] Carinho nos olhos detectado!");
          acionar_reacao_carinho();

          if (handler && (agora - ultimoEnvioMqtt >= TOUCH_RATE_LIMIT_MS)) {
            handler("tap", ultX, ultY, (int)modoAtual, duracao);
            ultimoEnvioMqtt = agora;
          }
        } else {
          // Toque na borda superior ou inferior: chaveia modo
          alternar_proximo_modo();
          if (handler && (agora - ultimoEnvioMqtt >= TOUCH_RATE_LIMIT_MS)) {
            handler("mode_change", ultX, ultY, (int)modoAtual, duracao);
            ultimoEnvioMqtt = agora;
          }
        }
      } else {
        // Nos dashboards (Clima ou Status do PC), qualquer toque avança o modo
        alternar_proximo_modo();
        if (handler && (agora - ultimoEnvioMqtt >= TOUCH_RATE_LIMIT_MS)) {
          handler("mode_change", ultX, ultY, (int)modoAtual, duracao);
          ultimoEnvioMqtt = agora;
        }
      }
    }
  }

  // 4. Timeout de dashboard: se inativo nos modos 1 ou 2 por 30s, retorna aos Olhos
  if (modoAtual != MODE_EYES && (agora - ultimoToqueTs >= DASHBOARD_TIMEOUT_MS)) {
    Serial.println("⏱ [Touch] Timeout de inatividade: retornando ao Modo 0 (Olhos)");
    definir_modo_atual(MODE_EYES);
  }
}
