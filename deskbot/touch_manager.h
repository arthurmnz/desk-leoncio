#ifndef DESKBOT_TOUCH_MANAGER_H
#define DESKBOT_TOUCH_MANAGER_H

#include <Arduino.h>
#include "config.h"

// Callback para notificação de eventos de toque para a rede
typedef void (*TouchEventHandler)(const char* evento, uint16_t x, uint16_t y, int modo, unsigned long duracaoMs);

// Obtém e altera o modo de exibição atual da tela
DisplayMode obter_modo_atual();
void definir_modo_atual(DisplayMode novoModo);
void alternar_proximo_modo();

// Inicialização e processamento no loop
void inicializar_touch();
void atualizar_touch(TouchEventHandler handler);

#endif // DESKBOT_TOUCH_MANAGER_H
