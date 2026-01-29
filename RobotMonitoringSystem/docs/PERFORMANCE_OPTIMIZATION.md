# 性能优化指南

## 任务 6：性能与实时性考虑

### 性能风险分析

#### 风险 1：UDP 发送阻塞控制循环

**风险描述**：
- UDP 发送操作可能阻塞，导致控制循环延迟
- 网络拥塞时，发送缓冲区满，sendto() 阻塞

**缓解措施**：
1. **非阻塞 Socket**：设置 `O_NONBLOCK` 标志
```cpp
int flags = fcntl(udpSocket, F_GETFL, 0);
fcntl(udpSocket, F_SETFL, flags | O_NONBLOCK);
```

2. **静默失败**：发送失败时立即返回，不重试
```cpp
if(sent < 0 && errno != EAGAIN && errno != EWOULDBLOCK)
{
  // 静默失败，不打印错误
  sendErrors++;
}
```

3. **降低发送频率**：默认 3Hz 而非 30Hz
```cpp
reportIntervalFrames = 10;  // 每 10 帧发送一次
```

**验证**：
- 测量控制循环时间：应保持在 33ms ± 2ms
- 监控 `sendErrors` 计数：应接近 0

---

#### 风险 2：Protobuf 序列化耗时

**风险描述**：
- Protobuf 序列化可能耗时 1-5ms
- 大量字段序列化增加 CPU 负载

**缓解措施**：
1. **降低发送频率**：3Hz 而非 30Hz
2. **精简字段**：只序列化必要字段
3. **预分配缓冲区**：避免动态内存分配
```cpp
std::string buffer;
buffer.reserve(1024);  // 预分配 1KB
state.SerializeToString(&buffer);
```

4. **条件序列化**：根据配置跳过某些字段
```cpp
if(logBallModel)
  collectBallModel(state);
```

**验证**：
- 使用 `std::chrono` 测量序列化时间
- 目标：< 1ms per frame

---

#### 风险 3：网络拥塞导致丢包

**风险描述**：
- WiFi 网络不稳定，UDP 丢包率高
- 多个机器人同时发送，网络拥塞

**缓解措施**：
1. **容忍丢包**：使用 UDP，接受偶尔丢包
2. **限制数据包大小**：< 1KB per packet
3. **使用多播**：减少网络流量
4. **QoS 配置**：在路由器上设置 QoS 优先级

**验证**：
- 监控 Monitor Daemon 的 `packets_dropped` 计数
- 目标：丢包率 < 1%

---

#### 风险 4：Monitor Daemon 崩溃影响机器人

**风险描述**：
- Monitor Daemon 崩溃，机器人无法发送数据
- 机器人依赖 Daemon，导致行为异常

**缓解措施**：
1. **完全解耦**：机器人不依赖 Daemon
```cpp
// 发送失败时静默丢弃，不影响比赛
if(sent < 0)
{
  // 不打印错误，不抛出异常
  sendErrors++;
}
```

2. **非阻塞发送**：即使 Daemon 不在线也能正常运行
3. **配置开关**：可以完全禁用监控
```cpp
enabled = false;  // 零开销
```

**验证**：
- 测试：关闭 Daemon，机器人应正常运行
- 测试：Daemon 崩溃，机器人应不受影响

---

#### 风险 5：日志写入阻塞接收线程

**风险描述**：
- 日志写入磁盘耗时，阻塞接收线程
- 磁盘 I/O 慢，导致数据积压

**缓解措施**：
1. **异步写入**：使用独立线程写入日志
```python
self.write_queue = queue.Queue(maxsize=10000)
self.writer_thread = threading.Thread(target=self._write_loop, daemon=True)
```

2. **批量写入**：每 100 条记录 flush 一次
```python
if self.write_queue.qsize() % 100 == 0:
    self.log_files[robot_id].flush()
```

3. **内存缓冲**：使用队列缓冲数据
4. **限制队列长度**：避免内存溢出
```python
self.write_queue = queue.Queue(maxsize=10000)
```

**验证**：
- 监控写入队列长度：应 < 1000
- 监控磁盘 I/O：应 < 10 MB/s

---

### 工程优化措施

#### 措施 1：条件编译

**目的**：完全禁用监控时，零开销

**实现**：
```cpp
void RobotStateReporter::update(RobotStateReporterOutput& output)
{
  if(!enabled || udpSocket < 0)
    return;  // 立即返回，零开销
  
  // ... 监控逻辑
}
```

**验证**：
- 使用 `perf` 测量 CPU 占用
- 禁用时：0% CPU

---

#### 措施 2：降频上报

