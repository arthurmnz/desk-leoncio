// DeskBot - ESP32 + ILI9341 (TFT_eSPI)
// Bibliotecas necessárias: TFT_eSPI, PubSubClient (Nick O'Leary), ArduinoJson (v7)

#include <Arduino.h>
#include "config.h"
#include "display_renderer.h"
#include "animation.h"
#include "network_manager.h"

static unsigned long ultimoFrame = 0;

void setup() {
  Serial.begin(115200);

  // Inicializa o display TFT e aloca sprite de tela dupla
  inicializar_display();

  // Inicia conexão Wi-Fi e configura broker MQTT
  inicializar_rede();
}

void loop() {
  // Mantém conexão de rede e processa mensagens MQTT recebidas
  atualizar_rede();

  // Renderiza quadro de animação a ~30 fps (33 ms)
  if (millis() - ultimoFrame >= 33) {
    ultimoFrame = millis();
    atualizar_frame_animacao();
  }
}
