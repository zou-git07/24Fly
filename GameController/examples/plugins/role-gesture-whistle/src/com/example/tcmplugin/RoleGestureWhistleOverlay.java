package com.example.tcmplugin;

import com.jogamp.opengl.GL2;

import teamcomm.data.RobotState;
import teamcomm.gui.Camera;
import teamcomm.gui.drawings.PerPlayer;

/**
 * 可选：在 3D 视图给每个机器人叠加简要标签。
 *
 * 说明：
 * - 该实现尽量轻量，仅演示入口。
 * - 如需显示真实 role/gesture/whistle，建议在此类中维护状态缓存，
 *   或从你们扩展消息对象中取值（按团队插件架构实现）。
 */
public class RoleGestureWhistleOverlay extends PerPlayer {

    @Override
    public boolean hasAlpha() {
        return true;
    }

    @Override
    public int getPriority() {
        // 比号码略高，避免被遮盖；可按效果微调。
        return 20;
    }

    @Override
    public void draw(GL2 gl, RobotState robot, Camera camera) {
        // 用户要求不要把信息绘制在场地上：此绘制项保留为占位，但不渲染任何内容。
    }
}
