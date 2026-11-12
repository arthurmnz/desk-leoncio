// DeskBot - ESP32 + ILI9341 (TFT_eSPI)
// Bibliotecas: TFT_eSPI, PubSubClient (Nick O'Leary), ArduinoJson (v7)

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <TFT_eSPI.h>

// Credenciais ficam em secrets.h (copie de secrets.h.example, não vai pro git):
// WIFI_SSID, WIFI_PASS e MQTT_HOST
#include "secrets.h"

const int   MQTT_PORT = 1883;
const char* TOPICO    = "desk/bot/state";

#define C565(r,g,b) ((((r) & 0xF8) << 8) | (((g) & 0xFC) << 3) | ((b) >> 3))
#define BG 0x0000

TFT_eSPI tft = TFT_eSPI();
TFT_eSprite spr = TFT_eSprite(&tft);
WiFiClient wifi;
PubSubClient mqtt(wifi);

// Faixa da tela onde ficam os olhos (desenhada num sprite = sem piscar a tela)
const int SW = 320, SH = 140, SY = 50;
const int CY = SH / 2;
const int CX_ESQ = 90, CX_DIR = 230;

struct Expr {
  const char* nome;
  float h, w;     // altura e largura do olho
  float lid;      // pálpebra superior descendo (0 a 1)
  float tilt;     // + bravo/focado, - triste/cansado
  float cheek;    // bochecha subindo (feliz)
  float olhar;    // quanto ele movimenta o olhar (0 a 1)
  uint16_t cor;
};

const Expr EXPRS[] = {
  {"neutro",    80, 70, 0.00,  0.00, 0.0, 1.0, C565(0, 220, 255)},
  {"feliz",     70, 72, 0.00,  0.00, 0.9, 0.6, C565(255, 220, 0)},
  {"jogando",   70, 74, 0.00,  0.55, 0.0, 0.2, C565(255, 40, 40)},
  {"codando",   50, 78, 0.25,  0.10, 0.0, 0.3, C565(0, 230, 90)},
  {"sonolento", 60, 72, 0.45, -0.25, 0.0, 0.3, C565(150, 120, 255)},
  {"dormindo",   6, 76, 0.00,  0.00, 0.0, 0.0, C565(90, 70, 160)},
  {"curioso",   95, 62, 0.00,  0.00, 0.0, 1.0, C565(0, 220, 255)},
  {"surpreso", 105, 60, 0.00,  0.00, 0.0, 0.3, C565(255, 255, 255)},
  {"entediado", 50, 70, 0.45,  0.00, 0.0, 1.0, C565(120, 150, 190)},
  {"offline",   70, 70, 0.00, -0.20, 0.0, 0.8, C565(110, 110, 110)},
};
const int N_EXPRS = sizeof(EXPRS) / sizeof(EXPRS[0]);
const int IDX_OFFLINE = 9;

// Valores atuais (suavizados em direção à expressão alvo)
int alvo = 0;
float ch = 80, cw = 70, clid = 0, ctilt = 0, ccheek = 0, colhar = 1;
uint16_t ccor = EXPRS[0].cor;
float energia = 1.0;

unsigned long ultimaMsg = 0, ultimoFrame = 0, ultMqtt = 0;
unsigned long proxPiscar = 3000, inicioPiscar = 0, proxOlhar = 0;
bool piscando = false;
float olharX = 0, olharY = 0, alvoX = 0, alvoY = 0;

float aprox(float a, float b, float k) { return a + (b - a) * k; }

void onMsg(char* topic, byte* payload, unsigned int len) {
  JsonDocument doc;
  if (deserializeJson(doc, payload, len)) return;
  const char* e = doc["expr"] | "neutro";
  for (int i = 0; i < N_EXPRS; i++) {
    if (strcmp(EXPRS[i].nome, e) == 0) { alvo = i; break; }
  }
  energia = doc["energy"] | 1.0;
  ultimaMsg = millis();
  Serial.printf("expr=%s energia=%.2f\n", e, energia);
}

