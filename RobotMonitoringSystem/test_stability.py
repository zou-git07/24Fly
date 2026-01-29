#!/usr/bin/env python3
"""
稳定性测试脚本
用于对比旧版和新版的性能差异
"""

import asyncio
import websockets
import json
import time
import statistics
from datetime import datetime

# 测试配置
TEST_DURATION = 300  # 5 分钟
WS_URL = "ws://localhost:8080/ws"

# 统计数据
stats = {
    "messages_received": 0,
    "messages_lost": 0,
    "reconnects": 0,
    "errors": 0,
    "latencies": [],
    "start_time": None,
    "end_time": None,
    "disconnects": []
}


async def test_websocket_stability():
    """测试 WebSocket 稳定性"""
    print("=" * 60)
    print("  🧪 WebSocket 稳定性测试")
    print("=" * 60)
    print(f"测试时长: {TEST_DURATION} 秒")
    print(f"目标地址: {WS_URL}")
    print("=" * 60)
    print("")
    
    stats["start_time"] = time.time()
    
    while time.time() - stats["start_time"] < TEST_DURATION:
        try:
            async with websockets.connect(WS_URL) as websocket:
                print(f"✅ 已连接 ({datetime.now().strftime('%H:%M:%S')})")
                
                # 接收消息
                while time.time() - stats["start_time"] < TEST_DURATION:
                    try:
                        message = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=5.0
                        )
                        
                        # 解析消息
                        msg = json.loads(message)
                        stats["messages_received"] += 1
                        
                        # 计算延迟
                        if "timestamp" in msg:
                            latency = time.time() - msg["timestamp"]
                            stats["latencies"].append(latency * 1000)  # ms
                        
                        # 每 100 条消息打印一次
                        if stats["messages_received"] % 100 == 0:
                            elapsed = time.time() - stats["start_time"]
                            rate = stats["messages_received"] / elapsed
                            print(f"📊 已接收 {stats["messages_received"]} 条消息 "
                                  f"({rate:.1f} msg/s)")
                        
                        # 响应 ping
                        if msg.get("type") == "ping":
                            await websocket.send(json.dumps({
                                "type": "pong",
                                "timestamp": time.time()
                            }))
                        
                    except asyncio.TimeoutError:
                        print("⚠️  5 秒无消息")
                        stats["messages_lost"] += 1
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON 解析错误: {e}")
                        stats["errors"] += 1
                    
        except websockets.exceptions.ConnectionClosed as e:
            disconnect_time = time.time() - stats["start_time"]
            print(f"🔴 连接断开 (第 {stats['reconnects'] + 1} 次, "
                  f"运行 {disconnect_time:.1f}s): {e}")
            stats["disconnects"].append(disconnect_time)
            stats["reconnects"] += 1
            
            # 等待 2 秒后重连
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f"❌ 错误: {e}")
            stats["errors"] += 1
            await asyncio.sleep(2)
    
    stats["end_time"] = time.time()
    print_report()


def print_report():
    """打印测试报告"""
    print("")
    print("=" * 60)
    print("  📊 测试报告")
    print("=" * 60)
    
    duration = stats["end_time"] - stats["start_time"]
    
    print(f"\n⏱️  测试时长: {duration:.1f} 秒")
    print(f"📨 接收消息: {stats['messages_received']} 条")
    print(f"📉 消息速率: {stats['messages_received'] / duration:.2f} msg/s")
    print(f"🔴 断开次数: {stats['reconnects']} 次")
    print(f"❌ 错误次数: {stats['errors']} 次")
    print(f"⚠️  超时次数: {stats['messages_lost']} 次")
    
    if stats["latencies"]:
        print(f"\n⏱️  延迟统计:")
        print(f"   平均: {statistics.mean(stats['latencies']):.1f} ms")
        print(f"   中位数: {statistics.median(stats['latencies']):.1f} ms")
        print(f"   最小: {min(stats['latencies']):.1f} ms")
        print(f"   最大: {max(stats['latencies']):.1f} ms")
        print(f"   标准差: {statistics.stdev(stats['latencies']):.1f} ms")
    
    if stats["disconnects"]:
        print(f"\n🔴 断开时间点:")
        for i, t in enumerate(stats["disconnects"], 1):
            print(f"   第 {i} 次: {t:.1f}s")
    
    # 评分
    print(f"\n🎯 稳定性评分:")
    
    score = 100
    score -= stats["reconnects"] * 10  # 每次断连扣 10 分
    score -= stats["errors"] * 5       # 每次错误扣 5 分
    score -= stats["messages_lost"]    # 每次超时扣 1 分
    score = max(0, score)
    
    if score >= 90:
        grade = "🟢 优秀"
    elif score >= 70:
        grade = "🟡 良好"
    elif score >= 50:
        grade = "🟠 一般"
    else:
        grade = "🔴 较差"
    
    print(f"   {grade} ({score} 分)")
    
    print("\n" + "=" * 60)
    
    # 建议
    if stats["reconnects"] > 0:
        print("\n⚠️  建议:")
        print("   - 检查网络稳定性")
        print("   - 确认心跳机制是否启用")
        print("   - 查看后端日志排查断连原因")
    
    if stats["messages_received"] / duration > 20:
        print("\n⚠️  消息频率过高:")
        print(f"   - 当前: {stats['messages_received'] / duration:.1f} msg/s")
        print("   - 建议: < 5 msg/s")
        print("   - 请启用节流聚合功能")


async def test_message_rate():
    """测试消息频率"""
    print("\n🔍 测试消息频率（10 秒）...")
    
    count = 0
    start = time.time()
    
    try:
        async with websockets.connect(WS_URL, timeout=5) as websocket:
            while time.time() - start < 10:
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    count += 1
                except asyncio.TimeoutError:
                    pass
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return
    
    rate = count / 10
    print(f"📊 消息频率: {rate:.1f} msg/s")
    
    if rate > 20:
        print("⚠️  频率过高！建议启用稳定版（目标 2-5 msg/s）")
    elif rate < 10:
        print("✅ 频率合理")
    else:
        print("🟡 频率偏高，可以进一步优化")


async def main():
    """主函数"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        # 快速测试（只测试消息频率）
        await test_message_rate()
    else:
        # 完整测试
        await test_websocket_stability()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被中断")
        if stats["start_time"]:
            stats["end_time"] = time.time()
            print_report()
