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

static DadosClima dadosClima = { 22.0f, 22.0f, 50, "Aguardando...", "São Paulo", false };
static DadosTempo dadosTempo = { "--:--", "--/--/----", "Iniciando DeskBot...", "dia", false };
static DadosBotState dadosEstado = { "neutro", 1.0f, "normal", "OFFLINE", false };

const DadosClima& obter_dados_clima() {
  return dadosClima;
}

const DadosTempo& obter_dados_tempo() {
  return dadosTempo;
}

const DadosBotState& obter_dados_estado() {
  return dadosEstado;
}

static void onMsg(char* topic, byte* payload, unsigned int len) {
  JsonDocument doc;
  if (deserializeJson(doc, payload, len)) return;

  // 1. Mensagens de Estado do DeskBot
  if (strcmp(topic, TOPICO_STATE) == 0 || strcmp(topic, TOPICO) == 0) {
    const char* e = doc["expr"] | "neutro";
    float n_energia = doc["energy"] | 1.0f;
    const char* fase = doc["phase"] | "normal";

    strncpy(dadosEstado.expr, e, sizeof(dadosEstado.expr) - 1);
    dadosEstado.expr[sizeof(dadosEstado.expr) - 1] = '\0';
    dadosEstado.energia = n_energia;
    strncpy(dadosEstado.fase, fase, sizeof(dadosEstado.fase) - 1);
    dadosEstado.fase[sizeof(dadosEstado.fase) - 1] = '\0';
    dadosEstado.valido = true;

    // Dedução do estado do PC baseado na expressão do servidor
    if (strcmp(e, "codando") == 0) strncpy(dadosEstado.estadoPc, "CODING", sizeof(dadosEstado.estadoPc) - 1);
    else if (strcmp(e, "jogando") == 0) strncpy(dadosEstado.estadoPc, "GAMING", sizeof(dadosEstado.estadoPc) - 1);
    else if (strcmp(e, "dormindo") == 0) strncpy(dadosEstado.estadoPc, "OFFLINE", sizeof(dadosEstado.estadoPc) - 1);
    else if (strcmp(e, "feliz") == 0) strncpy(dadosEstado.estadoPc, "MEDIA / ATIVO", sizeof(dadosEstado.estadoPc) - 1);
    else strncpy(dadosEstado.estadoPc, "ONLINE", sizeof(dadosEstado.estadoPc) - 1);
    dadosEstado.estadoPc[sizeof(dadosEstado.estadoPc) - 1] = '\0';

    int idx = encontrar_expressao(e);
    definir_alvo_expressao(idx, n_energia);
    registrar_atividade_servidor();

    Serial.printf("📥 [MQTT] Estado: expr=%s energia=%.2f fase=%s\n", e, n_energia, fase);
  }
  // 2. Mensagens do Serviço de Clima
  else if (strcmp(topic, TOPICO_WEATHER) == 0) {
    dadosClima.temp = doc["temp"] | 22.0f;
    dadosClima.sensacao = doc["apparent_temp"] | dadosClima.temp;
    dadosClima.umidade = doc["humidity"] | 50;
    const char* c = doc["condition"] | "Instável";
    const char* cid = doc["city"] | "São Paulo";
    strncpy(dadosClima.condicao, c, sizeof(dadosClima.condicao) - 1);
    dadosClima.condicao[sizeof(dadosClima.condicao) - 1] = '\0';
    strncpy(dadosClima.cidade, cid, sizeof(dadosClima.cidade) - 1);
    dadosClima.cidade[sizeof(dadosClima.cidade) - 1] = '\0';
    dadosClima.valido = true;

    Serial.printf("🌤 [MQTT] Clima: %.1f C, %s (%s)\n", dadosClima.temp, dadosClima.condicao, dadosClima.cidade);
  }
  // 3. Mensagens do Serviço de Tempo / Relógio
  else if (strcmp(topic, TOPICO_TIME) == 0) {
    const char* h = doc["time"] | "--:--";
    const char* d = doc["date_display"] | (const char*)(doc["date"] | "--/--/----");
    const char* g = doc["greeting"] | "Olá, Arthur!";
    const char* p = doc["period"] | "dia";

    strncpy(dadosTempo.hora, h, sizeof(dadosTempo.hora) - 1);
    dadosTempo.hora[sizeof(dadosTempo.hora) - 1] = '\0';
    strncpy(dadosTempo.data, d, sizeof(dadosTempo.data) - 1);
    dadosTempo.data[sizeof(dadosTempo.data) - 1] = '\0';
    strncpy(dadosTempo.saudacao, g, sizeof(dadosTempo.saudacao) - 1);
    dadosTempo.saudacao[sizeof(dadosTempo.saudacao) - 1] = '\0';
    strncpy(dadosTempo.periodo, p, sizeof(dadosTempo.periodo) - 1);
    dadosTempo.periodo[sizeof(dadosTempo.periodo) - 1] = '\0';
    dadosTempo.valido = true;

    Serial.printf("⏰ [MQTT] Tempo: %s | %s\n", dadosTempo.hora, dadosTempo.saudacao);
  }
}

void enviar_evento_toque_mqtt(const char* evento, uint16_t x, uint16_t y, int modo, unsigned long duracaoMs) {
  if (!mqttClient.connected()) return;

  JsonDocument doc;
  doc["event"] = evento;
  doc["x"] = x;
  doc["y"] = y;
  doc["mode"] = modo;
  doc["duration_ms"] = duracaoMs;

  char buffer[128];
  size_t n = serializeJson(doc, buffer, sizeof(buffer));
  mqttClient.publish(TOPICO_TOUCH, buffer, n);
  Serial.printf("📤 [MQTT Touch] Evento '%s' enviado (modo=%d, dur=%lums)\n", evento, modo, duracaoMs);
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
      mqttClient.subscribe(TOPICO_STATE);
      mqttClient.subscribe(TOPICO_WEATHER);
      mqttClient.subscribe(TOPICO_TIME);
      Serial.println("✓ MQTT conectado e tópicos inscritos (state, weather, time)");
    }
  }

  if (mqttClient.connected()) {
    mqttClient.loop();
  }
}

