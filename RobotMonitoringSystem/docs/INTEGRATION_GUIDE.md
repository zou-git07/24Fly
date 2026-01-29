# 集成指南

本文档详细说明如何将监控系统集成到 B-Human 框架中。

## 前置要求

### 软件依赖

**B-Human 侧**：
- Protobuf 编译器：`protoc` (版本 >= 3.0)
- Protobuf C++ 库：`libprotobuf-dev`

**Monitor Daemon 侧**：
- Python 3.7+
- Python 包：
  - `protobuf` (Python Protobuf 库)
  - `websockets` (WebSocket 服务器)

### 安装依赖

**Ubuntu/Debian**：
```bash
# B-Human 侧
sudo apt-get install protobuf-compiler libprotobuf-dev

# Monitor Daemon 侧
pip3 install protobuf websockets
```

## 步骤 1：编译 Protobuf 定义

```bash
cd RobotMonitoringSystem/bhuman_integration/proto

# 生成 C++ 代码
protoc --cpp_out=../RobotStateReporter robot_state.proto

# 生成 Python 代码
protoc --python_out=../../monitor_daemon robot_state.proto
```

生成的文件：
- `robot_state.pb.h` 和 `robot_state.pb.cc` (C++)
- `robot_state_pb2.py` (Python)

## 步骤 2：集成到 B-Human

### 2.1 复制模块到 B-Human 源码

```bash
# 假设 B-Human 源码在 /path/to/bhuman
cp -r RobotMonitoringSystem/bhuman_integration/RobotStateReporter \
      /path/to/bhuman/Src/Modules/Infrastructure/
```

### 2.2 注册模块

编辑 `/path/to/bhuman/Config/Modules/modules.cfg`，添加：

```
module RobotStateReporter
```

### 2.3 配置模块

创建配置文件 `/path/to/bhuman/Config/Modules/RobotStateReporter.cfg`：

```
# 监控系统配置
enabled = true;
monitorAddress = "239.0.0.1";  # 多播地址（或单播 IP）
monitorPort = 10020;
reportIntervalFrames = 10;     # 每 10 帧发送一次（3Hz）
detectEvents = true;
```

### 2.4 添加到线程

编辑 `/path/to/bhuman/Src/Threads/Cognition.cpp`，在模块列表中添加：

```cpp
USES(RobotStateReporter);
```

### 2.5 编译 B-Human

```bash
cd /path/to/bhuman
make
```

## 步骤 3：启动监控守护进程

### 3.1 启动 Daemon

```bash
cd RobotMonitoringSystem/monitor_daemon
python3 daemon.py --port 10020 --log-dir ./logs --ws-port 8765
```

输出示例：
```
[MonitorDaemon] Listening on 239.0.0.1:10020
[MonitorDaemon] Log directory: /path/to/logs
[MonitorDaemon] WebSocket server on port 8765
[WebSocketServer] Started on port 8765
[MonitorDaemon] Started successfully
```

### 3.2 验证连接

启动 B-Human（SimRobot 或真实机器人），应该看到：

```
[STATS] Packets: 30, Rate: 3.0/s, Dropped: 0, Errors: 0
```

## 步骤 4：打开 Web 监控界面

### 4.1 启动 Web 服务器

```bash
cd RobotMonitoringSystem/web_gui
python3 -m http.server 8080
```

### 4.2 访问界面

浏览器打开：`http://localhost:8080`

应该看到：
- 连接状态：✅ 已连接到监控服务器
- 机器人卡片（显示实时状态）
- 事件日志流

## 步骤 5：验证日志记录

### 5.1 运行比赛

在 SimRobot 中运行一场完整比赛（READY -> SET -> PLAYING -> FINISHED）

### 5.2 检查日志文件

```bash
cd RobotMonitoringSystem/monitor_daemon/logs
ls -la

# 应该看到：
# match_20260128_143022/
#   ├── robot_bhuman_1.jsonl
#   ├── robot_bhuman_2.jsonl
#   └── match_metadata.json
```

### 5.3 解析日志

```bash
cd RobotMonitoringSystem/analysis_tools
python3 log_parser.py ../monitor_daemon/logs/match_20260128_143022/robot_bhuman_1.jsonl
```

## 常见问题

### Q1: B-Human 编译失败，找不到 protobuf

**解决**：
```bash
# 检查 protobuf 是否安装
pkg-config --modversion protobuf

# 如果未安装
sudo apt-get install libprotobuf-dev
```

### Q2: Monitor Daemon 收不到数据

**检查清单**：
1. B-Human 中 `RobotStateReporter` 是否启用（`enabled = true`）
2. 网络地址和端口是否匹配
3. 防火墙是否阻止 UDP 10020 端口
4. 多播路由是否正确（`route -n` 检查）

**调试**：
```bash
# 监听 UDP 端口
sudo tcpdump -i any -n udp port 10020
```

### Q3: Web GUI 无法连接

**检查清单**：
1. Monitor Daemon 是否正在运行
2. WebSocket 端口 8765 是否被占用
3. 浏览器控制台是否有错误

**调试**：
```bash
# 检查端口
netstat -an | grep 8765
```

### Q4: 日志文件未生成

**原因**：
- 比赛未正常结束（未到达 FINISHED 状态）
- 日志目录权限不足

**解决**：
```bash
# 检查日志目录权限
ls -ld logs/
chmod 755 logs/
```

## 性能调优

### 降低 CPU 开销

修改 `RobotStateReporter.cfg`：
```
reportIntervalFrames = 30;  # 降低到 1Hz
```

### 降低网络带宽

在 `RobotStateReporter.cpp` 中注释掉不需要的字段。

### 禁用监控

```
enabled = false;
```

## 真实机器人部署

### 方案 A：Daemon 运行在外部 PC

1. 修改 B-Human 配置：
```
monitorAddress = "192.168.1.100";  # PC 的 IP
```

2. 在 PC 上启动 Daemon：
```bash
python3 daemon.py --port 10020
```

### 方案 B：Daemon 运行在 Nao 本地

1. 将 `monitor_daemon/` 复制到 Nao：
```bash
scp -r monitor_daemon/ nao@nao.local:/home/nao/
```

2. 在 Nao 上启动：
```bash
ssh nao@nao.local
cd /home/nao/monitor_daemon
python3 daemon.py --log-dir /tmp/logs
```

**注意**：方案 B 会增加 Nao 的 I/O 负载，建议仅用于测试。

## 下一步

- 阅读 [API 参考](API_REFERENCE.md) 了解详细接口
- 阅读 [架构设计](ARCHITECTURE.md) 了解系统原理
- 使用 `analysis_tools/` 中的工具分析日志
