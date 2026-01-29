# 🚀 Web 监控系统测试指南

## ✅ 已完成的工作

### 1. 后端服务器
- ✅ `web_monitor.py` - 集成 UDP + WebSocket + HTTP API
- ✅ UDP 接收器（Port 10020）
- ✅ WebSocket 服务器（实时推送）
- ✅ HTTP API（日志查询）

### 2. 前端页面
- ✅ `index.html` - 实时监控页面
- ✅ `logs.html` - 历史日志查看
- ✅ `monitor.js` - 实时监控逻辑
- ✅ `logs.js` - 日志查看逻辑
- ✅ `style.css` - 样式表

### 3. 工具脚本
- ✅ `start_web_monitor.sh` - 一键启动脚本

## 🎯 测试步骤

### Step 1: 启动 Web 监控系统

```bash
# 方法 1：使用启动脚本
./RobotMonitoringSystem/start_web_monitor.sh

# 方法 2：直接运行
python3 RobotMonitoringSystem/monitor_daemon/web_monitor.py
```

**预期输出：**
```
============================================================
  🤖 Robot Web Monitor - Starting
============================================================
✅ UDP Receiver started on port 10020
🌐 Web Server starting on http://localhost:8080
🔌 WebSocket Server on ws://localhost:8080/ws
============================================================
📊 Open in browser: http://localhost:8080
============================================================
```

### Step 2: 启动 SimRobot

**在新终端中：**
```bash
./Build/Linux/SimRobot/Develop/SimRobot Config/Scenes/GameFast.ros3
```

### Step 3: 打开浏览器

**实时监控页面：**
```
http://localhost:8080/static/index.html
```

**预期效果：**
- 🟢 连接状态显示 "Connected"
- 🤖 自动显示 10 个机器人卡片
- 📊 实时更新数据（电量、行为、摔倒状态、球可见性）
- 🎨 摔倒的机器人卡片背景变红
- ⏱️ 每秒自动刷新

### Step 4: 查看历史日志

**日志查看页面：**
```
http://localhost:8080/static/logs.html
```

**操作步骤：**
1. 选择比赛（自动加载最新的）
2. 选择机器人（如 5_5）
3. 点击 "📥 Load Data"

**预期效果：**
- 📊 显示日志统计信息
- ⏱️ 显示时间轴（持续时间、摔倒次数、球可见率）
- 📋 显示关键事件列表
- 📄 显示原始 JSON 数据

## 🔍 验证清单

### 实时监控功能
- [ ] WebSocket 连接成功（绿色状态）
- [ ] 显示所有 10 个机器人
- [ ] 机器人卡片实时更新
- [ ] 摔倒状态正确显示
- [ ] 球可见性正确显示
- [ ] 电量和温度显示
- [ ] 机器人离线检测（停止 SimRobot 后 5 秒变灰）

### 历史日志功能
- [ ] 比赛列表加载成功
- [ ] 机器人列表加载成功
- [ ] 日志数据加载成功
- [ ] 时间轴统计正确
- [ ] 事件列表显示（摔倒、球丢失等）
- [ ] 原始数据可查看

### 与 GameController 共存
- [ ] 可以同时运行 GC 和监控系统
- [ ] 端口不冲突
- [ ] SimRobot 正常运行
- [ ] 监控系统不影响比赛控制

## 🐛 故障排查

### 问题 1：浏览器无法连接
**症状：** 打开 http://localhost:8080 显示无法连接

**解决：**
```bash
# 检查 web_monitor.py 是否在运行
ps aux | grep web_monitor

# 检查端口是否被占用
netstat -tuln | grep 8080

# 重启服务
pkill -f web_monitor
./RobotMonitoringSystem/start_web_monitor.sh
```

### 问题 2：WebSocket 连接失败
**症状：** 页面显示 "🔴 Disconnected"

**解决：**
- 检查浏览器控制台（F12）是否有错误
- 确认 web_monitor.py 正在运行
- 刷新页面

### 问题 3：没有机器人数据
**症状：** 页面显示 "⏳ Waiting for robots..."

**解决：**
```bash
# 确认 SimRobot 正在运行
ps aux | grep SimRobot

# 确认 RobotStateReporter 已集成
grep -r "RobotStateReporter" Config/Scenarios/Default/threads.cfg

# 检查 UDP 端口
netstat -uln | grep 10020
```

### 问题 4：日志页面无数据
**症状：** 日志页面显示 "No matches found"

**解决：**
```bash
# 检查日志目录
ls -la RobotMonitoringSystem/monitor_daemon/logs/

# 确认有日志文件
ls -la RobotMonitoringSystem/monitor_daemon/logs/match_*/
```

## 📊 性能指标

**正常运行时：**
- UDP 接收率：4-5 Hz
- WebSocket 延迟：< 100ms
- 内存占用：< 100 MB
- CPU 占用：< 5%

## 🎉 成功标志

当你看到以下情况时，说明系统完全正常：

1. ✅ Web 监控页面显示 10 个机器人卡片
2. ✅ 数据实时更新（每秒多次）
3. ✅ 摔倒的机器人卡片背景变红
4. ✅ 球可见性正确显示（⚽ 或 ❌）
5. ✅ 日志页面可以查看历史数据
6. ✅ SimRobot 和 GameController 同时运行无冲突

## 📸 截图位置

建议截图保存：
- 实时监控页面（显示多个机器人）
- 日志查看页面（显示时间轴和事件）
- 浏览器控制台（显示 WebSocket 连接）

## 🚀 下一步

系统测试成功后，可以：
1. 自定义样式（修改 `style.css`）
2. 添加更多统计图表
3. 实现数据导出功能
4. 添加实时图表（使用 Chart.js）
5. 实现多比赛对比功能

---

**准备好测试了吗？** 🎯
