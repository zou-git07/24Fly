# Web 监控系统架构设计
# RoboCup SPL - SimRobot + bhuman + GameController 共存方案

## 任务 1：GC 与监控系统的职责与端口关系

### 1.1 GameController 在 SimRobot 中的作用

**通信方式：**
- **协议**：UDP 广播
- **端口**：3838（GC → Robot）、3939（Robot → GC）
- **消息格式**：RoboCupGameControlData 结构体（二进制）

**控制对象：**
- 比赛状态（INITIAL / READY / SET / PLAYING / FINISHED）
- 机器人罚下（PENALTY）
- 比分、剩余时间
- 踢球权（Kick-off）
- 机器人是否存活（心跳检测）

**关键特性：**
- GC 是"权威控制源"，所有机器人必须服从
- bhuman 的 GameControllerProvider 模块接收 GC 消息
- 机器人定期向 GC 发送心跳（RoboCupGameControlReturnData）

### 1.2 监控系统的正确定位

**定位原则：**
```
监控系统 = 旁路观察者（Observer），不是控制者（Controller）
```

**通信关系：**

```
┌─────────────────┐
│  GameController │  (控制者)
│   Port: 3838    │
└────────┬────────┘
         │ UDP Broadcast (RoboCupGameControlData)
         ↓
┌─────────────────────────────────────────┐
│           SimRobot (单进程)              │
│  ┌──────────┐  ┌──────────┐            │
│  │ bhuman_1 │  │ bhuman_2 │  ... x10   │
│  │ Team 5   │  │ Team 70  │            │
│  └────┬─────┘  └────┬─────┘            │
│       │             │                   │
│  ┌────▼─────────────▼─────┐            │
│  │  RobotStateReporter    │            │
│  │  (自定义监控模块)       │            │
│  └────────┬────────────────┘            │
└───────────┼─────────────────────────────┘
            │ UDP (JSON, Port 10020)
            ↓
┌───────────────────────────┐
│   Monitor Daemon (Python) │  (观察者)
│   - UDP Receiver          │
│   - WebSocket Server      │
│   - Log Writer            │
└───────────┬───────────────┘
            │ WebSocket (Port 8765)
            ↓
┌───────────────────────────┐
│   Web Browser (前端)       │
│   - 实时监控界面           │
│   - 历史日志查看           │
└───────────────────────────┘
```

**关键点：**
1. ✅ 监控系统**不与 SimRobot 直接通信**
2. ✅ 监控系统**不与 GC 通信**
3. ✅ 监控系统**只与 bhuman 通信**（通过自定义模块）
4. ✅ 监控系统**不影响比赛逻辑**

### 1.3 端口与协议设计原则

**端口分配：**

| 组件 | 端口 | 协议 | 方向 | 用途 |
|------|------|------|------|------|
| GameController | 3838 | UDP | GC → Robot | 比赛控制 |
| GameController | 3939 | UDP | Robot → GC | 心跳回传 |
| **Monitor System** | **10020** | **UDP** | **Robot → Monitor** | **状态上报** |
| **Web Server** | **8765** | **WebSocket** | **Monitor ↔ Browser** | **实时推送** |
| **Web Server** | **8080** | **HTTP** | **Browser → Monitor** | **日志查询** |

**设计原则：**
1. **端口隔离**：监控系统使用完全不同的端口段（10000+）
2. **单向通信**：Robot → Monitor（只上报，不接收控制）
3. **容错设计**：Monitor 挂掉不影响 SimRobot 和 GC
4. **协议简单**：使用 JSON（易调试、易扩展）

---

## 任务 2：Web 实时监控系统的总体架构设计

