MotionInfo.h:
MotionInfo 是一个极其重要的反馈型数据结构（Representation）。
如果说 MotionRequest 是大脑（行为层）给身体（运动层）下的“命令”，那么 MotionInfo 就是身体给大脑回传的“回执/进度报告”。
在 MotionInfo.h 中，有几个变量是你必须掌握的：
(1) executedPhase (当前相位)
这是最重要的字段。它告诉大脑机器人当前处于哪种运动大类：
stand: 正在站立。
walk: 正在行走。
kick: 正在踢球。
keyframeMotion: 正在执行预定义的“关键帧动作”（守门员的扑救、下跪都在这一类）。
getUp: 正在起身。
fall: 正在摔倒。
(2) executedKeyframeMotion (具体动作详情)
如果 executedPhase 是 keyframeMotion，那么这个变量会进一步说明具体是哪个动作。它包含：
动作 ID：比如是 jumpLeft 还是 keeperStand。
是否镜像：比如向左扑还是向右扑。
(3) isMotionStable (稳定性标志)
这是一个布尔值。它告诉大脑：机器人现在稳吗？
如果是 false，说明机器人正在剧烈运动（如侧扑中）或失去平衡。













这是一个非常深刻的架构问题！理清这两个文件的区别，你就真正搞懂了 B-Human（以及大多数现代机器人控制系统）的分层架构（Layered Architecture）。
用一句话来概括它们的区别：
MotionRequest 是大脑下达的“订单”（What to do），而 MotionPhase 是身体执行动作的“生产线”（How to do）。
我们可以从以下几个维度来严格区分它们属于哪一层：
1. 从所属层级（Layer）区分
MotionRequest.h：属于“跨层通信接口”（Bridge / Representation）
是谁创建的？ 它是被 行为层（Cognition / Behavior） 创建并赋值的。比如你的 HandleGoalkeeperCatchBall 和各种 Skill（如 Dive、Stand）都在向它里面写数据。
是谁读取的？ 它是被 运动层（Motion） 读取的。
它的本质：它是一个数据结构（Representation）。它就像是行为层递给运动层的一张“任务需求单”。
里面有什么？ 只有纯粹的意图。比如：“我要走路（Walk）”、“我要向左侧扑（jumpLeft）”。它不包含任何关于怎么动腿、怎么保持平衡的物理算法。
MotionPhase.h：属于“纯运动层”（Motion Engine）
是谁创建的？ 它只存在于 运动层（Motion） 的内部。行为层（Cognition）绝对不能、也无法直接操作它。
它的本质：它是一个 C++ 的基类（Base Class），是一个复杂的算法执行器。
里面有什么？ 它包含了物理世界的具体逻辑。还记得里面有个 calcJoints() 函数吗？它的任务是把 MotionRequest 里的那句“我要走路”，翻译成机器人全身 25 个电机在这一毫秒内具体应该转动多少度（JointRequest）。
2. 用一个形象的比喻来区分（老板与工厂）
假设机器人是一个大公司：
行为层（Behavior） 是 老板（大脑）。老板看着球场（视觉），做出了战术决定。
MotionRequest 是老板写的一张 任务派发单。
老板在单子上写：“给我生产一个【向左扑救】的动作！”（theMotionRequest.diveRequest = jumpLeft）。
写完单子，老板就不管了。老板不知道电机怎么转，也不知道怎么算重心。
运动引擎（Motion Engine） 是 工厂厂长。厂长拿到了这张 MotionRequest 任务单。
MotionPhase 是工厂里的 具体流水线。
厂长看到任务单要求“向左扑救”，于是启动了名为 FallPhase 或 KeyframeMotionPhase 的流水线。
这个流水线（MotionPhase）开始轰鸣，每一帧都在精确计算每个齿轮（电机）的转速，直到动作完成。
3. 数据流向闭环（它们是如何协同工作的？）
在代码中，它们的调用顺序构成了一个完美的闭环：
[行为层] 你写的状态机计算出需要拦截，调用 Dive 技能。
[接口层] Dive 技能将意图写入 MotionRequest。
[运动层] 运动总控模块（MotionSelector）读到了 MotionRequest，发现要扑救。
[运动层] 运动总控模块实例化了一个具体的 MotionPhase（比如关键帧相位）。
[运动层] MotionPhase 每 10 毫秒运行一次 calcJoints()，控制硬件让机器人飞出去。
[接口层] MotionPhase 把自己当前的进度写到 MotionInfo 里（“报告老板，我正在执行扑救关键帧”）。
[行为层] 你的代码读取 MotionInfo，确认机器人确实飞出去了，状态机跳转到 recovering。
总结
看文件名带 Request 的（如 MotionRequest, HeadMotionRequest），都是行为层控制意图的输出。
看文件名带 Phase 或 Engine 的（如 MotionPhase, WalkEngine, FallEngine），都是运动层处理物理执行的黑盒。
看文件名带 Info 的（如 MotionInfo），都是运动层给行为层的执行进度回执。
区分开它们，你就能清晰地知道：改战术去 Behavior 里找，改动作姿势去 Motion（或 cfg 文件）里找。


