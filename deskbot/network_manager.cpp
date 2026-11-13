#include "network_manager.h"
#include "config.h"
#include "expressions.h"
#include "animation.h"
#include <ArduinoJson.h>

#if __has_include("secrets.h")
#include "secrets.h"
#elif __has_include("secrets.h.example")
#include "secrets.h.example"
#else
const char* WIFI_SSID = "SEU_WIFI";
const char* WIFI_PASS = "SUA_SENHA";
const char* MQTT_HOST = "192.168.0.5";
#endif

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

static unsigned long ultMqtt = 0;

static void onMsg(char* topic, byte* payload, unsigned int len) {
  JsonDocument doc;
  if (deserializeJson(doc, payload, len)) return;

  const char* e = doc["expr"] | "neutro";
  float n_energia = doc["energy"] | 1.0f;

  int idx = encontrar_expressao(e);
  definir_alvo_expressao(idx, n_energia);
  registrar_atividade_servidor();

  Serial.printf("expr=%s energia=%.2f\n", e, n_energia);
}

void inicializar_rede() {
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  mqttClient.setServer(MQTT_HOST, MQTT_PORT);
  mqttClient.setCallback(onMsg);
  mqttClient.setSocketTimeout(2);
}

void atualizar_rede() {
  if (WiFi.status() != WL_CONNECTED) return; // ESP32 reconecta automaticamente

  if (!mqttClient.connected() && millis() - ultMqtt > 4000) {
    ultMqtt = millis();
    if (mqttClient.connect("deskbot")) {
      mqttClient.subscribe(TOPICO);
      Serial.println("MQTT conectado");
    }
  }

  if (mqttClient.connected()) {
    mqttClient.loop();
  }
}
