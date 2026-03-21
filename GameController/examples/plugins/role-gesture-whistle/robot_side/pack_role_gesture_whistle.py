#!/usr/bin/env python3
"""机器人端示例：打包 role/gesture/whistle 8 字节自定义消息。

与 RoleGestureWhistleMessage.java 对齐：
- little-endian
- 固定 8 字节
"""

from __future__ import annotations

import struct
from enum import IntEnum


class Role(IntEnum):
    UNKNOWN = 0
    GOALIE = 1
    DEFENDER = 2
    MIDFIELDER = 3
    STRIKER = 4
    SUPPORTER = 5


class Gesture(IntEnum):
    NONE = 0
    RAISE_LEFT = 1
    RAISE_RIGHT = 2
    BOTH_HANDS = 3
    POINT_LEFT = 4
    POINT_RIGHT = 5


PROTOCOL_VERSION = 1
PACK_FMT = "<BBBBBBH"  # version, role, gesture, whistle, confidence, reserved, eventAgeMs


def clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def pack_custom_data(
    role: Role,
    gesture: Gesture,
    whistle_detected: bool,
    confidence: int,
    event_age_ms: int,
    version: int = PROTOCOL_VERSION,
) -> bytes:
    """返回长度为 8 的 bytes，可直接写入 team message 的 data 字段。"""
    confidence = clamp(int(confidence), 0, 100)
    event_age_ms = clamp(int(event_age_ms), 0, 32767)

    return struct.pack(
        PACK_FMT,
        int(version) & 0xFF,
        int(role) & 0xFF,
        int(gesture) & 0xFF,
        1 if whistle_detected else 0,
        confidence,
        0,  # reserved
        event_age_ms,
    )


if __name__ == "__main__":
    payload = pack_custom_data(
        role=Role.DEFENDER,
        gesture=Gesture.RAISE_LEFT,
        whistle_detected=True,
        confidence=92,
        event_age_ms=180,
    )
    print("payload_len=", len(payload))
    print("payload_hex=", payload.hex())