---


# HandleGoalkeeperCatchBall 与 InterceptBall 模块总结


## 一、两个模块的定位

HandleGoalkeeperCatchBall 和 InterceptBall 是守门员扑救行为中的**上下级关系**：

- **HandleGoalkeeperCatchBall** 是"决策层"——决定守门员**要不要扑球**。
- **InterceptBall** 是"执行层"——决定守门员**用什么方式扑球**。

HandleGoalkeeperCatchBall 在判断"该扑"之后，内部调用 InterceptBall 技能来完成实际的扑救动作。

```
HandleGoalkeeperCatchBall（要不要扑？）
        │
        │ 调用
        ▼
  InterceptBall（怎么扑？站/走/蹲/跳？向左还是向右？）
        │
        │ 调用
        ▼
     Dive 技能（写入 MotionRequest，交给运动层执行）
```


## 二、HandleGoalkeeperCatchBall — 扑球决策状态机

文件位置：Src/Modules/BehaviorControl/SkillBehaviorControl/Options/HandleGoalkeeperCatchBall.cpp

### 功能
判断守门员是否需要启动扑球流程。它是一个三状态的状态机，职责是：
1. 持续监控球的运动状态
2. 在合适时机进入准备阶段
3. 准备完成后将控制权交给 InterceptBall

### 状态机流程

```
 ┌──────────────┐
 │  notCatching  │ ← 初始状态，正常站位防守
 │  （不扑球）    │
 └──────┬───────┘
        │ 满足5个触发条件
        ▼
 ┌────────────────┐
 │ preparingCatch  │ ← 准备阶段，张开手臂（keeperStand）
 │  （准备扑球）    │
 └──────┬─────────┘
        │ 等待 >= 100ms
        ▼
 ┌──────────────┐
 │  doingCatch   │ ← 执行阶段，调用 InterceptBall 技能
 │ （正在扑球）   │
 └──────────────┘
```

### 状态详解

#### 状态1：notCatching（不扑球）

这是初始/默认状态。守门员正常站位防守，每帧检查以下5个条件是否**全部满足**：

```
条件1: theGameState.isGoalkeeper()
       → 确认自己是守门员角色

条件2: between<float>(theFieldInterceptBall.timeUntilIntersectsOwnYAxis, 0.3f, 3.f)
       → 球将在 0.3~3.0 秒内经过自己身前（Y轴）
       → 太快（<0.3s）来不及反应，太慢（>3s）不需要现在扑

条件3: theFieldBall.ballWasSeen(100)
       → 最近 100ms 内看到过球（确保球的位置信息可靠）

条件4: theFieldBall.isRollingTowardsOwnGoal
       → 球正在滚向己方球门（由 FieldBallProvider 通过球轨迹与球门线
          的几何相交检测计算得出）

条件5: theFieldBall.positionRelative.squaredNorm() < sqr(3000.f)
       → 球在 3000mm（3米）以内
```

全部满足时，跳转到 preparingCatch。

#### 状态2：preparingCatch（准备扑球）

进入此状态后，守门员做三件事：
- **LookAtBall()** — 头部追踪球
- **KeyFrameArms(keeperStand)** — 双臂张开，摆出守门姿势
- **Stand()** — 身体站稳不走动

同时持续检查：
- 如果 5 个条件（放宽版）不再满足 → 回到 notCatching（取消扑球）
- 如果在此状态已停留 **>= 100ms** → 跳转到 doingCatch（准备完毕，开始扑）