### 2.1 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    SimRobot + bhuman                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  RobotStateReporter Module (C++)                     │   │
│  │  - 每帧采集状态                                       │   │
│  │  - 构造 JSON 消息                                     │   │
│  │  - UDP 发送到 127.0.0.1:10020                        │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ UDP (JSON)
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Monitor Daemon (Python - FastAPI)              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  1. UDP Receiver Thread                              │   │
│  │     - 接收 Robot 状态                                 │   │
│  │     - 解析 JSON                                       │   │
│  │     - 更新内存状态表                                  │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  2. Log Writer Thread                                │   │
│  │     - 写入 JSON Lines 文件                            │   │
│  │     - 按 match_id / robot_id 分文件                   │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  3. WebSocket Server                                 │   │
│  │     - 实时推送状态到前端                              │   │
│  │     - 广播到所有连接的客户端                          │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  4. HTTP API Server                                  │   │
│  │     - GET /api/matches (获取比赛列表)                 │   │
│  │     - GET /api/match/{id}/robots (获取机器人列表)     │   │
│  │     - GET /api/logs/{match}/{robot} (获取日志)        │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ WebSocket + HTTP
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Web Frontend (HTML + JS)                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  实时监控页面 (index.html)                            │   │
│  │  - WebSocket 连接                                     │   │
│  │  - 动态更新机器人卡片                                 │   │
│  │  - 显示：ID / 行为 / 摔倒 / 电量 / 球                 │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  历史日志页面 (logs.html)                             │   │
│  │  - 比赛选择器                                         │   │
│  │  - 机器人选择器                                       │   │
│  │  - 时间轴可视化                                       │   │
│  │  - 事件列表                                           │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 模块职责划分


#### 模块 1：RobotStateReporter (C++ - bhuman)
**职责：**
- 从 bhuman 内部模块读取状态
- 构造 JSON 消息
- UDP 发送（非阻塞）

**输出格式：**
```json
{
  "timestamp": 123456,
  "robot_id": "5_3",
  "team_id": 5,
  "player_number": 3,
  "battery": 85.5,
  "temperature": 42.0,
  "fallen": false,
  "behavior": "striker",
  "motion": "walk",
  "ball_visible": true,
  "ball_x": 1500.0,
  "ball_y": -200.0,
  "pos_x": -1000.0,
  "pos_y": 2000.0,
  "rotation": 1.57,
  "events": ["ball_lost", "penalty_received"]
}
```

#### 模块 2：Monitor Daemon (Python)
**职责：**
- UDP 接收 + 解析
- 维护内存状态表（dict）
- 写入日志文件
- WebSocket 广播
- HTTP API 服务

**内存状态表结构：**
```python
robot_states = {
    "5_1": {
        "last_update": 1234567890.123,
        "data": { ... }  # 最新状态
    },
    "5_2": { ... },
    ...
}
```

#### 模块 3：Web Frontend (HTML + JS)
**职责：**
- WebSocket 连接管理
- 动态渲染机器人卡片
- 历史日志查询和展示
- 用户交互

### 2.3 数据流设计

**实时数据流（Robot → Web）：**
```
bhuman (C++) 
  → UDP JSON (10020) 
  → Monitor Daemon (Python)
  → WebSocket (8765)
  → Browser (JS)
  → DOM Update
```

**历史日志数据流（Log → Web）：**
```
Browser (JS)
  → HTTP GET /api/logs/{match}/{robot}
  → Monitor Daemon (Python)
  → Read JSON Lines file (分页/流式)
  → HTTP Response (JSON Array)
  → Browser (JS)
  → Chart / Timeline Render
```

**多机器人区分：**
- **唯一标识**：`robot_id = f"{team_id}_{player_number}"`
- **前端维护**：`Map<robot_id, RobotState>`
- **自动新增**：收到新 robot_id 时动态创建卡片
- **超时移除**：5 秒无更新则标记为 offline

---

## 任务 3：实时网页监控页面设计

### 3.1 页面布局（最小可用版）

```html
<!DOCTYPE html>
<html>
<head>
    <title>Robot Monitor - Live</title>
    <style>
        .robot-card {
            border: 2px solid #ccc;
            padding: 10px;
            margin: 10px;
            display: inline-block;
            width: 200px;
        }
        .robot-card.online { border-color: green; }
        .robot-card.offline { border-color: red; }
        .fallen { background-color: #ffcccc; }
    </style>
</head>
<body>
    <h1>🤖 Robot Monitor - Live</h1>
    <div id="robots"></div>
    <script src="monitor.js"></script>
</body>
</html>
```

### 3.2 WebSocket 消息格式

**服务器 → 客户端（实时状态）：**
```json
{
  "type": "robot_update",
  "data": {
    "robot_id": "5_3",
    "timestamp": 123456,
    "battery": 85.5,
    "fallen": false,
    "behavior": "striker",
    "motion": "walk",
    "ball_visible": true,
    "events": ["goal_scored"]
  }
}
```