void olho(int cx, int cy, bool esq, float w, float h) {
  if (h < 3) h = 3;
  int x = cx - w / 2, y = cy - h / 2;
  int r = min(20.0f, h / 2);
  spr.fillRoundRect(x, y, (int)w, (int)h, r, ccor);

  // pálpebra superior
  if (clid > 0.01) spr.fillRect(x - 2, y - 2, (int)w + 4, (int)(h * clid) + 2, BG);

  // sobrancelha inclinada (bravo = cobre o canto interno, triste = o externo)
  if (fabs(ctilt) > 0.02) {
    int d = fabs(ctilt) * h;
    bool direita = (esq == (ctilt > 0));
    if (direita)
      spr.fillTriangle(x - 2, y - 2, x + (int)w + 2, y - 2, x + (int)w + 2, y + d, BG);
    else
      spr.fillTriangle(x - 2, y - 2, x + (int)w + 2, y - 2, x - 2, y + d, BG);
  }

  // bochecha subindo (olho "sorrindo")
  if (ccheek > 0.02)
    spr.fillCircle(cx, y + (int)h + w * 0.6 - ccheek * h * 0.5, w * 0.6, BG);
}

void quadro() {
  unsigned long agora = millis();
  bool semServidor = (agora - ultimaMsg) > 90000UL;
  const Expr& e = EXPRS[semServidor ? IDX_OFFLINE : alvo];

  // suaviza em direção à expressão alvo
  ch = aprox(ch, e.h, 0.18);     cw = aprox(cw, e.w, 0.18);
  clid = aprox(clid, e.lid, 0.18); ctilt = aprox(ctilt, e.tilt, 0.18);
  ccheek = aprox(ccheek, e.cheek, 0.18); colhar = aprox(colhar, e.olhar, 0.1);
  if (ccor != e.cor) ccor = spr.alphaBlend(45, e.cor, ccor);

  // piscar (às vezes duplo)
  float fp = 1.0;
  if (!piscando && agora > proxPiscar && e.h > 20) { piscando = true; inicioPiscar = agora; }
  if (piscando) {
    float t = (agora - inicioPiscar) / 160.0;
    if (t >= 1.0) {
      piscando = false;
      proxPiscar = agora + (random(100) < 15 ? 280 : random(2500, 6000));
    } else {
      fp = 1.0 - 0.95 * sin(PI * t);
    }
  }

  // olhar pelos lados (menos frequente quando está cansado)
  if (agora > proxOlhar) {
    alvoX = random(-100, 101) / 100.0;
    alvoY = random(-60, 61) / 100.0;
    proxOlhar = agora + (unsigned long)(random(1500, 4500) * (2.0 - energia));
  }
  olharX = aprox(olharX, alvoX, 0.12);
  olharY = aprox(olharY, alvoY, 0.12);

  // respiração
  float resp = 1.0 + 0.025 * sin(agora / 1400.0);
  float h = ch * fp * resp;
  int ox = olharX * 18 * colhar, oy = olharY * 10 * colhar;

  spr.fillSprite(BG);
  olho(CX_ESQ + ox, CY + oy, true, cw, h);
  olho(CX_DIR + ox, CY + oy, false, cw, h);
  spr.pushSprite(0, SY);
}

void rede() {
  if (WiFi.status() != WL_CONNECTED) return;   // o ESP32 reconecta sozinho
  if (!mqtt.connected() && millis() - ultMqtt > 4000) {
    ultMqtt = millis();
    if (mqtt.connect("deskbot")) {
      mqtt.subscribe(TOPICO);
      Serial.println("MQTT conectado");
    }
  }
}

void setup() {
  Serial.begin(115200);
  tft.init();
  tft.setRotation(1);
  tft.fillScreen(BG);

  // o sprite é criado antes do Wi-Fi pra garantir memória
  if (!spr.createSprite(SW, SH)) {
    Serial.println("Pouca memoria: usando sprite de 8 bits");
    spr.setColorDepth(8);
    spr.createSprite(SW, SH);
  }

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMsg);
  mqtt.setSocketTimeout(2);
}

void loop() {
  rede();
  if (mqtt.connected()) mqtt.loop();
  if (millis() - ultimoFrame >= 33) {   // ~30 fps
    ultimoFrame = millis();
    quadro();
  }
}