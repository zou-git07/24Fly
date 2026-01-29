// Web GUI 主程序
// 连接到 WebSocket 服务器并实时显示机器人状态

class RobotMonitor {
    constructor() {
        this.ws = null;
        this.robots = new Map();  // robot_id -> state
        this.events = [];
        this.maxEvents = 50;
        
        this.connect();
    }
    
    connect() {
        const wsUrl = 'ws://localhost:8765';
        console.log('Connecting to', wsUrl);
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('Connected to monitor server');
            this.updateConnectionStatus(true);
            
            // 请求机器人列表
            this.ws.send(JSON.stringify({ type: 'get_robots' }));
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
        
        this.ws.onclose = () => {
            console.log('Disconnected from monitor server');
            this.updateConnectionStatus(false);
            
            // 5秒后重连
            setTimeout(() => this.connect(), 5000);
        };
    }
    
    handleMessage(data) {
        switch(data.type) {
            case 'welcome':
                console.log('Server:', data.message);
                break;
                
            case 'robot_list':
                console.log('Robots:', data.robots);
                break;
                
            case 'robot_state':
                this.updateRobotState(data.robot_id, data.data);
                break;
                
            case 'error':
                console.error('Server error:', data.message);
                break;
        }
    }
    
    updateRobotState(robotId, state) {
        this.robots.set(robotId, state);
        this.renderRobots();
        
        // 处理事件
        if(state.events && state.events.length > 0) {
            state.events.forEach(event => {
                this.addEvent(robotId, event);
            });
        }
    }
    
    renderRobots() {
        const container = document.getElementById('robotsContainer');
        container.innerHTML = '';
        
        this.robots.forEach((state, robotId) => {
            const card = this.createRobotCard(robotId, state);
            container.appendChild(card);
        });
    }
    
    createRobotCard(robotId, state) {
        const card = document.createElement('div');
        card.className = 'robot-card';
        
        const gameState = this.getGameStateName(state.decision?.game_state);
        const battery = state.system?.battery_charge || 0;
        
        card.innerHTML = `
            <div class="robot-header">
                <div class="robot-id">Robot ${robotId}</div>
                <div class="robot-status status-${gameState.toLowerCase()}">${gameState}</div>
            </div>
            <div class="robot-info">
                <div class="info-item">
                    <div class="info-label">电量</div>
                    <div class="info-value">${battery.toFixed(1)}%</div>
                    <div class="battery-bar">
                        <div class="battery-fill ${this.getBatteryClass(battery)}" 
                             style="width: ${battery}%"></div>
                    </div>
                </div>
                <div class="info-item">
                    <div class="info-label">CPU 温度</div>
                    <div class="info-value">${(state.system?.cpu_temperature || 0).toFixed(1)}°C</div>
                </div>
                <div class="info-item">
                    <div class="info-label">角色</div>
                    <div class="info-value">${state.decision?.role || 'N/A'}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">运动</div>
                    <div class="info-value">${this.getMotionName(state.decision?.motion_type)}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">球可见</div>
                    <div class="info-value">${state.perception?.ball?.visible ? '✅ 是' : '❌ 否'}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">定位质量</div>
                    <div class="info-value">${this.getLocalizationQuality(state.perception?.localization?.quality)}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">位置</div>
                    <div class="info-value">
                        (${(state.perception?.localization?.pos_x || 0).toFixed(0)}, 
                         ${(state.perception?.localization?.pos_y || 0).toFixed(0)})
                    </div>
                </div>
                <div class="info-item">
                    <div class="info-label">状态</div>
                    <div class="info-value">${state.system?.is_fallen ? '❌ 摔倒' : '✅ 正常'}</div>
                </div>
            </div>
        `;
        
        return card;
    }
    
    addEvent(robotId, event) {
        const eventObj = {
            robotId,
            type: event.type,
            description: event.description,
            timestamp: event.timestamp_ms,
            time: new Date()
        };
        
        this.events.unshift(eventObj);
        
        // 限制事件数量
        if(this.events.length > this.maxEvents) {
            this.events = this.events.slice(0, this.maxEvents);
        }
        
        this.renderEvents();
    }
    
    renderEvents() {
        const container = document.getElementById('eventsLog');
        container.innerHTML = '';
        
        this.events.forEach(event => {
            const item = document.createElement('div');
            item.className = 'event-item';
            
            const timeStr = event.time.toLocaleTimeString();
            const eventTypeName = this.getEventTypeName(event.type);
            
            item.innerHTML = `
                <div class="event-time">${timeStr}</div>
                <div>
                    <span class="event-robot">[${event.robotId}]</span>
                    <span class="event-type">${eventTypeName}</span>
                </div>
                <div class="event-desc">${event.description}</div>
            `;
            
            container.appendChild(item);
        });
    }
    
    updateConnectionStatus(connected) {
        const status = document.getElementById('connectionStatus');
        if(connected) {
            status.className = 'connection-status connected';
            status.textContent = '✅ 已连接到监控服务器';
        } else {
            status.className = 'connection-status disconnected';
            status.textContent = '⚠️ 未连接到监控服务器 (正在重连...)';
        }
    }
    
    getGameStateName(state) {
        const names = ['INITIAL', 'READY', 'SET', 'PLAYING', 'FINISHED'];
        return names[state] || 'UNKNOWN';
    }
    
    getMotionName(type) {
        const names = ['STAND', 'WALK', 'KICK', 'GET_UP', 'SPECIAL'];
        return names[type] || 'UNKNOWN';
    }
    
    getLocalizationQuality(quality) {
        const names = ['POOR', 'OKAY', 'SUPERB'];
        return names[quality] || 'UNKNOWN';
    }
    
    getEventTypeName(type) {
        const names = [
            'BEHAVIOR_CHANGED', 'ROLE_CHANGED', 'FALLEN', 'GOT_UP',
            'BALL_LOST', 'BALL_FOUND', 'PENALIZED', 'UNPENALIZED',
            'COMMUNICATION_ERROR', 'LOCALIZATION_LOST', 'KICK_EXECUTED'
        ];
        return names[type] || 'UNKNOWN';
    }
    
    getBatteryClass(battery) {
        if(battery > 50) return 'battery-high';
        if(battery > 20) return 'battery-medium';
        return 'battery-low';
    }
}

// 启动监控
const monitor = new RobotMonitor();
