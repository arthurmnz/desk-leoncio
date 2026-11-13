#ifndef DESKBOT_NETWORK_MANAGER_H
#define DESKBOT_NETWORK_MANAGER_H

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>

extern WiFiClient wifiClient;
extern PubSubClient mqttClient;

// Estruturas de dados recebidas do servidor
struct DadosClima {
  float temp;
  float sensacao;
  int umidade;
  char condicao[32];
  char cidade[32];
  bool valido;
};

struct DadosTempo {
  char hora[16];
  char data[32];
  char saudacao[64];
  char periodo[16];
  bool valido;
};

struct DadosBotState {
  char expr[24];
  float energia;
  char fase[32];
  char estadoPc[16];
  bool valido;
};

void inicializar_rede();
void atualizar_rede();
void enviar_evento_toque_mqtt(const char* evento, uint16_t x, uint16_t y, int modo, unsigned long duracaoMs);

const DadosClima& obter_dados_clima();
const DadosTempo& obter_dados_tempo();
const DadosBotState& obter_dados_estado();

#endif // DESKBOT_NETWORK_MANAGER_H
