// 历史日志查看页面逻辑

let currentMatch = null;
let currentRobot = null;
let liveUpdateInterval = null;
let isLiveMode = false;

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    init();
    
    // 事件监听
    document.getElementById('match-select').addEventListener('change', onMatchChange);
    document.getElementById('robot-select').addEventListener('change', onRobotChange);
    document.getElementById('load-btn').addEventListener('click', loadLogs);
});

// 机器人选择变化
function onRobotChange(event) {
    currentRobot = event.target.value;
    
    // 如果在实时模式，立即加载新机器人的日志
    if (isLiveMode) {
        loadLiveLogs();
    }
}

// 初始化
async function init() {
    // 先检查是否有正在进行的比赛
    const activeMatch = await checkActiveMatch();
    
    if (activeMatch) {
        showActiveMatchBanner(activeMatch);
    }
    
    // 加载历史比赛列表
    loadMatches();
}

// 检查是否有正在进行的比赛
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

// 显示正在进行的比赛横幅
function showActiveMatchBanner(matchData) {
    const banner = document.createElement('div');
    banner.id = 'active-match-banner';
    banner.style.cssText = 'background: linear-gradient(135deg, #ff5722 0%, #ff7043 100%); color: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(255,87,34,0.3);';
    banner.innerHTML = `
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; align-items: center; gap: 20px;">
                <span style="font-size: 24px; animation: pulse 2s infinite;">🔴</span>
                <div>
                    <div style="font-size: 18px; font-weight: bold; margin-bottom: 5px;">正在进行的比赛</div>
                    <div style="font-size: 14px; opacity: 0.9;">
                        <span>${matchData.match_id}</span>
                        <span style="margin-left: 15px;">📊 ${matchData.robot_count} 个机器人</span>
                        <span style="margin-left: 15px;">⏱️ 已运行 ${formatDuration(matchData.duration)}</span>
                    </div>
                </div>
            </div>
            <button id="attach-live-btn" class="btn" style="background: white; color: #ff5722; font-weight: bold; padding: 12px 24px; border: none; cursor: pointer; border-radius: 8px; font-size: 16px;">
                📡 接入实时日志
            </button>
        </div>
    `;
    
    // 添加脉冲动画
    const style = document.createElement('style');
    style.textContent = `
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.7; transform: scale(1.1); }
        }
    `;
    document.head.appendChild(style);
    
    document.querySelector('.controls').insertAdjacentElement('beforebegin', banner);
    
    document.getElementById('attach-live-btn').addEventListener('click', () => {
        attachToLiveMatch(matchData);
    });
}

// 接入实时比赛
async function attachToLiveMatch(matchData) {
    try {
        isLiveMode = true;
        
        // 1. 加载机器人列表
        const response = await fetch('/api/current_match/robots');
        const data = await response.json();
        
        if (data.error) {
            alert(data.error);
            return;
        }
        
        const select = document.getElementById('robot-select');
        select.innerHTML = '';
        
        data.robots.forEach(robot => {
            const option = document.createElement('option');
            option.value = robot.robot_id;
            const status = robot.online ? '🟢' : '⚫';
            option.textContent = `Robot ${robot.robot_id} (${robot.packet_count} packets) ${status}`;
            select.appendChild(option);
        });
        
        // 2. 自动加载第一个机器人
        if (data.robots.length > 0) {
            currentRobot = data.robots[0].robot_id;
            loadLiveLogs();
            
            // 3. 启动自动刷新（每 2 秒）
            liveUpdateInterval = setInterval(loadLiveLogs, 2000);
        }
        
        // 4. 更新按钮状态
        const btn = document.getElementById('attach-live-btn');
        btn.textContent = '🔴 实时模式中...';
        btn.disabled = true;
        btn.style.opacity = '0.7';
        
        // 5. 隐藏比赛选择（实时模式下不需要）
        document.getElementById('match-select').disabled = true;
        document.getElementById('load-btn').style.display = 'none';
        
    } catch (error) {
        console.error('Failed to attach to live match:', error);
        alert('接入失败: ' + error.message);
    }
}