100ms 的等待是为了让手臂有时间展开到位，给 InterceptBall 一个稳定的起始姿态。

退出条件使用了比进入条件更宽松的阈值（时间窗口扩展为 0.1~4.0s），形成回差，防止在边界上反复进出。

#### 状态3：doingCatch（正在扑球）

这是实际扑救发生的状态。核心逻辑：

```cpp
// 计算是否靠近门柱（靠近门柱时禁止向该侧跳扑，防止撞柱）
const auto [isNearLeftPost, isNearRightPost] = theLibPosition.isNearPost(theRobotPose);

// 基础方法：站立 + 走位
unsigned interceptionMethods = bit(Interception::stand) | bit(Interception::walk);

// 只有在己方禁区内才允许跳扑
if(theLibPosition.isInOwnPenaltyArea(theRobotPose.translation))
{
    if(!isNearLeftPost)
      interceptionMethods |= bit(Interception::jumpLeft);   // 允许左扑
    if(!isNearRightPost)
      interceptionMethods |= bit(Interception::jumpRight);  // 允许右扑
}

// 调用 InterceptBall 技能，传入允许的方法集合
InterceptBall({.interceptionMethods = interceptionMethods,
               .allowDive = theBehaviorParameters.keeperJumpingOn});
```

退出条件：
- `action_done` — InterceptBall 技能执行完毕（扑救动作已完成）
- `!theFieldInterceptBall.interceptBall` — 球已经不可拦截了（飞走了/停了）


## 三、InterceptBall — 扑球执行技能

文件位置：Src/Modules/BehaviorControl/SkillBehaviorControl/Skills/Ball/InterceptBall.cpp

### 功能
根据球的轨迹和到达时间，选择最优的拦截方式并执行对应的运动动作。
它是一个通用技能，不仅守门员使用，防守球员也可以调用。

### 输入参数
```
interceptionMethods — 允许使用的拦截方式（位掩码），由调用者指定
allowGetUp          — 扑完是否允许自动起身
allowDive           — 是否允许真正执行扑救动作（false 时只播放音频模拟）
```

### 核心决策逻辑

InterceptBall 内部有三个关键的 lambda 函数：

#### (1) replaceJumpWithWalk — 跳扑安全阀

```cpp
auto replaceJumpWithWalk = [&](const unsigned interceptionMethods) -> bool
{
  return interceptionMethods & bit(Interception::walk) &&
    theFieldInterceptBall.timeUntilIntersectsOwnYAxis * 1000.f
      < theBehaviorParameters.timeForJump;
};
```

含义：如果球到达时间 < timeForJump（默认500ms），跳扑已经来不及了，强制改用走位拦截。
这是最重要的安全机制——防止守门员在球已经快到了才开始跳，结果扑空且倒地。

#### (2) getWalkRadius — 动态走位半径

```cpp
auto getWalkRadius = [&]() -> float
{
  return mapToRange(
    theFieldInterceptBall.timeUntilIntersectsOwnYAxis,
    theBehaviorParameters.timeForInterceptionForMaxWalkRadius.min,  // 0.3s
    theBehaviorParameters.timeForInterceptionForMaxWalkRadius.max,  // 1.4s
    theBehaviorParameters.walkRadius.min,   // 250mm
    theBehaviorParameters.walkRadius.max);  // 500mm
};
```

含义：球到达时间越长，守门员可以走得越远去拦球，walkRadius 在 250~500mm 之间线性插值。

#### (3) getIntersectionAction — 动作选择（核心）

这是整个 InterceptBall 最核心的函数。它的执行步骤：

**第一步：确定球从左边还是右边过来**
```cpp
float positionIntersectionYAxis = theFieldInterceptBall.intersectionPositionWithOwnYAxis.y();
left = positionIntersectionYAxis > 0.f;  // 正Y = 机器人左侧
```
如果 FieldInterceptBall 没有计算出交点（值为0），会用球速度方向作为备选方案。

**第二步：过滤掉错误方向的跳扑**
```cpp
if(left)
    filteredInterceptionMethods &= ~bit(Interception::jumpRight);  // 球在左，禁止右跳
else
    filteredInterceptionMethods &= ~bit(Interception::jumpLeft);   // 球在右，禁止左跳
```

**第三步：按距离从近到远依次匹配动作**

按优先级从高到低：

