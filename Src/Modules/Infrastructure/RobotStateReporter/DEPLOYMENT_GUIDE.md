# RobotStateReporter 部署指南（SimRobot）

## 快速开始（5 分钟）

### 步骤 1: 复制模块到 B-Human 源码

```bash
# 假设 B-Human 源码在 /path/to/bhuman
# 假设当前在 RobotMonitoringSystem 目录

cp -r bhuman_integration/RobotStateReporter_SimRobot \
      /path/to/bhuman/Src/Modules/Infrastructure/RobotStateReporter
```

### 步骤 2: 复制配置文件

```bash
cp bhuman_integration/RobotStateReporter_SimRobot/RobotStateReporter.cfg \
   /path/to/bhuman/Config/Modules/
```

### 步骤 3: 注册模块

**编辑: `/path/to/bhuman/Config/Scenarios/Default/modules.cfg`**

在文件末尾添加（Cognition 线程部分）:

```
module RobotStateReporter
```

完整示例:
```
# Cognition thread modules
module CameraProvider
module ImageProcessor
module BallPerceptor
# ... 其他模块 ...
module BehaviorControl
module RobotStateReporter  # <-- 添加在这里
```

### 步骤 4: 编译 B-Human

```bash
cd /path/to/bhuman
make
```

### 步骤 5: 启动 Monitor Daemon

```bash
cd RobotMonitoringSystem/monitor_daemon
python3 daemon.py --port 10020 --log-dir ./logs
```

应该看到:
```
[MonitorDaemon] Listening on 0.0.0.0:10020
[MonitorDaemon] Log directory: ./logs
[MonitorDaemon] Started successfully
```

### 步骤 6: 启动 SimRobot

```bash
cd /path/to/bhuman
./Build/Linux/SimRobot/Develop/SimRobot Config/Scenes/Default.ros2
```

在 SimRobot 中:
1. 加载场景
2. 启动机器人 (Ctrl+R)
3. 开始比赛 (使用 GameController)

### 步骤 7: 验证

Monitor Daemon 应该输出:
```
[STATS] Packets: 30, Rate: 3.0/s, Dropped: 0, Errors: 0
[INFO] Robot 1_1: behavior=searchForBall, fallen=false
```

---

## 详细配置

### 模块参数说明

**enabled**: 是否启用监控
- `true`: 启用（默认）
- `false`: 禁用（零开销）

**monitorAddress**: Monitor Daemon 地址
- SimRobot 本地: `"127.0.0.1"`
- 真机 WiFi: `"192.168.1.100"` (替换为 PC 的 IP)
- 多播: `"239.0.0.1"` (支持多个 Daemon)

**monitorPort**: UDP 端口
- 默认: `10020`
- 确保与 Monitor Daemon 一致

**reportIntervalFrames**: 上报间隔
- `5`: 6Hz（高频，适合调试）
- `10`: 3Hz（推荐，平衡性能和实时性）
- `30`: 1Hz（低频，最小开销）

**detectEvents**: 事件检测
- `true`: 检测行为切换、摔倒等事件
- `false`: 只上报状态，不检测事件

### 不同场景的配置

**场景 1: SimRobot 本地测试**

```cfg
enabled = true;
monitorAddress = "127.0.0.1";
monitorPort = 10020;
reportIntervalFrames = 10;
detectEvents = true;
```

**场景 2: 真机 WiFi 网络**

```cfg
enabled = true;
monitorAddress = "192.168.1.100";  # PC 的 IP
monitorPort = 10020;
reportIntervalFrames = 10;
detectEvents = true;
```

**场景 3: 禁用监控（比赛模式）**

```cfg
enabled = false;
```

---

## 调试技巧

### 1. 验证模块是否加载

在 SimRobot 控制台中:
```
mr RobotStateReporter
```

应该输出模块参数。

### 2. 查看网络数据包

```bash
# 监听 UDP 端口
sudo tcpdump -i lo -n udp port 10020 -A

# 应该看到 JSON 数据包
```

### 3. 手动测试 Monitor Daemon

```bash
# 发送测试数据
echo '{"timestamp":1000,"robot_id":"1_1","behavior":"test"}' | nc -u 127.0.0.1 10020
```

Monitor Daemon 应该接收并显示。

### 4. 检查日志文件

比赛结束后:
```bash
ls -la monitor_daemon/logs/
# 应该看到 match_YYYYMMDD_HHMMSS/ 目录

head -n 5 monitor_daemon/logs/match_*/robot_1_1.jsonl
# 应该看到 JSON Lines 格式的日志
```

---

## 常见问题

### Q1: 编译失败，找不到 TypeRegistry

**原因**: B-Human 版本不同，API 可能有差异

**解决**: 检查 B-Human 版本，调整代码中的 API 调用

### Q2: Monitor Daemon 收不到数据

**检查清单**:
1. `enabled = true` 是否设置
2. 地址和端口是否匹配
3. 防火墙是否阻止 UDP 10020
4. SimRobot 是否真的启动了机器人

**调试**:
```bash
# 检查 SimRobot 是否发送数据
sudo tcpdump -i lo -n udp port 10020
```

### Q3: SimRobot 运行变慢

**原因**: 上报频率过高或网络阻塞

**解决**:
1. 增加 `reportIntervalFrames` (如改为 30)
2. 检查 Monitor Daemon 是否正常运行
3. 临时禁用监控: `enabled = false`

### Q4: 日志文件未生成

**原因**: 比赛未正常结束（未到达 FINISHED 状态）

**解决**: 确保比赛正常结束，或手动停止 Monitor Daemon

---

## 性能指标

- **CPU 开销**: < 0.5% (Cognition 线程)
- **内存开销**: < 5 MB
- **网络带宽**: ~3 KB/s per robot (3Hz)
- **延迟**: < 5ms (UDP 发送)

---

## 下一步

- 阅读 [SIMROBOT_INTEGRATION_GUIDE.md](../../docs/SIMROBOT_INTEGRATION_GUIDE.md) 了解详细原理
- 查看 [INTEGRATION_GUIDE.md](../../docs/INTEGRATION_GUIDE.md) 了解真机部署
- 使用 [analysis_tools/](../../analysis_tools/) 分析日志
