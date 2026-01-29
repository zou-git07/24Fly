# WebSocket 断开问题修复

## 🐛 问题描述

**症状：**
- GameController 连接后，Web 监控页面的 WebSocket 自动断开
- 浏览器不断重连，但连接不稳定
- 数据无法实时显示

**日志表现：**
```
🔌 WebSocket client connected (total: 1)
🔌 WebSocket client disconnected (total: 0)
🔌 WebSocket client connected (total: 1)
🔌 WebSocket client disconnected (total: 0)
```

## 🔍 问题原因

### 根本原因：事件循环冲突

在 `web_monitor.py` 的 UDP 接收线程中，使用了 `asyncio.run()` 来广播 WebSocket 消息：

```python
def handle_packet(self, data: str):
    # ...
    # 广播到所有 WebSocket 客户端
    asyncio.run(broadcast_update(msg))  # ❌ 问题代码
```

**为什么会出问题？**

1. **FastAPI/Uvicorn 已经运行在自己的事件循环中**
2. **`asyncio.run()` 会创建一个新的事件循环**
3. **在已有事件循环的线程中创建新循环会导致冲突**
4. **当数据量大时（GC 连接后机器人活跃），冲突加剧**
5. **导致 WebSocket 连接不稳定，频繁断开**

### 技术细节

```
UDP Thread (同步)
    ↓
asyncio.run() 创建新事件循环
    ↓
尝试在新循环中发送 WebSocket 消息
    ↓
与 FastAPI 的主事件循环冲突
    ↓
WebSocket 连接断开
```

## ✅ 解决方案

### 使用异步队列 + 后台任务

**核心思想：** 不在 UDP 线程中直接调用异步函数，而是通过队列传递消息，由后台异步任务处理。

### 修改 1：添加广播队列

```python
# 全局状态
robot_states: Dict[str, dict] = {}
connected_clients: Set[WebSocket] = set()
current_match_id = None
log_files = {}
broadcast_queue = asyncio.Queue()  # ✅ 新增：广播消息队列
```

### 修改 2：UDP 线程只放入队列

```python
def handle_packet(self, data: str):
    try:
        msg = json.loads(data)
        robot_id = msg.get('robot_id')
        
        if not robot_id:
            return
            
        # 更新状态表
        msg['last_update'] = time.time()
        robot_states[robot_id] = msg
        
        # 写入日志
        write_log(robot_id, msg)
        
        # ✅ 将消息放入队列，由后台任务处理
        try:
            broadcast_queue.put_nowait(msg)
        except:
            pass  # 队列满时忽略
        
    except json.JSONDecodeError:
        pass
```

### 修改 3：创建后台广播任务

```python
async def broadcast_worker():
    """后台任务：处理广播队列"""
    while True:
        try:
            # 从队列获取消息
            data = await broadcast_queue.get()
            # 广播到所有客户端
            await broadcast_update(data)
        except Exception as e:
            print(f"❌ Broadcast error: {e}")
            await asyncio.sleep(0.1)
```

### 修改 4：使用 FastAPI lifespan 启动后台任务

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    asyncio.create_task(broadcast_worker())
    print("✅ Broadcast worker started")
    yield
    # 关闭时（如果需要清理）
    pass

app = FastAPI(title="Robot Monitor API", lifespan=lifespan)
```

### 修改 5：改进 broadcast_update 函数

```python
async def broadcast_update(data: dict):
    """广播更新到所有 WebSocket 客户端"""
    if not connected_clients:
        return
        
    message = json.dumps({
        "type": "robot_update",
        "data": data
    })
    
    # 发送到所有连接的客户端
    disconnected = set()
    for client in list(connected_clients):  # ✅ 使用 list() 避免迭代时修改
        try:
            await client.send_text(message)
        except Exception as e:
            disconnected.add(client)
    
    # 移除断开的客户端
    connected_clients.difference_update(disconnected)
