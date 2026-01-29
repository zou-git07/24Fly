// 实时监控页面逻辑

const robotStates = new Map();
let ws = null;
let reconnectTimer = null;

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    connectWebSocket();
});

// WebSocket 连接
function connectWebSocket() {
    const wsUrl = `ws://${window.location.hostname}:${window.location.port}/ws`;
    
    try {
        ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            console.log('✅ WebSocket connected');
            updateConnectionStatus(true);
        };
        
        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            
            if (msg.type === 'robot_update') {
                updateRobot(msg.data);
            } else if (msg.type === 'robot_offline') {
                markOffline(msg.robot_id);
            }
        };
        
        ws.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
            updateConnectionStatus(false);
        };
        
        ws.onclose = () => {
            console.log('🔴 WebSocket disconnected');
            updateConnectionStatus(false);
            
            // 5秒后重连
            reconnectTimer = setTimeout(() => {
                console.log('🔄 Reconnecting...');
                connectWebSocket();
            }, 5000);
        };
        
    } catch (error) {
        console.error('❌ Failed to connect:', error);
        updateConnectionStatus(false);
    }
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
    
    // 更新机器人计数
    updateRobotCount();
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
    card.className = 'robot-card online';
    if (data.fallen) {
        card.className += ' fallen';
    }
    
    // 更新各项数据
    card.querySelector('.battery').textContent = `${data.battery.toFixed(1)}%`;
    card.querySelector('.temperature').textContent = `${data.temperature.toFixed(1)}°C`;
    card.querySelector('.behavior').textContent = data.behavior || '未知';
    card.querySelector('.motion').textContent = data.motion || '未知';
    card.querySelector('.fallen').textContent = data.fallen ? '🤸 摔倒' : '✅ 正常';
    card.querySelector('.ball').textContent = data.ball_visible ? '⚽ 可见' : '❌ 不可见';
    card.querySelector('.timestamp').textContent = formatTimestamp(data.timestamp);
}

// 标记机器人离线
function markOffline(robotId) {
    const card = document.getElementById(`robot-${robotId}`);
    if (card) {
        card.className = 'robot-card offline';
        card.querySelector('.status-badge').textContent = '离线';
    }
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

// 更新机器人计数
function updateRobotCount() {
    const count = robotStates.size;
    document.getElementById('robot-count').textContent = `${count} 个机器人`;
}

// 隐藏"无机器人"提示
function hideNoRobots() {
    document.getElementById('no-robots').style.display = 'none';
}

// 格式化时间戳
function formatTimestamp(ms) {
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
