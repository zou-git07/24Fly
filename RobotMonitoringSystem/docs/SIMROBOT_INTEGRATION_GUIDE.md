# SimRobot + B-Human 监控系统接入完整指南

> **作者角色**: RoboCup SPL、SimRobot、B-Human 框架核心工程师  
> **目标**: 将已验证的监控系统 demo 真正接入 SimRobot 环境，获取真实数据

---

## 目录

1. [SimRobot 架构与接入点分析](#1-simrobot-架构与接入点分析)
2. [StateReporter 模块设计](#2-statereporter-模块设计)
3. [SimRobot 真实数据获取方法](#3-simrobot-真实数据获取方法)
4. [网络发送工程注意事项](#4-网络发送工程注意事项)
5. [最小可运行方案 (MVP)](#5-最小可运行方案-mvp)
6. [Sim → Real 迁移清单](#6-sim--real-迁移清单)

---

## 1. SimRobot 架构与接入点分析

### 1.1 B-Human + SimRobot 执行模型

B-Human 在 SimRobot 中运行时，采用 **多线程 + 模块化** 架构：

```
SimRobot (主进程)
├── RoboCupCtrl (控制器)
│   ├── Robot Instance 1
│   │   ├── Cognition Thread (30Hz)
│   │   │   ├── CameraProvider → ImageProcessor → BallPerceptor → ...
│   │   │   └── BehaviorControl → StrategyBehaviorControl
│   │   └── Motion Thread (83Hz)
│   │       ├── MotionEngine → WalkingEngine → ...
│   │       └── NaoProvider (读取传感器)
│   ├── Robot Instance 2
│   └── ...
└── Simulation Core (物理引擎)
```


### 1.2 每帧执行的模块

**Cognition Thread (30Hz)**:
- `CameraProvider`: 获取图像
- `BallPerceptor`: 球检测
- `RobotPoseProvider`: 定位
- `BehaviorControl`: 决策
- **✅ 推荐接入点**: 在 Cognition 线程末尾添加 `RobotStateReporter`

**Motion Thread (83Hz)**:
- `NaoProvider`: 读取传感器（关节角度、IMU、电量）
- `MotionEngine`: 运动控制
- **⚠️ 不推荐**: Motion 线程对实时性要求极高，不应添加网络 I/O

### 1.3 推荐接入点

**最佳选择: Cognition Thread 的 Infrastructure 模块**

理由:
1. **频率适中**: 30Hz，既能及时反映状态，又不会过载
2. **数据完整**: 可访问所有 Cognition 和 Motion 的 Representations
3. **非关键路径**: 即使模块失败，也不影响核心决策
4. **已有先例**: `RobotHealthProvider`、`GameStateProvider` 都在此位置

**具体位置**:
```
Src/Modules/Infrastructure/RobotStateReporter/
├── RobotStateReporter.h
├── RobotStateReporter.cpp
└── RobotStateReporter.cfg
```

**注册到线程**:
```cpp
// Src/Threads/Cognition.cpp
USES(RobotStateReporter);  // 在模块列表末尾添加
```


### 1.4 为什么不应该在某些模块中做网络发送

**❌ 不应该在以下位置添加网络 I/O**:

1. **Motion Thread**:
   - 频率 83Hz，CPU 预算极紧张
   - 任何阻塞都会导致机器人摔倒
   - 即使非阻塞，序列化开销也不可接受

2. **感知模块 (Perception)**:
   - 如 `BallPerceptor`、`LinePerceptor`
   - 这些模块的输出被后续模块依赖
   - 延迟会传播到整个决策链

3. **决策模块 (Behavior)**:
   - 如 `StrategyBehaviorControl`
   - 决策逻辑应保持纯净，不应有副作用
   - 网络失败不应影响行为选择

**✅ 安全的线程/周期**:

- **Cognition Thread 末尾**: 所有决策已完成，只是"旁观者"
- **降频执行**: 不是每帧都发送，而是每 N 帧发送一次（如 10 帧 = 3Hz）
- **非阻塞 Socket**: 发送失败立即返回，不重试

---

## 2. StateReporter 模块设计

### 2.1 模块接口定义

**文件: `Src/Modules/Infrastructure/RobotStateReporter/RobotStateReporter.h`**

```cpp
#pragma once

#include "Tools/Module/Module.h"
#include "Representations/Infrastructure/FrameInfo.h"
#include "Representations/Infrastructure/GameState.h"
#include "Representations/Infrastructure/RobotHealth.h"
#include "Representations/Modeling/BallModel.h"
#include "Representations/Modeling/RobotPose.h"
#include "Representations/MotionControl/MotionInfo.h"
#include "Representations/BehaviorControl/BehaviorStatus.h"
#include "Representations/Sensing/FallDownState.h"
#include "Representations/Sensing/GroundContactState.h"

#include <sys/socket.h>
#include <netinet/in.h>
#include <string>

MODULE(RobotStateReporter,
{,
  // ===== 必需的 Representations (每帧更新前必须就绪) =====
  REQUIRES(FrameInfo),           // 时间戳、帧号
  REQUIRES(GameState),           // 比赛状态、机器人编号
  REQUIRES(RobotHealth),         // 电量、温度、CPU 负载
  
  // ===== 使用的 Representations (不强制更新顺序) =====
  USES(BallModel),               // 球感知
  USES(RobotPose),               // 定位
  USES(MotionInfo),              // 当前运动状态
  USES(BehaviorStatus),          // 行为状态
  USES(FallDownState),           // 摔倒状态
  USES(GroundContactState),      // 地面接触
  
  // ===== 提供的 Representation (用于调试) =====
  PROVIDES(RobotStateReporterOutput),
  
  // ===== 可配置参数 =====
  LOADS_PARAMETERS(
  {,
    (bool) enabled,                    // 是否启用
    (std::string) monitorAddress,     // Monitor Daemon 地址
    (int) monitorPort,                 // UDP 端口
    (int) reportIntervalFrames,        // 上报间隔（帧数）
  }),
});
```


### 2.2 输出 Representation

```cpp
// 用于其他模块查询监控状态（可选）
STREAMABLE(RobotStateReporterOutput,
{
  void draw() const
  {
    PLOT("module:RobotStateReporter:reportCount", reportCount);
    PLOT("module:RobotStateReporter:sendErrors", sendErrors);
  },
  
  (bool)(false) isReporting,      // 是否正在上报
  (unsigned)(0) reportCount,      // 已上报次数
  (unsigned)(0) lastReportTime,   // 上次上报时间戳
  (unsigned)(0) sendErrors,       // 发送错误次数
});
```

### 2.3 模块类定义

```cpp
class RobotStateReporter : public RobotStateReporterBase
{
private:
  int udpSocket = -1;
  struct sockaddr_in monitorAddr;
  unsigned lastReportFrame = 0;
  
  // 事件检测状态
  std::string lastBehavior;
  bool lastBallVisible = false;
  bool lastFallen = false;
  
  unsigned reportCount = 0;
  unsigned sendErrors = 0;
  
  void initSocket();
  void collectState(std::string& jsonBuffer);
  void sendState(const std::string& jsonBuffer);
  
public:
  RobotStateReporter();
  ~RobotStateReporter();
  
  void update(RobotStateReporterOutput& output) override;
};
```

### 2.4 update() 调用频率

- **调用频率**: 30Hz (Cognition Thread)
- **实际发送频率**: 3Hz (每 10 帧发送一次)
- **控制逻辑**:

```cpp
void RobotStateReporter::update(RobotStateReporterOutput& output)
{
  output.reportCount = reportCount;
  output.sendErrors = sendErrors;
  
  if (!enabled || udpSocket < 0)
    return;
  
  // 降频：每 N 帧发送一次
  if (theFrameInfo.getFrameNumber() - lastReportFrame < reportIntervalFrames)
    return;
  
  lastReportFrame = theFrameInfo.getFrameNumber();
  
  // 采集 + 发送
  std::string jsonBuffer;
  collectState(jsonBuffer);
  sendState(jsonBuffer);
  
  output.isReporting = true;
  output.lastReportTime = theFrameInfo.time;
}
```


---

## 3. SimRobot 真实数据获取方法

### 3.1 时间戳

**仿真时间 vs 系统时间**:

```cpp
// ✅ 推荐：使用仿真时间（可暂停、可加速）
unsigned timestamp = theFrameInfo.time;  // 单位：毫秒

// ❌ 不推荐：系统时间（与仿真不同步）
// unsigned timestamp = SystemCall::getCurrentSystemTime();
```

**说明**:
- `theFrameInfo.time`: SimRobot 的仿真时间，从 0 开始递增
- 支持暂停、加速、慢放
- 日志分析时与 SimRobot 时间轴一致

### 3.2 电量

**SimRobot 中的电量模拟**:

```cpp
// 从 RobotHealth 读取
float batteryLevel = theRobotHealth.batteryLevel;  // 0-100%
float batteryCurrent = theRobotHealth.totalCurrent;  // 单位：安培
```

**SimRobot 行为**:
- **默认**: 电量固定为 100%（不消耗）
- **可配置**: 在 `Config/Robots/<RobotName>/robotHealth.cfg` 中设置初始值
- **真机差异**: 真机电量会实际下降，SimRobot 中是静态值

**处理建议**:
```cpp
#ifdef TARGET_ROBOT
  // 真机：使用真实电量
  float battery = theRobotHealth.batteryLevel;
#else
  // SimRobot：可以模拟消耗（可选）
  float battery = 100.0f - (theFrameInfo.time / 1000.0f) * 0.01f;  // 每秒下降 0.01%
#endif
```

### 3.3 关节角度 / 温度

**关节角度**:

```cpp
// 从 JointAngles 读取（需要 USES(JointAngles)）
for (int i = 0; i < Joints::numOfJoints; ++i)
{
  float angle = theJointAngles.angles[i];  // 单位：弧度
  // SimRobot 中是物理引擎计算的真实值
}
```

**关节温度**:

```cpp
// 从 RobotHealth 读取
float maxTemp = theRobotHealth.maxJointTemperatureStatus;  // 最高温度

// ⚠️ SimRobot 中温度是模拟的，不会真实上升
// 真机中会根据负载实际变化
```

**可用性**:
- ✅ **关节角度**: SimRobot 中完全可用，物理引擎实时计算
- ⚠️ **温度**: SimRobot 中是静态值或简单模拟，真机中才有意义


### 3.4 是否摔倒

**方法 1: 使用 FallDownState (推荐)**

```cpp
// USES(FallDownState)
bool isFallen = (theFallDownState.state != FallDownState::upright);

// 详细状态
switch (theFallDownState.state)
{
  case FallDownState::upright:
    // 正常站立
    break;
  case FallDownState::falling:
    // 正在摔倒
    break;
  case FallDownState::fallen:
    // 已摔倒
    break;
}

// 摔倒方向
FallDownState::Direction direction = theFallDownState.direction;
// front, back, left, right
```

**方法 2: 使用 InertialData (备选)**

```cpp
// USES(InertialData)
bool isFallen = theInertialData.angle.x() > 0.5f ||  // Roll > 30°
                theInertialData.angle.y() > 0.5f;    // Pitch > 30°
```

**SimRobot 中的行为**:
- ✅ **完全可用**: 物理引擎会真实模拟摔倒
- ✅ **FallDownState 可靠**: B-Human 的摔倒检测模块在 SimRobot 中正常工作

### 3.5 当前行为名称

**从 BehaviorStatus 读取**:

```cpp
// USES(BehaviorStatus)
std::string activity = TypeRegistry::getEnumName(theBehaviorStatus.activity);

// 可能的值（取决于 B-Human 版本）:
// - "unknown"
// - "standHigh"
// - "standLow"
// - "walk"
// - "kick"
// - "getUp"
// - "searchForBall"
// - "dribble"
// - ...
```

**注意**:
- `BehaviorStatus` 是 B-Human 的标准 Representation
- SimRobot 和真机完全一致
- 如果需要更详细的行为信息，可以添加 `USES(ActivationGraph)`


### 3.6 感知结果

**球感知 (BallModel)**:

```cpp
// USES(BallModel)
bool ballVisible = (theFrameInfo.time - theBallModel.timeWhenLastSeen) < 1000;  // 1秒内看到
Vector2f ballPos = theBallModel.estimate.position;  // 机器人坐标系
Vector2f ballVel = theBallModel.estimate.velocity;

// SimRobot 中完全可用，基于虚拟相机图像
```

**定位 (RobotPose)**:

```cpp
// USES(RobotPose)
Vector2f position = theRobotPose.translation;  // 场地坐标系 (mm)
float rotation = theRobotPose.rotation;        // 弧度

// 定位质量
RobotPose::LocalizationQuality quality = theRobotPose.quality;
// - RobotPose::superb
// - RobotPose::okay
// - RobotPose::poor
```

**队友/对手感知**:

```cpp
// USES(ObstacleModel)
for (const auto& obstacle : theObstacleModel.obstacles)
{
  Vector2f pos = obstacle.center;
  Obstacle::Type type = obstacle.type;
  // - Obstacle::goalpost
  // - Obstacle::unknown
  // - Obstacle::someRobot
  // - Obstacle::opponent
  // - Obstacle::teammate
}
```

### 3.7 数据可用性总结

| 数据类型 | SimRobot 可用性 | 真机可用性 | 说明 |
|---------|----------------|-----------|------|
| 时间戳 | ✅ 仿真时间 | ✅ 系统时间 | 使用 `theFrameInfo.time` |
| 电量 | ⚠️ 静态值 | ✅ 真实值 | SimRobot 中不消耗 |
| 关节角度 | ✅ 物理引擎 | ✅ 传感器 | 完全一致 |
| 关节温度 | ⚠️ 模拟值 | ✅ 真实值 | SimRobot 中不上升 |
| 摔倒状态 | ✅ 物理引擎 | ✅ IMU | 完全一致 |
| 行为名称 | ✅ 决策输出 | ✅ 决策输出 | 完全一致 |
| 球感知 | ✅ 虚拟相机 | ✅ 真实相机 | 完全一致 |
| 定位 | ✅ 虚拟感知 | ✅ 真实感知 | 完全一致 |

**处理不可用数据的策略**:

```cpp
void RobotStateReporter::collectState(std::string& jsonBuffer)
{
  // 对于 SimRobot 中不可用的数据，使用占位符或跳过
  
#ifdef TARGET_ROBOT
  float battery = theRobotHealth.batteryLevel;
  float temp = theRobotHealth.maxJointTemperatureStatus;
#else
  float battery = 100.0f;  // SimRobot 固定值
  float temp = 40.0f;      // SimRobot 固定值
#endif
  
  // 构建 JSON
  jsonBuffer = "{"
    "\"timestamp\":" + std::to_string(theFrameInfo.time) + ","
    "\"battery\":" + std::to_string(battery) + ","
    "\"temperature\":" + std::to_string(temp) + ","
    // ...
    "}";
}
```

---

## 4. 网络发送工程注意事项

### 4.1 SimRobot 多机器人环境

**问题**: SimRobot 是单进程多机器人，如何区分不同实例？

**解决方案**:

```cpp
// 使用 GameState 中的机器人编号
int teamNumber = theGameState.ownTeam.number;
int playerNumber = theGameState.playerNumber;

std::string robotId = std::to_string(teamNumber) + "_" + std::to_string(playerNumber);
// 例如: "1_3" 表示 1 号队伍的 3 号机器人
```


### 4.2 UDP 端口设计

**方案 1: 单一端口 + 多播 (推荐)**

```cpp
// 所有机器人发送到同一个多播地址
monitorAddress = "239.0.0.1";
monitorPort = 10020;

// Monitor Daemon 监听多播，通过 robot_id 区分
```

**优点**:
- 配置简单，所有机器人使用相同配置
- Monitor Daemon 只需监听一个端口

**方案 2: 每个机器人独立端口**

```cpp
// 根据机器人编号分配端口
int port = 10020 + playerNumber;  // 10021, 10022, ...

// Monitor Daemon 需要监听多个端口
```

**缺点**:
- 配置复杂
- Monitor Daemon 需要多线程监听

**推荐**: 使用方案 1（多播）

### 4.3 保证 SimRobot 运行不受影响

**原则**: 监控系统是"旁观者"，绝不能影响仿真

**实现**:

```cpp
void RobotStateReporter::initSocket()
{
  udpSocket = socket(AF_INET, SOCK_DGRAM, 0);
  if (udpSocket < 0)
  {
    OUTPUT_WARNING("RobotStateReporter: Failed to create socket, disabling");
    enabled = false;
    return;  // 静默失败，继续运行
  }
  
  // 设置非阻塞模式（关键！）
  int flags = fcntl(udpSocket, F_GETFL, 0);
  fcntl(udpSocket, F_SETFL, flags | O_NONBLOCK);
  
  // 设置发送超时（额外保险）
  struct timeval timeout;
  timeout.tv_sec = 0;
  timeout.tv_usec = 1000;  // 1ms
  setsockopt(udpSocket, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
}

void RobotStateReporter::sendState(const std::string& jsonBuffer)
{
  ssize_t sent = sendto(udpSocket, jsonBuffer.c_str(), jsonBuffer.size(), 0,
                        (struct sockaddr*)&monitorAddr, sizeof(monitorAddr));
  
  if (sent < 0)
  {
    // 非阻塞模式下，EAGAIN/EWOULDBLOCK 是正常的
    if (errno != EAGAIN && errno != EWOULDBLOCK)
    {
      sendErrors++;
      // 不打印错误，避免日志洪水
    }
    return;  // 静默失败
  }
  
  reportCount++;
}
```

**关键措施**:
1. **非阻塞 Socket**: `O_NONBLOCK` 标志
2. **发送超时**: `SO_SNDTIMEO` 设置为 1ms
3. **静默失败**: 发送失败不打印错误，不抛异常
4. **降频发送**: 3Hz 而非 30Hz
5. **条件编译**: 可通过配置完全禁用


### 4.4 Monitor Daemon 不存在时的处理

**场景**: SimRobot 启动时，Monitor Daemon 可能未运行

**处理**:

```cpp
// 构造函数中初始化
RobotStateReporter::RobotStateReporter()
{
  if (enabled)
  {
    initSocket();
    // 即使 initSocket 失败，也不影响 SimRobot 运行
  }
}

// update() 中检查
void RobotStateReporter::update(RobotStateReporterOutput& output)
{
  if (!enabled || udpSocket < 0)
  {
    // 静默跳过，不打印警告
    return;
  }
  
  // 正常发送逻辑
  // ...
}
```

**结果**:
- Monitor Daemon 不在线 → 数据包丢失，SimRobot 正常运行
- Monitor Daemon 后启动 → 自动开始接收数据
- Monitor Daemon 崩溃 → SimRobot 不受影响

---

## 5. 最小可运行方案 (MVP)

### 5.1 目标

在 SimRobot 中启动 B-Human，Monitor Daemon 在 PC 上运行，能看到：
- 仿真时间
- 机器人编号
- 当前行为
- 是否摔倒
- 并生成日志文件

### 5.2 步骤 1: 创建最小模块

**文件: `Src/Modules/Infrastructure/RobotStateReporter/RobotStateReporter.h`**

```cpp
#pragma once

#include "Tools/Module/Module.h"
#include "Representations/Infrastructure/FrameInfo.h"
#include "Representations/Infrastructure/GameState.h"
#include "Representations/BehaviorControl/BehaviorStatus.h"
#include "Representations/Sensing/FallDownState.h"

#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <fcntl.h>
#include <unistd.h>
#include <string>

MODULE(RobotStateReporter,
{,
  REQUIRES(FrameInfo),
  REQUIRES(GameState),
  USES(BehaviorStatus),
  USES(FallDownState),
  
  LOADS_PARAMETERS(
  {,
    (bool)(true) enabled,
    (std::string)("127.0.0.1") monitorAddress,
    (int)(10020) monitorPort,
    (int)(10) reportIntervalFrames,
  }),
});

class RobotStateReporter : public RobotStateReporterBase
{
private:
  int udpSocket = -1;
  struct sockaddr_in monitorAddr;
  unsigned lastReportFrame = 0;
  
  void initSocket();
  void sendState();
  
public:
  RobotStateReporter();
  ~RobotStateReporter();
  
  void update() override;
};
```


**文件: `Src/Modules/Infrastructure/RobotStateReporter/RobotStateReporter.cpp`**

```cpp
#include "RobotStateReporter.h"
#include "Platform/BHAssert.h"
#include <cstring>
#include <errno.h>
#include <sstream>

MAKE_MODULE(RobotStateReporter);

RobotStateReporter::RobotStateReporter()
{
  if (enabled)
    initSocket();
}

RobotStateReporter::~RobotStateReporter()
{
  if (udpSocket >= 0)
    close(udpSocket);
}

void RobotStateReporter::initSocket()
{
  udpSocket = socket(AF_INET, SOCK_DGRAM, 0);
  if (udpSocket < 0)
  {
    OUTPUT_WARNING("RobotStateReporter: Failed to create socket");
    enabled = false;
    return;
  }
  
  // 非阻塞模式
  int flags = fcntl(udpSocket, F_GETFL, 0);
  if (flags >= 0)
    fcntl(udpSocket, F_SETFL, flags | O_NONBLOCK);
  
  // 配置目标地址
  memset(&monitorAddr, 0, sizeof(monitorAddr));
  monitorAddr.sin_family = AF_INET;
  monitorAddr.sin_port = htons(monitorPort);
  inet_pton(AF_INET, monitorAddress.c_str(), &monitorAddr.sin_addr);
  
  OUTPUT_TEXT("RobotStateReporter: Initialized, sending to " 
              << monitorAddress << ":" << monitorPort);
}

void RobotStateReporter::update()
{
  if (!enabled || udpSocket < 0)
    return;
  
  // 降频：每 N 帧发送一次
  if (theFrameInfo.getFrameNumber() - lastReportFrame < reportIntervalFrames)
    return;
  
  lastReportFrame = theFrameInfo.getFrameNumber();
  
  sendState();
}

void RobotStateReporter::sendState()
{
  // 构建最小 JSON
  std::ostringstream json;
  json << "{"
       << "\"timestamp\":" << theFrameInfo.time << ","
       << "\"robot_id\":\"" << theGameState.ownTeam.number 
       << "_" << theGameState.playerNumber << "\","
       << "\"behavior\":\"" << TypeRegistry::getEnumName(theBehaviorStatus.activity) << "\","
       << "\"fallen\":" << (theFallDownState.state != FallDownState::upright ? "true" : "false")
       << "}";
  
  std::string buffer = json.str();
  
  // 发送（非阻塞）
  sendto(udpSocket, buffer.c_str(), buffer.size(), 0,
         (struct sockaddr*)&monitorAddr, sizeof(monitorAddr));
  
  // 忽略错误
}
```


### 5.3 步骤 2: 配置文件

**文件: `Config/Modules/RobotStateReporter.cfg`**

```
enabled = true;
monitorAddress = "127.0.0.1";  // 本地测试
monitorPort = 10020;
reportIntervalFrames = 10;     // 3Hz
```

### 5.4 步骤 3: 注册模块

**编辑: `Make/Common/moduleList.txt`** (或对应的模块列表文件)

添加:
```
Modules/Infrastructure/RobotStateReporter
```

**编辑: `Config/Scenarios/Default/modules.cfg`**

在 Cognition 线程末尾添加:
```
module RobotStateReporter
```

### 5.5 步骤 4: 编译

```bash
cd /path/to/bhuman
make
```

### 5.6 步骤 5: 启动 Monitor Daemon

```bash
cd RobotMonitoringSystem/monitor_daemon
python3 daemon.py --port 10020 --log-dir ./logs
```

输出:
```
[MonitorDaemon] Listening on 0.0.0.0:10020
[MonitorDaemon] Log directory: ./logs
[MonitorDaemon] Started successfully
```

### 5.7 步骤 6: 启动 SimRobot

```bash
./Build/Linux/SimRobot/Develop/SimRobot Config/Scenes/Default.ros2
```

在 SimRobot 中:
1. 加载场景
2. 启动机器人 (Ctrl+R)
3. 开始比赛 (GameController)

### 5.8 步骤 7: 验证数据接收

Monitor Daemon 应该输出:
```
[STATS] Packets: 30, Rate: 3.0/s, Dropped: 0, Errors: 0
[INFO] Robot 1_1: behavior=searchForBall, fallen=false
[INFO] Robot 1_2: behavior=walk, fallen=false
```

### 5.9 步骤 8: 检查日志

比赛结束后:
```bash
ls -la logs/
# 应该看到:
# match_20260128_143022/
#   ├── robot_1_1.jsonl
#   ├── robot_1_2.jsonl
#   └── match_metadata.json
```

查看日志内容:
```bash
head -n 5 logs/match_20260128_143022/robot_1_1.jsonl
```

输出示例:
```json
{"timestamp":1000,"robot_id":"1_1","behavior":"standHigh","fallen":false}
{"timestamp":1333,"robot_id":"1_1","behavior":"searchForBall","fallen":false}
{"timestamp":1666,"robot_id":"1_1","behavior":"walk","fallen":false}
```

---

## 6. Sim → Real 迁移清单

### 6.1 完全复用的代码

✅ **无需修改**:
- 模块接口定义 (`MODULE` 宏)
- `update()` 逻辑
- 数据采集逻辑 (`collectState()`)
- 网络发送逻辑 (`sendState()`)
- 事件检测逻辑

### 6.2 需要条件编译的部分

**电量和温度**:

```cpp
#ifdef TARGET_ROBOT
  float battery = theRobotHealth.batteryLevel;  // 真实值
  float temp = theRobotHealth.maxJointTemperatureStatus;
#else
  float battery = 100.0f;  // SimRobot 固定值
  float temp = 40.0f;
#endif
```

**时间戳**:

```cpp
// SimRobot 和真机都使用 theFrameInfo.time，无需修改
unsigned timestamp = theFrameInfo.time;
```


### 6.3 网络配置差异

**SimRobot (本地测试)**:

```cfg
monitorAddress = "127.0.0.1";  // 本地
monitorPort = 10020;
```

**真机 (WiFi 网络)**:

```cfg
monitorAddress = "192.168.1.100";  // PC 的 IP
monitorPort = 10020;
```

或使用多播:
```cfg
monitorAddress = "239.0.0.1";  // 多播地址
monitorPort = 10020;
```

### 6.4 迁移步骤

**步骤 1: 验证 SimRobot 中运行正常**

- 确保数据采集正确
- 确保网络发送不阻塞
- 确保日志生成完整

**步骤 2: 修改配置文件**

```bash
# 真机配置
cp Config/Modules/RobotStateReporter.cfg \
   Config/Robots/Nao/RobotStateReporter.cfg

# 编辑真机配置
vim Config/Robots/Nao/RobotStateReporter.cfg
```

修改为:
```cfg
enabled = true;
monitorAddress = "192.168.1.100";  // 替换为 PC 的 IP
monitorPort = 10020;
reportIntervalFrames = 10;
```

**步骤 3: 部署到真机**

```bash
# 编译真机版本
make Nao

# 部署
./Make/Linux/deploy <nao_ip>
```

**步骤 4: 在 PC 上启动 Monitor Daemon**

```bash
cd RobotMonitoringSystem/monitor_daemon
python3 daemon.py --port 10020 --log-dir ./logs
```

**步骤 5: 启动真机**

```bash
ssh nao@<nao_ip>
bhumand start
```

**步骤 6: 验证连接**

Monitor Daemon 应该输出:
```
[INFO] Received packet from 192.168.1.10:xxxxx
[STATS] Packets: 30, Rate: 3.0/s
```

### 6.5 迁移清单总结

| 项目 | SimRobot | 真机 | 修改方式 |
|-----|---------|------|---------|
| 模块代码 | ✅ | ✅ | 无需修改 |
| 电量/温度 | 固定值 | 真实值 | `#ifdef TARGET_ROBOT` |
| 网络地址 | 127.0.0.1 | PC IP | 配置文件 |
| 时间戳 | 仿真时间 | 系统时间 | 无需修改（都用 `theFrameInfo.time`） |
| 摔倒检测 | 物理引擎 | IMU | 无需修改 |
| 行为名称 | 决策输出 | 决策输出 | 无需修改 |
| 球感知 | 虚拟相机 | 真实相机 | 无需修改 |

**关键原则**: 
- 代码层面尽量统一，差异通过配置文件或条件编译处理
- 优先使用 B-Human 的标准 Representations，避免直接访问硬件

---

## 附录 A: 完整模块代码（生产级）

### A.1 头文件

**文件: `Src/Modules/Infrastructure/RobotStateReporter/RobotStateReporter.h`**

```cpp
#pragma once

#include "Tools/Module/Module.h"
#include "Representations/Infrastructure/FrameInfo.h"
#include "Representations/Infrastructure/GameState.h"
#include "Representations/Infrastructure/RobotHealth.h"
#include "Representations/Modeling/BallModel.h"
#include "Representations/Modeling/RobotPose.h"
#include "Representations/MotionControl/MotionInfo.h"
#include "Representations/BehaviorControl/BehaviorStatus.h"
#include "Representations/Sensing/FallDownState.h"

#include <sys/socket.h>
#include <netinet/in.h>
#include <string>

MODULE(RobotStateReporter,
{,
  REQUIRES(FrameInfo),
  REQUIRES(GameState),
  REQUIRES(RobotHealth),
  USES(BallModel),
  USES(RobotPose),
  USES(MotionInfo),
  USES(BehaviorStatus),
  USES(FallDownState),
  
  LOADS_PARAMETERS(
  {,
    (bool)(true) enabled,
    (std::string)("127.0.0.1") monitorAddress,
    (int)(10020) monitorPort,
    (int)(10) reportIntervalFrames,
    (bool)(true) detectEvents,
  }),
});

class RobotStateReporter : public RobotStateReporterBase
{
private:
  int udpSocket = -1;
  struct sockaddr_in monitorAddr;
  unsigned lastReportFrame = 0;
  
  // 事件检测
  std::string lastBehavior;
  bool lastBallVisible = false;
  bool lastFallen = false;
  
  unsigned reportCount = 0;
  unsigned sendErrors = 0;
  
  void initSocket();
  void collectState(std::string& jsonBuffer);
  void sendState(const std::string& jsonBuffer);
  
public:
  RobotStateReporter();
  ~RobotStateReporter();
  
  void update() override;
};
```


### A.2 实现文件

**文件: `Src/Modules/Infrastructure/RobotStateReporter/RobotStateReporter.cpp`**

```cpp
#include "RobotStateReporter.h"
#include "Platform/BHAssert.h"
#include <fcntl.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <cstring>
#include <errno.h>
#include <sstream>
#include <iomanip>

MAKE_MODULE(RobotStateReporter);

RobotStateReporter::RobotStateReporter()
{
  if (enabled)
    initSocket();
}

RobotStateReporter::~RobotStateReporter()
{
  if (udpSocket >= 0)
    close(udpSocket);
}

void RobotStateReporter::initSocket()
{
  udpSocket = socket(AF_INET, SOCK_DGRAM, 0);
  if (udpSocket < 0)
  {
    OUTPUT_WARNING("RobotStateReporter: Failed to create socket: " << strerror(errno));
    enabled = false;
    return;
  }
  
  // 非阻塞模式（关键！）
  int flags = fcntl(udpSocket, F_GETFL, 0);
  if (flags < 0 || fcntl(udpSocket, F_SETFL, flags | O_NONBLOCK) < 0)
  {
    OUTPUT_WARNING("RobotStateReporter: Failed to set non-blocking mode");
    close(udpSocket);
    udpSocket = -1;
    enabled = false;
    return;
  }
  
  // 发送超时（额外保险）
  struct timeval timeout;
  timeout.tv_sec = 0;
  timeout.tv_usec = 1000;  // 1ms
  setsockopt(udpSocket, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
  
  // 配置目标地址
  memset(&monitorAddr, 0, sizeof(monitorAddr));
  monitorAddr.sin_family = AF_INET;
  monitorAddr.sin_port = htons(monitorPort);
  
  if (inet_pton(AF_INET, monitorAddress.c_str(), &monitorAddr.sin_addr) <= 0)
  {
    OUTPUT_WARNING("RobotStateReporter: Invalid monitor address: " << monitorAddress);
    close(udpSocket);
    udpSocket = -1;
    enabled = false;
    return;
  }
  
  OUTPUT_TEXT("RobotStateReporter: Initialized, sending to " 
              << monitorAddress << ":" << monitorPort);
}

void RobotStateReporter::update()
{
  if (!enabled || udpSocket < 0)
    return;
  
  // 降频：每 N 帧发送一次
  if (theFrameInfo.getFrameNumber() - lastReportFrame < reportIntervalFrames)
    return;
  
  lastReportFrame = theFrameInfo.getFrameNumber();
  
  // 采集状态
  std::string jsonBuffer;
  collectState(jsonBuffer);
  
  // 发送
  sendState(jsonBuffer);
}

void RobotStateReporter::collectState(std::string& jsonBuffer)
{
  std::ostringstream json;
  json << std::fixed << std::setprecision(2);
  
  // 机器人 ID
  std::string robotId = std::to_string(theGameState.ownTeam.number) + "_" + 
                        std::to_string(theGameState.playerNumber);
  
  // 时间戳
  unsigned timestamp = theFrameInfo.time;
  
  // 电量和温度（SimRobot 中是固定值）
#ifdef TARGET_ROBOT
  float battery = theRobotHealth.batteryLevel;
  float temp = theRobotHealth.maxJointTemperatureStatus;
#else
  float battery = 100.0f;
  float temp = 40.0f;
#endif
  
  // 摔倒状态
  bool fallen = (theFallDownState.state != FallDownState::upright);
  
  // 行为
  std::string behavior = TypeRegistry::getEnumName(theBehaviorStatus.activity);
  
  // 球感知
  bool ballVisible = (theFrameInfo.time - theBallModel.timeWhenLastSeen) < 1000;
  float ballX = theBallModel.estimate.position.x();
  float ballY = theBallModel.estimate.position.y();
  
  // 定位
  float posX = theRobotPose.translation.x();
  float posY = theRobotPose.translation.y();
  float rotation = theRobotPose.rotation;
  
  // 运动状态
  std::string motion = TypeRegistry::getEnumName(theMotionInfo.executedPhase);
  
  // 构建 JSON
  json << "{"
       << "\"timestamp\":" << timestamp << ","
       << "\"robot_id\":\"" << robotId << "\","
       << "\"battery\":" << battery << ","
       << "\"temperature\":" << temp << ","
       << "\"fallen\":" << (fallen ? "true" : "false") << ","
       << "\"behavior\":\"" << behavior << "\","
       << "\"motion\":\"" << motion << "\","
       << "\"ball_visible\":" << (ballVisible ? "true" : "false") << ","
       << "\"ball_x\":" << ballX << ","
       << "\"ball_y\":" << ballY << ","
       << "\"pos_x\":" << posX << ","
       << "\"pos_y\":" << posY << ","
       << "\"rotation\":" << rotation;
  
  // 事件检测
  if (detectEvents)
  {
    json << ",\"events\":[";
    bool firstEvent = true;
    
    // 行为切换
    if (!behavior.empty() && behavior != lastBehavior && !lastBehavior.empty())
    {
      if (!firstEvent) json << ",";
      json << "{\"type\":\"behavior_changed\",\"from\":\"" << lastBehavior 
           << "\",\"to\":\"" << behavior << "\"}";
      firstEvent = false;
    }
    lastBehavior = behavior;
    
    // 球丢失/发现
    if (ballVisible != lastBallVisible)
    {
      if (!firstEvent) json << ",";
      json << "{\"type\":\"" << (ballVisible ? "ball_found" : "ball_lost") << "\"}";
      firstEvent = false;
    }
    lastBallVisible = ballVisible;
    
    // 摔倒/起身
    if (fallen != lastFallen)
    {
      if (!firstEvent) json << ",";
      json << "{\"type\":\"" << (fallen ? "fallen" : "got_up") << "\"}";
      firstEvent = false;
    }
    lastFallen = fallen;
    
    json << "]";
  }
  
  json << "}";
  
  jsonBuffer = json.str();
}

void RobotStateReporter::sendState(const std::string& jsonBuffer)
{
  ssize_t sent = sendto(udpSocket, jsonBuffer.c_str(), jsonBuffer.size(), 0,
                        (struct sockaddr*)&monitorAddr, sizeof(monitorAddr));
  
  if (sent < 0)
  {
    // 非阻塞模式下，EAGAIN/EWOULDBLOCK 是正常的
    if (errno != EAGAIN && errno != EWOULDBLOCK)
    {
      sendErrors++;
      // 静默失败，不打印错误
    }
  }
  else
  {
    reportCount++;
  }
}
```

---

## 附录 B: 调试技巧

### B.1 验证模块是否加载

在 SimRobot 控制台中:
```
mr RobotStateReporter
```

应该输出模块参数。

### B.2 查看发送统计

添加 Debug 绘制:
```cpp
void RobotStateReporter::update()
{
  // ...
  
  DEBUG_RESPONSE("module:RobotStateReporter:stats")
  {
    OUTPUT_TEXT("Reports: " << reportCount << ", Errors: " << sendErrors);
  }
}
```

在 SimRobot 中执行:
```
dr module:RobotStateReporter:stats
```

### B.3 抓包验证

```bash
sudo tcpdump -i lo -n udp port 10020 -X
```

应该看到 JSON 数据包。

### B.4 测试 Monitor Daemon

手动发送测试数据:
```bash
echo '{"timestamp":1000,"robot_id":"1_1","behavior":"test"}' | nc -u 127.0.0.1 10020
```

Monitor Daemon 应该接收并显示。

---

## 总结

本指南提供了将监控系统接入 SimRobot 的完整方案：

1. **接入点**: Cognition Thread 的 Infrastructure 模块
2. **数据获取**: 使用 B-Human 标准 Representations
3. **网络发送**: 非阻塞 UDP，静默失败
4. **MVP**: 最小 50 行代码即可运行
5. **迁移**: 代码 95% 复用，配置文件区分 Sim/Real

按照本指南，你可以在 SimRobot 中真正跑起来监控系统，并平滑迁移到真机。
