# RobotStateReporter 快速参考

## 一键部署（复制粘贴）

```bash
# 1. 复制模块
cp -r RobotMonitoringSystem/bhuman_integration/RobotStateReporter_SimRobot \
      <BHUMAN_PATH>/Src/Modules/Infrastructure/RobotStateReporter

# 2. 复制配置
cp RobotMonitoringSystem/bhuman_integration/RobotStateReporter_SimRobot/RobotStateReporter.cfg \
   <BHUMAN_PATH>/Config/Modules/

# 3. 编辑模块列表
echo "module RobotStateReporter" >> <BHUMAN_PATH>/Config/Scenarios/Default/modules.cfg

# 4. 编译
cd <BHUMAN_PATH> && make

# 5. 启动 Monitor Daemon
cd RobotMonitoringSystem/monitor_daemon
python3 daemon.py --port 10020 --log-dir ./logs

# 6. 启动 SimRobot
cd <BHUMAN_PATH>
./Build/Linux/SimRobot/Develop/SimRobot Config/Scenes/Default.ros2
```

---

## 数据字段说明

### 基础字段

| 字段 | 类型 | 说明 | SimRobot 可用性 |
|-----|------|------|----------------|
| `timestamp` | int | 仿真时间（毫秒） | ✅ 完全可用 |
| `robot_id` | string | 机器人 ID（如 "1_3"） | ✅ 完全可用 |
| `battery` | float | 电量（0-100%） | ⚠️ 固定值 100 |
| `temperature` | float | 最高温度（℃） | ⚠️ 固定值 40 |
| `fallen` | bool | 是否摔倒 | ✅ 完全可用 |
| `behavior` | string | 当前行为 | ✅ 完全可用 |
| `motion` | string | 运动状态 | ✅ 完全可用 |

### 感知字段

| 字段 | 类型 | 说明 | SimRobot 可用性 |
|-----|------|------|----------------|
| `ball_visible` | bool | 球是否可见 | ✅ 完全可用 |
| `ball_x` | float | 球 X 坐标（mm） | ✅ 完全可用 |
| `ball_y` | float | 球 Y 坐标（mm） | ✅ 完全可用 |
| `pos_x` | float | 机器人 X 坐标（mm） | ✅ 完全可用 |
| `pos_y` | float | 机器人 Y 坐标（mm） | ✅ 完全可用 |
| `rotation` | float | 机器人朝向（弧度） | ✅ 完全可用 |

### 事件字段

| 事件类型 | 说明 |
|---------|------|
| `behavior_changed` | 行为切换 |
| `ball_found` | 发现球 |
| `ball_lost` | 球丢失 |
| `fallen` | 摔倒 |
| `got_up` | 起身 |

---

## 配置速查

### 本地测试（SimRobot）

```cfg
enabled = true;
monitorAddress = "127.0.0.1";
monitorPort = 10020;
reportIntervalFrames = 10;  # 3Hz
```

### 真机部署

```cfg
enabled = true;
monitorAddress = "192.168.1.100";  # 替换为 PC IP
monitorPort = 10020;
reportIntervalFrames = 10;
```

### 禁用监控

```cfg
enabled = false;
```

---

## 调试命令

### SimRobot 控制台

```
# 查看模块参数
mr RobotStateReporter

# 查看模块状态
get module:RobotStateReporter
```

### 网络抓包

```bash
# 监听 UDP 数据包
sudo tcpdump -i lo -n udp port 10020 -A

# 手动发送测试数据
echo '{"test":true}' | nc -u 127.0.0.1 10020
```

### 日志查看

```bash
# 列出日志目录
ls -la monitor_daemon/logs/

# 查看最新日志
tail -f monitor_daemon/logs/match_*/robot_1_1.jsonl

# 解析日志
python3 analysis_tools/log_parser.py monitor_daemon/logs/match_*/robot_1_1.jsonl
```

---

## 性能调优

### 降低 CPU 开销

```cfg
reportIntervalFrames = 30;  # 降低到 1Hz
```

### 降低网络带宽

```cfg
detectEvents = false;  # 禁用事件检测
```

### 完全禁用

```cfg
enabled = false;  # 零开销
```

---

## 故障排查

| 问题 | 可能原因 | 解决方案 |
|-----|---------|---------|
| 编译失败 | 模块未正确复制 | 检查文件路径 |
| 模块未加载 | 未注册到 modules.cfg | 添加 `module RobotStateReporter` |
| 收不到数据 | Monitor Daemon 未启动 | 启动 daemon.py |
| 数据包丢失 | 网络拥塞 | 增加 reportIntervalFrames |
| SimRobot 变慢 | 上报频率过高 | 增加 reportIntervalFrames 或禁用 |

---

## 联系与支持

- 详细文档: [SIMROBOT_INTEGRATION_GUIDE.md](../../docs/SIMROBOT_INTEGRATION_GUIDE.md)
- 部署指南: [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
- 架构设计: [ARCHITECTURE.md](../../docs/ARCHITECTURE.md)
