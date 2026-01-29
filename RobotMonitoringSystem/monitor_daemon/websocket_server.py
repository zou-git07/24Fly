#!/usr/bin/env python3
"""
WebSocket 服务器

功能：
1. 提供 WebSocket 接口供 Web GUI 订阅
2. 广播机器人状态更新
3. 处理客户端请求（获取机器人列表、历史数据等）
"""

import asyncio
import websockets
import json
import threading
from google.protobuf.json_format import MessageToDict


class WebSocketServer:
    """WebSocket 服务器"""
    
    def __init__(self, port=8765, daemon=None):
        self.port = port
        self.daemon = daemon  # MonitorDaemon 实例
        self.clients = set()
        self.loop = None
        self.server = None
        
    def start(self):
        """启动 WebSocket 服务器（独立线程）"""
        thread = threading.Thread(target=self._run_server, daemon=True)
        thread.start()
        
    def _run_server(self):
        """运行服务器（在独立线程中）"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        start_server = websockets.serve(self._handle_client, '0.0.0.0', self.port)
        self.server = self.loop.run_until_complete(start_server)
        
        print(f"[WebSocketServer] Started on port {self.port}")
        self.loop.run_forever()
        
    async def _handle_client(self, websocket, path):
        """处理客户端连接"""
        self.clients.add(websocket)
        print(f"[WebSocketServer] Client connected: {websocket.remote_address}")
        
        try:
            # 发送欢迎消息
            await websocket.send(json.dumps({
                'type': 'welcome',
                'message': 'Connected to Robot Monitoring System'
            }))
            
            # 处理客户端消息
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(websocket, data)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'Invalid JSON'
                    }))
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)
            print(f"[WebSocketServer] Client disconnected: {websocket.remote_address}")
            
    async def _handle_message(self, websocket, data):
        """处理客户端消息"""
        msg_type = data.get('type')
        
        if msg_type == 'get_robots':
            # 获取所有机器人列表
            robot_ids = self.daemon.get_all_robot_ids()
            await websocket.send(json.dumps({
                'type': 'robot_list',
                'robots': robot_ids
            }))
            
        elif msg_type == 'get_state':
            # 获取指定机器人的最新状态
            robot_id = data.get('robot_id')
            state = self.daemon.get_latest_state(robot_id)
            if state:
                state_dict = MessageToDict(state, preserving_proto_field_name=True)
                await websocket.send(json.dumps({
                    'type': 'robot_state',
                    'robot_id': robot_id,
                    'data': state_dict
                }))
            else:
                await websocket.send(json.dumps({
                    'type': 'error',
                    'message': f'No state for robot {robot_id}'
                }))
                
    def broadcast_state(self, robot_id, state):
        """广播状态更新到所有客户端"""
        if not self.clients or self.loop is None:
            return
            
        state_dict = MessageToDict(state, preserving_proto_field_name=True)
        message = json.dumps({
            'type': 'robot_state',
            'robot_id': robot_id,
            'data': state_dict
        })
        
        # 在事件循环中异步发送
        asyncio.run_coroutine_threadsafe(
            self._broadcast(message),
            self.loop
        )
        
    async def _broadcast(self, message):
        """异步广播消息"""
        if self.clients:
            await asyncio.gather(
                *[client.send(message) for client in self.clients],
                return_exceptions=True
            )
            
    def stop(self):
        """停止服务器"""
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