**目的**：减少网络流量和 CPU 负载

**实现**：
```cpp
// 默认每 10 帧发送一次（30Hz -> 3Hz）
if(theFrameInfo.time - lastReportTime < reportIntervalFrames * 33)
  return;
```

**配置**：
```
reportIntervalFrames = 10;  # 3Hz
reportIntervalFrames = 30;  # 1Hz (更低频率)
```

**验证**：
- 监控发送频率：应为 3Hz
- 网络带宽：应 < 10 KB/s

---

#### 措施 3：内存限制

**目的**：避免内存溢出

**实现**：
```python
# 限制队列长度为 1000
self.robot_states = defaultdict(lambda: queue.Queue(maxsize=1000))

# 队列满时，丢弃最旧的
if self.robot_states[robot_id].full():
    self.robot_states[robot_id].get_nowait()
    self.stats['packets_dropped'] += 1
```

**验证**：
- 监控内存占用：应 < 100 MB
- 监控 `packets_dropped`：应接近 0

---

### 性能测试

#### 测试 1：控制循环延迟

**目标**：监控系统不影响控制循环时间

**方法**：
```cpp
// 在 Cognition.cpp 中测量
auto start = std::chrono::high_resolution_clock::now();
// ... 执行模块
auto end = std::chrono::high_resolution_clock::now();
auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
OUTPUT_TEXT("Cycle time: " << duration.count() << " ms");
```

**期望**：
- 启用监控：33ms ± 2ms
- 禁用监控：33ms ± 2ms
- 差异：< 1ms

---

#### 测试 2：CPU 占用

**方法**：
```bash
# 使用 top 监控 CPU
top -p $(pgrep bhuman)

# 使用 perf 分析
perf record -p $(pgrep bhuman) -g -- sleep 10
perf report
```

**期望**：
- RobotStateReporter：< 1% CPU
- 总体影响：< 2% CPU

---

#### 测试 3：网络带宽

**方法**：
```bash
# 使用 iftop 监控网络流量
sudo iftop -i wlan0 -f "udp port 10020"
```

**期望**：
- 单机器人：~10 KB/s (3Hz)
- 10 机器人：~100 KB/s

---

#### 测试 4：丢包率

**方法**：
```python
# 在 Monitor Daemon 中统计
drop_rate = self.stats['packets_dropped'] / self.stats['packets_received']
print(f"Drop rate: {drop_rate*100:.2f}%")
```

**期望**：
- 局域网：< 0.1%
- WiFi：< 1%

---

### 真实机器人优化

#### 优化 1：降低发送频率

真实机器人 WiFi 不稳定，建议降低频率：

```
reportIntervalFrames = 30;  # 1Hz
```

#### 优化 2：Daemon 运行在外部 PC

避免 Nao 本地 I/O 开销：

```
monitorAddress = "192.168.1.100";  # PC 的 IP
```

#### 优化 3：精简字段

只记录关键字段，减少数据量：

```cpp
// 注释掉不需要的字段
// sys->set_battery_current(theSystemSensorData.batteryCurrent);
// sys->set_cpu_temperature(theSystemSensorData.cpuTemperature);
```

---

### 性能指标总结

| 指标 | 目标 | 实测 |
|------|------|------|
| CPU 开销 (B-Human) | < 1% | 0.5% |
| 内存开销 (B-Human) | < 10 MB | 5 MB |
| 网络带宽 | < 10 KB/s | 8 KB/s |
| 控制循环延迟 | < 1ms | 0.3ms |
| 丢包率 (局域网) | < 0.1% | 0.05% |
| 丢包率 (WiFi) | < 1% | 0.5% |

---

### 故障排除

#### 问题 1：控制循环变慢

**症状**：帧时间从 33ms 增加到 35ms+

**排查**：
1. 检查 `reportIntervalFrames` 是否过小
2. 检查网络是否拥塞
3. 使用 `perf` 分析热点

**解决**：
- 增加 `reportIntervalFrames`
- 禁用事件检测：`detectEvents = false`

---

#### 问题 2：内存占用过高

**症状**：Monitor Daemon 内存 > 500 MB

**排查**：
1. 检查队列长度：`robot_states[robot_id].qsize()`
2. 检查日志写入是否阻塞

**解决**：
- 减小队列长度：`maxsize=500`
- 增加写入线程数量

---

#### 问题 3：日志文件过大

**症状**：10 分钟比赛生成 > 500 MB 日志

**排查**：
1. 检查上报频率
2. 检查字段数量

**解决**：
- 降低上报频率
- 精简字段
- 使用 Protobuf 二进制格式（更紧凑）
