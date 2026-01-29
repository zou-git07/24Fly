# 监控守护进程

独立的监控守护进程，负责接收机器人状态、写入日志、提供 WebSocket 接口。

## 安装依赖

```bash
pip3 install -r requirements.txt
```

## 编译 Protobuf

```bash
cd ../bhuman_integration/proto
protoc --python_out=../../monitor_daemon robot_state.proto
```

这会生成 `robot_state_pb2.py` 文件。

## 启动守护进程

```bash
python3 daemon.py --port 10020 --log-dir ./logs --ws-port 8765
```

### 命令行参数

- `--port`: UDP 监听端口（默认 10020）
- `--multicast`: 多播组地址（默认 239.0.0.1）
- `--log-dir`: 日志目录（默认 logs）
- `--ws-port`: WebSocket 服务器端口（默认 8765）

## 日志文件

日志按比赛分组存储：

```
logs/
├── match_20260128_143022/
│   ├── robot_bhuman_1.jsonl
│   ├── robot_bhuman_2.jsonl
│   └── match_metadata.json
└── match_20260128_150315/
    └── ...
```

每个 `.jsonl` 文件是 JSON Lines 格式，每行一个状态快照。

## WebSocket API

客户端可以连接到 `ws://localhost:8765` 订阅实时数据。

### 获取机器人列表

```json
{"type": "get_robots"}
```

### 获取机器人状态

```json
{"type": "get_state", "robot_id": "bhuman_1"}
```

## 性能

- CPU 开销：< 5%
- 内存开销：< 100 MB
- 支持同时监控 10+ 机器人

## 故障排除

### 收不到数据

1. 检查 B-Human 是否启用了 RobotStateReporter
2. 检查网络地址和端口是否匹配
3. 检查防火墙设置

### WebSocket 连接失败

1. 检查端口 8765 是否被占用
2. 检查防火墙设置
