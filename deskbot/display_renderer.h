#ifndef DESKBOT_DISPLAY_RENDERER_H
#define DESKBOT_DISPLAY_RENDERER_H

#include <Arduino.h>
#include <TFT_eSPI.h>

extern TFT_eSPI tft;
extern TFT_eSprite spr;

void inicializar_display();
void limpar_sprite();
void enviar_sprite_para_tela(int x, int y);
void desenhar_olho(int cx, int cy, bool esq, float w, float h, float clid, float ctilt, float ccheek, uint16_t ccor);

#endif // DESKBOT_DISPLAY_RENDERER_H
