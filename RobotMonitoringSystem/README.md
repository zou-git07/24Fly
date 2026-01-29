# Nao 机器人监控与日志系统

## 项目概述

这是一个为 B-Human 框架设计的独立监控与日志系统，用于实时监控 Nao 机器人的运行状态并生成完整的比赛日志。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Nao 机器人 (B-Human 进程)                      │
│                    RobotStateReporter 模块                        │
│                           ↓ UDP                                  │
└───────────────────────────┼───────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│              Monitor Daemon (独立进程)                            │
│              ├─ UDP Receiver                                     │
│              ├─ Log Writer                                       │
│              └─ WebSocket Server                                 │
│                           ↓                                      │
└───────────────────────────┼───────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│              Web GUI (浏览器)                                     │
│              实时监控多机器人状态                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 目录结构

```
RobotMonitoringSystem/
├── bhuman_integration/          # B-Human 框架集成代码
│   ├── RobotStateReporter/      # 状态上报模块
│   └── proto/                   # Protobuf 定义
├── monitor_daemon/              # 监控守护进程
│   ├── daemon.py                # 主程序
│   ├── log_writer.py            # 日志写入器
│   └── websocket_server.py      # WebSocket 服务
├── web_gui/                     # Web 监控界面
│   ├── index.html
│   └── app.js
├── analysis_tools/              # 赛后分析工具
│   ├── log_parser.py
│   └── visualizer.py
├── docs/                        # 文档
│   ├── ARCHITECTURE.md          # 架构设计
│   ├── INTEGRATION_GUIDE.md     # 集成指南
│   └── API_REFERENCE.md         # API 参考
└── tests/                       # 测试
    └── test_integration.py
```

## 核心特性

1. **解耦设计**：监控系统与比赛逻辑完全分离
2. **非阻塞通信**：UDP 非阻塞发送，不影响实时性
3. **多机器人支持**：同时监控多个机器人
4. **事件驱动**：自动检测行为切换、摔倒等关键事件
5. **完整日志**：比赛全程记录，支持赛后分析

## 快速开始

### 1. 集成到 B-Human

```bash
# 复制模块到 B-Human 源码目录
cp -r bhuman_integration/RobotStateReporter Src/Modules/Infrastructure/

# 编译 Protobuf
cd bhuman_integration/proto
protoc --cpp_out=../RobotStateReporter robot_state.proto

# 重新编译 B-Human
cd /path/to/bhuman
make
```

### 2. 启动监控守护进程

```bash
cd monitor_daemon
python3 daemon.py --port 10020 --log-dir ./logs
```

### 3. 打开 Web 监控界面

```bash
cd web_gui
python3 -m http.server 8080
# 浏览器访问 http://localhost:8080
```

## 性能指标

- **CPU 开销**：< 1% (30Hz 上报频率)
- **网络带宽**：~10 KB/s per robot
- **延迟**：< 5ms (UDP 发送)
- **日志大小**：~50 MB per 10-minute match

## 文档

详细文档请参考 `docs/` 目录：
- [架构设计](docs/ARCHITECTURE.md)
- [集成指南](docs/INTEGRATION_GUIDE.md)
- [API 参考](docs/API_REFERENCE.md)

## 许可证

MIT License
