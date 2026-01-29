# 🔧 实时监控系统稳定性升级指南

## 📋 问题诊断报告

### 根本原因分析（5 个工程级问题）

| 问题 | 严重性 | 现象 | 根本原因 |
|------|--------|------|----------|
| **1. 无节流高频推送** | 🔴 严重 | 频繁断连 | 10 机器人 × 5Hz = 50 msg/s 直接灌入 WebSocket |
| **2. 无批量处理** | 🔴 严重 | 事件循环阻塞 | 队列中 100 条消息触发 100 次 send() |
| **3. 缺少心跳机制** | 🟡 中等 | 空闲时断连 | 路由器/防火墙关闭空闲连接 |
| **4. 异常处理不完整** | 🟡 中等 | 静默失败 | 慢客户端、缓冲区满导致异常未记录 |
| **5. 简单重连策略** | 🟡 中等 | 重连风暴 | 固定 5 秒重连，无指数退避 |

---

## 🏗️ 新架构设计

### 数据流（三层缓冲）

```
┌─────────────────────────────────────────────────────────────┐
│  UDP 接收 (50 Hz)                                            │
│  ↓                                                           │
│  Layer 1: 状态表 (robot_states)                              │
│  - 高频更新                                                   │
│  - 只保留最新状态                                             │
│  ↓                                                           │
│  Layer 2: 聚合器 (broadcast_worker)                          │
│  - 每 500ms 打包一次                                          │
│  - 收集所有机器人快照                                         │
│  ↓                                                           │
│  Layer 3: WebSocket 推送 (2 Hz)                              │
│  - 批量发送                                                   │
│  - 慢客户端保护                                               │
└─────────────────────────────────────────────────────────────┘
```

### 关键指标

| 指标 | 旧版 | 新版 | 改善 |
|------|------|------|------|
| WebSocket 消息频率 | 50 Hz | 2 Hz | **96% ↓** |
| 单次消息大小 | 1 KB | 10 KB | 10× ↑ |
| 总带宽 | 50 KB/s | 20 KB/s | **60% ↓** |
| 事件循环阻塞 | 频繁 | 无 | ✅ |
| 慢客户端影响 | 全局阻塞 | 隔离 | ✅ |

---

## 🛠️ 任务 4：多机器人数据节流与聚合

### 核心设计

```python
# Layer 1: 状态表（高频更新）
robot_states: Dict[str, dict] = {}

def handle_udp_packet(msg):
    robot_id = msg['robot_id']
    robot_states[robot_id] = msg  # 直接覆盖，只保留最新

# Layer 2: 聚合器（定期打包）
async def broadcast_worker():
    while True:
        await asyncio.sleep(0.5)  # 500ms
        
        # 收集快照
        snapshot = []
        for robot_id, state in robot_states.items():
            snapshot.append(state)
        
        # 批量推送
        message = json.dumps({
            "type": "snapshot",
            "robots": snapshot  # 一次发送所有机器人
        })
        
        await client_manager.broadcast(message)
```

### 前端批量处理

```javascript
function handleSnapshot(robots) {
    // 使用 requestAnimationFrame 批量更新 DOM
    requestAnimationFrame(() => {
        robots.forEach(robot => {
            updateRobot(robot);
        });
    });
}
```

**优势**：
- 中间状态自动丢弃（例如 500ms 内的 25 个更新只保留最后 1 个）
- 前端一次性处理，减少重排重绘
- 网络效率提升（1 个大包 vs 50 个小包）

---

## 💓 任务 3：WebSocket 保活方案

### 心跳机制

#### 后端实现

```python
async def heartbeat_loop():
    while True:
        await asyncio.sleep(10.0)  # 10 秒
        
        ping_msg = json.dumps({
            "type": "ping",
            "timestamp": time.time()
        })
        
        await client_manager.broadcast(ping_msg)
        
        # 检查超时客户端
        now = time.time()
        for client in list(clients):
            if now - client.last_pong > 30.0:
                print(f"⏱️  Client timeout")
                await remove_client(client)
```

#### 前端实现

```javascript
// 接收 ping，发送 pong
ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    
    if (msg.type === 'ping') {
        ws.send(JSON.stringify({
            type: 'pong',
            timestamp: Date.now()
        }));
    }
};

// 定期主动发送心跳
setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.dumps({type: 'pong'}));
    }
}, 15000);  // 15 秒
```

