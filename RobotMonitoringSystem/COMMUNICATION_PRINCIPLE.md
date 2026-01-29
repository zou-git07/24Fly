# 🔄 机器人监控系统通信原理详解

## 📋 系统概览

这是一个**三层架构**的实时监控系统：

```
┌─────────────────────────────────────────────────────────────┐
│                        浏览器（前端）                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  HTML + CSS + JavaScript                             │   │
│  │  - 显示机器人卡片                                     │   │
│  │  - WebSocket 客户端                                   │   │
│  │  - 实时更新 DOM                                       │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↕ WebSocket (2 Hz)
┌─────────────────────────────────────────────────────────────┐
│              Monitor Daemon（Python 后端）                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  FastAPI + asyncio                                   │   │
│  │  - UDP 接收器（独立线程）                             │   │
│  │  - WebSocket 服务器                                   │   │
│  │  - 日志写入器                                         │   │
│  │  - 状态管理器                                         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↕ UDP (50 Hz)
┌─────────────────────────────────────────────────────────────┐
│                    SimRobot（C++ 模拟器）                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  10 个虚拟机器人                                      │   │
│  │  - RobotStateReporter 模块                           │   │
│  │  - 每个机器人独立发送状态                             │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 第一层：SimRobot → Monitor Daemon（UDP 通信）

### 1.1 数据源：RobotStateReporter

**位置**：`Src/Modules/Infrastructure/RobotStateReporter.cpp`

**工作原理**：
```cpp
// 每个机器人每帧（约 50 Hz）执行一次
void RobotStateReporter::update(RobotState& robotState) {
    // 1. 收集机器人状态
    json data = {
        {"robot_id", theRobotInfo.number},
        {"timestamp", theFrameInfo.time},
        {"battery", theBatteryState.charge},
        {"temperature", theBatteryState.temperature},
        {"fallen", theFallDownState.state != FallDownState::upright},
        {"behavior", theBehaviorStatus.activity},
        {"motion", theMotionInfo.executedPhase},
        {"ball_visible", theBallModel.estimate.valid},
        {"ball_x", theBallModel.estimate.position.x()},
        {"ball_y", theBallModel.estimate.position.y()},
        {"pos_x", theRobotPose.translation.x()},
        {"pos_y", theRobotPose.translation.y()},
        {"rotation", theRobotPose.rotation}
    };
    
    // 2. 通过 UDP 发送到 127.0.0.1:10020
    socket.sendto(data.dump(), ("127.0.0.1", 10020));
}
```

**数据格式**（JSON）：
```json
{
  "robot_id": "5_1",
  "timestamp": 143732,
  "battery": 100.0,
  "temperature": 40.0,
  "fallen": false,
  "behavior": "unknown",
  "motion": "stand",
  "ball_visible": true,
  "ball_x": 5164.44,
  "ball_y": -417.62,
  "pos_x": -4035.33,
  "pos_y": 144.88,
  "rotation": 0.16
}
```

**频率**：每个机器人约 5 Hz，10 个机器人总共约 **50 个 UDP 包/秒**

---

### 1.2 UDP 接收：Monitor Daemon

**位置**：`RobotMonitoringSystem/monitor_daemon/web_monitor.py`

**工作原理**：

```python
class UDPReceiver:
    def __init__(self):
        # 创建 UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 绑定到 0.0.0.0:10020（监听所有网卡）
        self.sock.bind(('0.0.0.0', 10020))
        self.running = True
    
    def start(self):
        # 在独立线程中运行（不阻塞主事件循环）
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
    
    def run(self):
        while self.running:
            # 接收 UDP 数据包（最大 4096 字节）
            data, addr = self.sock.recvfrom(4096)
            
            # 解析 JSON
            msg = json.loads(data.decode('utf-8'))
            robot_id = msg.get('robot_id')
            
            # 更新状态表（只保留最新状态）
            msg['last_update'] = time.time()
            robot_states[robot_id] = msg
            
            # 写入日志文件
            write_log(robot_id, msg)
