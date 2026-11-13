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