### 超时检测

```python
class WebSocketClient:
    def __init__(self, websocket):
        self.websocket = websocket
        self.last_pong = time.time()
    
    def is_alive(self):
        return time.time() - self.last_pong < 30.0
```

### 自动重连（指数退避）

```javascript
let reconnectAttempts = 0;

function scheduleReconnect() {
    // 1s, 2s, 4s, 8s, 16s, 30s (max)
    const delay = Math.min(
        1000 * Math.pow(2, reconnectAttempts),
        30000
    );
    
    reconnectAttempts++;
    
    setTimeout(() => {
        connectWebSocket();
    }, delay);
}

ws.onopen = () => {
    reconnectAttempts = 0;  // 重置
};
```

### 慢客户端保护

```python
class WebSocketClient:
    def __init__(self, websocket):
        self.send_queue = asyncio.Queue(maxsize=10)
    
    async def send_safe(self, message):
        try:
            self.send_queue.put_nowait(message)
        except asyncio.QueueFull:
            # 队列满 = 慢客户端，丢弃最旧消息
            self.send_queue.get_nowait()
            self.send_queue.put_nowait(message)
    
    async def sender_loop(self):
        """独立发送协程"""
        while self.active:
            message = await self.send_queue.get()
            try:
                await self.websocket.send_text(message)
            except Exception as e:
                print(f"Send failed: {e}")
                break
```

---

## 🚀 任务 5：最小修改落地方案（MVP）

### 必须改的地方（3 处）

#### ✅ 改动 1：添加聚合层

**文件**：`web_monitor.py`

```python
# 旧代码（删除）
broadcast_queue.put_nowait(msg)  # ❌ 每个包立即推送

# 新代码（添加）
async def broadcast_worker():
    while True:
        await asyncio.sleep(0.5)  # 500ms 聚合
        
        snapshot = list(robot_states.values())
        message = json.dumps({"type": "snapshot", "robots": snapshot})
        
        await client_manager.broadcast(message)
```

**工作量**：10 行代码

---

#### ✅ 改动 2：前端批量处理

**文件**：`monitor.js`

```javascript
// 旧代码（修改）
ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    
    // 新增
    if (msg.type === 'snapshot') {
        handleSnapshot(msg.robots);  // 批量处理
        return;
    }
    
    // 保留旧逻辑（兼容）
    if (msg.type === 'robot_update') {
        updateRobot(msg.data);
    }
};

// 新增函数
function handleSnapshot(robots) {
    requestAnimationFrame(() => {
        robots.forEach(r => updateRobot(r));
    });
}
```

**工作量**：15 行代码

---

#### ✅ 改动 3：添加心跳

**后端**：`web_monitor.py`

```python
async def heartbeat_loop():
    while True:
        await asyncio.sleep(10.0)
        await client_manager.broadcast(json.dumps({"type": "ping"}))

# 在 lifespan 中启动
asyncio.create_task(heartbeat_loop())
```

**前端**：`monitor.js`

```javascript
ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    
    if (msg.type === 'ping') {
        ws.send(JSON.stringify({type: 'pong'}));
    }
};
```

**工作量**：10 行代码

---

### 可以先不动的地方

| 模块 | 原因 | 优先级 |
|------|------|--------|
| 日志写入 | 已经是异步，不影响稳定性 | 低 |
| HTTP API | 不在热路径上 | 低 |
| 前端 UI | 只要数据稳定，UI 可以慢慢优化 | 低 |
| 指数退避重连 | 有基础重连就够用 | 中 |

---

## 📊 预期效果

### 改造前 vs 改造后

| 场景 | 改造前 | 改造后 |
|------|--------|--------|
| **10 机器人运行 10 分钟** | 断连 5-10 次 | 0 次断连 |
| **WebSocket 消息量** | 30,000 条 | 1,200 条 |
| **CPU 占用（前端）** | 15-20% | 3-5% |
| **内存占用（后端）** | 持续增长 | 稳定 |
| **网络延迟** | 100-500ms | 50-100ms |

---

## 🧪 测试验证

### 测试 1：长时间稳定性

```bash
# 启动稳定版
python3 RobotMonitoringSystem/monitor_daemon/web_monitor_stable.py

# 启动 SimRobot
./Build/Linux/SimRobot/Develop/SimRobot Config/Scenes/GameFast.ros3

# 运行 30 分钟，检查：
# - WebSocket 是否断连
# - 浏览器控制台是否有错误
# - 后端日志是否有异常
```

