package com.example.tcmplugin;

import com.jogamp.opengl.GL2;

import data.GameControlReturnData;
import teamcomm.PluginLoader;
import teamcomm.data.RobotState;
import teamcomm.gui.Camera;
import teamcomm.gui.drawings.Drawing;
import teamcomm.gui.drawings.PerPlayer;
import teamcomm.gui.drawings.RoSi2Loader;

import java.util.Collection;
import java.util.HashSet;
import java.util.Set;

/**
 * 队服颜色叠加渲染：
 * - 队号 5 -> 黑色
 * - 队号 70 -> 黄色
 */
public class TeamUniformOverlay extends PerPlayer {

    private static final Set<Integer> disabledBaseTeams = new HashSet<>();

    @Override
    protected void init(GL2 gl) {
        RoSi2Loader.getInstance().cacheModels(gl, "robotBlack", "robotYellow");
    }

    @Override
    public boolean hasAlpha() {
        return true;
    }

    @Override
    public int getPriority() {
        return 0;
    }

    @Override
    public void draw(GL2 gl, RobotState robot, Camera camera) {
        if (robot == null) {
            return;
        }

        final int team = robot.getTeamNumber();
        final String model = modelForTeam(team);
        if (model == null) {
            return;
        }

        disableBasePlayerIfNeeded(team);

        final GameControlReturnData gcrd = robot.getLastGCRDMessage();
        if (gcrd == null || !gcrd.poseValid) {
            return;
        }

        // 与原 Player 渲染保持一致的位姿变换逻辑
        final float x = gcrd.pose[0] / 1000f;
        final float y = gcrd.pose[1] / 1000f;
        final float thetaDeg = (float) Math.toDegrees(gcrd.pose[2]);

        gl.glPushMatrix();
        try {
            gl.glTranslatef(x, y, 0f);
            gl.glRotatef(thetaDeg, 0f, 0f, 1f);

            if (gcrd.fallenValid && gcrd.fallen) {
                gl.glTranslatef(0f, 0f, 0.05f);
                gl.glRotatef(90f, 0f, 1f, 0f);
            }

            gl.glCallList(RoSi2Loader.getInstance().loadModel(gl, model));
        } finally {
            gl.glPopMatrix();
        }
    }

    private static String modelForTeam(int team) {
        if (team == 5) {
            return "robotBlack";
        }
        if (team == 70) {
            return "robotYellow";
        }
        return null;
    }

    private static void disableBasePlayerIfNeeded(int team) {
        if (disabledBaseTeams.contains(team)) {
            return;
        }
        final Collection<Drawing> drawings = PluginLoader.getInstance().getDrawings(team);
        for (Drawing d : drawings) {
            if (d.getClass().getName().equals("teamcomm.gui.drawings.common.Player")) {
                d.setActive(false);
            }
        }
        disabledBaseTeams.add(team);
    }
}
