#!/usr/bin/env python3
"""
日志写入器

功能：
1. 管理日志文件生命周期（比赛开始/结束）
2. 异步写入日志（避免阻塞接收线程）
3. 按机器人分文件存储
4. JSON Lines 格式
"""

import json
import threading
import queue
from datetime import datetime
from pathlib import Path
from google.protobuf.json_format import MessageToDict


class LogWriter:
    """日志写入器"""
    
    def __init__(self, log_dir='logs'):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # 当前比赛信息
        self.current_match_id = None
        self.current_match_dir = None
        self.log_files = {}  # robot_id -> file handle
        
        # 写入队列（robot_id, state）
        self.write_queue = queue.Queue(maxsize=10000)
        
        # 写入线程
        self.writer_thread = threading.Thread(target=self._write_loop, daemon=True)
        self.writer_thread.start()
        
        # 比赛状态跟踪
        self.last_game_states = {}  # robot_id -> last_game_state
        
    def write_state(self, robot_id, state):
        """写入状态（非阻塞）"""
        # 检测比赛开始/结束
        self._check_match_lifecycle(robot_id, state)
        
        # 放入写入队列
        try:
            self.write_queue.put_nowait((robot_id, state))
        except queue.Full:
            print(f"[WARNING] Write queue full, dropping state for {robot_id}")
            
    def _check_match_lifecycle(self, robot_id, state):
        """检测比赛生命周期"""
        current_game_state = state.decision.game_state
        last_game_state = self.last_game_states.get(robot_id)
        
        # 比赛开始：INITIAL -> READY
        if (last_game_state == 0 and current_game_state == 1) or \
           (self.current_match_id is None and current_game_state >= 1):
            self._start_match()
            
        # 比赛结束：-> FINISHED
        if current_game_state == 4 and last_game_state != 4:
            self._end_match()
            
        self.last_game_states[robot_id] = current_game_state
        
    def _start_match(self):
        """开始新比赛"""
        if self.current_match_id is not None:
            return  # 已经在比赛中
            
        self.current_match_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.current_match_dir = self.log_dir / f"match_{self.current_match_id}"
        self.current_match_dir.mkdir(exist_ok=True)
        
        print(f"[LogWriter] Match started: {self.current_match_id}")
        print(f"[LogWriter] Log directory: {self.current_match_dir}")
        
    def _end_match(self):
        """结束比赛"""
        if self.current_match_id is None:
            return
            
        print(f"[LogWriter] Match ended: {self.current_match_id}")
        
        # 关闭所有日志文件
        for robot_id, f in self.log_files.items():
            f.close()
            print(f"[LogWriter] Closed log file for {robot_id}")
            
        # 生成元数据文件
        self._write_metadata()
        
        # 重置状态
        self.log_files.clear()
        self.current_match_id = None
        self.current_match_dir = None
        
    def _write_metadata(self):
        """写入比赛元数据"""
        if self.current_match_dir is None:
            return
            
        metadata = {
            'match_id': self.current_match_id,
            'start_time': self.current_match_id,
            'robots': list(self.log_files.keys()),
        }
        
        metadata_file = self.current_match_dir / 'match_metadata.json'
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
            
    def _write_loop(self):
        """写入循环（独立线程）"""
        while True:
            try:
                robot_id, state = self.write_queue.get(timeout=1)
                
                # 确保比赛已开始
                if self.current_match_id is None:
                    continue
                    
                # 打开日志文件（如果尚未打开）
                if robot_id not in self.log_files:
                    log_file = self.current_match_dir / f"robot_{robot_id}.jsonl"
                    self.log_files[robot_id] = open(log_file, 'a')
                    print(f"[LogWriter] Opened log file: {log_file}")
                    
                # 转换为 JSON
                state_dict = MessageToDict(state, preserving_proto_field_name=True)
                
                # 写入一行 JSON
                json_line = json.dumps(state_dict, ensure_ascii=False)
                self.log_files[robot_id].write(json_line + '\n')
                
                # 每 100 条记录 flush 一次
                if self.write_queue.qsize() % 100 == 0:
                    self.log_files[robot_id].flush()
                    
            except queue.Empty:
                # 超时，flush 所有文件
                for f in self.log_files.values():
                    f.flush()
            except Exception as e:
                print(f"[ERROR] Error in write loop: {e}")
                
    def close_all(self):
        """关闭所有日志文件"""
        for f in self.log_files.values():
            f.close()
        self.log_files.clear()
