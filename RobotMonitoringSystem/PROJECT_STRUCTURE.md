# 项目结构说明

## 完整目录树

```
RobotMonitoringSystem/
├── README.md                           # 项目总览
├── QUICK_START.md                      # 5分钟快速开始指南
├── PROJECT_STRUCTURE.md                # 本文件：项目结构说明
│
├── bhuman_integration/                 # B-Human 框架集成代码
│   ├── README.md                       # 集成模块说明
│   ├── proto/
│   │   └── robot_state.proto           # Protobuf 数据模型定义
│   └── RobotStateReporter/             # 状态上报模块
│       ├── RobotStateReporter.h        # 模块头文件
│       └── RobotStateReporter.cpp      # 模块实现
│
├── monitor_daemon/                     # 监控守护进程
│   ├── README.md                       # Daemon 使用说明
│   ├── requirements.txt                # Python 依赖
│   ├── daemon.py                       # 主程序（UDP 接收 + 日志管理）
│   ├── log_writer.py                   # 日志写入器（异步写入）
│   └── websocket_server.py             # WebSocket 服务器（实时推送）
│
├── web_gui/                            # Web 监控界面
│   ├── index.html                      # 主页面
│   └── app.js                          # 前端逻辑（WebSocket 客户端）
│
├── analysis_tools/                     # 赛后分析工具
│   └── log_parser.py                   # 日志解析器（生成统计报告）
│
└── docs/                               # 完整文档
    ├── COMPLETE_DESIGN_SUMMARY.md      # 完整设计总结（任务1-6全部内容）
    ├── ARCHITECTURE.md                 # 架构设计文档
    ├── INTEGRATION_GUIDE.md            # 集成指南（详细步骤）
    ├── API_REFERENCE.md                # API 参考文档
    └── PERFORMANCE_OPTIMIZATION.md     # 性能优化指南
```

## 文件说明

### 根目录

| 文件 | 说明 | 用途 |
|------|------|------|
| `README.md` | 项目总览 | 快速了解项目功能和特性 |
| `QUICK_START.md` | 快速开始 | 5分钟启动完整系统 |
| `PROJECT_STRUCTURE.md` | 项目结构 | 本文件，说明目录组织 |

### bhuman_integration/ - B-Human 集成代码

| 文件 | 说明 | 用途 |
|------|------|------|
| `proto/robot_state.proto` | Protobuf 定义 | 定义机器人状态数据模型 |
| `RobotStateReporter/RobotStateReporter.h` | 模块头文件 | 模块接口定义 |
| `RobotStateReporter/RobotStateReporter.cpp` | 模块实现 | 状态采集、序列化、UDP 发送 |

**编译步骤**：
```bash
cd proto
protoc --cpp_out=../RobotStateReporter robot_state.proto
```

**集成步骤**：
```bash
cp -r RobotStateReporter /path/to/bhuman/Src/Modules/Infrastructure/
```

### monitor_daemon/ - 监控守护进程

| 文件 | 说明 | 用途 |
|------|------|------|
| `daemon.py` | 主程序 | UDP 接收、数据分流、统计输出 |
| `log_writer.py` | 日志写入器 | 异步写入 JSON Lines 日志 |
| `websocket_server.py` | WebSocket 服务器 | 实时推送数据到 Web GUI |
| `requirements.txt` | Python 依赖 | protobuf, websockets |

**启动命令**：
```bash
python3 daemon.py --port 10020 --log-dir ./logs --ws-port 8765
```

**生成的日志**：
```
logs/
├── match_20260128_143022/
│   ├── robot_bhuman_1.jsonl
│   ├── robot_bhuman_2.jsonl
│   └── match_metadata.json
```

### web_gui/ - Web 监控界面

| 文件 | 说明 | 用途 |
|------|------|------|
| `index.html` | 主页面 | HTML 结构和样式 |
| `app.js` | 前端逻辑 | WebSocket 连接、数据解析、DOM 更新 |

**启动命令**：
```bash
python3 -m http.server 8080
# 浏览器访问 http://localhost:8080
```

**显示内容**：
- 连接状态指示器
- 多机器人状态卡片（电量、姿态、定位、球感知）
- 事件日志流（实时滚动）

### analysis_tools/ - 赛后分析工具

| 文件 | 说明 | 用途 |
|------|------|------|
| `log_parser.py` | 日志解析器 | 解析 JSON Lines 日志，生成统计报告 |

**使用示例**：
```bash
python3 log_parser.py ../monitor_daemon/logs/match_20260128_143022/robot_bhuman_1.jsonl
```

**输出报告**：
- 总帧数、比赛时长
- 电量消耗
- 球感知率
- 定位质量分布
- 运动类型分布
- 事件统计

### docs/ - 完整文档

| 文件 | 说明 | 内容 |
|------|------|------|
| `COMPLETE_DESIGN_SUMMARY.md` | 完整设计总结 | **任务1-6全部内容**，包含架构、数据模型、通信、日志、GUI、性能 |
| `ARCHITECTURE.md` | 架构设计 | 系统架构、模块职责、数据流、线程安全 |
| `INTEGRATION_GUIDE.md` | 集成指南 | 详细的集成步骤、配置说明、故障排除 |
| `API_REFERENCE.md` | API 参考 | Protobuf 消息定义、WebSocket API、Python API、C++ API |
| `PERFORMANCE_OPTIMIZATION.md` | 性能优化 | 性能风险分析、优化措施、性能测试 |

