// RobustWebSocket - 稳定的 WebSocket 连接类
// 特性：
// - 自动重连（指数退避）
// - 心跳保活
// - 异常容错
// - 连接状态管理

class RobustWebSocket {
    constructor(url, options = {}) {
        this.url = url;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectDelay = options.maxReconnectDelay || 30000;  // 最大 30 秒
        this.heartbeatInterval = null;
        this.lastPongTime = Date.now();
        this.isIntentionallyClosed = false;
        this.reconnectTimer = null;
        
        // 回调函数
        this.onConnected = null;
        this.onDisconnected = null;
        this.onMessage = null;
        this.onError = null;
    }
    
    connect() {
        // 清除之前的重连定时器
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        
        try {
            console.log(`🔌 Connecting to ${this.url}...`);
            this.ws = new WebSocket(this.url);
            
            this.ws.onopen = () => {
                console.log('✅ WebSocket connected');
                this.reconnectAttempts = 0;
                this.lastPongTime = Date.now();
                this.startHeartbeat();
                
                if (this.onConnected) {
                    this.onConnected();
                }
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);
                    
                    if (msg.type === 'ping') {
                        // 响应 ping
                        this.sendPong(msg.timestamp);
                        this.lastPongTime = Date.now();
                    } else {
                        // 更新最后接收时间
                        this.lastPongTime = Date.now();
                        
                        // 调用消息处理回调
                        if (this.onMessage) {
                            this.onMessage(msg);
                        }
                    }
                } catch (e) {
                    console.error('❌ Parse error:', e);
                }
            };
            
            this.ws.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
                
                if (this.onError) {
                    this.onError(error);
                }
            };
            
            this.ws.onclose = (event) => {
                console.log(`🔴 WebSocket closed: code=${event.code}, reason=${event.reason || 'none'}`);
                this.stopHeartbeat();
                
                if (this.onDisconnected) {
                    this.onDisconnected(event);
                }
                
                if (!this.isIntentionallyClosed) {
                    this.scheduleReconnect();
                }
            };
            
        } catch (error) {
            console.error('❌ Failed to create WebSocket:', error);
            this.scheduleReconnect();
        }
    }
    
    sendPong(timestamp) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            try {
                this.ws.send(JSON.stringify({
                    type: 'pong',
                    timestamp: timestamp,
                    clientTime: Date.now()
                }));
            } catch (e) {
                console.error('❌ Failed to send pong:', e);
                // 不要因为 pong 失败就断开，可能只是暂时的
            }
        }
    }
    
    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            try {
                const message = typeof data === 'string' ? data : JSON.stringify(data);
                this.ws.send(message);
                return true;
            } catch (e) {
                console.error('❌ Failed to send message:', e);
                return false;
            }
        }
        return false;
    }
    
    startHeartbeat() {
        this.stopHeartbeat();
        
        // 每 15 秒主动发送一次心跳
        this.heartbeatInterval = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                try {
                    this.ws.send(JSON.stringify({
                        type: 'heartbeat',
                        timestamp: Date.now()
                    }));
                } catch (e) {
                    console.error('❌ Heartbeat failed:', e);
                }
            }
            
            // 检查是否长时间没收到消息
            const now = Date.now();
            const timeSinceLastPong = now - this.lastPongTime;
            
            if (timeSinceLastPong > 45000) {  // 45 秒
                console.warn(`⚠️  No message for ${Math.floor(timeSinceLastPong/1000)}s, reconnecting...`);
                if (this.ws) {
                    this.ws.close();
                }
            }
        }, 15000);
    }
    
    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }
    
    scheduleReconnect() {
        // 清除之前的定时器
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
        }
        
        // 指数退避：1s, 2s, 4s, 8s, 16s, 30s (max)
        const delay = Math.min(
            1000 * Math.pow(2, this.reconnectAttempts),
            this.maxReconnectDelay
        );
        
        this.reconnectAttempts++;
        
        console.log(`🔄 Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})...`);
        
        this.reconnectTimer = setTimeout(() => {
            if (!this.isIntentionallyClosed) {
                this.connect();
            }
        }, delay);
    }
    
    close() {
        console.log('🛑 Closing WebSocket intentionally');
        this.isIntentionallyClosed = true;
        this.stopHeartbeat();
        
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
    
    getState() {
        if (!this.ws) return 'CLOSED';
        
        switch (this.ws.readyState) {
            case WebSocket.CONNECTING: return 'CONNECTING';
            case WebSocket.OPEN: return 'OPEN';
            case WebSocket.CLOSING: return 'CLOSING';
            case WebSocket.CLOSED: return 'CLOSED';
            default: return 'UNKNOWN';
        }
    }
    
    isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }
}

// 导出（如果使用模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RobustWebSocket;
}
