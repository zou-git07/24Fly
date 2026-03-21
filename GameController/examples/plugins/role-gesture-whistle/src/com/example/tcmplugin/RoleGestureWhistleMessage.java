package com.example.tcmplugin;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;

import teamcomm.data.AdvancedMessage;

/**
 * 机器人自定义消息解析示例：角色 + 手势 + 口哨。
 *
 * 注意：
 * 1) 仅示例骨架，需与机器人端发送格式保持一致。
 * 2) 该类会被 TCM 当作团队消息类加载。
 */
public class RoleGestureWhistleMessage extends AdvancedMessage {

    private static final int MIN_SIZE = 8;

    private int version = 0;
    private int role = 0;
    private int gesture = 0;
    private int whistle = 0;
    private int confidence = 0;
    private int eventAgeMs = 0;

    @Override
    public void init() {
        // 默认值
        version = 0;
        role = 0;
        gesture = 0;
        whistle = 0;
        confidence = 0;
        eventAgeMs = 0;

        if (data == null || data.length < MIN_SIZE) {
            return;
        }

        final ByteBuffer bb = ByteBuffer.wrap(data).order(ByteOrder.LITTLE_ENDIAN);
        version = u8(bb.get());
        role = u8(bb.get());
        gesture = u8(bb.get());
        whistle = u8(bb.get());
        confidence = u8(bb.get());
        bb.get(); // reserved
        eventAgeMs = u16(bb.getShort());
    }

    @Override
    public String[] display() {
        final String roleText = roleToText(role);
        final String gestureText = gestureToText(gesture);
        final String whistleText = whistle > 0 ? "检测到" : "无";

        return new String[] {
            "角色: " + roleText,
            "手势: " + gestureText,
            "口哨: " + whistleText,
            "置信度: " + confidence + "%",
            "事件年龄: " + eventAgeMs + " ms",
            "协议版本: v" + version,
        };
    }

    private static int u8(byte b) {
        return b & 0xFF;
    }

    private static int u16(short s) {
        return s & 0xFFFF;
    }

    private static String roleToText(int v) {
        switch (v) {
            case 1:
                return "守门员";
            case 2:
                return "后卫";
            case 3:
                return "中场";
            case 4:
                return "前锋";
            case 5:
                return "支援";
            default:
                return "未知";
        }
    }

    private static String gestureToText(int v) {
        switch (v) {
            case 1:
                return "左手举起";
            case 2:
                return "右手举起";
            case 3:
                return "双手举起";
            case 4:
                return "指向左侧";
            case 5:
                return "指向右侧";
            default:
                return "无";
        }
    }
}
