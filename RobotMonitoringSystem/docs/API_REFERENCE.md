# API 参考文档

## Protobuf 消息定义

### RobotState

完整的机器人状态消息。

```protobuf
message RobotState {
  SystemStatus system = 1;
  PerceptionStatus perception = 2;
  DecisionStatus decision = 3;
  repeated Event events = 4;
  string robot_id = 5;
}
```

### SystemStatus

系统运行状态。

**字段**：
- `timestamp_ms` (uint64): 系统时间戳（毫秒）
- `frame_number` (uint32): 帧计数器
- `cycle_time_ms` (uint32): 本帧耗时（毫秒）
- `battery_charge` (float): 电量百分比 [0-100]
- `battery_current` (float): 电流（安培）
- `cpu_temperature` (float): CPU 温度（摄氏度）
- `orientation` (Orientation): 姿态（横滚、俯仰、偏航）
- `is_upright` (bool): 是否直立
- `is_fallen` (bool): 是否摔倒

### PerceptionStatus

感知状态。

**字段**：
- `ball` (BallInfo): 球感知信息
- `localization` (LocalizationInfo): 定位信息
- `teammates_seen` (repeated uint32): 看到的队友编号列表
- `opponents_count` (uint32): 看到的对手数量

### DecisionStatus

决策状态。

**字段**：
- `game_state` (GameState): 比赛状态（INITIAL/READY/SET/PLAYING/FINISHED）
- `team_number` (uint32): 队伍编号
- `player_number` (uint32): 球员编号
- `is_penalized` (bool): 是否被处罚
- `role` (string): 角色（striker/supporter/defender 等）
- `active_behavior` (string): 当前行为
- `motion_type` (MotionType): 运动类型（STAND/WALK/KICK/GET_UP/SPECIAL）
- `walk_speed_x` (float): 行走速度 X（mm/s）
- `walk_speed_y` (float): 行走速度 Y（mm/s）
- `walk_speed_rot` (float): 旋转速度（rad/s）

### Event

事件消息。

**字段**：
- `type` (EventType): 事件类型
- `description` (string): 事件描述
- `timestamp_ms` (uint64): 事件时间戳

**EventType 枚举**：
- `BEHAVIOR_CHANGED` (0): 行为切换
- `ROLE_CHANGED` (1): 角色切换
- `FALLEN` (2): 摔倒
- `GOT_UP` (3): 起身
- `BALL_LOST` (4): 球丢失
- `BALL_FOUND` (5): 球发现
- `PENALIZED` (6): 被处罚
- `UNPENALIZED` (7): 解除处罚
- `COMMUNICATION_ERROR` (8): 通信错误
- `LOCALIZATION_LOST` (9): 定位丢失
- `KICK_EXECUTED` (10): 踢球执行

## WebSocket API

### 连接

```
ws://localhost:8765
```

### 消息格式

所有消息使用 JSON 格式。

### 客户端 -> 服务器

#### 获取机器人列表

```json
{
  "type": "get_robots"
}
```

**响应**：
```json
{
  "type": "robot_list",
  "robots": ["bhuman_1", "bhuman_2", ...]
}
```

#### 获取机器人状态

```json
{
  "type": "get_state",
  "robot_id": "bhuman_1"
}
```

**响应**：
```json
{
  "type": "robot_state",
  "robot_id": "bhuman_1",
  "data": {
    "system": {...},
    "perception": {...},
    "decision": {...},
    "events": [...]
  }
}
```

### 服务器 -> 客户端

#### 欢迎消息

连接建立后自动发送：
```json
{
  "type": "welcome",
  "message": "Connected to Robot Monitoring System"
}
```

#### 状态更新（广播）

每次收到机器人状态时自动广播：
```json
{
  "type": "robot_state",
  "robot_id": "bhuman_1",
  "data": {
    "system": {
      "timestamp_ms": 1234567890,
      "battery_charge": 85.5,
      ...
    },
    ...
  }
}
```

#### 错误消息

```json
{
  "type": "error",
  "message": "Error description"
}
```

## 日志文件格式

### JSON Lines 格式

每行一个 JSON 对象，表示一个状态快照。