// 加载实时日志
async function loadLiveLogs() {
    const robotId = document.getElementById('robot-select').value;
    
    if (!robotId) return;
    
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
            stopLiveMode();
            alert('⚠️ 比赛已结束，已切换到历史模式');
            location.reload();
        }
        
    } catch (error) {
        console.error('Failed to load live logs:', error);
    }
}

// 停止实时模式
function stopLiveMode() {
    if (liveUpdateInterval) {
        clearInterval(liveUpdateInterval);
        liveUpdateInterval = null;
    }
    isLiveMode = false;
}

// 加载比赛列表
async function loadMatches() {
    try {
        const response = await fetch('/api/matches');
        const data = await response.json();
        
        const select = document.getElementById('match-select');
        select.innerHTML = '';
        
        if (data.matches.length === 0) {
            select.innerHTML = '<option>未找到比赛</option>';
            return;
        }
        
        data.matches.forEach(match => {
            const option = document.createElement('option');
            option.value = match.id;
            option.textContent = `${match.id} (${match.robot_count} robots, ${formatSize(match.total_size)})`;
            select.appendChild(option);
        });
        
        // 自动选择第一个
        if (data.matches.length > 0) {
            currentMatch = data.matches[0].id;
            loadRobots(currentMatch);
        }
        
    } catch (error) {
        console.error('Failed to load matches:', error);
        document.getElementById('match-select').innerHTML = '<option>加载比赛失败</option>';
    }
}

// 比赛选择变化
function onMatchChange(event) {
    currentMatch = event.target.value;
    loadRobots(currentMatch);
}

// 加载机器人列表
async function loadRobots(matchId) {
    try {
        const response = await fetch(`/api/match/${matchId}/robots`);
        const data = await response.json();
        
        const select = document.getElementById('robot-select');
        select.innerHTML = '';
        
        if (data.robots && data.robots.length > 0) {
            data.robots.forEach(robot => {
                const option = document.createElement('option');
                option.value = robot.robot_id;
                option.textContent = `Robot ${robot.robot_id} (${robot.packet_count} packets, ${formatSize(robot.file_size)})`;
                select.appendChild(option);
            });
            
            currentRobot = data.robots[0].robot_id;
        } else {
            select.innerHTML = '<option>未找到机器人</option>';
        }
        
    } catch (error) {
        console.error('Failed to load robots:', error);
        document.getElementById('robot-select').innerHTML = '<option>加载机器人失败</option>';
    }
}

// 加载日志
async function loadLogs() {
    const matchId = document.getElementById('match-select').value;
    const robotId = document.getElementById('robot-select').value;
    
    if (!matchId || !robotId) {
        alert('请选择比赛和机器人');
        return;
    }
    
    try {
        // 显示加载状态
        document.getElementById('log-info').innerHTML = '<p class="loading">⏳ 加载日志中...</p>';
        document.getElementById('timeline').innerHTML = '';
        document.getElementById('events').innerHTML = '';
        document.getElementById('raw-data').textContent = '';
        
        // 加载日志数据
        const response = await fetch(`/api/logs/${matchId}/${robotId}?offset=0&limit=1000`);
        const data = await response.json();
        
        if (data.error) {
            alert(data.error);
            return;
        }
        
        // 显示日志信息
        displayLogInfo(data);
        
        // 显示时间轴
        displayTimeline(data.data);
        
        // 显示事件
        displayEvents(data.data);
        
        // 显示原始数据（最新50条）
        displayRawData(data.data.slice(-50));
        
    } catch (error) {
        console.error('Failed to load logs:', error);
        alert('加载日志失败: ' + error.message);
    }
}

