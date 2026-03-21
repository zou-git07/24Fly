#!/usr/bin/env python3
"""调试工具：解码 8 字节 payload，验证与 TCM 插件协议一致。"""

from __future__ import annotations

import struct
import sys

FMT = "<BBBBBBH"


def decode(hex_payload: str):
    raw = bytes.fromhex(hex_payload)
    if len(raw) != 8:
        raise ValueError(f"payload 长度必须为 8 字节，当前 {len(raw)}")
    version, role, gesture, whistle, confidence, _reserved, event_age_ms = struct.unpack(FMT, raw)
    return {
        "version": version,
        "role": role,
        "gesture": gesture,
        "whistle": whistle,
        "confidence": confidence,
        "event_age_ms": event_age_ms,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 unpack_role_gesture_whistle.py <hex_payload>")
        print("示例: python3 unpack_role_gesture_whistle.py 010201015c00b400")
        sys.exit(1)

    result = decode(sys.argv[1].strip())
    for k, v in result.items():
        print(f"{k}: {v}")
