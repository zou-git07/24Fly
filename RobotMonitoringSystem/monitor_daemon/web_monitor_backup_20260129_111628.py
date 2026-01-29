#!/usr/bin/env python3
"""
Web Monitor Daemon - 集成 UDP + WebSocket + HTTP API
类似 GameController 的 Web 实时监控系统
"""

import asyncio
import json
import socket
import time
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Set
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import threading
from concurrent.futures import ThreadPoolExecutor

# 配置
UDP_PORT = 10020
WS_PORT = 8765
HTTP_PORT = 8080
LOG_DIR = Path("RobotMonitoringSystem/monitor_daemon/logs")
ROBOT_TIMEOUT = 5.0  # 5秒无数据则标记为离线

# 全局状态
robot_states: Dict[str, dict] = {}  # robot_id -> state
connected_clients: Set[WebSocket] = set()
current_match_id = None
log_files = {}
broadcast_queue = asyncio.Queue()  # 广播消息队列

# FastAPI 应用
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

# 挂载静态文件
try:
    app.mount("/static", StaticFiles(directory="RobotMonitoringSystem/web_monitor"), name="static")
except:
    pass  # 如果目录不存在，稍后创建


class UDPReceiver:
    """UDP 接收线程"""
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
                
            # 更新状态表
            msg['last_update'] = time.time()
            robot_states[robot_id] = msg
            
            # 写入日志
            write_log(robot_id, msg)
            
            # 将消息放入队列，由后台任务处理
            try:
                broadcast_queue.put_nowait(msg)
            except:
                pass  # 队列满时忽略
            
        except json.JSONDecodeError:
            pass


def write_log(robot_id: str, data: dict):
    """写入日志文件"""
    global current_match_id, log_files
    
    # 创建 match_id（如果还没有）
    if current_match_id is None:
        current_match_id = f"match_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        match_dir = LOG_DIR / current_match_id
        match_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Created match log: {current_match_id}")
    
    # 打开日志文件（如果还没打开）
    if robot_id not in log_files:
        log_path = LOG_DIR / current_match_id / f"robot_{robot_id}.jsonl"
        log_files[robot_id] = open(log_path, 'a')
    
    # 写入一行 JSON
    log_files[robot_id].write(json.dumps(data) + '\n')
    log_files[robot_id].flush()


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
    for client in list(connected_clients):  # 使用 list() 避免迭代时修改
        try:
            await client.send_text(message)
        except Exception as e:
            disconnected.add(client)
    
    # 移除断开的客户端
    connected_clients.difference_update(disconnected)


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


# ============ HTTP API ============

@app.get("/")
async def root():
    """重定向到实时监控页面"""
    return HTMLResponse("""
    <html>
    <head><meta http-equiv="refresh" content="0; url=/static/index.html"></head>
    <body>Redirecting to monitor...</body>
    </html>
    """)


@app.get("/api/robots")
async def get_robots():
    """获取当前所有机器人状态"""
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


@app.get("/api/matches")
async def get_matches():
    """获取所有比赛列表"""
    matches = []
    
    if not LOG_DIR.exists():
        return {"matches": []}
    
    for match_dir in sorted(LOG_DIR.iterdir(), reverse=True):
        if match_dir.is_dir() and match_dir.name.startswith("match_"):
            log_files_list = list(match_dir.glob("robot_*.jsonl"))
            total_size = sum(f.stat().st_size for f in log_files_list)
            
            matches.append({
                "id": match_dir.name,
                "robot_count": len(log_files_list),
                "total_size": total_size,
                "timestamp": match_dir.stat().st_mtime
            })
    
    return {"matches": matches}


@app.get("/api/match/{match_id}/robots")
async def get_match_robots(match_id: str):
    """获取指定比赛的机器人列表"""
    match_dir = LOG_DIR / match_id
    
    if not match_dir.exists():
        return {"error": "Match not found"}
    
    robots = []
    for log_file in match_dir.glob("robot_*.jsonl"):
        robot_id = log_file.stem.replace("robot_", "")
        packet_count = sum(1 for _ in open(log_file))
        
        robots.append({
            "robot_id": robot_id,
            "packet_count": packet_count,
            "file_size": log_file.stat().st_size
        })
    
    return {"robots": robots}


@app.get("/api/logs/{match_id}/{robot_id}")
async def get_logs(match_id: str, robot_id: str, offset: int = 0, limit: int = 100):
    """获取机器人日志（分页）"""
    log_file = LOG_DIR / match_id / f"robot_{robot_id}.jsonl"
    
    if not log_file.exists():
        return {"error": "Log file not found"}
    
    data = []
    with open(log_file, 'r') as f:
        # 跳过前 offset 行
        for _ in range(offset):
            if not f.readline():
                break
        
        # 读取 limit 行
        for _ in range(limit):
            line = f.readline()
            if not line:
                break
            try:
                data.append(json.loads(line))
            except:
                pass
    
    # 统计总行数
    total_packets = sum(1 for _ in open(log_file))
    
    return {
        "robot_id": robot_id,
        "match_id": match_id,
        "total_packets": total_packets,
        "offset": offset,
        "limit": limit,
        "data": data
    }


# ============ WebSocket ============

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 连接处理"""
    await websocket.accept()
    connected_clients.add(websocket)
    print(f"🔌 WebSocket client connected (total: {len(connected_clients)})")
    
    try:
        # 发送当前所有机器人状态
        for robot_id, state in robot_states.items():
            await websocket.send_text(json.dumps({
                "type": "robot_update",
                "data": state
            }))
        
        # 保持连接
        while True:
            data = await websocket.receive_text()
            # 可以处理客户端发来的消息（如果需要）
            
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        print(f"🔌 WebSocket client disconnected (total: {len(connected_clients)})")


# ============ 主函数 ============

def main():
    print("=" * 60)
    print("  🤖 Robot Web Monitor - Starting")
    print("=" * 60)
    
    # 创建日志目录
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # 启动 UDP 接收器
    udp_receiver = UDPReceiver()
    udp_receiver.start()
    
    # 启动 Web 服务器
    print(f"🌐 Web Server starting on http://localhost:{HTTP_PORT}")
    print(f"🔌 WebSocket Server on ws://localhost:{HTTP_PORT}/ws")
    print("=" * 60)
    print("📊 Open in browser: http://localhost:8080")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=HTTP_PORT, log_level="warning")


if __name__ == "__main__":
    main()
