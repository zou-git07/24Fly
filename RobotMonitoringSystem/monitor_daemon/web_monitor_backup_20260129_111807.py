#!/usr/bin/env python3
"""
Web Monitor Daemon - 稳定版
核心改进：
1. 节流推送（2 Hz）
2. 批量聚合
3. 心跳保活
4. 异常隔离
"""

import asyncio
import json
import socket
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Set
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import threading

# ============ 配置 ============
UDP_PORT = 10020
HTTP_PORT = 8080
LOG_DIR = Path("RobotMonitoringSystem/monitor_daemon/logs")
ROBOT_TIMEOUT = 5.0

# 稳定性配置
BROADCAST_INTERVAL = 0.5  # 500ms = 2 Hz
HEARTBEAT_INTERVAL = 10.0  # 10 秒心跳
CLIENT_TIMEOUT = 30.0      # 30 秒无响应断开
MAX_SEND_QUEUE = 10        # 每个客户端最多缓存 10 条消息

# ============ 全局状态 ============
robot_states: Dict[str, dict] = {}
current_match_id = None
log_files = {}


class WebSocketClient:
    """WebSocket 客户端包装器（带缓冲和超时）"""
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.send_queue = asyncio.Queue(maxsize=MAX_SEND_QUEUE)
        self.last_pong = time.time()
        self.active = True
        
    async def send_safe(self, message: str):
        """安全发送（不阻塞）"""
        try:
            self.send_queue.put_nowait(message)
        except asyncio.QueueFull:
            # 队列满 = 慢客户端，丢弃旧消息
            try:
                self.send_queue.get_nowait()
                self.send_queue.put_nowait(message)
            except:
                pass
    
    async def sender_loop(self):
        """发送循环（独立协程）"""
        try:
            while self.active:
                message = await asyncio.wait_for(
                    self.send_queue.get(), 
                    timeout=1.0
                )
                await self.websocket.send_text(message)
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            print(f"⚠️  Sender error: {e}")
            self.active = False


class ClientManager:
    """客户端管理器"""
    def __init__(self):
        self.clients: Set[WebSocketClient] = set()
        self.lock = asyncio.Lock()
    
    async def add(self, client: WebSocketClient):
        async with self.lock:
            self.clients.add(client)
            print(f"🔌 Client connected (total: {len(self.clients)})")
    
    async def remove(self, client: WebSocketClient):
        async with self.lock:
            self.clients.discard(client)
            client.active = False
            print(f"🔌 Client disconnected (total: {len(self.clients)})")
    
    async def broadcast(self, message: str):
        """广播消息（非阻塞）"""
        async with self.lock:
            dead_clients = []
            for client in self.clients:
                if not client.active:
                    dead_clients.append(client)
                else:
                    await client.send_safe(message)
            
            # 清理死连接
            for client in dead_clients:
                self.clients.discard(client)
    
    async def heartbeat_loop(self):
        """心跳循环"""
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            
            ping_msg = json.dumps({"type": "ping", "timestamp": time.time()})
            await self.broadcast(ping_msg)
            
            # 检查超时客户端
            now = time.time()
            async with self.lock:
                timeout_clients = [
                    c for c in self.clients 
                    if now - c.last_pong > CLIENT_TIMEOUT
                ]
                for client in timeout_clients:
                    print(f"⏱️  Client timeout, removing")
                    client.active = False
                    self.clients.discard(client)


client_manager = ClientManager()