**服务器 → 客户端（机器人离线）：**
```json
{
  "type": "robot_offline",
  "robot_id": "5_3"
}
```

### 3.3 前端状态管理（monitor.js）


```javascript
// 机器人状态表
const robotStates = new Map();

// WebSocket 连接
const ws = new WebSocket('ws://localhost:8765');

ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    
    if (msg.type === 'robot_update') {
        updateRobot(msg.data);
    } else if (msg.type === 'robot_offline') {
        markOffline(msg.robot_id);
    }
};

function updateRobot(data) {
    const robotId = data.robot_id;
    
    // 更新状态表
    robotStates.set(robotId, {
        ...data,
        lastUpdate: Date.now()
    });
    
    // 更新 DOM
    let card = document.getElementById(`robot-${robotId}`);
    if (!card) {
        card = createRobotCard(robotId);
        document.getElementById('robots').appendChild(card);
    }
    
    // 更新卡片内容
    card.querySelector('.battery').textContent = `🔋 ${data.battery}%`;
    card.querySelector('.behavior').textContent = `🧠 ${data.behavior}`;
    card.querySelector('.fallen').textContent = data.fallen ? '🤸 FALLEN' : '✅ OK';
    card.querySelector('.ball').textContent = data.ball_visible ? '⚽ Ball' : '❌ No Ball';
    card.className = `robot-card online ${data.fallen ? 'fallen' : ''}`;
}

function createRobotCard(robotId) {
    const card = document.createElement('div');
    card.id = `robot-${robotId}`;
    card.className = 'robot-card';
    card.innerHTML = `
        <h3>Robot ${robotId}</h3>
        <div class="battery">🔋 --</div>
        <div class="behavior">🧠 --</div>
        <div class="fallen">--</div>
        <div class="ball">--</div>
    `;
    return card;
}

// 定期检查超时
setInterval(() => {
    const now = Date.now();
    robotStates.forEach((state, robotId) => {
        if (now - state.lastUpdate > 5000) {
            markOffline(robotId);
        }
    });
}, 1000);

function markOffline(robotId) {
    const card = document.getElementById(`robot-${robotId}`);
    if (card) {
        card.className = 'robot-card offline';
    }
}
```

---

## 任务 4：比赛结束后在网页中查看完整日志

### 4.1 日志查看页面设计

**页面结构（logs.html）：**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Robot Monitor - Logs</title>
</head>
<body>
    <h1>📊 Match Logs</h1>
    
    <!-- 比赛选择 -->
    <select id="match-select">
        <option>Loading...</option>
    </select>
    
    <!-- 机器人选择 -->
    <select id="robot-select">
        <option>Select a match first</option>
    </select>
    
    <!-- 时间轴 -->
    <div id="timeline"></div>
    
    <!-- 事件列表 -->
    <div id="events"></div>
    
    <!-- 原始数据 -->
    <pre id="raw-data"></pre>
    
    <script src="logs.js"></script>
</body>
</html>
```

### 4.2 HTTP API 设计

**API 1：获取比赛列表**
```
GET /api/matches

Response:
{
  "matches": [
    {
      "id": "match_20260128_145538",
      "start_time": "2026-01-28T14:55:38",
      "robot_count": 10,
      "total_packets": 3592
    }
  ]
}
```

**API 2：获取比赛中的机器人列表**
```
GET /api/match/{match_id}/robots

Response:
{
  "robots": [
    {"robot_id": "5_1", "packet_count": 319},
    {"robot_id": "5_2", "packet_count": 238},
    ...
  ]
}
```

**API 3：获取机器人日志（分页）**
```
GET /api/logs/{match_id}/{robot_id}?offset=0&limit=100

Response:
{
  "robot_id": "5_1",
  "total_packets": 319,
  "offset": 0,
  "limit": 100,
  "data": [
    { "timestamp": 123, "battery": 100, ... },
    { "timestamp": 456, "battery": 99.5, ... },
    ...
  ]
}
```

### 4.3 避免大文件加载的策略

**策略 1：分页加载**
```python
def get_logs(match_id, robot_id, offset=0, limit=100):
    file_path = f"logs/{match_id}/robot_{robot_id}.jsonl"
    
    with open(file_path, 'r') as f:
        # 跳过前 offset 行
        for _ in range(offset):
            f.readline()
        
        # 读取 limit 行
        data = []
        for _ in range(limit):
            line = f.readline()
            if not line:
                break
            data.append(json.loads(line))
    
    return data
