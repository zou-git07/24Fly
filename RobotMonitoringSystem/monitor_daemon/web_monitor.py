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


# ============ ActiveMatch 管理 ============
class ActiveMatch:
    """正在进行的比赛管理"""
    def __init__(self):
        self.match_id = None
        self.start_time = None
        self.log_dir = None
        self.robots = set()
        self.is_active = False
        self.last_activity = 0
    
    def start(self, match_id, log_dir):
        """启动新比赛"""
        self.match_id = match_id
        self.start_time = time.time()
        self.log_dir = log_dir
        self.robots = set()
        self.is_active = True
        self.last_activity = time.time()
        print(f"🎬 Started active match: {match_id}")
    
    def add_robot(self, robot_id):
        """添加机器人"""
        self.robots.add(robot_id)
        self.last_activity = time.time()
        
        # 如果比赛已结束但又收到数据，重新激活
        if not self.is_active and self.match_id:
            self.is_active = True
            print(f"🔄 Match reactivated: {self.match_id}")
    
    def check_timeout(self):
        """检查是否超时（60 秒无数据则标记为结束）"""
        if self.is_active and time.time() - self.last_activity > 60:
            self.is_active = False
            print(f"🏁 Match ended (timeout): {self.match_id}")
    
    def to_dict(self):
        """转为字典"""
        if not self.is_active:
            return {"active": False}
        
        return {
            "active": True,
            "match_id": self.match_id,
            "start_time": self.start_time,
            "duration": time.time() - self.start_time if self.start_time else 0,
            "robot_count": len(self.robots),
            "robots": sorted(list(self.robots))
        }

active_match = ActiveMatch()


class WebSocketClient:
    """WebSocket 客户端包装器（带缓冲和超时）"""
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.send_queue = asyncio.Queue(maxsize=MAX_SEND_QUEUE)
        self.last_pong = time.time()
        self.active = True
        self.error_count = 0  # 新增：错误计数
        self.max_errors = 3   # 新增：最大允许错误次数
        
    async def send_safe(self, message: str):
        """安全发送（改进版 - 避免竞态条件）"""
        try:
            # 使用 put 而不是 put_nowait，带超时
            await asyncio.wait_for(
                self.send_queue.put(message),
                timeout=0.1
            )
        except asyncio.TimeoutError:
            # 队列满，丢弃最旧的消息
            try:
                self.send_queue.get_nowait()
                await asyncio.wait_for(
                    self.send_queue.put(message),
                    timeout=0.1
                )
            except:
                pass  # 仍然失败，放弃这条消息
        except Exception as e:
            print(f"⚠️  send_safe error: {e}")
    
    async def sender_loop(self):
        """发送循环（带重试机制）"""
        while self.active and self.error_count < self.max_errors:
            try:
                message = await asyncio.wait_for(
                    self.send_queue.get(), 
                    timeout=1.0
                )
                
                # 发送消息（带重试）
                retry = 0
                while retry < 3:
                    try:
                        await self.websocket.send_text(message)
                        self.error_count = 0  # 成功后重置错误计数
                        break
                    except Exception as e:
                        retry += 1
                        if retry >= 3:
                            raise
                        await asyncio.sleep(0.1 * retry)  # 指数退避
                
            except asyncio.TimeoutError:
                # 正常超时，继续
                continue
            except Exception as e:
                self.error_count += 1
                print(f"⚠️  Sender error ({self.error_count}/{self.max_errors}): {e}")
                
                if self.error_count >= self.max_errors:
                    print(f"❌ Client failed after {self.max_errors} errors")
                    self.active = False
                    break
                
                # 等待一下再继续
                await asyncio.sleep(1.0)


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
                print(f"⚠️  Received packet without robot_id: {data[:100]}")
                return
                
            # 更新状态表（Layer 1）
            msg['last_update'] = time.time()
            robot_states[robot_id] = msg
            
            # 调试输出
            if len(robot_states) <= 10:
                print(f"📦 Received from {robot_id}, total robots: {len(robot_states)}")
            
            # 写入日志（异步，不阻塞）
            write_log(robot_id, msg)
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}, data: {data[:100]}")


def write_log(robot_id: str, data: dict):
    """写入日志文件"""
    global current_match_id, log_files, active_match
    
    if current_match_id is None:
        current_match_id = f"match_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        match_dir = LOG_DIR / current_match_id
        match_dir.mkdir(parents=True, exist_ok=True)
        
        # 启动 ActiveMatch
        active_match.start(current_match_id, match_dir)
    
    # 添加机器人到 ActiveMatch
    active_match.add_robot(robot_id)
    
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


# ============ ActiveMatch API ============

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
        
        # 接收循环（处理 pong 和 heartbeat）
        while client.active:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
                msg = json.loads(data)
                
                msg_type = msg.get("type")
                if msg_type == "pong":
                    client.last_pong = time.time()
                elif msg_type == "heartbeat":
                    # 客户端主动心跳，更新时间
                    client.last_pong = time.time()
                # 忽略其他消息类型
                    
            except asyncio.TimeoutError:
                # 正常超时，继续等待
                continue
            except json.JSONDecodeError as e:
                print(f"⚠️  JSON decode error: {e}")
                continue
                
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
