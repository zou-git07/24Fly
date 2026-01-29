# 🎯 实时接入正在进行的比赛 - 完整设计方案

## 📋 核心问题

**当前状态**：用户必须等比赛结束才能查看日志  
**目标状态**：像 GameController 一样，随时可以接入正在进行的比赛

---

## 🏗️ 任务 1：ActiveMatch 系统概念

### 数据结构

```python
class ActiveMatch:
    match_id: str           # 例如 "match_20260129_112918"
    start_time: float       # Unix timestamp
    log_dir: Path           # 日志目录路径
    robots: Set[str]        # 已接入的机器人 ID
    is_active: bool         # 是否正在进行
    last_activity: float    # 最后活动时间
```

### 生命周期

```
Monitor Daemon 启动
    ↓
创建 ActiveMatch（首次收到 UDP 数据时）
    ↓
持续接收数据（更新 last_activity）
    ↓
超过 60 秒无数据 → 自动标记为结束
    ↓
转为历史比赛
```

---

## 🔧 任务 2：边写边读的日志系统

### 方案：JSON Lines + 内存缓存

#### 核心设计

```python
# 1. 写入：保持不变（追加写入）
with open(log_file, 'a') as f:
    f.write(json.dumps(data) + '\n')
    f.flush()  # 立即刷新到磁盘

# 2. 读取：使用 tail 模式
def read_latest_logs(file_path, limit=50):
    """读取最新 N 条日志"""
    with open(file_path, 'r') as f:
        lines = f.readlines()
        return [json.loads(line) for line in lines[-limit:]]
```

#### 为什么安全？

1. **追加写入**：不会修改已有内容
2. **按行读取**：即使读到正在写的行，也只是该行不完整，不影响前面的行
3. **flush()**：确保数据及时落盘
4. **无文件锁**：Python 的文件操作在 Linux 上默认不加锁

#### 内存缓存（可选优化）

```python
# 为每个机器人维护最近 100 条数据的环形缓冲区
recent_logs: Dict[str, deque] = {}

def handle_packet(data):
    robot_id = data['robot_id']
    
    # 写入文件
    write_log(robot_id, data)
    
    # 更新内存缓存
    if robot_id not in recent_logs:
        recent_logs[robot_id] = deque(maxlen=100)
    recent_logs[robot_id].append(data)
```

**优势**：
- 读取最新数据时直接从内存返回，无需读文件
- 自动限制内存占用（每个机器人最多 100 条）

---

## 📡 任务 3：当前比赛 API 设计

### API 1: 获取当前比赛信息

```http
GET /api/current_match
```

**响应**：
```json
{
  "active": true,
  "match_id": "match_20260129_112918",
  "start_time": 1769656763.0,
  "duration": 125.5,
  "robot_count": 10,
  "robots": ["5_1", "5_2", "5_3", "5_4", "5_5", 
             "70_1", "70_2", "70_3", "70_4", "70_5"]
}
```

**无比赛时**：
```json
{
  "active": false
}
```

---

### API 2: 获取当前比赛的机器人列表

```http
GET /api/current_match/robots
```

**响应**：
```json
{
  "robots": [
    {
      "robot_id": "5_1",
      "packet_count": 523,
      "last_update": 1769656888.0,
      "online": true
    },
    ...
  ]
}
```

---

### API 3: 获取当前比赛的实时日志

```http
GET /api/current_match/logs/{robot_id}?limit=50
```

**响应**：
```json
{
  "match_id": "match_20260129_112918",
  "robot_id": "5_1",
  "is_active": true,
  "total_packets": 523,
  "data": [
    {
      "timestamp": 143732,
      "robot_id": "5_1",
      "battery": 100.0,
      "fallen": false,
      ...
    },
    ...
  ]
}
```

---

## 🎨 任务 4：前端交互优化

### 页面打开时的逻辑

```javascript
// 1. 检测是否有正在进行的比赛
async function checkActiveMatch() {
    const response = await fetch('/api/current_match');
    const data = await response.json();
    
    if (data.active) {
        showActiveMatchBanner(data);
    } else {
        loadHistoricalMatches();
    }
}

// 2. 显示"正在进行的比赛"横幅
function showActiveMatchBanner(matchData) {
    const banner = document.createElement('div');
    banner.className = 'active-match-banner';
    banner.innerHTML = `
        <div class="banner-content">
            <span class="live-indicator">🔴 正在进行的比赛</span>
            <span>${matchData.match_id}</span>
            <span>${matchData.robot_count} 个机器人</span>
            <span>已运行 ${formatDuration(matchData.duration)}</span>
            <button id="attach-btn" class="btn-primary">
                📡 接入实时日志
            </button>
        </div>
    `;
    
    document.querySelector('.controls').prepend(banner);
    
    document.getElementById('attach-btn').addEventListener('click', () => {
        attachToActiveMatch(matchData.match_id);
    });
}
```

### 实时日志模式