**示例**：
```json
{"system":{"timestamp_ms":1234567,"frame_number":1,"battery_charge":100.0,...},"perception":{...},"decision":{...},"events":[],"robot_id":"bhuman_1"}
{"system":{"timestamp_ms":1234600,"frame_number":2,"battery_charge":99.9,...},"perception":{...},"decision":{...},"events":[],"robot_id":"bhuman_1"}
```

### 元数据文件

每场比赛生成一个 `match_metadata.json`：

```json
{
  "match_id": "20260128_143022",
  "start_time": "20260128_143022",
  "robots": ["bhuman_1", "bhuman_2", "bhuman_3"]
}
```

## Python API

### LogParser

解析日志文件并生成统计报告。

```python
from log_parser import LogParser

parser = LogParser('logs/match_20260128_143022/robot_bhuman_1.jsonl')
parser.parse()
stats = parser.get_statistics()
parser.print_report()
```

**返回的统计数据**：
```python
{
  'total_frames': 1000,
  'duration_ms': 300000,
  'battery': {
    'initial': 100.0,
    'final': 85.5,
    'consumed': 14.5,
    'average': 92.7
  },
  'ball_perception': {
    'visible_frames': 450,
    'visible_rate': 0.45
  },
  'localization': {
    'superb_rate': 0.8,
    'okay_rate': 0.15,
    'poor_rate': 0.05
  },
  'motion': {
    'STAND': 0.2,
    'WALK': 0.7,
    'KICK': 0.05,
    'GET_UP': 0.05
  },
  'events': {
    0: 5,  # BEHAVIOR_CHANGED
    4: 10, # BALL_LOST
    5: 10  # BALL_FOUND
  }
}
```

## C++ API

### RobotStateReporter

B-Human 模块，负责采集和发送状态。

**配置参数**：
```cpp
DEFINES_PARAMETERS(
{,
  (bool)(true) enabled,                           // 是否启用
  (std::string)("239.0.0.1") monitorAddress,      // 监控地址
  (int)(10020) monitorPort,                       // 监控端口
  (int)(10) reportIntervalFrames,                 // 上报间隔（帧）
  (bool)(true) detectEvents,                      // 是否检测事件
})
```

**输出表示**：
```cpp
STREAMABLE(RobotStateReporterOutput,
{,
  (bool)(false) isReporting,          // 是否正在上报
  (unsigned)(0) reportCount,          // 已上报次数
  (unsigned)(0) lastReportTime,       // 上次上报时间戳
  (unsigned)(0) sendErrors,           // 发送错误次数
})
```

**使用示例**：
```cpp
// 在其他模块中查询监控状态
if(theRobotStateReporterOutput.isReporting)
{
  OUTPUT_TEXT("Monitoring active, " << theRobotStateReporterOutput.reportCount << " reports sent");
}
```

## 性能指标

### B-Human 侧

- **CPU 开销**：< 1% (3Hz 上报频率)
- **内存开销**：< 10 MB
- **网络带宽**：~10 KB/s per robot
- **延迟**：< 5ms (UDP 发送)

### Monitor Daemon 侧

- **CPU 开销**：< 5% (接收 + 日志写入)
- **内存开销**：< 100 MB (缓存 1000 条状态)
- **磁盘 I/O**：~50 MB per 10-minute match

## 扩展性

### 添加新字段

1. 修改 `robot_state.proto`
2. 重新生成代码：`protoc --cpp_out=. --python_out=. robot_state.proto`
3. 在 `RobotStateReporter::collectState()` 中填充新字段
4. 更新 Web GUI 显示逻辑

### 添加新事件类型

1. 在 `robot_state.proto` 的 `EventType` 枚举中添加
2. 在 `RobotStateReporter::detectEvents()` 中添加检测逻辑
3. 更新 Web GUI 的事件名称映射

## 安全性

### 网络安全

- UDP 通信未加密，仅适用于可信网络
- 建议在生产环境中使用 VPN 或专用网络
- 可以添加消息签名验证（需要修改代码）

### 数据隐私

- 日志文件包含完整的机器人状态，注意保护
- 建议定期清理旧日志文件
- 不要在公共网络上暴露 WebSocket 端口
