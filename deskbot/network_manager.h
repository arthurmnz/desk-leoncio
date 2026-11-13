#ifndef DESKBOT_NETWORK_MANAGER_H
#define DESKBOT_NETWORK_MANAGER_H

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>

extern WiFiClient wifiClient;
extern PubSubClient mqttClient;

void inicializar_rede();
void atualizar_rede();

#endif // DESKBOT_NETWORK_MANAGER_H
