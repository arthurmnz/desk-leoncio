#ifndef DESKBOT_ANIMATION_H
#define DESKBOT_ANIMATION_H

#include <Arduino.h>

float aprox(float a, float b, float k);

void definir_alvo_expressao(int novo_alvo, float nova_energia);
void registrar_atividade_servidor();
void atualizar_frame_animacao();
void acionar_reacao_carinho();

float obter_energia_atual();
int obter_alvo_expressao_atual();

#endif // DESKBOT_ANIMATION_H