| 优先级 | 动作 | 触发条件 | 对应参数 |
|--------|------|----------|----------|
| 1 | stand（站立） | 球偏移 < standRadius (60mm) | standRadius |
| 2 | walk（走位拦截） | 球偏移 < walkRadius (250~500mm) | walkRadius |
| 3 | genuflectStand（下蹲扑救） | 球偏移 < genuflectStandRadius (200mm) | genuflectStandRadius |
| 4 | genuflectStandDefender（宽距下蹲） | 球偏移 < genuflectStandRadius (200mm) | genuflectStandRadius |
| 5 | jumpLeft（左跳扑） | 球偏移 < jumpRadius (600mm) 且时间足够 | jumpRadius, timeForJump |
| 6 | jumpRight（右跳扑） | 球偏移 < jumpRadius (600mm) 且时间足够 | jumpRadius, timeForJump |
| 兜底 | walk（走位） | 以上都不满足 | - |

注意：每个条件中都有一个 `|| filteredInterceptionMethods < (bit(X) << 1)` 的兜底逻辑，
含义是"如果这是允许的方法中优先级最高的那个，不管距离条件是否满足都直接选它"。
这保证了在方法集合受限时不会卡死。

### 状态机流程

```
  ┌──────────────┐
  │ chooseAction  │ ← 初始状态（只存在一帧，立即跳转）
  └──────┬───────┘
         │ 由 common_transition 统一调度
         ▼
  ┌──────────────────────────────────────────────────┐
  │              common_transition（每帧执行）          │
  │                                                    │
  │  调用 getIntersectionAction() 得到最优动作          │
  │  根据结果跳转到对应状态：                            │
  │                                                    │
  │  stand → stand 状态                                │
  │  walk  → walk 状态                                 │
  │  genuflectStand → genuflectStand 状态              │
  │  genuflectStandDefender → genuflectStandDefender   │
  │  jumpLeft/jumpRight → keeperSitJump 状态           │
  │                                                    │
  │  如果 allowDive=false：                             │
  │    genuflect → audioGenuflect（只播放语音）          │
  │    jump → audioJump（只播放语音）                    │
  └──────────────────────────────────────────────────┘
```

### 各执行状态的行为

**stand 状态**：站立不动，持续看球。
退出条件：球不再可见(300ms) 或球到达时间超出 0.1~3.5s 范围。

**walk 状态**：向球经过 Y 轴的交点走位。
```cpp
WalkToPoint({.target = {0.f, 0.f, theFieldInterceptBall.intersectionPositionWithOwnYAxis.y()},
             .reduceWalkSpeedType = ReduceWalkSpeedType::noChange,
             .disableAligning = true});
```
守门员只做横向平移（Y方向），不转身，以最快速度走到拦截点。

**genuflectStand 状态**：下蹲 + 手臂向后张开，覆盖更宽的拦截范围。
根据 left 变量选择 squatArmsBackLeft 或 squatArmsBackRight。
退出条件：执行超过 2 秒且球不再威胁。

**genuflectStandDefender 状态**：宽距下蹲 + 手臂后张（覆盖范围更大）。
逻辑与 genuflectStand 相同，动作为 squatWideArmsBackLeft/Right。

**keeperSitJump 状态**：向左或向右跳扑。
```cpp
Dive({.request = left ? MotionRequest::Dive::jumpLeft : MotionRequest::Dive::jumpRight});
```
这是最剧烈的动作，机器人会侧身扑出。退出条件：执行超过 2 秒后自动起身。

**audioGenuflect / audioJump 状态**：当 allowDive=false 时的替代状态。
不执行真实动作，只播放语音（"Genuflect" / "Jump left" / "Jump right"）并站立。
用于仿真测试或保护机器人。

**targetStand 状态**：终止状态，恢复站立。标记 action_done，控制权返回给调用者。


## 四、两个模块的逻辑关系

### 调用关系

