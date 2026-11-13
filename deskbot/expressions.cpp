#include "expressions.h"
#include <string.h>

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

int encontrar_expressao(const char* nome) {
  if (!nome) return 0;
  for (int i = 0; i < N_EXPRS; i++) {
    if (strcmp(EXPRS[i].nome, nome) == 0) {
      return i;
    }
  }
  return 0; // Fallback para "neutro"
}