```javascript
let liveUpdateInterval = null;

function attachToActiveMatch(matchId) {
    // 1. 切换到实时模式
    document.querySelector('.active-match-banner').classList.add('attached');
    
    // 2. 加载机器人列表
    loadActiveMatchRobots();
    
    // 3. 启动自动刷新（每 2 秒）
    liveUpdateInterval = setInterval(() => {
        refreshLiveLogs();
    }, 2000);
}

async function refreshLiveLogs() {
    const robotId = document.getElementById('robot-select').value;
    
    const response = await fetch(
        `/api/current_match/logs/${robotId}?limit=50`
    );
    const data = await response.json();
    
    // 更新显示
    updateLogDisplay(data);
    
    // 如果比赛结束，停止刷新
    if (!data.is_active) {
        stopLiveMode();
        showMatchEndedNotification();
    }
}
```

---

## 🚀 任务 5：最小可落地改造方案（MVP）

### 必须改的代码（3 处）

#### ✅ 改动 1：添加 ActiveMatch 管理（后端）

**文件**：`web_monitor.py`

```python
# 在全局变量区域添加
class ActiveMatch:
    def __init__(self):
        self.match_id = None
        self.start_time = None
        self.log_dir = None
        self.robots = set()
        self.is_active = False
        self.last_activity = 0
    
    def start(self, match_id, log_dir):
        self.match_id = match_id
        self.start_time = time.time()
        self.log_dir = log_dir
        self.robots = set()
        self.is_active = True
        self.last_activity = time.time()
        print(f"🎬 Started active match: {match_id}")
    
    def add_robot(self, robot_id):
        self.robots.add(robot_id)
        self.last_activity = time.time()
    
    def check_timeout(self):
        """60 秒无数据则标记为结束"""
        if self.is_active and time.time() - self.last_activity > 60:
            self.is_active = False
            print(f"🏁 Match ended: {self.match_id}")
    
    def to_dict(self):
        return {
            "active": self.is_active,
            "match_id": self.match_id,
            "start_time": self.start_time,
            "duration": time.time() - self.start_time if self.start_time else 0,
            "robot_count": len(self.robots),
            "robots": list(self.robots)
        }

active_match = ActiveMatch()

# 修改 write_log 函数
def write_log(robot_id: str, data: dict):
    global current_match_id, log_files, active_match
    
    if current_match_id is None:
        current_match_id = f"match_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        match_dir = LOG_DIR / current_match_id
        match_dir.mkdir(parents=True, exist_ok=True)
        
        # 启动 ActiveMatch
        active_match.start(current_match_id, match_dir)
    
    # 添加机器人
    active_match.add_robot(robot_id)
    
    # 写入日志...
```

**工作量**：40 行代码

---

#### ✅ 改动 2：添加 3 个新 API（后端）

**文件**：`web_monitor.py`

```python
@app.get("/api/current_match")
async def get_current_match():
    """获取当前比赛信息"""
    active_match.check_timeout()
    return active_match.to_dict()


@app.get("/api/current_match/robots")
async def get_current_match_robots():
    """获取当前比赛的机器人列表"""
    if not active_match.is_active:
        return {"error": "No active match"}
    
    robots = []
    for robot_id in active_match.robots:
        log_file = active_match.log_dir / f"robot_{robot_id}.jsonl"
        packet_count = sum(1 for _ in open(log_file)) if log_file.exists() else 0
        
        robots.append({
            "robot_id": robot_id,
            "packet_count": packet_count,
            "last_update": robot_states.get(robot_id, {}).get('last_update', 0),
            "online": robot_id in robot_states
        })
    
    return {"robots": robots}


@app.get("/api/current_match/logs/{robot_id}")
async def get_current_match_logs(robot_id: str, limit: int = 50):
    """获取当前比赛的实时日志"""
    if not active_match.is_active:
        return {"error": "No active match"}
    
    log_file = active_match.log_dir / f"robot_{robot_id}.jsonl"
    
    if not log_file.exists():
        return {"error": "Robot not found"}
    
    # 读取最新 N 条
    data = []
    with open(log_file, 'r') as f:
        lines = f.readlines()
        for line in lines[-limit:]:
            try:
                data.append(json.loads(line))
            except:
                pass
    
    total_packets = len(lines)
    
    return {
        "match_id": active_match.match_id,
        "robot_id": robot_id,
        "is_active": active_match.is_active,
        "total_packets": total_packets,
        "data": data
    }
```

**工作量**：60 行代码

---

#### ✅ 改动 3：前端添加实时接入逻辑

**文件**：`logs.js`