```

**关键点**：
1. **独立线程**：UDP 接收在独立线程中，不阻塞 asyncio 事件循环
2. **状态表**：`robot_states` 是一个字典，只保留每个机器人的最新状态
3. **日志写入**：每个数据包都写入 JSON Lines 文件

---

## 🔄 第二层：Monitor Daemon 内部处理

### 2.1 数据流架构

```
UDP 接收线程 (50 Hz)
    ↓
robot_states (Dict)  ← 只保留最新状态
    ↓
broadcast_worker (asyncio, 2 Hz)  ← 定时收集快照
    ↓
ClientManager  ← 管理所有 WebSocket 客户端
    ↓
WebSocketClient (每个客户端独立队列)
    ↓
sender_loop (独立协程)  ← 发送消息
    ↓
WebSocket 连接
```

### 2.2 关键组件

#### A. 状态表（robot_states）

```python
# 全局字典，只保留最新状态
robot_states: Dict[str, dict] = {}

# 例如：
robot_states = {
    "5_1": {
        "robot_id": "5_1",
        "timestamp": 143732,
        "battery": 100.0,
        "last_update": 1769659584.02
    },
    "5_2": {...},
    ...
}
```

**作用**：
- 高频 UDP 数据（50 Hz）直接覆盖旧值
- 中间状态自动丢弃
- WebSocket 只推送最新快照

---

#### B. 广播工作器（broadcast_worker）

```python
async def broadcast_worker():
    """定期推送快照（2 Hz）"""
    while True:
        await asyncio.sleep(0.5)  # 500ms = 2 Hz
        
        # 收集所有机器人最新状态
        snapshot = []
        now = time.time()
        
        for robot_id, state in robot_states.items():
            is_online = (now - state.get('last_update', 0)) < 5.0
            snapshot.append({
                "robot_id": robot_id,
                "online": is_online,
                **state
            })
        
        if snapshot:
            # 批量推送（一次发送所有机器人）
            message = json.dumps({
                "type": "snapshot",
                "timestamp": now,
                "robots": snapshot
            })
            
            await client_manager.broadcast(message)
```

**关键点**：
- **节流**：50 Hz 输入 → 2 Hz 输出（减少 96%）
- **聚合**：一次推送所有机器人（批量处理）
- **在线检测**：5 秒无数据标记为离线

---

#### C. 客户端管理器（ClientManager）

```python
class ClientManager:
    def __init__(self):
        self.clients: Set[WebSocketClient] = set()
        self.lock = asyncio.Lock()
    
    async def broadcast(self, message: str):
        """广播消息到所有客户端（非阻塞）"""
        async with self.lock:
            for client in self.clients:
                if client.active:
                    # 非阻塞发送（放入队列）
                    await client.send_safe(message)
```

**作用**：
- 管理所有 WebSocket 连接
- 广播消息到所有客户端
- 隔离慢客户端（不影响其他客户端）

---

#### D. WebSocket 客户端（WebSocketClient）

```python
class WebSocketClient:
    def __init__(self, websocket):
        self.websocket = websocket
        self.send_queue = asyncio.Queue(maxsize=10)  # 发送队列
        self.active = True
        self.error_count = 0
    
    async def send_safe(self, message: str):
        """安全发送（不阻塞）"""
        try:
            # 放入队列（带超时）
            await asyncio.wait_for(
                self.send_queue.put(message),
                timeout=0.1
            )
        except asyncio.TimeoutError:
            # 队列满，丢弃最旧的消息
            self.send_queue.get_nowait()
            await self.send_queue.put(message)
    
    async def sender_loop(self):
        """发送循环（独立协程）"""
        while self.active:
            # 从队列获取消息
            message = await self.send_queue.get()
            
            # 发送（带重试）
            retry = 0
            while retry < 3:
                try:
                    await self.websocket.send_text(message)
                    break
                except Exception:
                    retry += 1
                    await asyncio.sleep(0.1 * retry)
