# Pause 真机断连问题 - 修复方案

## 问题根因分析

### 当前实现的问题

1. **主循环使用 `pause()` 系统调用**
   - 位置：`Src/Apps/Nao/Main.cpp:395`
   ```cpp
   while(run)
     pause();  // 这会让整个进程进入睡眠状态
   ```

2. **心跳包机制被阻塞**
   - `GameControllerDataProvider` 需要定期发送心跳包（每 1000ms）
   - 当进程被 `pause()` 暂停时，所有线程都停止运行
   - 心跳包无法发送，GameController 认为机器人掉线

3. **SimRobot 中为什么正常**
   - SimRobot 不使用 `pause()` 系统调用
   - 所有线程持续运行
   - 只是在 Pause 状态下冻结行为决策

## 修复方案

### 方案 1：替换主循环的 pause() 调用（推荐）

**原理**：让主循环持续运行，使用 sleep 代替 pause，确保线程不被完全阻塞。

**修改位置**：`Src/Apps/Nao/Main.cpp`

```cpp
// 修改前：
while(run)
  pause();

// 修改后：
while(run)
{
  // 短暂休眠，让出 CPU，但不阻塞进程
  // 这样线程可以继续运行，心跳包可以正常发送
  Thread::sleep(100);  // 100ms
}
```

**优点**：
- 简单直接
- 不影响现有逻辑
- 线程继续运行，心跳包正常发送

**缺点**：
- 主线程会定期唤醒（但开销很小）

### 方案 2：使用条件变量（更优雅）

**原理**：使用条件变量让主线程等待，当需要退出时通知唤醒。

**修改位置**：`Src/Apps/Nao/Main.cpp`

```cpp
// 在文件顶部添加
#include <condition_variable>
#include <mutex>

static std::mutex runMutex;
static std::condition_variable runCondition;

// 修改 sighandlerShutdown
static void sighandlerShutdown(int sig)
{
  if(pthread_self() != mainThread)
  {
    shutdownNAO = true;
    pthread_kill(mainThread, sig);
  }
  else
  {
    if(run)
      fprintf(stderr, "Caught signal %i\nShutting down...\n", sig);
    run = false;
    runCondition.notify_one();  // 通知主线程退出
  }
}

// 修改主循环
while(run)
{
  std::unique_lock<std::mutex> lock(runMutex);
  runCondition.wait_for(lock, std::chrono::milliseconds(100));
}
```

**优点**：
- 更符合现代 C++ 风格
- CPU 占用更低
- 可以精确控制唤醒时机

**缺点**：
- 代码改动稍大

### 方案 3：确保 Pause 状态下线程继续运行（最小改动）

**原理**：保持当前的 `pause()` 调用，但确保关键线程（如通信线程）不受影响。

这个方案实际上不可行，因为 `pause()` 会暂停整个进程的所有线程。

## 推荐实施方案

### 第一步：修改主循环（方案 1）

**文件**：`Src/Apps/Nao/Main.cpp`

```cpp
// 在文件顶部添加
#include "Platform/Thread.h"

// 修改主循环（约第 395 行）
while(run)
  Thread::sleep(100);  // 替换 pause()
```

### 第二步：同样修改 Booster

**文件**：`Src/Apps/Booster/Main.cpp`

```cpp
// 同样的修改（约第 251 行）
while(run)
  Thread::sleep(100);  // 替换 pause()
```

### 第三步：验证心跳包机制

确认 `GameControllerDataProvider` 的心跳包机制正常工作：

1. **心跳间隔**：1000ms（`aliveDelay` 参数）
2. **超时判断**：2000ms（`gameControllerTimeout` 参数）
3. **发送条件**：
   - 收到过 GC 数据包
   - 距离上次发送超过 1000ms
   - 发送成功

### 第四步：测试验证

1. **SimRobot 测试**：
   - 启动 SimRobot
   - 点击 GC 的 Pause
   - 确认机器人保持连接
   - 点击 Resume
   - 确认正常恢复

2. **真实机器人测试**：
   - 部署修改后的代码
   - 启动机器人
   - 点击 GC 的 Pause
   - 确认机器人不断连
   - 点击 Resume
   - 确认正常恢复

## 为什么这个方案有效

### 问题的本质

- `pause()` 系统调用会让进程进入 **SIGSTOP** 状态
- 所有线程都被冻结，包括：
  - Cognition 线程（处理 GameController 数据）
  - Motion 线程
  - 通信线程

### 解决方案的原理

- 使用 `Thread::sleep(100)` 代替 `pause()`
- 主线程定期唤醒（100ms），但不做任何事
- **关键**：其他线程（Cognition、Motion）继续正常运行
- GameControllerDataProvider 可以正常发送心跳包
- GameController 认为机器人仍然在线

### Pause 状态的处理

Pause 状态的冻结是在**行为层**实现的，不是在**进程层**：

1. **GameStateProvider** 检测到 `GAME_PHASE_PAUSED`
2. 设置 `gameState.paused = true`
3. **SkillBehaviorControl** 检查 `theGameState.paused`
4. 如果为 true，不更新运动请求
5. **MotionEngine** 检查 `theGameState.paused`
6. 如果为 true，切换到 Freeze 状态
7. 机器人保持当前姿态，但**进程和线程继续运行**

## 额外优化建议

### 1. 添加日志输出

在 Pause 状态切换时输出日志，方便调试：

```cpp
// 在 GameStateProvider.cpp 中
if(gameState.paused != wasPaused)
{
  OUTPUT_TEXT("GameState: Pause state changed to " << (gameState.paused ? "PAUSED" : "RESUMED"));
}
```

### 2. 监控心跳包发送

添加调试输出，确认心跳包正常发送：

```cpp
// 在 GameControllerDataProvider.cpp 中
if(sendReturnPacket())
{
  OUTPUT_TEXT("GameController: Heartbeat sent");
  whenPacketWasSent = theFrameInfo.time;
}
```

### 3. 添加断连检测

在真实机器人上添加断连检测和恢复机制：

```cpp
// 在 GameControllerDataProvider.cpp 中
if(theFrameInfo.getTimeSince(theGameControllerData.timeLastPacketReceived) > gameControllerTimeout * 2)
{
  OUTPUT_WARNING("GameController: Connection lost, attempting to reconnect...");
  // 可以添加重连逻辑
}
```

## 总结

**核心修改**：
- 将 `pause()` 替换为 `Thread::sleep(100)`
- 仅需修改 2 个文件，2 行代码
- 不影响现有的 Pause 行为逻辑
- 确保线程继续运行，心跳包正常发送

**效果**：
- SimRobot 和真实机器人行为一致
- Pause 时机器人保持连接
- Resume 后正常恢复
- 不会出现断连问题