**预期**：30 分钟 0 次断连

---

### 测试 2：慢客户端

```javascript
// 在浏览器控制台模拟慢客户端
ws.onmessage = (event) => {
    // 故意延迟 1 秒处理
    setTimeout(() => {
        console.log('Slow processing:', event.data);
    }, 1000);
};
```

**预期**：后端不阻塞，慢客户端自动丢弃旧消息

---

### 测试 3：网络抖动

```bash
# 模拟网络延迟
sudo tc qdisc add dev lo root netem delay 100ms

# 模拟丢包
sudo tc qdisc add dev lo root netem loss 5%
```

**预期**：自动重连，数据恢复

---

## 📦 部署步骤

### 方案 A：直接替换（推荐）

```bash
# 1. 备份旧版
cp RobotMonitoringSystem/monitor_daemon/web_monitor.py \
   RobotMonitoringSystem/monitor_daemon/web_monitor_old.py

# 2. 使用稳定版
cp RobotMonitoringSystem/monitor_daemon/web_monitor_stable.py \
   RobotMonitoringSystem/monitor_daemon/web_monitor.py

# 3. 更新前端
cp RobotMonitoringSystem/web_monitor/monitor_stable.js \
   RobotMonitoringSystem/web_monitor/monitor.js

# 4. 重启服务
pkill -f web_monitor
python3 RobotMonitoringSystem/monitor_daemon/web_monitor.py
```

### 方案 B：并行测试

```bash
# 稳定版使用不同端口
python3 RobotMonitoringSystem/monitor_daemon/web_monitor_stable.py --port 8081

# 访问 http://localhost:8081 测试
# 确认稳定后再替换
```

---

## 🎯 核心改进总结

### 技术层面

1. **节流聚合**：50 Hz → 2 Hz，减少 96% 消息量
2. **批量处理**：一次发送所有机器人，减少事件循环阻塞
3. **心跳保活**：10 秒 ping/pong，防止空闲断连
4. **慢客户端隔离**：独立发送队列，不影响其他客户端
5. **指数退避重连**：1s → 2s → 4s → 30s，避免重连风暴

### 工程层面

1. **最小改动**：只需修改 3 处，约 35 行代码
2. **向后兼容**：保留旧消息格式，渐进式升级
3. **可观测性**：添加日志，方便排查问题
4. **容错性**：任何客户端异常都不影响其他客户端

---

## 🔍 故障排查

### 问题 1：仍然断连

**检查**：
```bash
# 查看后端日志
tail -f /tmp/web_monitor.log

# 查看浏览器控制台
# 是否有 "WebSocket error" 或 "Parse error"
```

**可能原因**：
- 防火墙阻止 WebSocket
- 消息格式错误
- 后端崩溃

---

### 问题 2：数据不更新

**检查**：
```bash
# 确认 UDP 数据到达
sudo tcpdump -i lo -n udp port 10020

# 确认 robot_states 有数据
# 在 web_monitor.py 添加：
print(f"States: {len(robot_states)}")
```

---

### 问题 3：前端卡顿

**检查**：
```javascript
// 浏览器控制台
console.time('update');
handleSnapshot(robots);
console.timeEnd('update');
```

**优化**：
- 减少 DOM 操作
- 使用虚拟滚动
- 降低推送频率到 1 Hz

---

## ✅ 验收标准

系统达到以下标准即为成功：

- [ ] SimRobot 运行 30 分钟，WebSocket 0 次断连
- [ ] 10 个机器人数据实时更新，延迟 < 1 秒
- [ ] 浏览器 CPU 占用 < 10%
- [ ] 后端内存稳定，无泄漏
- [ ] 网络断开后自动重连
- [ ] 慢客户端不影响其他客户端
- [ ] 日志完整记录所有数据

---

## 📚 参考资料

- WebSocket RFC 6455: https://tools.ietf.org/html/rfc6455
- FastAPI WebSocket: https://fastapi.tiangolo.com/advanced/websockets/
- 背压处理: https://nodejs.org/en/docs/guides/backpressuring-in-streams/

---

**作者**：实时系统稳定性专家  
**日期**：2026-01-29  
**版本**：1.0
