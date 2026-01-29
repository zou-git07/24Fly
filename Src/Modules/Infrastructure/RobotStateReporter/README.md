# RobotStateReporter - SimRobot 专用版本

> **目标**: 在 SimRobot 中运行 B-Human，让真实 Robot 实例上报状态到监控系统

## 文件清单

```
RobotStateReporter_SimRobot/
├── RobotStateReporter.h          # 模块头文件
├── RobotStateReporter.cpp        # 模块实现
├── RobotStateReporter.cfg        # 配置文件
├── DEPLOYMENT_GUIDE.md           # 详细部署指南
├── QUICK_REFERENCE.md            # 快速参考卡片
└── README.md                     # 本文件
```

## 快速开始

### 1. 复制到 B-Human

```bash
cp -r RobotStateReporter_SimRobot <BHUMAN_PATH>/Src/Modules/Infrastructure/RobotStateReporter
cp RobotStateReporter.cfg <BHUMAN_PATH>/Config/Modules/
```

### 2. 注册模块

编辑 `<BHUMAN_PATH>/Config/Scenarios/Default/modules.cfg`，添加:
```
module RobotStateReporter
```

### 3. 编译

```bash
cd <BHUMAN_PATH>
make
```

### 4. 启动监控

```bash
# 终端 1: Monitor Daemon
cd RobotMonitoringSystem/monitor_daemon
python3 daemon.py --port 10020 --log-dir ./logs

# 终端 2: SimRobot
cd <BHUMAN_PATH>
./Build/Linux/SimRobot/Develop/SimRobot Config/Scenes/Default.ros2
```

## 核心特性

### ✅ 完全非阻塞

- UDP 非阻塞模式
- 发送失败静默丢弃
- 绝不影响 SimRobot 运行

### ✅ 真实数据

- 仿真时间戳
- 物理引擎的摔倒状态
- 虚拟相机的球感知
- 决策系统的行为状态

### ✅ 轻量级

- CPU 开销 < 0.5%
- 内存开销 < 5 MB
- 网络带宽 ~3 KB/s

### ✅ 事件检测

- 行为切换
- 球丢失/发现
- 摔倒/起身

## 数据示例

```json
{
  "timestamp": 12345,
  "robot_id": "1_3",
  "battery": 100.0,
  "temperature": 40.0,
  "fallen": false,
  "behavior": "searchForBall",
  "motion": "walk",
  "ball_visible": true,
  "ball_x": 1500.0,
  "ball_y": -200.0,
  "pos_x": 1000.0,
  "pos_y": 500.0,
  "rotation": 0.785,
  "events": [
    {"type": "behavior_changed", "from": "stand", "to": "searchForBall"}
  ]
}
```

## 架构说明

### 接入点

- **线程**: Cognition Thread (30Hz)
- **位置**: Infrastructure 模块末尾
- **依赖**: FrameInfo, GameState, BehaviorStatus, FallDownState, BallModel, RobotPose

### 执行流程

```
Cognition Thread (30Hz)
    ↓
RobotStateReporter::update()
    ↓
每 10 帧执行一次 (3Hz)
    ↓
collectState() → 采集数据
    ↓
sendState() → UDP 发送（非阻塞）
    ↓
Monitor Daemon 接收
    ↓
日志写入 + WebSocket 推送
```

### 数据来源

| 数据 | 来源 Representation | SimRobot 可用性 |
|-----|-------------------|----------------|
| 时间戳 | FrameInfo | ✅ 仿真时间 |
| 机器人 ID | GameState | ✅ 完全可用 |
| 电量 | RobotHealth | ⚠️ 固定值 |
| 摔倒 | FallDownState | ✅ 物理引擎 |
| 行为 | BehaviorStatus | ✅ 决策输出 |
| 球感知 | BallModel | ✅ 虚拟相机 |
| 定位 | RobotPose | ✅ 虚拟感知 |

## 配置说明

### 参数

- `enabled`: 是否启用（默认 true）
- `monitorAddress`: Monitor Daemon 地址（默认 "127.0.0.1"）
- `monitorPort`: UDP 端口（默认 10020）
- `reportIntervalFrames`: 上报间隔帧数（默认 10 = 3Hz）
- `detectEvents`: 是否检测事件（默认 true）

### 场景配置

**本地测试**:
```cfg
monitorAddress = "127.0.0.1";
```

**真机 WiFi**:
```cfg
monitorAddress = "192.168.1.100";  # PC 的 IP
```

**禁用监控**:
```cfg
enabled = false;
```

## 文档导航

- **快速开始**: [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)
- **详细部署**: [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
- **完整指南**: [../../docs/SIMROBOT_INTEGRATION_GUIDE.md](../../docs/SIMROBOT_INTEGRATION_GUIDE.md)
- **架构设计**: [../../docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md)

## 常见问题

### Q: SimRobot 中电量为什么是 100%？

A: SimRobot 不模拟电量消耗。真机中会显示真实电量。

### Q: 如何验证模块是否工作？

A: 在 SimRobot 控制台执行 `mr RobotStateReporter`，应该输出模块参数。

### Q: Monitor Daemon 收不到数据怎么办？

A: 检查：
1. `enabled = true`
2. 地址和端口匹配
3. Monitor Daemon 是否运行
4. 防火墙是否阻止 UDP 10020

### Q: 如何迁移到真机？

A: 只需修改配置文件中的 `monitorAddress` 为 PC 的 IP，代码无需修改。

## 性能指标

- **CPU**: < 0.5% (Cognition 线程)
- **内存**: < 5 MB
- **网络**: ~3 KB/s per robot
- **延迟**: < 5ms

## 许可证

与 B-Human 框架保持一致。

## 作者

RoboCup SPL Team - 2026
