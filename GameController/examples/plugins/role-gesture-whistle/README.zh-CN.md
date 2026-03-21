# TCM 插件方案：角色 / 手势 / 口哨

这个示例是**方案草案 + 代码骨架**，用于评估与快速落地：

- 在机器人信息卡片显示：角色、手势识别、口哨检测
- 可选：在 3D 视图叠加简单文本提示
- 不改 TeamCommunicationMonitor 主逻辑，仅使用插件机制

## 可行性结论

可行，前提是机器人端将对应字段写入 team message 的 `data` 自定义字节区。

## 推荐字段协议（v1）

按小端序（Little Endian），固定长度 8 字节：

- `byte version`：协议版本，当前 `1`
- `byte role`：角色枚举
- `byte gesture`：手势枚举
- `byte whistle`：口哨状态（0=无，1=检测到）
- `byte confidence`：0~100
- `byte reserved`：保留
- `short eventAgeMs`：事件距今毫秒（0~32767）

> 说明：`eventAgeMs` 可用于界面端做“最近事件”显示与超时清空。

## 枚举建议

- Role
  - `0 Unknown`
  - `1 Goalie`
  - `2 Defender`
  - `3 Midfielder`
  - `4 Striker`
  - `5 Supporter`
- Gesture
  - `0 None`
  - `1 RaiseLeft`
  - `2 RaiseRight`
  - `3 BothHands`
  - `4 PointLeft`
  - `5 PointRight`

## 插件文件结构

- `src/com/example/tcmplugin/RoleGestureWhistleMessage.java`
- `src/com/example/tcmplugin/RoleGestureWhistleOverlay.java`（可选）
- `src/com/example/tcmplugin/RoleGestureWhistleDetailFrame.java`（详情卡片扩展）
- `src/com/example/tcmplugin/TeamUniformOverlay.java`（5/70 队服颜色叠加）
- `robot_side/pack_role_gesture_whistle.py`（机器人端 Python 打包模板）
- `robot_side/pack_role_gesture_whistle.h`（机器人端 C/C++ 打包模板）

将编译后的 jar 放到：

- `plugins/<team number>/your-plugin.jar`

TCM 会在该队伍出现时动态加载。

## 编译示例

在本目录执行：

- `javac -encoding UTF-8 -cp ../../../../TeamCommunicationMonitor.jar:../../../../plugins/common.jar -d out $(find src -name "*.java")`
- `jar cf role-gesture-whistle-plugin.jar -C out .`

或直接一键执行：

- `./build_plugin.sh`

然后复制到：

- `plugins/<team number>/role-gesture-whistle-plugin.jar`

或直接部署：

- `./deploy_plugin.sh <team_number>`

## 联调建议

1. 先只实现消息类 `RoleGestureWhistleMessage`，验证卡片显示正确。
2. 再加 `RoleGestureWhistleOverlay`，仅做轻量叠加文字。
3. 统一机器人端编码与插件端解码（version + little-endian）。
4. 字段超时建议：若 `eventAgeMs > 3000`，显示为“无”。

> 当前仓库内示例已将 Overlay 设为“不渲染场地文本”，并通过
> `RoleGestureWhistleDetailFrame` 在详情窗口显示角色/手势/口哨字段。
>
> 另外新增 `TeamUniformOverlay`：队号 `5` 叠加黑色队服效果，队号 `70`
> 叠加黄色队服效果（半透明色块）。

## 机器人端发送模板

### Python

见 `robot_side/pack_role_gesture_whistle.py`，核心接口：

- `pack_custom_data(role, gesture, whistle_detected, confidence, event_age_ms)`

返回固定 8 字节，可直接写入你们的 team message 自定义 `data`。

### C/C++

见 `robot_side/pack_role_gesture_whistle.h`，核心接口：

- `pack_role_gesture_whistle(out, role, gesture, whistle, confidence, eventAgeMs)`

把 `out[8]` 拷贝到你们消息体的自定义数据区即可。
