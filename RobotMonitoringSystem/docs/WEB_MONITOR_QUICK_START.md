# Web 监控系统快速启动指南

## 🎯 目标

将现有的终端监控系统升级为 **Web 实时监控系统**（类似 GameController）

## 📋 系统对比

| 特性 | 当前系统 | 目标系统 |
|------|---------|---------|
| 数据采集 | ✅ UDP + JSON | ✅ 保持不变 |
| 实时显示 | ✅ 终端输出 | ✅ **Web 页面** |
| 历史日志 | ✅ JSON Lines 文件 | ✅ **Web 查看器** |
| 多机器人 | ✅ 支持 | ✅ **动态卡片** |
| 与 GC 共存 | ✅ 不冲突 | ✅ **完全隔离** |

## 🏗️ 架构概览

```
SimRobot (10 robots)
    ↓ UDP JSON (Port 10020)
Monitor Daemon (Python)
    ↓ WebSocket (Port 8765) + HTTP (Port 8080)
Web Browser
    - 实时监控页面
    - 历史日志查看
```

## 🚀 实现步骤

### Step 1: 创建 Web Monitor Daemon
- 文件：`RobotMonitoringSystem/monitor_daemon/web_monitor.py`
- 功能：UDP 接收 + WebSocket 推送 + HTTP API

### Step 2: 创建前端页面
- `RobotMonitoringSystem/web_monitor/index.html` - 实时监控
- `RobotMonitoringSystem/web_monitor/logs.html` - 历史日志
- `RobotMonitoringSystem/web_monitor/monitor.js` - 前端逻辑

### Step 3: 启动系统
```bash
# 1. 启动 Web Monitor
python3 RobotMonitoringSystem/monitor_daemon/web_monitor.py

# 2. 启动 SimRobot
./Build/Linux/SimRobot/Develop/SimRobot Config/Scenes/GameFast.ros3

# 3. 打开浏览器
http://localhost:8080
```

## 📊 Web 页面功能

### 实时监控页面
- 🤖 动态机器人卡片
- 🔋 电量显示
- 🧠 当前行为
- 🤸 摔倒状态
- ⚽ 球可见性
- 📡 在线/离线状态

### 历史日志页面
- 📅 比赛选择器
- 🤖 机器人选择器
- 📈 时间轴可视化
- 📋 事件列表
- 📄 原始数据查看

## 🔧 技术细节

### 端口分配
- **10020**: UDP (Robot → Monitor)
- **8765**: WebSocket (Monitor → Browser)
- **8080**: HTTP (Browser → Monitor)

### 与 GameController 的关系
- ✅ **完全独立**：不同端口，不同协议
- ✅ **不冲突**：GC 控制，Monitor 观察
- ✅ **可共存**：同时运行无影响

## 📁 文件结构

```
RobotMonitoringSystem/
├── monitor_daemon/
│   ├── daemon_json.py          # 现有：终端版
│   └── web_monitor.py          # 新增：Web 版
├── web_monitor/                # 新增目录
│   ├── index.html
│   ├── logs.html
│   ├── monitor.js
│   ├── logs.js
│   └── style.css
└── docs/
    ├── WEB_MONITOR_ARCHITECTURE.md  # 完整架构
    └── WEB_MONITOR_QUICK_START.md   # 本文档
```

## ✅ 准备开始实现

详细架构设计请查看：`WEB_MONITOR_ARCHITECTURE.md`

准备好开始编码了吗？🚀