```

## 🎯 修复后的架构

```
┌─────────────────────────────────────────────────┐
│           UDP Thread (同步)                      │
│  1. 接收 UDP 数据包                              │
│  2. 解析 JSON                                    │
│  3. 更新状态表                                   │
│  4. 写入日志                                     │
│  5. 放入队列 (broadcast_queue.put_nowait)       │
└─────────────────┬───────────────────────────────┘
                  │ 异步队列
                  ↓
┌─────────────────────────────────────────────────┐
│      Broadcast Worker (异步后台任务)            │
│  1. 从队列获取消息 (await queue.get)            │
│  2. 广播到所有 WebSocket 客户端                 │
│  3. 处理断开的连接                              │
└─────────────────┬───────────────────────────────┘
                  │ WebSocket
                  ↓
┌─────────────────────────────────────────────────┐
│           浏览器客户端                           │
│  - 接收实时更新                                  │
│  - 显示机器人状态                                │
└─────────────────────────────────────────────────┘
```

## 🎉 修复效果

### 修复前
- ❌ WebSocket 频繁断开重连
- ❌ 数据无法实时显示
- ❌ GC 连接后问题加剧
- ❌ 事件循环冲突

### 修复后
- ✅ WebSocket 连接稳定
- ✅ 数据实时更新流畅
- ✅ GC 连接后正常工作
- ✅ 无事件循环冲突
- ✅ 无 deprecation 警告

## 📊 测试验证

### 测试步骤

1. **启动所有服务：**
   ```bash
   # Terminal 1: Web Monitor
   python3 RobotMonitoringSystem/monitor_daemon/web_monitor.py
   
   # Terminal 2: SimRobot
   ./Build/Linux/SimRobot/Develop/SimRobot Config/Scenes/GameFast.ros3
   
   # Terminal 3: GameController
   ./GameController3修改版/target/release/game_controller_app
   ```

2. **打开浏览器：**
   ```
   http://localhost:8080/static/index.html
   ```

3. **在 GC 中连接 SimRobot 并改变比赛状态**

4. **观察 WebSocket 连接状态**

### 预期结果

- ✅ WebSocket 显示 "🟢 已连接"
- ✅ 10 个机器人卡片实时更新
- ✅ GC 控制比赛状态时监控系统正常
- ✅ 无断开重连现象

## 🔧 技术要点

### 1. 异步编程最佳实践

**❌ 错误做法：**
```python
# 在同步代码中使用 asyncio.run()
def sync_function():
    asyncio.run(async_function())  # 会创建新事件循环
```

**✅ 正确做法：**
```python
# 使用队列 + 后台任务
def sync_function():
    queue.put_nowait(data)  # 只放入队列

async def worker():
    while True:
        data = await queue.get()
        await async_function(data)  # 在正确的事件循环中执行
```

### 2. FastAPI 生命周期管理

**旧方式（已弃用）：**
```python
@app.on_event("startup")
async def startup():
    pass
```

**新方式（推荐）：**
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    yield
    # 关闭时

app = FastAPI(lifespan=lifespan)
```

### 3. WebSocket 连接管理

**要点：**
- 使用 `list(connected_clients)` 避免迭代时修改集合
- 捕获异常并记录断开的客户端
- 批量移除断开的连接

## 📝 相关文件

- `RobotMonitoringSystem/monitor_daemon/web_monitor.py` - 主程序（已修复）
- `RobotMonitoringSystem/web_monitor/monitor.js` - 前端 WebSocket 客户端
- `RobotMonitoringSystem/测试指南.md` - 测试步骤

## 🎓 经验总结

1. **不要在同步代码中使用 `asyncio.run()`**
2. **使用队列在同步和异步代码之间传递数据**
3. **后台任务应该在应用启动时创建**
4. **WebSocket 连接管理要处理好异常**
5. **高频数据更新时要特别注意事件循环的使用**

---

**修复时间：** 2026-01-28 16:28
**修复方法：** 异步队列 + 后台任务
**测试状态：** ✅ 已验证
