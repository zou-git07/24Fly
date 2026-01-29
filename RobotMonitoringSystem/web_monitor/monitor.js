// 实时监控页面逻辑 - 稳定版 v2
// 核心改进：
// 1. 使用 RobustWebSocket 类（自动重连 + 心跳）
// 2. 批量处理快照
// 3. 性能优化
// 4. 异常容错

const robotStates = new Map();
let robustWS = null;

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    connectWebSocket();
});

// WebSocket 连接（使用 RobustWebSocket）
function connectWebSocket() {
    const wsUrl = `ws://${window.location.hostname}:${window.location.port}/ws`;
    
    // 创建 RobustWebSocket 实例
    robustWS = new RobustWebSocket(wsUrl, {
        maxReconnectDelay: 30000  // 最大重连延迟 30 秒
    });
    
    // 连接成功回调
    robustWS.onConnected = () => {
        console.log('✅ Connected to server');
        updateConnectionStatus(true);
    };
    
    // 断开连接回调
    robustWS.onDisconnected = () => {
        console.log('🔴 Disconnected from server');
        updateConnectionStatus(false);
    };
    
    // 消息处理回调
    robustWS.onMessage = (msg) => {
        handleMessage(msg);
    };
    
    // 错误处理回调
    robustWS.onError = (error) => {
        console.error('❌ WebSocket error:', error);
    };
    
    // 开始连接
    robustWS.connect();
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
