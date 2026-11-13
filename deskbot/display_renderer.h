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

void solicitar_redesenho_completo();
void desenhar_barra_navegacao(int modoAtivo);
void desenhar_dashboard_clima(const char* hora, const char* data, const char* saudacao, float temp, float sensacao, int umidade, const char* condicao, const char* cidade);
void desenhar_status_pc(const char* estadoPc, float energia, const char* faseCircadiana, const char* nomePc);

#endif // DESKBOT_DISPLAY_RENDERER_H
