package com.example.tcmplugin;

import java.awt.Component;
import java.awt.Container;
import java.util.ArrayList;
import java.util.List;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.SwingUtilities;

import data.SPLTeamMessage;
import teamcomm.data.RobotState;
import teamcomm.data.event.RobotStateEvent;
import teamcomm.gui.RobotDetailFrame;

/**
 * 自定义详情卡片：在默认详情窗口底部增加“角色/手势/口哨”信息。
 *
 * 说明：
 * - 不依赖 AdvancedMessage 是否成功接管。
 * - 直接从最后一条 team message 的 data 中按约定 8 字节协议解码。
 */
public class RoleGestureWhistleDetailFrame extends RobotDetailFrame {

    private static final long serialVersionUID = 1L;
    private static final int MIN_SIZE = 8;

    private final JPanel anchor;
    private JLabel roleLabel;
    private JLabel gestureLabel;
    private JLabel whistleLabel;
    private JLabel ageLabel;

    public RoleGestureWhistleDetailFrame(RobotState robot, JPanel anchor) {
        super(robot, anchor);
        this.anchor = anchor;
    }

    @Override
    protected void init(RobotState robot) {
        // 该窗口不显示；仅作为对 RobotPanel 的扩展载体。
        setUndecorated(true);
        setVisible(false);

        final JPanel foreground = findForegroundPanel(anchor);
        if (foreground != null) {
            roleLabel = new JLabel("角色: 无数据", JLabel.CENTER);
            gestureLabel = new JLabel("手势: 无数据", JLabel.CENTER);
            whistleLabel = new JLabel("口哨: 无数据", JLabel.CENTER);
            ageLabel = new JLabel("距今: 无数据", JLabel.CENTER);

            foreground.add(roleLabel);
            foreground.add(gestureLabel);
            foreground.add(whistleLabel);
            foreground.add(ageLabel);
            foreground.revalidate();
            foreground.repaint();
        }

        updateLabels(robot);
    }

    @Override
    public void robotStateChanged(RobotStateEvent event) {
        SwingUtilities.invokeLater(() -> updateLabels((RobotState) event.getSource()));
    }

    @Override
    public void connectionStatusChanged(RobotStateEvent event) {
        // no-op
    }

    private void updateLabels(RobotState robot) {
        if (roleLabel == null || gestureLabel == null || whistleLabel == null || ageLabel == null) {
            return;
        }

        final SPLTeamMessage msg = robot.getLastTeamMessage();
        if (msg == null || msg.data == null || msg.data.length < MIN_SIZE) {
            roleLabel.setText("角色: 无数据");
            gestureLabel.setText("手势: 无数据");
            whistleLabel.setText("口哨: 无数据");
            ageLabel.setText("距今: 无数据");
            return;
        }

        final byte[] d = msg.data;
        final int version = u8(d[0]);
        final int role = u8(d[1]);
        final int gesture = u8(d[2]);
        final int whistle = u8(d[3]);
        final int confidence = u8(d[4]);
        final int eventAgeMs = u16le(d[6], d[7]);

        roleLabel.setText("角色: " + roleToText(role));
        gestureLabel.setText("手势: " + gestureToText(gesture));
        whistleLabel.setText("口哨: " + (whistle > 0 ? "检测到" : "无")
            + "  置信度: " + confidence + "%  v" + version);
        ageLabel.setText("距今: " + eventAgeMs + " ms");
    }

    private static JPanel findForegroundPanel(Container root) {
        final List<JLabel> labels = new ArrayList<>();
        final JPanel[] hit = new JPanel[1];
        dfs(root, labels, hit);
        return hit[0];
    }

    private static void dfs(Container c, List<JLabel> labels, JPanel[] hit) {
        if (hit[0] != null) {
            return;
        }
        if (c instanceof JPanel) {
            labels.clear();
            for (Component child : c.getComponents()) {
                if (child instanceof JLabel) {
                    labels.add((JLabel) child);
                }
            }
            if (labels.size() == 4) {
                hit[0] = (JPanel) c;
                return;
            }
        }
        for (Component child : c.getComponents()) {
            if (child instanceof Container) {
                dfs((Container) child, labels, hit);
            }
        }
    }

    private static int u8(byte b) {
        return b & 0xFF;
    }

    private static int u16le(byte lo, byte hi) {
        return (u8(hi) << 8) | u8(lo);
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
