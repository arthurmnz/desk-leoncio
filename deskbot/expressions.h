#ifndef DESKBOT_EXPRESSIONS_H
#define DESKBOT_EXPRESSIONS_H

#include <stdint.h>
#ifdef ARDUINO
#include <Arduino.h>
#endif

#define C565(r,g,b) ((((r) & 0xF8) << 8) | (((g) & 0xFC) << 3) | ((b) >> 3))

struct Expr {
  const char* nome;
  float h, w;     // altura e largura do olho
  float lid;      // pálpebra superior descendo (0 a 1)
  float tilt;     // + bravo/focado, - triste/cansado
  float cheek;    // bochecha subindo (feliz)
  float olhar;    // quanto ele movimenta o olhar (0 a 1)
  uint16_t cor;
};

extern const Expr EXPRS[];
extern const int N_EXPRS;
extern const int IDX_OFFLINE;

int encontrar_expressao(const char* nome);

#endif // DESKBOT_EXPRESSIONS_H
