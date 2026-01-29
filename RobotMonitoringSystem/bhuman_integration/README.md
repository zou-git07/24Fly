# B-Human 集成模块

本目录包含需要集成到 B-Human 框架的代码。

## 目录结构

```
bhuman_integration/
├── RobotStateReporter/          # 状态上报模块
│   ├── RobotStateReporter.h     # 模块头文件
│   ├── RobotStateReporter.cpp   # 模块实现
│   ├── robot_state.pb.h         # Protobuf 生成的头文件（需编译）
│   └── robot_state.pb.cc        # Protobuf 生成的实现（需编译）
└── proto/
    └── robot_state.proto        # Protobuf 定义文件
```

## 快速开始

### 1. 编译 Protobuf

```bash
cd proto
protoc --cpp_out=../RobotStateReporter robot_state.proto
```

### 2. 复制到 B-Human

```bash
cp -r RobotStateReporter /path/to/bhuman/Src/Modules/Infrastructure/
```

### 3. 配置模块

在 B-Human 的 `Config/Modules/modules.cfg` 中添加：
```
module RobotStateReporter
```

创建 `Config/Modules/RobotStateReporter.cfg`：
```
enabled = true;
monitorAddress = "239.0.0.1";
monitorPort = 10020;
reportIntervalFrames = 10;
detectEvents = true;
```

### 4. 编译 B-Human

```bash
cd /path/to/bhuman
make
```

## 配置说明

- `enabled`: 是否启用监控（默认 true）
- `monitorAddress`: 监控守护进程地址（多播或单播）
- `monitorPort`: UDP 端口（默认 10020）
- `reportIntervalFrames`: 上报间隔（帧数，默认 10 = 3Hz）
- `detectEvents`: 是否检测事件（默认 true）

## 性能影响

- CPU 开销：< 1%
- 内存开销：< 10 MB
- 网络带宽：~10 KB/s (3Hz 上报)
- 延迟：< 5ms (非阻塞 UDP)

## 故障排除

### 编译错误：找不到 protobuf

```bash
sudo apt-get install libprotobuf-dev
```

### 运行时错误：无法创建 socket

检查配置文件中的地址和端口是否正确。

### 数据未发送

检查 `enabled` 是否为 true，以及监控守护进程是否正在运行。