## 核心工作流程

### 1. 开发阶段

```
开发者
  ↓
编译 Protobuf
  ↓
集成到 B-Human
  ↓
配置模块参数
  ↓
编译 B-Human
```

### 2. 运行阶段

```
启动 Monitor Daemon
  ↓
启动 B-Human (SimRobot 或真实机器人)
  ↓
打开 Web GUI
  ↓
实时监控 + 自动记录日志
```

### 3. 分析阶段

```
比赛结束
  ↓
日志文件生成
  ↓
使用 log_parser.py 分析
  ↓
生成统计报告
```

## 数据流

```
B-Human (RobotStateReporter)
  ↓ UDP (Protobuf, 3Hz)
Monitor Daemon
  ├─ WebSocket (JSON) → Web GUI (实时显示)
  └─ 异步写入 → JSON Lines 日志文件
                  ↓
            log_parser.py (赛后分析)
```

## 依赖关系

### B-Human 侧

```
RobotStateReporter.cpp
  ├─ 依赖：Protobuf C++ 库
  ├─ 依赖：B-Human Representations (FrameInfo, BallModel, RobotPose, etc.)
  └─ 生成：robot_state.pb.h, robot_state.pb.cc
```

### Monitor Daemon 侧

```
daemon.py
  ├─ 依赖：protobuf (Python)
  ├─ 依赖：websockets (Python)
  ├─ 依赖：robot_state_pb2.py (Protobuf 生成)
  ├─ 调用：log_writer.py
  └─ 调用：websocket_server.py
```

### Web GUI 侧

```
index.html
  └─ 调用：app.js
      └─ 连接：WebSocket (ws://localhost:8765)
```

## 配置文件

### B-Human 配置

**位置**：`/path/to/bhuman/Config/Modules/RobotStateReporter.cfg`

```
enabled = true;
monitorAddress = "239.0.0.1";
monitorPort = 10020;
reportIntervalFrames = 10;
detectEvents = true;
```

### Monitor Daemon 配置

**命令行参数**：
```bash
python3 daemon.py \
  --port 10020 \
  --multicast 239.0.0.1 \
  --log-dir ./logs \
  --ws-port 8765
```

## 端口使用

| 端口 | 协议 | 用途 |
|------|------|------|
| 10020 | UDP | B-Human → Monitor Daemon (状态数据) |
| 8765 | WebSocket | Monitor Daemon → Web GUI (实时推送) |
| 8080 | HTTP | Web GUI 静态文件服务 |

## 性能指标

| 组件 | CPU | 内存 | 网络 |
|------|-----|------|------|
| RobotStateReporter | < 1% | < 10 MB | ~10 KB/s |
| Monitor Daemon | < 5% | < 100 MB | ~100 KB/s (10 robots) |
| Web GUI | < 1% | < 50 MB | ~10 KB/s |

## 文件大小估算

| 文件类型 | 大小 |
|---------|------|
| 单个状态数据包 (Protobuf) | ~1 KB |
| 单个日志行 (JSON) | ~500 bytes |
| 10分钟比赛日志 (单机器人) | ~50 MB |
| 10分钟比赛日志 (10机器人) | ~500 MB |

## 开发建议

### 添加新字段

1. 修改 `proto/robot_state.proto`
2. 重新生成代码：`protoc --cpp_out=. --python_out=. robot_state.proto`
3. 在 `RobotStateReporter.cpp` 的 `collectState()` 中填充新字段
4. 更新 `web_gui/app.js` 的显示逻辑

### 添加新事件

1. 在 `proto/robot_state.proto` 的 `EventType` 枚举中添加
2. 在 `RobotStateReporter.cpp` 的 `detectEvents()` 中添加检测逻辑
3. 更新 `web_gui/app.js` 的事件名称映射

### 优化性能

1. 降低发送频率：修改 `reportIntervalFrames`
2. 精简字段：注释掉不需要的字段
3. 禁用监控：设置 `enabled = false`

## 故障排除

### 问题：B-Human 编译失败

**检查**：
- Protobuf 是否安装：`pkg-config --modversion protobuf`
- Protobuf 代码是否生成：检查 `robot_state.pb.h` 是否存在

### 问题：Monitor Daemon 收不到数据

**检查**：
- B-Human 配置中 `enabled = true`
- 网络地址和端口是否匹配
- 防火墙是否阻止 UDP 10020
- 使用 `tcpdump -i any -n udp port 10020` 检查网络流量

### 问题：Web GUI 无法连接

**检查**：
- Monitor Daemon 是否正在运行
- WebSocket 端口 8765 是否被占用
- 浏览器控制台是否有错误

## 下一步

1. 阅读 `QUICK_START.md` 快速启动系统
2. 阅读 `docs/COMPLETE_DESIGN_SUMMARY.md` 了解完整设计
3. 阅读 `docs/INTEGRATION_GUIDE.md` 进行详细集成
4. 使用 `analysis_tools/log_parser.py` 分析日志

## 许可证

MIT License
