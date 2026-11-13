#ifndef DESKBOT_CONFIG_H
#define DESKBOT_CONFIG_H

#include <stdint.h>
#ifdef ARDUINO
#include <Arduino.h>
#endif

// ---------------------------------------------------------------------------
// Parâmetros de Rede e MQTT
// ---------------------------------------------------------------------------
const int   MQTT_PORT = 1883;
const char* const TOPICO = "desk/bot/state";

// ---------------------------------------------------------------------------
// Dimensões e Posicionamento do Display (ILI9341 / 320x240)
// Faixa da tela onde ficam os olhos (desenhada num sprite para evitar flicker)
// ---------------------------------------------------------------------------
const int SW = 320;
const int SH = 140;
const int SY = 50;
const int CY = SH / 2;
const int CX_ESQ = 90;
const int CX_DIR = 230;

#define BG 0x0000

#endif // DESKBOT_CONFIG_H
