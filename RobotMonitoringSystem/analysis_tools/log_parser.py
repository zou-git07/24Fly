#!/usr/bin/env python3
"""
日志解析器

功能：
1. 解析 JSON Lines 日志文件
2. 提取关键指标
3. 生成统计报告
"""

import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime


class LogParser:
    """日志解析器"""
    
    def __init__(self, log_file):
        self.log_file = Path(log_file)
        self.states = []
        self.events = []
        
    def parse(self):
        """解析日志文件"""
        print(f"Parsing {self.log_file}...")
        
        with open(self.log_file, 'r') as f:
            for line in f:
                try:
                    state = json.loads(line.strip())
                    self.states.append(state)
                    
                    # 提取事件
                    if 'events' in state:
                        for event in state['events']:
                            self.events.append(event)
                except json.JSONDecodeError as e:
                    print(f"Warning: Failed to parse line: {e}")
                    
        print(f"Parsed {len(self.states)} states, {len(self.events)} events")
        
    def get_statistics(self):
        """生成统计报告"""
        if not self.states:
            return {}
            
        stats = {
            'total_frames': len(self.states),
            'duration_ms': self.states[-1]['system']['timestamp_ms'] - self.states[0]['system']['timestamp_ms'],
            'battery': self._analyze_battery(),
            'ball_perception': self._analyze_ball_perception(),
            'localization': self._analyze_localization(),
            'motion': self._analyze_motion(),
            'events': self._analyze_events(),
        }
        
        return stats
        
    def _analyze_battery(self):
        """分析电量"""
        charges = [s['system']['battery_charge'] for s in self.states if 'system' in s]
        if not charges:
            return {}
            
        return {
            'initial': charges[0],
            'final': charges[-1],
            'consumed': charges[0] - charges[-1],
            'average': sum(charges) / len(charges),
        }
        
    def _analyze_ball_perception(self):
        """分析球感知"""
        visible_count = sum(1 for s in self.states 
                           if s.get('perception', {}).get('ball', {}).get('visible', False))
        
        return {
            'visible_frames': visible_count,
            'visible_rate': visible_count / len(self.states) if self.states else 0,
        }
        
    def _analyze_localization(self):
        """分析定位"""
        qualities = [s.get('perception', {}).get('localization', {}).get('quality', 0) 
                    for s in self.states]
        
        quality_counts = defaultdict(int)
        for q in qualities:
            quality_counts[q] += 1
            
        return {
            'superb_rate': quality_counts[2] / len(qualities) if qualities else 0,
            'okay_rate': quality_counts[1] / len(qualities) if qualities else 0,
            'poor_rate': quality_counts[0] / len(qualities) if qualities else 0,
        }
        
    def _analyze_motion(self):
        """分析运动"""
        motion_types = [s.get('decision', {}).get('motion_type', 0) for s in self.states]
        
        motion_counts = defaultdict(int)
        for m in motion_types:
            motion_counts[m] += 1
            
        motion_names = ['STAND', 'WALK', 'KICK', 'GET_UP', 'SPECIAL']
        
        return {
            motion_names[m]: count / len(motion_types) if motion_types else 0
            for m, count in motion_counts.items()
        }
        
    def _analyze_events(self):
        """分析事件"""
        event_counts = defaultdict(int)
        for event in self.events:
            event_counts[event['type']] += 1
            
        return dict(event_counts)
        
    def print_report(self):
        """打印统计报告"""
        stats = self.get_statistics()
        
        print("\n" + "="*60)
        print(f"Log Analysis Report: {self.log_file.name}")
        print("="*60)
        
        print(f"\n📊 General:")
        print(f"  Total frames: {stats['total_frames']}")
        print(f"  Duration: {stats['duration_ms']/1000:.1f} seconds")
        
        print(f"\n🔋 Battery:")
        battery = stats['battery']
        print(f"  Initial: {battery['initial']:.1f}%")
        print(f"  Final: {battery['final']:.1f}%")
        print(f"  Consumed: {battery['consumed']:.1f}%")
        
        print(f"\n⚽ Ball Perception:")
        ball = stats['ball_perception']
        print(f"  Visible frames: {ball['visible_frames']}")
        print(f"  Visible rate: {ball['visible_rate']*100:.1f}%")
        
        print(f"\n📍 Localization:")
        loc = stats['localization']
        print(f"  Superb: {loc['superb_rate']*100:.1f}%")
        print(f"  Okay: {loc['okay_rate']*100:.1f}%")
        print(f"  Poor: {loc['poor_rate']*100:.1f}%")
        
        print(f"\n🏃 Motion:")
        motion = stats['motion']
        for name, rate in motion.items():
            print(f"  {name}: {rate*100:.1f}%")
            
        print(f"\n📋 Events:")
        events = stats['events']
        event_names = [
            'BEHAVIOR_CHANGED', 'ROLE_CHANGED', 'FALLEN', 'GOT_UP',
            'BALL_LOST', 'BALL_FOUND', 'PENALIZED', 'UNPENALIZED',
            'COMMUNICATION_ERROR', 'LOCALIZATION_LOST', 'KICK_EXECUTED'
        ]
        for event_type, count in events.items():
            event_name = event_names[event_type] if event_type < len(event_names) else f'UNKNOWN_{event_type}'
            print(f"  {event_name}: {count}")
            
        print("\n" + "="*60)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Parse robot log files')
    parser.add_argument('log_file', help='Path to log file (.jsonl)')
    
    args = parser.parse_args()
    
    parser = LogParser(args.log_file)
    parser.parse()
    parser.print_report()


if __name__ == '__main__':
    main()