```javascript
// 在 DOMContentLoaded 中添加
async function init() {
    // 先检查是否有正在进行的比赛
    const activeMatch = await checkActiveMatch();
    
    if (activeMatch) {
        showActiveMatchBanner(activeMatch);
    }
    
    // 加载历史比赛列表
    loadMatches();
}

async function checkActiveMatch() {
    try {
        const response = await fetch('/api/current_match');
        const data = await response.json();
        return data.active ? data : null;
    } catch (error) {
        console.error('Failed to check active match:', error);
        return null;
    }
}

function showActiveMatchBanner(matchData) {
    const banner = document.createElement('div');
    banner.className = 'active-match-banner';
    banner.innerHTML = `
        <div style="background: #ff5722; color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <span style="font-size: 20px;">🔴</span>
                    <strong>正在进行的比赛</strong>
                    <span style="margin-left: 20px;">${matchData.match_id}</span>
                    <span style="margin-left: 20px;">${matchData.robot_count} 个机器人</span>
                    <span style="margin-left: 20px;">已运行 ${formatDuration(matchData.duration)}</span>
                </div>
                <button id="attach-live-btn" class="btn" style="background: white; color: #ff5722;">
                    📡 接入实时日志
                </button>
            </div>
        </div>
    `;
    
    document.querySelector('.controls').insertAdjacentElement('beforebegin', banner);
    
    document.getElementById('attach-live-btn').addEventListener('click', () => {
        attachToLiveMatch(matchData);
    });
}

let liveUpdateInterval = null;

async function attachToLiveMatch(matchData) {
    // 1. 加载机器人列表
    const response = await fetch('/api/current_match/robots');
    const data = await response.json();
    
    const select = document.getElementById('robot-select');
    select.innerHTML = '';
    
    data.robots.forEach(robot => {
        const option = document.createElement('option');
        option.value = robot.robot_id;
        option.textContent = `Robot ${robot.robot_id} (${robot.packet_count} packets) ${robot.online ? '🟢' : '⚫'}`;
        select.appendChild(option);
    });
    
    // 2. 自动加载第一个机器人
    if (data.robots.length > 0) {
        currentRobot = data.robots[0].robot_id;
        loadLiveLogs();
        
        // 3. 启动自动刷新
        liveUpdateInterval = setInterval(loadLiveLogs, 2000);
    }
    
    // 4. 更新按钮状态
    document.getElementById('attach-live-btn').textContent = '🔴 实时模式';
    document.getElementById('attach-live-btn').disabled = true;
}

async function loadLiveLogs() {
    const robotId = document.getElementById('robot-select').value;
    
    try {
        const response = await fetch(`/api/current_match/logs/${robotId}?limit=100`);
        const data = await response.json();
        
        if (data.error) {
            console.error(data.error);
            return;
        }
        
        // 显示日志信息
        displayLogInfo(data);
        displayTimeline(data.data);
        displayEvents(data.data);
        displayRawData(data.data.slice(-50));
        
        // 如果比赛结束，停止刷新
        if (!data.is_active) {
            clearInterval(liveUpdateInterval);
            alert('比赛已结束，已切换到历史模式');
            location.reload();
        }
        
    } catch (error) {
        console.error('Failed to load live logs:', error);
    }
}
```

**工作量**：80 行代码

---

### 可以先不动的地方

| 模块 | 原因 |
|------|------|
| 日志文件格式 | JSON Lines 已经支持边写边读 |
| 实时监控页面 | 已经有 WebSocket 实时推送 |
| 历史比赛 API | 保持不变，继续支持历史查询 |

---

## 📊 改造总结

### 代码量统计

| 改动 | 文件 | 行数 |
|------|------|------|
| ActiveMatch 管理 | web_monitor.py | 40 行 |
| 3 个新 API | web_monitor.py | 60 行 |
| 前端实时接入 | logs.js | 80 行 |
| **总计** | | **180 行** |

### 改造效果

| 功能 | 改造前 | 改造后 |
|------|--------|--------|
| 查看正在进行的比赛 | ❌ 不支持 | ✅ 支持 |
| 实时日志更新 | ❌ 不支持 | ✅ 2 秒刷新 |
| 比赛结束自动切换 | ❌ 不支持 | ✅ 自动检测 |
| 历史比赛查看 | ✅ 支持 | ✅ 保持不变 |

---

## 🧪 测试验证

### 测试场景 1：启动 SimRobot

```bash
# 1. 启动监控系统
python3 RobotMonitoringSystem/monitor_daemon/web_monitor.py

# 2. 启动 SimRobot
./Build/Linux/SimRobot/Develop/SimRobot Config/Scenes/GameFast.ros3

# 3. 打开日志页面
http://localhost:8080/static/logs.html

# 预期：看到"🔴 正在进行的比赛"横幅
```

### 测试场景 2：接入实时日志

```bash
# 1. 点击"接入实时日志"按钮
# 2. 选择一个机器人
# 3. 观察数据每 2 秒自动刷新

# 预期：
# - 日志信息实时更新
# - 时间轴持续增长
# - 事件列表动态添加
```

### 测试场景 3：比赛结束

```bash
# 1. 停止 SimRobot（60 秒后自动标记为结束）
# 2. 页面自动检测到比赛结束
# 3. 弹出提示并刷新页面

# 预期：
# - 横幅消失
# - 比赛出现在历史列表中
```

---

## 🎯 核心优势

1. **最小改动**：只需 180 行代码
2. **无需重写**：日志格式、文件结构保持不变
3. **向后兼容**：历史比赛查看功能完全不受影响
4. **实时性好**：2 秒刷新，接近 GameController 体验
5. **自动化**：比赛开始/结束自动检测

---

**下一步**：立即实施这 3 处改动，即可实现"随时接入正在进行的比赛"！
