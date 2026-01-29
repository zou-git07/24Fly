# 系统架构设计文档

## 1. 总体架构

### 1.1 模块职责边界

**RobotStateReporter (B-Human 内部模块)**
- 职责：
  - 每帧采集机器人状态数据（从 Blackboard 读取 Representations）
  - 检测事件触发条件（行为切换、摔倒、球丢失等）
  - 将状态数据序列化为 Protobuf
  - 通过 UDP 非阻塞发送到 Monitor Daemon
- 边界：
  - **不做任何 GUI 渲染**
  - **不做文件 I/O**（避免阻塞实时控制循环）
  - **不依赖外部服务**（即使 Monitor Daemon 不在线也能正常运行）
  - 发送失败时静默丢弃（不影响比赛）

**Monitor Daemon (独立进程)**
- 职责：
  - 接收来自多个机器人的状态数据（UDP 多播或单播）
  - 按 robot_id 分流并缓存最近数据
  - 异步写入日志文件（按比赛/时间分段）
  - 提供 WebSocket 接口供 GUI 订阅实时数据
  - 管理日志生命周期（比赛开始/结束控制）
- 边界：
  - **不修改机器人行为**
  - **不向机器人发送控制指令**
  - 可以运行在 Nao 本地或外部 PC

**Web GUI (前端)**
- 职责：
  - 通过 WebSocket 订阅 Monitor Daemon 的实时数据
  - 显示多机器人状态面板（电量、姿态、定位等）
  - 显示事件日志流（行为切换、异常等）
  - 提供简单的控制（开始/停止日志记录）
- 边界：
  - **只读数据，不控制机器人**
  - 轻量级，无复杂渲染

**Analysis Tools (离线工具)**
- 职责：
  - 解析日志文件（JSON Lines）
  - 生成统计报告（行为时长、定位精度、球感知率等）
  - 可视化（轨迹图、状态时序图）
  - 对比分析（baseline vs modified）
- 边界：
  - **离线工具，不参与实时系统**

### 1.2 数据流

```
GameController → GameControllerData → RobotStateReporter
                                            ↓
                                    Collect State Data
                                    (FrameInfo, BallModel,
                                     RobotPose, MotionRequest,
                                     StrategyStatus, etc.)
                                            ↓
                                    Format Protobuf
                                            ↓
                                    UDP Send (非阻塞)
                                            ↓
                        ┌───────────────────┴───────────────────┐
                        ↓                                       ↓
                Monitor Daemon                          (丢包容忍)
                (UDP Receiver)
                        ↓
                ┌───────┴───────┐
                ↓               ↓
        Real-time Cache    Log Writer
        (内存队列)         (异步写入)
                ↓               ↓
        WebSocket Server   JSON Lines File
                ↓
            Web GUI
```

### 1.3 线程安全

- 每个机器人实例运行在独立进程中，无共享内存
- Monitor Daemon 使用线程安全队列（`queue.Queue`）
- 日志写入使用独立线程，避免阻塞接收

## 2. 状态数据模型

### 2.1 RobotState 结构

详见 `bhuman_integration/proto/robot_state.proto`

**核心字段**：
- `SystemStatus`: 时间戳、电量、温度、姿态、摔倒状态
- `PerceptionStatus`: 球感知、定位、队友/对手感知
- `DecisionStatus`: 比赛状态、角色、行为、运动请求
- `Event[]`: 事件列表（行为切换、摔倒、球丢失等）

### 2.2 上报策略

**每帧上报 (30Hz)**：
- 基础状态：时间戳、电量、姿态
- 感知状态：球位置、定位、可见性
- 决策状态：角色、行为、运动类型

**事件触发上报**：
- 行为切换、角色切换
- 摔倒/起身
- 球丢失/发现
- 处罚状态变化

**优化**：
- 低频字段（电量）每 10 帧上报一次
- 可配置上报频率（默认每 10 帧发送一次，即 3Hz）

## 3. 通信协议

### 3.1 UDP 通信

**参数**：
- 端口：`10020`
- 多播地址：`239.0.0.1`（可选）
- 序列化：Protobuf

**优势**：
- 非阻塞发送
- 低延迟（< 5ms）
- 容忍丢包
- 支持多播（一对多）

### 3.2 WebSocket 通信

**端口**：`8765`
**协议**：JSON over WebSocket

**消息格式**：
```json
{
  "type": "robot_state",
  "robot_id": "bhuman_1",
  "data": {
    "timestamp": 1234567890,
    "battery": 85.5,
    "position": {"x": 100, "y": 200},
    ...
  }
}
```

## 4. 日志系统

### 4.1 文件格式

**JSON Lines** (每行一个 JSON 对象)：
```json
{"timestamp":1234567,"frame":1,"game_state":"READY","role":"none","motion":"stand",...}
{"timestamp":1234600,"frame":2,"game_state":"READY","role":"none","motion":"stand",...}
```

