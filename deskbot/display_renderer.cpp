#include "display_renderer.h"
#include "config.h"
#include <math.h>

TFT_eSPI tft = TFT_eSPI();
TFT_eSprite spr = TFT_eSprite(&tft);

void inicializar_display() {
  tft.init();
  tft.setRotation(1);
  tft.fillScreen(BG);

  // O sprite é criado antes do Wi-Fi para garantir bloco de memória contígua
  if (!spr.createSprite(SW, SH)) {
    Serial.println("Pouca memoria: usando sprite de 8 bits");
    spr.setColorDepth(8);
    spr.createSprite(SW, SH);
  }
}

void limpar_sprite() {
  spr.fillSprite(BG);
}

void enviar_sprite_para_tela(int x, int y) {
  spr.pushSprite(x, y);
}

void desenhar_olho(int cx, int cy, bool esq, float w, float h, float clid, float ctilt, float ccheek, uint16_t ccor) {
  if (h < 3) h = 3;
  int x = cx - w / 2;
  int y = cy - h / 2;
  int r = min(20.0f, h / 2.0f);
  spr.fillRoundRect(x, y, (int)w, (int)h, r, ccor);

  // Pálpebra superior
  if (clid > 0.01) {
    spr.fillRect(x - 2, y - 2, (int)w + 4, (int)(h * clid) + 2, BG);
  }

  // Sobrancelha inclinada (bravo = cobre canto interno, triste/cansado = canto externo)
  if (fabs(ctilt) > 0.02) {
    int d = fabs(ctilt) * h;
    bool direita = (esq == (ctilt > 0));
    if (direita) {
      spr.fillTriangle(x - 2, y - 2, x + (int)w + 2, y - 2, x + (int)w + 2, y + d, BG);
    } else {
      spr.fillTriangle(x - 2, y - 2, x + (int)w + 2, y - 2, x - 2, y + d, BG);
    }
  }

  // Bochecha subindo (sorriso)
  if (ccheek > 0.02) {
    spr.fillCircle(cx, y + (int)h + w * 0.6 - ccheek * h * 0.5, w * 0.6, BG);
  }
}

static bool forcarRedesenho = true;

void solicitar_redesenho_completo() {
  forcarRedesenho = true;
}

void desenhar_barra_navegacao(int modoAtivo) {
  // Rodapé minimalista com 3 pílulas de status dos modos (Y=220 a Y=236)
  int y = 224;
  const char* labels[3] = { "Olhos", "Clima", "PC" };
  int xs[3] = { 60, 160, 260 };

  tft.drawFastHLine(10, 218, 300, 0x2104); // Linha divisória cinza escuro

  for (int i = 0; i < 3; i++) {
    bool ativo = (i == modoAtivo);
    uint16_t corBorda = ativo ? TFT_CYAN : 0x39E7;
    uint16_t corTexto = ativo ? TFT_WHITE : 0x7BEF;

    tft.drawRoundRect(xs[i] - 38, y, 76, 14, 4, corBorda);
    if (ativo) {
      tft.fillRoundRect(xs[i] - 36, y + 2, 72, 10, 2, 0x01E8);
    } else {
      tft.fillRoundRect(xs[i] - 36, y + 2, 72, 10, 2, BG);
    }
    tft.setTextDatum(MC_DATUM);
    tft.setTextColor(corTexto, ativo ? 0x01E8 : BG);
    tft.drawString(labels[i], xs[i], y + 7, 2);
  }
}