```

**策略 2：流式传输（大文件）**
```python
from fastapi.responses import StreamingResponse

def stream_logs(match_id, robot_id):
    file_path = f"logs/{match_id}/robot_{robot_id}.jsonl"
    
    def generate():
        with open(file_path, 'r') as f:
            yield '{"data": ['
            first = True
            for line in f:
                if not first:
                    yield ','
                yield line.strip()
                first = False
            yield ']}'
    
    return StreamingResponse(generate(), media_type="application/json")
```

**策略 3：时间范围查询**
```python
def get_logs_by_time(match_id, robot_id, start_time, end_time):
    # 只返回指定时间范围内的数据
    data = []
    with open(file_path, 'r') as f:
        for line in f:
            entry = json.loads(line)
            if start_time <= entry['timestamp'] <= end_time:
                data.append(entry)
    return data
```

---

## 任务 5：多机器人 + GC 共存的工程细节


### 5.1 SimRobot 单进程多机器人数据区分

**问题：**
SimRobot 中 10 个机器人运行在同一进程中，如何保证数据不混淆？

**解决方案：**

**方法 1：bhuman 内部已有机制**
```cpp
// bhuman 中每个机器人实例都有独立的：
- Settings::teamNumber  (队伍编号，如 5 或 70)
- Settings::playerNumber (球员编号，1-5)

// RobotStateReporter 中使用：
std::string robotId = std::to_string(theSettings.teamNumber) + "_" + 
                      std::to_string(theSettings.playerNumber);
```

**方法 2：UDP 发送时携带标识**
```cpp
void RobotStateReporter::update(DummyRepresentation& dummy) {
    nlohmann::json msg;
    msg["robot_id"] = getRobotId();  // "5_3"
    msg["team_id"] = theSettings.teamNumber;
    msg["player_number"] = theSettings.playerNumber;
    // ... 其他数据
    
    sendUDP(msg.dump());
}
```

**方法 3：Monitor Daemon 端验证**
```python
def handle_udp_packet(data):
    msg = json.loads(data)
    robot_id = msg.get('robot_id')
    
    # 验证格式
    if not re.match(r'^\d+_\d+$', robot_id):
        logger.warning(f"Invalid robot_id: {robot_id}")
        return
    
    # 更新状态表
    robot_states[robot_id] = msg
```

### 5.2 GC 与监控系统的控制与监听关系

**职责划分：**

| 系统 | 角色 | 通信方向 | 影响范围 |
|------|------|----------|----------|
| **GameController** | **控制者** | GC → Robot | 比赛状态、罚下、比分 |
| **Monitor System** | **观察者** | Robot → Monitor | 状态采集、日志、可视化 |

**关键原则：**
1. ✅ **GC 控制，Monitor 观察**
2. ✅ **GC 可以改变机器人行为，Monitor 不能**
3. ✅ **Monitor 不监听 GC 的消息**
4. ✅ **Monitor 不向 Robot 发送任何控制指令**

**实现细节：**
```cpp
// bhuman 中的模块依赖关系：
MODULE(RobotStateReporter)
  REQUIRES(FrameInfo)
  REQUIRES(RobotHealth)
  REQUIRES(BehaviorStatus)
  REQUIRES(MotionInfo)
  REQUIRES(BallModel)
  REQUIRES(RobotPose)
  REQUIRES(Settings)
  // 注意：不依赖 GameControllerData！
  // 监控系统不关心 GC 的控制指令
