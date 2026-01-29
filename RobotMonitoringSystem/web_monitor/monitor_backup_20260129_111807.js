// 实时监控页面逻辑 - 稳定版
// 核心改进：
// 1. 批量处理快照
// 2. 心跳保活
// 3. 指数退避重连
// 4. 性能优化

const robotStates = new Map();
let ws = null;
let reconnectAttempts = 0;
let reconnectTimer = null;
let heartbeatTimer = null;

// 重连配置
const RECONNECT_BASE_DELAY = 1000;  // 1 秒
const RECONNECT_MAX_DELAY = 30000;  // 30 秒
const HEARTBEAT_INTERVAL = 15000;   // 15 秒

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    connectWebSocket();
});

// WebSocket 连接（带指数退避）
function connectWebSocket() {
    const wsUrl = `ws://${window.location.hostname}:${window.location.port}/ws`;
    
    try {
        ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            console.log('✅ WebSocket connected');
            updateConnectionStatus(true);
            reconnectAttempts = 0;  // 重置重连计数
            startHeartbeat();
        };
        
        ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                handleMessage(msg);
            } catch (e) {
                console.error('❌ Parse error:', e);
            }
        };
        
        ws.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
            updateConnectionStatus(false);
        };
        
        ws.onclose = () => {
            console.log('🔴 WebSocket disconnected');
            updateConnectionStatus(false);
            stopHeartbeat();
            scheduleReconnect();
        };
        
    } catch (error) {
        console.error('❌ Failed to connect:', error);
        updateConnectionStatus(false);
        scheduleReconnect();
    }
}

// 处理消息
function handleMessage(msg) {
    switch (msg.type) {
        case 'snapshot':
            // 批量更新（核心优化）
            handleSnapshot(msg.robots);
            break;
            
        case 'robot_update':
            // 单个更新（兼容旧版）
            updateRobot(msg.data);
            break;
            
        case 'ping':
            // 响应心跳
            sendPong();
            break;
            
        default:
            console.warn('Unknown message type:', msg.type);
    }
}

// 处理快照（批量更新）
function handleSnapshot(robots) {
    if (!robots || !Array.isArray(robots)) {
        return;
    }
    
    // 使用 requestAnimationFrame 批量更新 DOM
    requestAnimationFrame(() => {
        robots.forEach(robot => {
            updateRobot(robot);
        });
        updateRobotCount();
    });
}

// 心跳机制
function startHeartbeat() {
    stopHeartbeat();
    heartbeatTimer = setInterval(() => {
        sendPong();
    }, HEARTBEAT_INTERVAL);
}

function stopHeartbeat() {
    if (heartbeatTimer) {
        clearInterval(heartbeatTimer);
        heartbeatTimer = null;
    }
}

function sendPong() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        try {
            ws.send(JSON.stringify({
                type: 'pong',
                timestamp: Date.now()
            }));
        } catch (e) {
            console.error('❌ Failed to send pong:', e);
        }
    }
}

// 指数退避重连
function scheduleReconnect() {
    if (reconnectTimer) {
        clearTimeout(reconnectTimer);
    }
    
    // 计算延迟：1s, 2s, 4s, 8s, ..., 最多 30s
    const delay = Math.min(
        RECONNECT_BASE_DELAY * Math.pow(2, reconnectAttempts),
        RECONNECT_MAX_DELAY
    );
    
    reconnectAttempts++;
    
    console.log(`🔄 Reconnecting in ${delay}ms (attempt ${reconnectAttempts})...`);
    
    reconnectTimer = setTimeout(() => {
        connectWebSocket();
    }, delay);
}

// 更新连接状态
function updateConnectionStatus(connected) {
    const statusEl = document.getElementById('connection-status');
    if (connected) {
        statusEl.textContent = '🟢 已连接';
        statusEl.style.color = '#4caf50';
    } else {
        statusEl.textContent = '🔴 未连接';
        statusEl.style.color = '#f44336';
    }
}