void desenhar_dashboard_clima(const char* hora, const char* data, const char* saudacao, float temp, float sensacao, int umidade, const char* condicao, const char* cidade) {
  tft.setTextDatum(TL_DATUM);

  // Barra de status superior
  tft.fillRoundRect(10, 8, 300, 24, 6, 0x18E3);
  tft.setTextColor(TFT_WHITE, 0x18E3);
  tft.drawString(cidade && strlen(cidade) > 0 ? cidade : "São Paulo", 20, 13, 2);

  tft.setTextDatum(TR_DATUM);
  tft.setTextColor(TFT_CYAN, 0x18E3);
  tft.drawString(data && strlen(data) > 0 ? data : "--/--/----", 300, 13, 2);

  // Relógio grande no centro
  tft.setTextDatum(TC_DATUM);
  tft.setTextColor(TFT_WHITE, BG);
  tft.drawString(hora && strlen(hora) > 0 ? hora : "--:--", 160, 42, 6);

  // Saudação contextual
  tft.setTextColor(0xFDE0, BG); // Amarelo suave
  tft.drawString(saudacao && strlen(saudacao) > 0 ? saudacao : "DeskBot Ativo", 160, 98, 2);

  // Bloco de Cartão do Clima
  tft.fillRoundRect(16, 126, 288, 80, 8, 0x10A2);
  tft.drawRoundRect(16, 126, 288, 80, 8, 0x2965);

  char bufTemp[32];
  snprintf(bufTemp, sizeof(bufTemp), "%.1f C", temp);
  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(TFT_ORANGE, 0x10A2);
  tft.drawString(bufTemp, 30, 136, 4);

  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(TFT_LIGHTGREY, 0x10A2);
  char bufSens[32];
  snprintf(bufSens, sizeof(bufSens), "Sensacao: %.1f C", sensacao);
  tft.drawString(bufSens, 30, 172, 2);

  tft.setTextDatum(TR_DATUM);
  tft.setTextColor(TFT_CYAN, 0x10A2);
  tft.drawString(condicao && strlen(condicao) > 0 ? condicao : "Estavel", 290, 138, 2);

  char bufUmid[32];
  snprintf(bufUmid, sizeof(bufUmid), "Umid: %d%%", umidade);
  tft.setTextColor(TFT_WHITE, 0x10A2);
  tft.drawString(bufUmid, 290, 168, 2);

  // Navegação no rodapé
  desenhar_barra_navegacao(1);
}

void desenhar_status_pc(const char* estadoPc, float energia, const char* faseCircadiana, const char* nomePc) {
  tft.setTextDatum(TL_DATUM);

  // Barra de status superior
  tft.fillRoundRect(10, 8, 300, 24, 6, 0x18E3);
  tft.setTextColor(TFT_WHITE, 0x18E3);
  tft.drawString("DESKBOT // VITALIDADE", 20, 13, 2);

  tft.setTextDatum(TR_DATUM);
  tft.setTextColor(TFT_GREEN, 0x18E3);
  tft.drawString("ONLINE", 300, 13, 2);

  // Cartão 1: Atividade Consolidada do PC
  tft.fillRoundRect(16, 42, 288, 64, 8, 0x10A2);
  tft.drawRoundRect(16, 42, 288, 64, 8, 0x2965);

  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(TFT_LIGHTGREY, 0x10A2);
  tft.drawString("Atividade Atual (PC):", 30, 52, 2);

  const char* est = estadoPc && strlen(estadoPc) > 0 ? estadoPc : "OFFLINE";
  uint16_t corEstado = TFT_LIGHTGREY;
  if (strcmp(est, "CODING") == 0) corEstado = TFT_CYAN;
  else if (strcmp(est, "GAMING") == 0) corEstado = 0x07E0; // Verde
  else if (strcmp(est, "MEDIA") == 0) corEstado = TFT_ORANGE;
  else if (strcmp(est, "IDLE") == 0) corEstado = TFT_YELLOW;

  tft.setTextColor(corEstado, 0x10A2);
  tft.drawString(est, 30, 74, 4);

  // Cartão 2: Energia e Ritmo Circadiano
  tft.fillRoundRect(16, 116, 288, 88, 8, 0x10A2);
  tft.drawRoundRect(16, 116, 288, 88, 8, 0x2965);

  tft.setTextColor(TFT_LIGHTGREY, 0x10A2);
  tft.drawString("Bateria Cognitiva:", 30, 126, 2);

  int percEnergia = (int)(energia * 100.0f);
  if (percEnergia < 0) percEnergia = 0;
  if (percEnergia > 100) percEnergia = 100;

  char bufPerc[16];
  snprintf(bufPerc, sizeof(bufPerc), "%d%%", percEnergia);
  tft.setTextDatum(TR_DATUM);
  tft.setTextColor(TFT_WHITE, 0x10A2);
  tft.drawString(bufPerc, 290, 126, 2);

  // Barra de Energia horizontal
  tft.fillRoundRect(30, 146, 260, 14, 4, 0x2104);
  int wBarra = (int)(256.0f * (percEnergia / 100.0f));
  uint16_t corBarra = percEnergia > 50 ? 0x07E0 : (percEnergia > 20 ? TFT_YELLOW : TFT_RED);
  if (wBarra > 0) {
    tft.fillRoundRect(32, 148, wBarra, 10, 3, corBarra);
  }

  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(0x7BEF, 0x10A2);
  char bufFase[48];
  snprintf(bufFase, sizeof(bufFase), "Fase: %s", faseCircadiana && strlen(faseCircadiana) > 0 ? faseCircadiana : "Normal");
  tft.drawString(bufFase, 30, 172, 2);

  // Navegação no rodapé
  desenhar_barra_navegacao(2);
}