**优势**：
- 流式写入，无需缓冲整个文件
- 人类可读，便于调试
- 易于解析和增量读取

### 4.2 生命周期管理

**比赛开始**：
- 检测 `game_state` 从 `INITIAL` 变为 `READY`
- 创建新的日志文件：`match_<timestamp>/robot_<team>_<player>.jsonl`

**比赛进行**：
- 异步写入日志（独立线程）
- 每 100 条记录 flush 一次

**比赛结束**：
- 检测 `game_state` 变为 `FINISHED`
- 关闭日志文件
- 生成元数据文件（比赛时长、总帧数等）

### 4.3 文件命名

```
logs/
├── match_20260128_143022/
│   ├── robot_bhuman_1.jsonl
│   ├── robot_bhuman_2.jsonl
│   ├── robot_bhuman_3.jsonl
│   └── match_metadata.json
└── match_20260128_150315/
    └── ...
```

## 5. 性能与实时性

### 5.1 性能指标

- **CPU 开销**：< 1% (B-Human 侧)
- **内存开销**：< 10 MB (B-Human 侧)
- **网络带宽**：~10 KB/s per robot (3Hz 上报)
- **延迟**：< 5ms (UDP 发送)

### 5.2 优化措施

1. **降频上报**：默认每 10 帧发送一次（3Hz），而非 30Hz
2. **非阻塞 I/O**：UDP socket 设置为 `O_NONBLOCK`
3. **静默失败**：发送失败时不打印错误，避免日志洪水
4. **异步日志**：Monitor Daemon 使用独立线程写入文件
5. **内存限制**：实时缓存队列限制为 1000 条，超出则丢弃最旧的
6. **条件编译**：可通过配置完全禁用监控（零开销）

### 5.3 风险控制

**风险 1：UDP 发送阻塞**
- 缓解：设置 `O_NONBLOCK` 标志
- 缓解：发送失败时立即返回，不重试

**风险 2：Protobuf 序列化耗时**
- 缓解：降低上报频率（3Hz）
- 缓解：只序列化必要字段

**风险 3：网络拥塞**
- 缓解：使用 UDP（容忍丢包）
- 缓解：限制数据包大小（< 1KB）

**风险 4：Monitor Daemon 崩溃**
- 缓解：B-Human 侧不依赖 Daemon，发送失败时静默丢弃
- 缓解：Daemon 崩溃不影响机器人运行

## 6. 错误处理

### 6.1 B-Human 侧

- Socket 创建失败：禁用监控，继续运行
- 发送失败：静默丢弃，不打印错误
- 序列化失败：跳过本帧，继续下一帧

### 6.2 Monitor Daemon 侧

- 接收错误：记录日志，继续接收
- 解析错误：跳过该数据包
- 文件写入失败：记录错误，尝试重新打开文件

### 6.3 Web GUI 侧

- WebSocket 断开：自动重连（指数退避）
- 数据解析错误：显示错误提示，继续接收

## 7. 扩展性

### 7.1 支持新字段

1. 在 `robot_state.proto` 中添加新字段
2. 重新生成 C++ 和 Python 代码
3. 在 `RobotStateReporter::collectState()` 中填充新字段
4. 更新 Web GUI 显示逻辑

### 7.2 支持新事件

1. 在 `robot_state.proto` 的 `EventType` 枚举中添加新类型
2. 在 `RobotStateReporter::detectEvents()` 中添加检测逻辑

### 7.3 支持新通信方式

- 可替换 UDP 为 TCP（需要修改 socket 创建和发送逻辑）
- 可替换 Protobuf 为 JSON（需要修改序列化逻辑）
- 可添加 MQTT 支持（适合云端监控）

## 8. 测试策略

### 8.1 单元测试

- RobotStateReporter 模块加载测试
- Protobuf 序列化/反序列化测试
- 事件检测逻辑测试

### 8.2 集成测试

- B-Human + Monitor Daemon 端到端测试
- 多机器人并发测试
- 网络丢包模拟测试

### 8.3 性能测试

- CPU 和内存占用测试
- 网络带宽测试
- 延迟测试（发送到接收的时间）

## 9. 部署方案

### 9.1 仿真环境 (SimRobot)

- B-Human 运行在本地
- Monitor Daemon 运行在本地
- Web GUI 通过浏览器访问

### 9.2 真实机器人

**方案 A：Daemon 运行在外部 PC**
- Nao 通过 WiFi 发送 UDP 到 PC
- PC 运行 Monitor Daemon 和 Web GUI

**方案 B：Daemon 运行在 Nao 本地**
- Nao 本地运行轻量级 Daemon
- 日志写入 Nao 存储
- 比赛后通过 SSH 下载日志

**推荐**：方案 A（避免 Nao 本地 I/O 开销）
