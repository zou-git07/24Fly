# 快速开始指南

5 分钟快速启动监控系统。

## 步骤 1：安装依赖

```bash
# Ubuntu/Debian
sudo apt-get install protobuf-compiler libprotobuf-dev python3-pip

# Python 依赖
pip3 install protobuf websockets
```

## 步骤 2：编译 Protobuf

```bash
cd bhuman_integration/proto

# 生成 C++ 代码
protoc --cpp_out=../RobotStateReporter robot_state.proto

# 生成 Python 代码
protoc --python_out=../../monitor_daemon robot_state.proto
```

## 步骤 3：集成到 B-Human

```bash
# 复制模块
cp -r bhuman_integration/RobotStateReporter /path/to/bhuman/Src/Modules/Infrastructure/

# 编辑 /path/to/bhuman/Config/Modules/modules.cfg，添加：
# module RobotStateReporter

# 创建 /path/to/bhuman/Config/Modules/RobotStateReporter.cfg：
# enabled = true;
# monitorAddress = "239.0.0.1";
# monitorPort = 10020;
# reportIntervalFrames = 10;
# detectEvents = true;

# 编译 B-Human
cd /path/to/bhuman
make
```

## 步骤 4：启动监控守护进程

```bash
cd monitor_daemon
python3 daemon.py
```

输出：
```
[MonitorDaemon] Listening on 239.0.0.1:10020
[MonitorDaemon] Log directory: /path/to/logs
[WebSocketServer] Started on port 8765
[MonitorDaemon] Started successfully
```

## 步骤 5：启动 B-Human

```bash
cd /path/to/bhuman
./Build/Linux/SimRobot/Develop/SimRobot
```

在 SimRobot 中加载场景并启动机器人。

## 步骤 6：打开 Web 监控界面

```bash
cd web_gui
python3 -m http.server 8080
```

浏览器访问：`http://localhost:8080`

## 验证

你应该看到：

1. **Monitor Daemon 输出**：
```
[STATS] Packets: 30, Rate: 3.0/s, Dropped: 0, Errors: 0
```

2. **Web GUI**：
- 连接状态：✅ 已连接到监控服务器
- 机器人卡片显示实时状态
- 事件日志流

3. **日志文件**：
```bash
ls monitor_daemon/logs/
# match_20260128_143022/
```

## 下一步

- 阅读 [集成指南](docs/INTEGRATION_GUIDE.md) 了解详细配置
- 阅读 [架构设计](docs/ARCHITECTURE.md) 了解系统原理
- 使用 `analysis_tools/log_parser.py` 分析日志

## 常见问题

**Q: 编译失败，找不到 protobuf**
```bash
sudo apt-get install libprotobuf-dev
```

**Q: Monitor Daemon 收不到数据**
- 检查 B-Human 配置中 `enabled = true`
- 检查网络地址和端口是否匹配
- 使用 `tcpdump -i any -n udp port 10020` 检查网络流量

**Q: Web GUI 无法连接**
- 检查 Monitor Daemon 是否正在运行
- 检查浏览器控制台是否有错误
- 尝试刷新页面