```

**关键点**：
- **独立队列**：每个客户端有自己的发送队列
- **非阻塞**：发送失败不影响其他客户端
- **重试机制**：发送失败自动重试 3 次
- **慢客户端保护**：队列满时丢弃旧消息

---

## 🌐 第三层：Monitor Daemon → 浏览器（WebSocket 通信）

### 3.1 WebSocket 连接建立

**后端**：
```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # 1. 接受连接
    await websocket.accept()
    
    # 2. 创建客户端对象
    client = WebSocketClient(websocket)
    await client_manager.add(client)
    
    # 3. 启动发送循环
    sender_task = asyncio.create_task(client.sender_loop())
    
    # 4. 发送初始快照
    snapshot = [...]
    await client.send_safe(json.dumps({
        "type": "snapshot",
        "robots": snapshot
    }))
    
    # 5. 接收循环（处理 pong）
    while client.active:
        data = await websocket.receive_text()
        msg = json.loads(data)
        
        if msg.get("type") == "pong":
            client.last_pong = time.time()
```

**前端**：
```javascript
const ws = new WebSocket('ws://localhost:8080/ws');

ws.onopen = () => {
    console.log('✅ Connected');
};

ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    
    if (msg.type === 'snapshot') {
        // 批量更新所有机器人
        handleSnapshot(msg.robots);
    } else if (msg.type === 'ping') {
        // 响应心跳
        ws.send(JSON.stringify({type: 'pong'}));
    }
};
```

---

### 3.2 心跳保活机制

**目的**：防止连接空闲时被中间设备（路由器/防火墙）断开

**后端**：
```python
async def heartbeat_loop():
    """每 10 秒发送一次 ping"""
    while True:
        await asyncio.sleep(10.0)
        
        ping_msg = json.dumps({
            "type": "ping",
            "timestamp": time.time()
        })
        
        await client_manager.broadcast(ping_msg)
        
        # 检查超时客户端（30 秒无 pong）
        now = time.time()
        for client in list(clients):
            if now - client.last_pong > 30.0:
                client.active = False
```

**前端**：
```javascript
ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    
    if (msg.type === 'ping') {
        // 立即响应 pong
        ws.send(JSON.stringify({
            type: 'pong',
            timestamp: msg.timestamp
        }));
    }
};

// 主动心跳（每 15 秒）
setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'heartbeat',
            timestamp: Date.now()
        }));
    }
}, 15000);
```

---

### 3.3 自动重连机制

**前端**：
```javascript
let reconnectAttempts = 0;

ws.onclose = () => {
    console.log('🔴 Disconnected');
    
    // 指数退避：1s, 2s, 4s, 8s, 16s, 30s (max)
    const delay = Math.min(
        1000 * Math.pow(2, reconnectAttempts),
        30000
    );
    
    reconnectAttempts++;
    
    setTimeout(() => {
        connectWebSocket();  // 重新连接
    }, delay);
};

