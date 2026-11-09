#include <Arduino_RouterBridge.h>
#include <Arduino_LED_Matrix.h>

Arduino_LED_Matrix matrix;
const int BUTTON_PIN = 2;            // pushbutton (or jumper wire) from D2 to GND = firewall switch

volatile int state = 0;              // 0 safe, 1 alert, 2 blocked, 3 firewall off
volatile int attack = 0;             // 0 none, 1 jam, 2 spoof, 3 ddos, 4 scan
volatile int level = 0;              // packets/s into the board, 0..8 (log scale), sent by Linux
volatile int presses = 0;            // button presses since boot, read by Linux
volatile uint32_t lastMsg = 0;       // millis() of the last wsentry_show call (watchdog)

uint8_t frame[104];                  // 8 rows x 13 columns, row-major
uint8_t hist[13];                    // bar-graph history, one column per 250 ms

struct Glyph { char c; uint8_t rows[5]; };   // 3x5 font, bit 2 = left column
const Glyph FONT[] = {
  {'A', {2, 5, 7, 5, 5}}, {'B', {6, 5, 6, 5, 6}}, {'C', {3, 4, 4, 4, 3}}, {'D', {6, 5, 5, 5, 6}},
  {'E', {7, 4, 6, 4, 7}}, {'F', {7, 4, 6, 4, 4}}, {'J', {1, 1, 1, 5, 2}}, {'K', {5, 5, 6, 5, 5}},
  {'L', {4, 4, 4, 4, 7}}, {'M', {5, 7, 7, 5, 5}}, {'N', {6, 5, 5, 5, 5}}, {'O', {2, 5, 5, 5, 2}},
  {'P', {6, 5, 6, 4, 4}}, {'S', {3, 4, 2, 1, 6}}, {'!', {2, 2, 2, 0, 2}}, {' ', {0, 0, 0, 0, 0}},
};
const int FONT_N = sizeof(FONT) / sizeof(FONT[0]);
const char* ATTACK_NAME[] = {"", "JAM", "SPOOF", "DDOS", "SCAN"};

const uint8_t* glyph(char c) {
  for (int i = 0; i < FONT_N; i++) if (FONT[i].c == c) return FONT[i].rows;
  return FONT[FONT_N - 1].rows;                        // unknown -> space
}
void px(int r, int c) { if (r >= 0 && r < 8 && c >= 0 && c < 13) frame[r * 13 + c] = 1; }
void text(const char* s, int x) {                      // rows 1..5, 4 columns per character
  for (int i = 0; s[i]; i++, x += 4) {
    const uint8_t* g = glyph(s[i]);
    for (int r = 0; r < 5; r++)
      for (int c = 0; c < 3; c++)
        if (g[r] & (4 >> c)) px(r + 1, x + c);
  }
}
int textWidth(const char* s) { return (int)strlen(s) * 4 - 1; }
void bars() { for (int c = 0; c < 13; c++) for (int r = 0; r < hist[c]; r++) px(7 - r, c); }

void wsentry_show(int s, int a, int lv) {
  state = s; attack = (a >= 0 && a <= 4) ? a : 0; level = lv; lastMsg = millis();
}
int wsentry_presses() { return presses; }

void setup() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  matrix.begin();
  matrix.setGrayscaleBits(1);                          // on/off pixels
  Bridge.begin();
  Bridge.provide("wsentry_show", wsentry_show);
  Bridge.provide("wsentry_presses", wsentry_presses);
}

void loop() {
  static uint32_t lastShift = 0, lastScroll = 0;
  static int lowCount = 0, scroll = 13, prevKey = -1;
  static bool latched = false;
  uint32_t now = millis();

  if (digitalRead(BUTTON_PIN) == LOW) {                // pressed = LOW; count once per press,
    if (++lowCount >= 2 && !latched) { presses++; latched = true; }   // after 2 stable samples
  } else {
    lowCount = 0;
    latched = false;
  }

  // Watchdog: no update from Linux for 3 s means the detector is not running -> show OFF.
  int st = (now - lastMsg > 3000) ? 3 : state;
  int key = st * 8 + attack;                           // restart the scroll when the message changes
  if (key != prevKey) { scroll = 13; prevKey = key; }

  if (now - lastShift >= 250) {                        // advance the packets/s graph
    lastShift = now;
    memmove(hist, hist + 1, 12);
    hist[12] = level > 8 ? 8 : level;
  }

  memset(frame, 0, sizeof(frame));
  if (st == 3) {
    text("OFF", 1);                                    // firewall off (or detector down): static OFF
  } else if (st == 0) {
    if ((now / 1000) % 4 == 0) text("ON", 3);          // firewall on: flash ON every 4 s,
    else bars();                                       // otherwise the live packet graph
  } else {                                             // alert / blocked: scroll the attack name
    char msg[24];
    snprintf(msg, sizeof msg, st == 2 ? "%s BLOCKED" : "%s !", ATTACK_NAME[attack]);
    text(msg, scroll);
    if (now - lastScroll >= 110) { lastScroll = now; scroll--; }
    if (scroll < -textWidth(msg)) scroll = 13;
    if (st == 2 && (now / 300) % 2) for (int c = 0; c < 13; c++) px(0, c);   // blinking top bar
  }
  matrix.draw(frame);
  delay(30);
}
