#ifndef PACK_ROLE_GESTURE_WHISTLE_H
#define PACK_ROLE_GESTURE_WHISTLE_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

enum Role {
  ROLE_UNKNOWN = 0,
  ROLE_GOALIE = 1,
  ROLE_DEFENDER = 2,
  ROLE_MIDFIELDER = 3,
  ROLE_STRIKER = 4,
  ROLE_SUPPORTER = 5,
};

enum Gesture {
  GESTURE_NONE = 0,
  GESTURE_RAISE_LEFT = 1,
  GESTURE_RAISE_RIGHT = 2,
  GESTURE_BOTH_HANDS = 3,
  GESTURE_POINT_LEFT = 4,
  GESTURE_POINT_RIGHT = 5,
};

#define RGW_PROTOCOL_VERSION 1
#define RGW_CUSTOM_SIZE 8

/*
 * 按 little-endian 打包 8 字节：
 * [0] version
 * [1] role
 * [2] gesture
 * [3] whistle(0/1)
 * [4] confidence(0..100)
 * [5] reserved(0)
 * [6..7] eventAgeMs (uint16 little-endian, 建议 <= 32767)
 */
static inline void pack_role_gesture_whistle(
    uint8_t out[RGW_CUSTOM_SIZE],
    uint8_t role,
    uint8_t gesture,
    uint8_t whistle,
    uint8_t confidence,
    uint16_t eventAgeMs)
{
  if(confidence > 100) confidence = 100;
  if(eventAgeMs > 32767) eventAgeMs = 32767;

  out[0] = RGW_PROTOCOL_VERSION;
  out[1] = role;
  out[2] = gesture;
  out[3] = whistle ? 1 : 0;
  out[4] = confidence;
  out[5] = 0;
  out[6] = (uint8_t)(eventAgeMs & 0xFF);
  out[7] = (uint8_t)((eventAgeMs >> 8) & 0xFF);
}

#ifdef __cplusplus
}
#endif

#endif