```
SkillBehaviorControl（行为主循环，每帧执行）
  │
  ├── 常规行为处理（站位、找球、踢球等）
  │
  └── HandleGoalkeeperCatchBall（作为 Option 被注册并每帧检查）
        │
        │  notCatching 状态：每帧检查 5 个条件
        │  preparingCatch 状态：张开手臂，等待 100ms
        │  doingCatch 状态：
        │     │
        │     │  确定允许的拦截方法集合（考虑门柱安全）
        │     │  调用 InterceptBall 技能
        │     ▼
        │  InterceptBall（作为 Skill 被调用）
        │     │
        │     │  getIntersectionAction() 选择最优动作
        │     │  进入对应状态（stand/walk/genuflect/jump）
        │     │  调用 Dive/Stand/WalkToPoint 等底层技能
        │     ▼
        │  MotionRequest（写入运动请求）
        │     │
        │     ▼
        │  运动层执行实际动作
        │
        └── MotionInfo（运动层反馈执行状态）
```

### 职责划分

| 维度 | HandleGoalkeeperCatchBall | InterceptBall |
|------|--------------------------|---------------|
| 层级 | Option（行为选项） | Skill（技能） |
| 职责 | 决策：要不要扑球 | 执行：怎么扑球 |
| 输入 | 球状态、比赛状态、角色信息 | 允许的拦截方法、球轨迹数据 |
| 输出 | 调用 InterceptBall 技能 | 调用 Dive/Stand/Walk 等运动技能 |
| 专属性 | 守门员专用 | 通用（守门员和防守球员都可用） |
| 状态数 | 3 个（不扑/准备/执行） | 8 个（选择/站/走/蹲/跳/音频/结束） |

### 数据依赖

两个模块共同依赖以下数据表示（Representation）：

```
FieldBall（球状态）
  ├── isRollingTowardsOwnGoal  → HandleGoalkeeperCatchBall 用于判断是否触发
  ├── ballWasSeen()            → 两者都用于确认球信息可靠性
  └── positionRelative         → HandleGoalkeeperCatchBall 用于距离判断

FieldInterceptBall（拦截计算）
  ├── timeUntilIntersectsOwnYAxis        → 两者都用于时间窗口判断
  ├── intersectionPositionWithOwnYAxis   → InterceptBall 用于确定拦截方向和距离
  └── interceptBall                      → HandleGoalkeeperCatchBall 用于判断是否退出

BehaviorParameters（行为参数，来自 cfg 配置文件）
  ├── keeperJumpingOn       → HandleGoalkeeperCatchBall 传给 InterceptBall 的 allowDive
  ├── standRadius           → InterceptBall 站立拦截范围
  ├── walkRadius            → InterceptBall 走位拦截范围
  ├── genuflectStandRadius  → InterceptBall 下蹲拦截范围
  ├── jumpRadius            → InterceptBall 跳扑拦截范围
  └── timeForJump           → InterceptBall 跳扑时间安全阀

LibPosition（位置工具库）
  ├── isNearPost()            → HandleGoalkeeperCatchBall 用于门柱安全检查
  └── isInOwnPenaltyArea()   → HandleGoalkeeperCatchBall 用于限制跳扑区域
```

### 完整执行时序（一次扑救的生命周期）

```
时间轴 →

T0: 对方射门，球开始滚向己方球门
    FieldBallProvider 计算出 isRollingTowardsOwnGoal = true
    FieldInterceptBallProvider 计算出 timeUntilIntersectsOwnYAxis = 2.5s

T1: HandleGoalkeeperCatchBall 在 notCatching 状态检测到 5 个条件全部满足
    状态跳转 → preparingCatch
    守门员张开双臂（keeperStand），头部追踪球

T2: (T1 + 100ms) preparingCatch 等待时间到
    状态跳转 → doingCatch
    计算允许的拦截方法（检查门柱安全性）
    调用 InterceptBall 技能

T3: InterceptBall 的 getIntersectionAction() 被调用
    计算球经过 Y 轴的位置 = +350mm（左侧）
    left = true，过滤掉 jumpRight
    350mm > standRadius(60) > walkRadius(~400) → 可能匹配 genuflect 或 jump
    假设匹配 jumpLeft → 进入 keeperSitJump 状态

T4: InterceptBall 调用 Dive({.request = jumpLeft})
    Dive 技能写入 MotionRequest
    运动层开始执行左跳扑关键帧动作

T5: 球到达，守门员身体扑到位，球被拦截（或未拦截）

T6: keeperSitJump 状态超过 2000ms
    跳转 → targetStand（action_done = true）
    HandleGoalkeeperCatchBall 检测到 action_done
    跳转 → notCatching
    守门员起身，恢复正常防守站位
```