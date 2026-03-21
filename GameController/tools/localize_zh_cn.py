#!/usr/bin/env python3
"""
将 GameController 工具链中的界面英文文案替换为中文（仅替换 class 常量池字符串，不改业务逻辑）。

用法：
  python3 tools/localize_zh_cn.py
"""

from __future__ import annotations

import io
import struct
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JARS = [
    ROOT / "TeamCommunicationMonitor.jar",
    ROOT / "EventRecorder.jar",
    ROOT / "GameControllerTester.jar",
    ROOT / "LogExporter.jar",
]

TRANSLATIONS = {
    # 主菜单 / 窗口
    "File": "文件",
    "View": "视图",
    "Exit": "退出",
    "Reset": "重置",
    "Replay log file": "回放日志文件",
    "Switch to GameStateVisualizer": "切换到比赛状态可视化",
    "Mirror": "镜像",
    "Drawings": "渲染",
    "Markdown View": "Markdown 视图",
    "View as MarkDown": "以 Markdown 查看",
    "Save as MarkDown": "另存为 Markdown",
    "Save Before Exit Dialog": "退出前保存",

    # 程序标题/状态提示
    "TeamCommunicationMonitor": "队伍通信监视器",
    "GameController": "比赛控制器",
    "GameStateVisualizer": "比赛状态可视化",
    "Waiting for messages from the GameController...": "正在等待来自比赛控制器的消息...",
    "Connected to GameController!": "已连接到比赛控制器！",
    "No active GameController in network.": "网络中未发现活动的比赛控制器。",
    "Error while setting up GameController listener.": "设置比赛控制器监听器时出错。",

    # 通用字段
    "Player #": "球员 #",

    # 渲染/回放相关可见文案
    "Paused": "已暂停",
    "Rewinding": "回退中",
    "Fast forward ": "快速前进 ",
    "Fast rewind ": "快速后退 ",
    "Messages: ": "消息：",
    "Team Messages: ": "队伍消息：",
    "GameController Return Messages: ": "比赛控制器回传消息：",
    "Per second: ": "每秒：",
}


def patch_class_bytes(data: bytes, table: dict[str, str]) -> tuple[bytes, int]:
    if len(data) < 10 or data[:4] != b"\xCA\xFE\xBA\xBE":
        return data, 0

    buf = bytearray(data)
    cp_count = struct.unpack(">H", buf[8:10])[0]
    i = 10
    idx = 1
    patches: list[tuple[int, int, bytes]] = []

    while idx < cp_count and i < len(buf):
        tag = buf[i]
        i += 1

        if tag == 1:  # CONSTANT_Utf8
            if i + 2 > len(buf):
                break
            length = struct.unpack(">H", buf[i:i + 2])[0]
            start = i + 2
            end = start + length
            if end > len(buf):
                break

            raw = bytes(buf[start:end])
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = None

            if text is not None and text in table:
                new_raw = table[text].encode("utf-8")
                patches.append((i, length, new_raw))

            i = end

        elif tag in (3, 4):
            i += 4
        elif tag in (5, 6):
            i += 8
            idx += 1
        elif tag in (7, 8, 16, 19, 20):
            i += 2
        elif tag in (9, 10, 11, 12, 18):
            i += 4
        elif tag == 15:
            i += 3
        else:
            break

        idx += 1

    if not patches:
        return data, 0

    shift = 0
    replaced = 0
    for length_pos, old_len, new_raw in patches:
        pos = length_pos + shift
        old_start = pos + 2
        old_end = old_start + old_len

        buf[pos:pos + 2] = struct.pack(">H", len(new_raw))
        buf[old_start:old_end] = new_raw

        shift += len(new_raw) - old_len
        replaced += 1

    return bytes(buf), replaced


def patch_jar(path: Path, table: dict[str, str]) -> tuple[int, int]:
    if not path.exists():
        return 0, 0

    backup = path.with_suffix(path.suffix + ".bak")
    if not backup.exists():
        backup.write_bytes(path.read_bytes())

    patched_entries = 0
    replaced_strings = 0

    with zipfile.ZipFile(path, "r") as zin:
        items = zin.infolist()
        payloads: list[tuple[zipfile.ZipInfo, bytes]] = []

        for info in items:
            data = zin.read(info.filename)
            if info.filename.endswith(".class"):
                new_data, count = patch_class_bytes(data, table)
                data = new_data
                if count:
                    patched_entries += 1
                    replaced_strings += count
            payloads.append((info, data))

    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with zipfile.ZipFile(tmp_path, "w") as zout:
        for info, data in payloads:
            out_info = zipfile.ZipInfo(filename=info.filename, date_time=info.date_time)
            out_info.compress_type = info.compress_type
            out_info.comment = info.comment
            out_info.extra = info.extra
            out_info.internal_attr = info.internal_attr
            out_info.external_attr = info.external_attr
            out_info.create_system = info.create_system
            out_info.create_version = info.create_version
            out_info.extract_version = info.extract_version
            out_info.flag_bits = info.flag_bits
            zout.writestr(out_info, data)

    tmp_path.replace(path)
    return patched_entries, replaced_strings


def main() -> None:
    print("开始替换界面文案（中文）...")
    total_entries = 0
    total_replaced = 0

    for jar in JARS:
        entries, replaced = patch_jar(jar, TRANSLATIONS)
        total_entries += entries
        total_replaced += replaced
        if jar.exists():
            print(f"- {jar.name}: 修改 {entries} 个 class，替换 {replaced} 处文案")
        else:
            print(f"- {jar.name}: 未找到，跳过")

    print(f"完成。共修改 {total_entries} 个 class，替换 {total_replaced} 处文案。")
    print("已自动生成 .bak 备份文件。")


if __name__ == "__main__":
    main()
