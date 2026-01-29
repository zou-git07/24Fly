# 准备测试 - SimRobot 监控系统

## ✅ 系统状态

**时间**: 2026-01-28  
**状态**: ✅ 准备就绪，可以测试

---

## 🎯 已完成的工作

### 1. 模块集成 ✅

- ✅ RobotStateReporter 模块已复制到 `Src/Modules/Infrastructure/`
- ✅ 配置文件已复制到 `Config/Scenarios/Default/`
- ✅ 模块已注册到 `threads.cfg`
- ✅ 代码已修复并编译成功

### 2. Monitor Daemon ✅

- ✅ 创建了 JSON 版本的 daemon (`daemon_json.py`)
- ✅ Daemon 已启动并监听端口 10020
- ✅ 日志目录已创建

### 3. SimRobot ✅

- ✅ SimRobot 已编译（包含 RobotStateReporter 模块）
- ✅ 配置文件已就位
- ✅ 准备启动

---

## 🚀 测试步骤

### 当前状态

```
✅ Monitor Daemon: 运行中 (PID: 查看进程)
   - 监听: 0.0.0.0:10020
   - 日志目录: RobotMonitoringSystem/monitor_daemon/logs
   - 状态: 等待数据

⏳ SimRobot: 准备启动
   - 可执行文件: Build/Linux/SimRobot/Develop/SimRobot
   - 场景文件: Config/Scenes/Default.ros2
```

### 启动 SimRobot

```bash
./Build/Linux/SimRobot/Develop/SimRobot Config/Scenes/Default.ros2
```

或使用测试脚本:

```bash
./test_simrobot_monitoring.sh
```

### 在 SimRobot 中操作

1. **加载场景**
   - SimRobot 启动后会自动加载场景

2. **启动机器人**
   - 按 `Ctrl+R` 或点击菜单 `Simulation → Start`

3. **观察 Monitor Daemon 输出**
   - 应该看到类似以下的输出：
   ```
   [LogWriter] Started new match: logs/match_20260128_HHMMSS
   [LogWriter] Created log file: logs/match_20260128_HHMMSS/robot_1_1.jsonl
   🟢 Robot 1_1: t=12345, battery=100.0%, behavior=unknown, ball=❌
   ``

4. **检查日志文件**
   ```bash
   ls -la RobotMonitoringSystem/monitor_daemon/logs/match_*/
   ```

---

## 📊 预期结果

### Monitor Daemon 输出

```
[MonitorDaemon] Listening on 0.0.0.0:10020
[MonitorDaemon] Log directory: /path/to/logs
[MonitorDaemon] Started successfully

[LogWriter] Started new match: logs/match_20260128_143022
[LogWriter] Created log file: logs/match_20260128_143022/robot_1_1.jsonl
  🟢 Robot 1_1: t=12345, battery=100.0%, behavior=unknown, ball=❌
  🟢 Robot 1_2: t=12346, battery=100.0%, behavior=unknown, ball=❌

[STATS] Packets: 30, Rate: 3.0/s, Dropped: 0, Errors: 0
```

### 日志文件

```
RobotMonitoringSystem/monitor_daemon/logs/
└── match_20260128_143022/
    ├── robot_1_1.jsonl
    ├── robot_1_2.jsonl
    └── ...
```

### 日志内容示例

```json
{"timestamp":12345,"robot_id":"1_1","battery":100.0,"temperature":40.0,"fallen":false,"behavior":"unknown","motion":"stand","ball_visible":false,"ball_x":0,"ball_y":0,"pos_x":1000,"pos_y":500,"rotation":0.5,"events":[]}
```

---

## 🔧 配置说明

### RobotStateReporter 配置

**文件**: `Config/Scenarios/Default/RobotStateReporter.cfg`

```cfg
# 是否启用监控
enabled = true;

# Monitor Daemon 地址
monitorAddress = "127.0.0.1";

# UDP 端口
monitorPort = 10020;

# 上报间隔（帧数）
# Cognition 线程是 30Hz，每 10 帧 = 3Hz
reportIntervalFrames = 10;

# 是否检测事件
detectEvents = true;
```

### 调整上报频率

如果想改变上报频率，修改 `reportIntervalFrames`:

- `5` → 6Hz (高频)
- `10` → 3Hz (推荐)
- `30` → 1Hz (低频)

---

## 🐛 故障排查

### 问题 1: Monitor Daemon 收不到数据

**检查清单**:
1. ✅ Monitor Daemon 是否运行？
   ```bash
   pgrep -f daemon_json.py
   ```

2. ✅ 端口是否正确？
   ```bash
   netstat -an | grep 10020
   ```

3. ✅ SimRobot 是否启动了机器人？
   - 按 `Ctrl+R` 启动

4. ✅ 配置文件中的地址是否正确？
   - 检查 `RobotStateReporter.cfg` 中的 `monitorAddress`

### 问题 2: 编译错误

如果修改了代码后编译失败：

```bash
# 重新生成构建文件
./Make/Linux/generate

# 重新编译
./Make/Linux/compile Develop SimRobot
```

### 问题 3: 日志文件未生成

**原因**: 可能还没有接收到数据

**解决**: 
1. 确保 SimRobot 中的机器人已启动
2. 等待几秒钟
3. 检查 Monitor Daemon 的输出

---

## 📝 测试清单

- [ ] Monitor Daemon 启动成功
- [ ] SimRobot 启动成功
- [ ] 机器人在 SimRobot 中运行
- [ ] Monitor Daemon 接收到数据包
- [ ] 日志文件生成
- [ ] 日志内容正确（JSON 格式）
- [ ] 统计信息显示正常（Rate: ~3.0/s）

---

## 🎉 成功标志

当你看到以下输出时，说明集成成功：

```
[STATS] Packets: 30, Rate: 3.0/s, Dropped: 0, Errors: 0
  🟢 Robot 1_1: t=12345, battery=100.0%, behavior=unknown, ball=❌
```

并且日志文件已生成：

```bash
$ ls -la RobotMonitoringSystem/monitor_daemon/logs/match_*/
robot_1_1.jsonl
robot_1_2.jsonl
...
```

---

## 📚 相关文档

1. **[SIMROBOT_INTEGRATION_SUCCESS.md](SIMROBOT_INTEGRATION_SUCCESS.md)** - 集成成功报告
2. **[SIMROBOT_INTEGRATION_SUMMARY.md](SIMROBOT_INTEGRATION_SUMMARY.md)** - 完整总结
3. **[DEPLOYMENT_GUIDE.md](bhuman_integration/RobotStateReporter_SimRobot/DEPLOYMENT_GUIDE.md)** - 部署指南

---

## 🚀 下一步

测试成功后，可以：

1. **分析日志**
   ```bash
   python3 RobotMonitoringSystem/analysis_tools/log_parser.py \
           RobotMonitoringSystem/monitor_daemon/logs/match_*/robot_1_1.jsonl
   ```

2. **启动 Web GUI**
   ```bash
   cd RobotMonitoringSystem/web_gui
   python3 -m http.server 8080
   ```
   然后访问: http://localhost:8080

3. **部署到真机**
   - 参考 [SIMROBOT_INTEGRATION_GUIDE.md](docs/SIMROBOT_INTEGRATION_GUIDE.md) 的任务 6

---

**准备时间**: 2026-01-28  
**状态**: ✅ 准备就绪，可以开始测试！