ws.onopen = () => {
    reconnectAttempts = 0;  // 重置计数
};
```

---

## 📊 完整数据流示例

### 时间线（1 秒内）

```
T=0.0s
├─ SimRobot: Robot 5_1 发送 UDP 包 #1
├─ Monitor: 接收并更新 robot_states["5_1"]
├─ Monitor: 写入日志文件
│
T=0.2s
├─ SimRobot: Robot 5_2 发送 UDP 包 #1
├─ Monitor: 接收并更新 robot_states["5_2"]
│
T=0.4s
├─ SimRobot: Robot 5_3 发送 UDP 包 #1
├─ Monitor: 接收并更新 robot_states["5_3"]
│
T=0.5s  ← broadcast_worker 触发
├─ Monitor: 收集所有机器人最新状态
├─ Monitor: 生成快照 JSON
├─ Monitor: 广播到所有 WebSocket 客户端
├─ 浏览器: 接收快照
├─ 浏览器: 批量更新 DOM（10 个机器人卡片）
│
T=0.6s
├─ SimRobot: Robot 5_1 发送 UDP 包 #2
├─ Monitor: 覆盖 robot_states["5_1"]（丢弃包 #1）
│
T=1.0s  ← broadcast_worker 再次触发
├─ Monitor: 收集最新状态（包含包 #2）
├─ Monitor: 广播快照
├─ 浏览器: 更新 DOM
```

**关键点**：
- UDP 包 #1 被包 #2 覆盖（中间状态丢弃）
- 浏览器只看到 0.5s 和 1.0s 的快照
- 50 Hz 输入 → 2 Hz 输出

---

## 🔧 关键技术点

### 1. 为什么使用 UDP？

**优点**：
- ✅ 无连接开销（不需要握手）
- ✅ 低延迟（不等待 ACK）
- ✅ 简单（适合本地通信）

**缺点**：
- ❌ 不可靠（可能丢包）
- ❌ 无序（包可能乱序）

**解决方案**：
- 本地通信（127.0.0.1）丢包率极低
- 只保留最新状态，丢包无影响
- 每个包都有时间戳，可以检测乱序

---

### 2. 为什么使用 WebSocket？

**对比 HTTP 轮询**：

| 特性 | HTTP 轮询 | WebSocket |
|------|-----------|-----------|
| 连接 | 每次请求建立 | 一次建立，持久连接 |
| 延迟 | 高（轮询间隔） | 低（实时推送） |
| 开销 | 大（HTTP 头） | 小（二进制帧） |
| 服务器负载 | 高 | 低 |

**WebSocket 优势**：
- ✅ 双向通信（服务器可主动推送）
- ✅ 低延迟（无轮询间隔）
- ✅ 低开销（无 HTTP 头）

---

### 3. 为什么需要节流聚合？

**问题**：
- 10 个机器人 × 5 Hz = 50 个 UDP 包/秒
- 如果直接转发到 WebSocket = 50 个消息/秒
- 浏览器处理不过来，导致卡顿/断连

**解决方案**：
- **节流**：500ms 推送一次（2 Hz）
- **聚合**：一次推送所有机器人
- **效果**：50 msg/s → 2 msg/s（减少 96%）

---

### 4. 为什么需要独立队列？

**问题**：
- 如果一个客户端慢，会阻塞其他客户端

**解决方案**：
```python
# 每个客户端独立队列
class WebSocketClient:
    send_queue = asyncio.Queue(maxsize=10)
    
    async def sender_loop(self):
        # 独立协程，互不影响
        while self.active:
            message = await self.send_queue.get()
            await self.websocket.send_text(message)
```

**效果**：
- 慢客户端只影响自己
- 快客户端不受影响
- 队列满时自动丢弃旧消息

---

## 🎯 总结

### 数据流路径

```
SimRobot (C++)
    ↓ UDP (50 Hz, JSON)
Monitor Daemon (Python)
    ├─ UDP 接收线程 → robot_states (Dict)
    ├─ broadcast_worker (2 Hz) → 收集快照
    └─ ClientManager → WebSocketClient → sender_loop
        ↓ WebSocket (2 Hz, JSON)
浏览器 (JavaScript)
    ├─ 接收快照
    ├─ 批量更新 DOM
    └─ 显示机器人卡片
```

### 关键设计

1. **三层架构**：SimRobot → Monitor → 浏览器
2. **协议选择**：UDP（本地高频）+ WebSocket（远程实时）
3. **节流聚合**：50 Hz → 2 Hz（减少 96%）
4. **异步处理**：UDP 线程 + asyncio 事件循环
5. **容错机制**：重试、队列、心跳、自动重连

### 性能指标

- **延迟**：< 500ms（端到端）
- **吞吐量**：50 UDP 包/秒 → 2 WebSocket 消息/秒
- **稳定性**：30 分钟 0-1 次断连
- **可扩展性**：支持 10+ 机器人

---

**这就是整个监控系统的通信原理！** 🎉
