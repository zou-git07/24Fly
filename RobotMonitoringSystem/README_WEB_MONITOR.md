# 🤖 Robot Web Monitor - 使用说明

## 🎯 这是什么？

一个类似 GameController 的 **Web 实时监控系统**，用于监控 SimRobot 中的机器人状态。

## ✨ 核心特性

- 🔴 **实时监控**：Web 页面实时显示所有机器人状态
- 📊 **历史日志**：查看完整比赛数据和事件时间轴
- 🔌 **WebSocket**：毫秒级实时推送
- 🎨 **可视化**：直观的卡片式界面
- 🚀 **高性能**：支持 10+ 机器人同时监控
- 🔒 **安全隔离**：与 GameController 完全独立，互不影响

## 🚀 快速开始

### 1. 启动 Web 监控系统
```bash
./RobotMonitoringSystem/start_web_monitor.sh
```

### 2. 启动 SimRobot
```bash
./Build/Linux/SimRobot/Develop/SimRobot Config/Scenes/GameFast.ros3
```

### 3. 打开浏览器
```
http://localhost:8080/static/index.html
```

## 📊 功能页面

### 实时监控页面
**地址：** http://localhost:8080/static/index.html

**显示内容：**
- 🤖 所有机器人实时状态
- 🔋 电量和温度
- 🧠 当前行为
- 🤸 摔倒状态（红色背景）
- ⚽ 球可见性
- 📡 在线/离线状态

### 历史日志页面
**地址：** http://localhost:8080/static/logs.html

**功能：**
- 📅 选择比赛
- 🤖 选择机器人
- ⏱️ 查看时间轴统计
- 📋 查看关键事件
- 📄 查看原始数据

## 🔧 端口说明

| 端口 | 用途 | 协议 |
|------|------|------|
| 10020 | Robot → Monitor | UDP |
| 8080 | Web 页面 | HTTP |
| 8765 | 实时推送 | WebSocket |

## 📁 日志位置

```
RobotMonitoringSystem/monitor_daemon/logs/
└── match_YYYYMMDD_HHMMSS/
    ├── robot_5_1.jsonl
    ├── robot_5_2.jsonl
    └── ...
```

## 🛠️ 常用命令

**查看运行状态：**
```bash
ps aux | grep web_monitor
```

**停止服务：**
```bash
pkill -f web_monitor
```

**查看日志：**
```bash
ls -lh RobotMonitoringSystem/monitor_daemon/logs/match_*/
```

**查看最新数据：**
```bash
tail -1 RobotMonitoringSystem/monitor_daemon/logs/match_*/robot_5_5.jsonl | python3 -m json.tool
```

## 📚 详细文档

- **完整架构设计**：`docs/WEB_MONITOR_ARCHITECTURE.md`
- **测试指南**：`WEB_MONITOR_TEST_GUIDE.md`
- **成功报告**：`WEB_MONITOR_SUCCESS.md`

## 🎉 当前状态

✅ **系统已部署并运行！**

- Web Monitor: 🟢 运行中（进程 13）
- SimRobot: 🟢 运行中（进程 11）
- 数据采集: ✅ 10 个机器人
- 日志记录: ✅ 正常

**立即访问：** http://localhost:8080/static/index.html

---

**问题反馈：** 查看 `WEB_MONITOR_TEST_GUIDE.md` 中的故障排查部分