END_MODULE
```

### 5.3 容错设计：任一组件挂掉的影响

**场景 1：Monitor Daemon 挂掉**
```
SimRobot + bhuman: ✅ 正常运行
GameController: ✅ 正常控制
RobotStateReporter: ✅ 继续发送 UDP（无人接收，但不阻塞）
影响：❌ 无法查看实时监控和日志
```

**实现要点：**
```cpp
// RobotStateReporter 中使用非阻塞 UDP
void sendUDP(const std::string& data) {
    try {
        socket.send_to(boost::asio::buffer(data), endpoint);
        // 不等待响应，立即返回
    } catch (const std::exception& e) {
        // 发送失败也不影响主逻辑
        // 可选：记录到本地日志
    }
}
```

**场景 2：GameController 挂掉**
```
SimRobot + bhuman: ✅ 正常运行（但无比赛控制）
Monitor System: ✅ 正常监控
影响：❌ 机器人无法接收比赛状态（会进入 INITIAL 状态）
```

**场景 3：SimRobot 挂掉**
```
GameController: ✅ 继续运行（无机器人连接）
Monitor System: ✅ 继续运行（无数据接收）
影响：❌ 整个仿真停止
```

**场景 4：Web Frontend 关闭**
```
SimRobot + bhuman: ✅ 正常运行
Monitor Daemon: ✅ 继续接收和记录日志
影响：❌ 无法查看实时界面（但日志仍在记录）
```

---

## 任务 6：最小可运行实现方案（MVP）

### 6.1 MVP 目标

**实时监控：**
- ✅ 显示至少 2 台机器人
- ✅ 显示：行为 + 摔倒状态 + 电量 + 球可见性
- ✅ 自动刷新（WebSocket）

**历史日志：**
- ✅ 比赛结束后可查看
- ✅ 选择机器人
- ✅ 查看完整时间序列

### 6.2 实现步骤

**Step 1：确认 RobotStateReporter 已集成**
```bash
# 已完成（当前状态）
ls Src/Modules/Infrastructure/RobotStateReporter/
# RobotStateReporter.h
# RobotStateReporter.cpp
```

**Step 2：升级 Monitor Daemon（添加 WebSocket + HTTP）**
```bash
cd RobotMonitoringSystem/monitor_daemon
# 创建新的 web_monitor.py
```

**Step 3：创建 Web 前端**
```bash
cd RobotMonitoringSystem/web_monitor
# 创建 index.html (实时监控)
# 创建 logs.html (历史日志)
# 创建 monitor.js
# 创建 logs.js
```

**Step 4：启动系统**
```bash
# Terminal 1: 启动 Monitor Daemon
python3 RobotMonitoringSystem/monitor_daemon/web_monitor.py

# Terminal 2: 启动 SimRobot
./Build/Linux/SimRobot/Develop/SimRobot Config/Scenes/GameFast.ros3

# Terminal 3: 启动 GameController (可选)
# (如果需要比赛控制)

# Browser: 打开监控页面
http://localhost:8080
```

### 6.3 文件清单

**需要创建的文件：**
```
RobotMonitoringSystem/
├── monitor_daemon/
│   └── web_monitor.py          # 新：集成 WebSocket + HTTP 的守护进程
├── web_monitor/
│   ├── index.html              # 新：实时监控页面
│   ├── logs.html               # 新：历史日志页面
│   ├── monitor.js              # 新：实时监控逻辑
│   ├── logs.js                 # 新：日志查看逻辑
│   └── style.css               # 新：样式
└── docs/
    └── WEB_MONITOR_ARCHITECTURE.md  # 本文档
```

**已有文件（复用）：**
```
Src/Modules/Infrastructure/RobotStateReporter/  # 已完成
Config/Scenarios/Default/robotStateReporter.cfg  # 已完成
Config/Scenarios/Default/threads.cfg             # 已完成
```

---

## 总结

### 核心设计原则

1. **职责分离**：GC 控制，Monitor 观察
2. **端口隔离**：避免冲突（10020 / 8765 / 8080）
3. **单向通信**：Robot → Monitor（只上报）
4. **容错设计**：任一组件挂掉不影响其他
5. **协议简单**：JSON（易调试、易扩展）

### 技术栈

- **后端**：Python + FastAPI + WebSocket
- **前端**：HTML + JavaScript（原生，无框架）
- **通信**：UDP (Robot → Daemon) + WebSocket (Daemon → Browser)
- **存储**：JSON Lines 文件

### 下一步

准备好开始实现了吗？我可以帮你：
1. 创建 `web_monitor.py`（集成 WebSocket + HTTP）
2. 创建前端页面（`index.html` + `logs.html`）
3. 测试完整流程

请告诉我是否开始实现！🚀