// 更新机器人状态
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
        document.getElementById('robots-container').appendChild(card);
        hideNoRobots();
    }
    
    // 更新卡片内容
    updateRobotCard(card, data);
}

// 创建机器人卡片
function createRobotCard(robotId) {
    const card = document.createElement('div');
    card.id = `robot-${robotId}`;
    card.className = 'robot-card';
    card.innerHTML = `
        <h3>
            <span>🤖 机器人 ${robotId}</span>
            <span class="status-badge">在线</span>
        </h3>
        <div class="info-row">
            <span class="label">🔋 电量</span>
            <span class="value battery">--</span>
        </div>
        <div class="info-row">
            <span class="label">🌡️ 温度</span>
            <span class="value temperature">--</span>
        </div>
        <div class="info-row">
            <span class="label">🧠 行为</span>
            <span class="value behavior">--</span>
        </div>
        <div class="info-row">
            <span class="label">🚶 运动</span>
            <span class="value motion">--</span>
        </div>
        <div class="info-row">
            <span class="label">🤸 状态</span>
            <span class="value fallen">--</span>
        </div>
        <div class="info-row">
            <span class="label">⚽ 球</span>
            <span class="value ball">--</span>
        </div>
        <div class="info-row">
            <span class="label">⏱️ 时间</span>
            <span class="value timestamp">--</span>
        </div>
    `;
    return card;
}

// 更新机器人卡片
function updateRobotCard(card, data) {
    // 更新在线状态
    const isOnline = data.online !== false;
    card.className = isOnline ? 'robot-card online' : 'robot-card offline';
    
    if (data.fallen) {
        card.className += ' fallen';
    }
    
    card.querySelector('.status-badge').textContent = isOnline ? '在线' : '离线';
    
    // 更新各项数据
    if (isOnline) {
        card.querySelector('.battery').textContent = `${data.battery?.toFixed(1) || '--'}%`;
        card.querySelector('.temperature').textContent = `${data.temperature?.toFixed(1) || '--'}°C`;
        card.querySelector('.behavior').textContent = data.behavior || '未知';
        card.querySelector('.motion').textContent = data.motion || '未知';
        card.querySelector('.fallen').textContent = data.fallen ? '🤸 摔倒' : '✅ 正常';
        card.querySelector('.ball').textContent = data.ball_visible ? '⚽ 可见' : '❌ 不可见';
        card.querySelector('.timestamp').textContent = formatTimestamp(data.timestamp);
    }
}

// 定期检查超时（降低频率）
setInterval(() => {
    const now = Date.now();
    robotStates.forEach((state, robotId) => {
        if (now - state.lastUpdate > 5000) {
            const card = document.getElementById(`robot-${robotId}`);
            if (card && !card.classList.contains('offline')) {
                card.className = 'robot-card offline';
                card.querySelector('.status-badge').textContent = '离线';
            }
        }
    });
}, 2000);  // 2 秒检查一次（而不是 1 秒）

// 更新机器人计数
function updateRobotCount() {
    const count = robotStates.size;
    document.getElementById('robot-count').textContent = `${count} 个机器人`;
}

// 隐藏"无机器人"提示
function hideNoRobots() {
    const noRobotsEl = document.getElementById('no-robots');
    if (noRobotsEl) {
        noRobotsEl.style.display = 'none';
    }
}

// 格式化时间戳
function formatTimestamp(ms) {
    if (!ms) return '--';
    
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) {
        return `${hours}:${String(minutes % 60).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
    } else if (minutes > 0) {
        return `${minutes}:${String(seconds % 60).padStart(2, '0')}`;
    } else {
        return `${seconds}s`;
    }
}

// 页面可见性优化
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        console.log('📴 Page hidden, reducing activity');
        stopHeartbeat();
    } else {
        console.log('📱 Page visible, resuming activity');
        if (ws && ws.readyState === WebSocket.OPEN) {
            startHeartbeat();
        }
    }
});