// 显示日志信息
function displayLogInfo(data) {
    const infoEl = document.getElementById('log-info');
    infoEl.innerHTML = `
        <h3>📊 日志信息</h3>
        <p><strong>比赛：</strong> ${data.match_id}</p>
        <p><strong>机器人：</strong> ${data.robot_id}</p>
        <p><strong>总数据包：</strong> ${data.total_packets}</p>
        <p><strong>已加载：</strong> ${data.data.length} 条数据</p>
    `;
}

// 显示时间轴
function displayTimeline(logs) {
    const timelineEl = document.getElementById('timeline');
    
    if (logs.length === 0) {
        timelineEl.innerHTML = '<p>无可用数据</p>';
        return;
    }
    
    // 计算统计信息
    const startTime = logs[0].timestamp;
    const endTime = logs[logs.length - 1].timestamp;
    const duration = (endTime - startTime) / 1000; // 秒
    
    const fallenCount = logs.filter(l => l.fallen).length;
    const ballVisibleCount = logs.filter(l => l.ball_visible).length;
    
    timelineEl.innerHTML = `
        <h3>⏱️ 时间轴</h3>
        <p><strong>持续时间：</strong> ${formatDuration(duration)}</p>
        <p><strong>开始时间：</strong> ${formatTimestamp(startTime)}</p>
        <p><strong>结束时间：</strong> ${formatTimestamp(endTime)}</p>
        <p><strong>摔倒次数：</strong> ${fallenCount} / ${logs.length} (${(fallenCount/logs.length*100).toFixed(1)}%)</p>
        <p><strong>球可见：</strong> ${ballVisibleCount} / ${logs.length} (${(ballVisibleCount/logs.length*100).toFixed(1)}%)</p>
    `;
}

// 显示事件
function displayEvents(logs) {
    const eventsEl = document.getElementById('events');
    
    if (logs.length === 0) {
        eventsEl.innerHTML = '<p>无事件</p>';
        return;
    }
    
    // 提取关键事件
    const events = [];
    let wasFallen = false;
    let hadBall = logs[0].ball_visible;
    
    logs.forEach((log, index) => {
        // 摔倒事件
        if (log.fallen && !wasFallen) {
            events.push({
                time: log.timestamp,
                type: 'fallen',
                message: '🤸 机器人摔倒'
            });
        } else if (!log.fallen && wasFallen) {
            events.push({
                time: log.timestamp,
                type: 'recovered',
                message: '✅ 机器人恢复'
            });
        }
        wasFallen = log.fallen;
        
        // 球可见性变化
        if (log.ball_visible && !hadBall) {
            events.push({
                time: log.timestamp,
                type: 'ball_found',
                message: '⚽ 发现球'
            });
        } else if (!log.ball_visible && hadBall) {
            events.push({
                time: log.timestamp,
                type: 'ball_lost',
                message: '❌ 丢失球'
            });
        }
        hadBall = log.ball_visible;
    });
    
    // 显示事件
    eventsEl.innerHTML = '<h3>📋 事件列表</h3>';
    
    if (events.length === 0) {
        eventsEl.innerHTML += '<p>无重要事件</p>';
    } else {
        events.forEach(event => {
            const eventDiv = document.createElement('div');
            eventDiv.className = 'event-item';
            eventDiv.innerHTML = `
                <strong>${formatTimestamp(event.time)}</strong> - ${event.message}
            `;
            eventsEl.appendChild(eventDiv);
        });
    }
}

// 显示原始数据
function displayRawData(logs) {
    const rawDataEl = document.getElementById('raw-data');
    rawDataEl.textContent = JSON.stringify(logs, null, 2);
}

// 格式化文件大小
function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// 格式化时长
function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
        return `${hours}小时 ${minutes}分 ${secs}秒`;
    } else if (minutes > 0) {
        return `${minutes}分 ${secs}秒`;
    } else {
        return `${secs}秒`;
    }
}

// 格式化时间戳
function formatTimestamp(ms) {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    
    return `${String(hours).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
}