# ============ UDP 接收器 ============
class UDPReceiver:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', UDP_PORT))
        self.running = True
        
    def start(self):
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        print(f"✅ UDP Receiver started on port {UDP_PORT}")
        
    def run(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                self.handle_packet(data.decode('utf-8'))
            except Exception as e:
                print(f"❌ UDP Error: {e}")
                
    def handle_packet(self, data: str):
        try:
            msg = json.loads(data)
            robot_id = msg.get('robot_id')
            
            if not robot_id:
                return
                
            # 更新状态表（Layer 1）
            msg['last_update'] = time.time()
            robot_states[robot_id] = msg
            
            # 写入日志（异步，不阻塞）
            write_log(robot_id, msg)
            
        except json.JSONDecodeError:
            pass


def write_log(robot_id: str, data: dict):
    """写入日志文件"""
    global current_match_id, log_files
    
    if current_match_id is None:
        current_match_id = f"match_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        match_dir = LOG_DIR / current_match_id
        match_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Created match log: {current_match_id}")
    
    if robot_id not in log_files:
        log_path = LOG_DIR / current_match_id / f"robot_{robot_id}.jsonl"
        log_files[robot_id] = open(log_path, 'a')
    
    log_files[robot_id].write(json.dumps(data) + '\n')
    log_files[robot_id].flush()


# ============ 广播任务（Layer 2 + 3）============
async def broadcast_worker():
    """定期广播机器人状态快照（2 Hz）"""
    print("✅ Broadcast worker started (2 Hz)")
    
    while True:
        try:
            await asyncio.sleep(BROADCAST_INTERVAL)
            
            # 收集所有机器人最新状态
            snapshot = []
            now = time.time()
            
            for robot_id, state in list(robot_states.items()):
                is_online = (now - state.get('last_update', 0)) < ROBOT_TIMEOUT
                snapshot.append({
                    "robot_id": robot_id,
                    "online": is_online,
                    **state
                })
            
            if not snapshot:
                continue
            
            # 批量推送
            message = json.dumps({
                "type": "snapshot",
                "timestamp": now,
                "robots": snapshot
            })
            
            await client_manager.broadcast(message)
            
        except Exception as e:
            print(f"❌ Broadcast error: {e}")
            await asyncio.sleep(1.0)


# ============ FastAPI 应用 ============
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动后台任务
    asyncio.create_task(broadcast_worker())
    asyncio.create_task(client_manager.heartbeat_loop())
    yield

app = FastAPI(title="Robot Monitor API (Stable)", lifespan=lifespan)

try:
    app.mount("/static", StaticFiles(directory="RobotMonitoringSystem/web_monitor"), name="static")
except:
    pass


@app.get("/")
async def root():
    return HTMLResponse("""
    <html>
    <head><meta http-equiv="refresh" content="0; url=/static/index.html"></head>
    <body>Redirecting...</body>
    </html>
    """)


@app.get("/api/robots")
async def get_robots():
    now = time.time()
    robots = []
    
    for robot_id, state in robot_states.items():
        is_online = (now - state.get('last_update', 0)) < ROBOT_TIMEOUT
        robots.append({
            "robot_id": robot_id,
            "online": is_online,
            "state": state
        })
    
    return {"robots": robots}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    client = WebSocketClient(websocket)
    await client_manager.add(client)
    
    # 启动发送循环
    sender_task = asyncio.create_task(client.sender_loop())
    
    try:
        # 发送初始快照
        snapshot = []
        now = time.time()
        for robot_id, state in robot_states.items():
            is_online = (now - state.get('last_update', 0)) < ROBOT_TIMEOUT
            snapshot.append({"robot_id": robot_id, "online": is_online, **state})
        
        if snapshot:
            await client.send_safe(json.dumps({
                "type": "snapshot",
                "robots": snapshot
            }))
        
        # 接收循环（处理 pong）
        while client.active:
            data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
            msg = json.loads(data)
            
            if msg.get("type") == "pong":
                client.last_pong = time.time()
                
    except asyncio.TimeoutError:
        pass
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"⚠️  WebSocket error: {e}")
    finally:
        await client_manager.remove(client)
        sender_task.cancel()


def main():
    print("=" * 60)
    print("  🤖 Robot Web Monitor - STABLE VERSION")
    print("=" * 60)
    
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    udp_receiver = UDPReceiver()
    udp_receiver.start()
    
    print(f"🌐 Web Server: http://localhost:{HTTP_PORT}")
    print(f"📊 Broadcast: {1/BROADCAST_INTERVAL} Hz")
    print(f"💓 Heartbeat: every {HEARTBEAT_INTERVAL}s")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=HTTP_PORT, log_level="warning")


if __name__ == "__main__":
    main()
