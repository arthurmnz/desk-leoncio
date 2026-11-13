#include "animation.h"
#include "config.h"
#include "expressions.h"
#include "display_renderer.h"
#include <math.h>

// Valores atuais suavizados em direção à expressão alvo
static int alvo = 0;
static float ch = 80, cw = 70, clid = 0, ctilt = 0, ccheek = 0, colhar = 1;
static uint16_t ccor = EXPRS[0].cor;
static float energia = 1.0;

static unsigned long ultimaMsg = 0;
static unsigned long proxPiscar = 3000, inicioPiscar = 0, proxOlhar = 0;
static unsigned long carinhoAte = 0;
static bool piscando = false;
static float olharX = 0, olharY = 0, alvoX = 0, alvoY = 0;

float aprox(float a, float b, float k) {
  return a + (b - a) * k;
}

void definir_alvo_expressao(int novo_alvo, float nova_energia) {
  if (novo_alvo >= 0 && novo_alvo < N_EXPRS) {
    alvo = novo_alvo;
  }
  energia = nova_energia < 0.0f ? 0.0f : (nova_energia > 1.0f ? 1.0f : nova_energia);
}

void acionar_reacao_carinho() {
  carinhoAte = millis() + 3500;
  piscando = true;
  inicioPiscar = millis();
}

float obter_energia_atual() {
  return energia;
}

int obter_alvo_expressao_atual() {
  return alvo;
}

void registrar_atividade_servidor() {
  ultimaMsg = millis();
}

void atualizar_frame_animacao() {
  unsigned long agora = millis();
  bool semServidor = (agora - ultimaMsg) > 90000UL;
  int idxAtivo = alvo;
  if (agora < carinhoAte) {
    idxAtivo = encontrar_expressao("feliz");
  } else if (semServidor) {
    idxAtivo = IDX_OFFLINE;
  }
  const Expr& e = EXPRS[idxAtivo];


  // Suavização em direção aos parâmetros da expressão alvo
  ch = aprox(ch, e.h, 0.18);
  cw = aprox(cw, e.w, 0.18);
  clid = aprox(clid, e.lid, 0.18);
  ctilt = aprox(ctilt, e.tilt, 0.18);
  ccheek = aprox(ccheek, e.cheek, 0.18);
  colhar = aprox(colhar, e.olhar, 0.1);
  if (ccor != e.cor) {
    ccor = spr.alphaBlend(45, e.cor, ccor);
  }

  // Piscar de olhos (com probabilidade de piscar duplo rápido)
  float fp = 1.0;
  if (!piscando && agora > proxPiscar && e.h > 20) {
    piscando = true;
    inicioPiscar = agora;
  }
  if (piscando) {
    float t = (agora - inicioPiscar) / 160.0;
    if (t >= 1.0) {
      piscando = false;
      proxPiscar = agora + (random(100) < 15 ? 280 : random(2500, 6000));
    } else {
      fp = 1.0 - 0.95 * sin(PI * t);
    }
  }

  // Movimento de olhar pelos lados (menos frequente quando cansado)
  if (agora > proxOlhar) {
    alvoX = random(-100, 101) / 100.0;
    alvoY = random(-60, 61) / 100.0;
    proxOlhar = agora + (unsigned long)(random(1500, 4500) * (2.0 - energia));
  }
  olharX = aprox(olharX, alvoX, 0.12);
  olharY = aprox(olharY, alvoY, 0.12);

  // Micro-movimento de respiração
  float resp = 1.0 + 0.025 * sin(agora / 1400.0);
  float h = ch * fp * resp;
  int ox = olharX * 18 * colhar;
  int oy = olharY * 10 * colhar;

  limpar_sprite();
  desenhar_olho(CX_ESQ + ox, CY + oy, true, cw, h, clid, ctilt, ccheek, ccor);
  desenhar_olho(CX_DIR + ox, CY + oy, false, cw, h, clid, ctilt, ccheek, ccor);
  enviar_sprite_para_tela(0, SY);
}
