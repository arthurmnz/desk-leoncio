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
const char* const TOPICO         = "desk/bot/state";
const char* const TOPICO_STATE   = "desk/bot/state";
const char* const TOPICO_WEATHER = "desk/bot/weather";
const char* const TOPICO_TIME    = "desk/bot/time";
const char* const TOPICO_TOUCH   = "desk/bot/touch";

// ---------------------------------------------------------------------------
// Pinos de Hardware
// ---------------------------------------------------------------------------
#define PIN_TOUCH_CS 5

// ---------------------------------------------------------------------------
// Máquina de Estados da Tela / Modos Visuais
// ---------------------------------------------------------------------------
enum DisplayMode {
  MODE_EYES = 0,       // Modo 0: Olhos Expressivos
  MODE_WEATHER = 1,    // Modo 1: Dashboard Clima & Relógio
  MODE_PC_STATUS = 2,  // Modo 2: Status do PC & Vitalidade
  MODE_MAX = 3
};

// Temporizações de Toque e Interface (ms)
const unsigned long TOUCH_DEBOUNCE_MS    = 40;
const unsigned long TOUCH_LONG_PRESS_MS = 1500;
const unsigned long TOUCH_RATE_LIMIT_MS = 250;
const unsigned long DASHBOARD_TIMEOUT_MS = 30000;


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
