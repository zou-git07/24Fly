# Pause Freeze 架构说明

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      GameController                          │
│                                                              │
│  [⏸️ PAUSE Button] ──> sends GAME_PHASE_PAUSED (4)         │
│  [▶️ RESUME Button] ──> sends normal game phase             │
└──────────────────────────┬───────────────────────────────────┘
                           │ Network Protocol
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   GameStateProvider                          │
│                                                              │
│  Receives: GAME_PHASE_PAUSED                                │
│  Sets: gameState.paused = true                              │
└──────────────────────────┬───────────────────────────────────┘
                           │ GameState Representation
                           ▼
        ┌──────────────────┴──────────────────┐
        │                                     │
        ▼                                     ▼
┌──────────────────┐              ┌──────────────────────┐
│ Behavior Layer   │              │   Motion Layer       │
│                  │              │                      │
│ SkillBehavior    │              │   MotionEngine       │
│ Control          │              │                      │
└──────────────────┘              └──────────────────────┘
        │                                     │
        │ if(paused) return;                  │
        │ (stops behavior updates)            │
        │                                     │
        │                                     │ if(paused && !freeze)
        │                                     │   phase = FreezePhase
        │                                     │
        │                                     ▼
        │                         ┌──────────────────────┐
        │                         │   FreezePhase        │
        │                         │                      │
        │                         │ - Captures current   │
        │                         │   joint angles       │
        │                         │ - Sets stiffness=60  │
        │                         │ - No gait updates    │
        │                         │ - No balance control │
        │                         │                      │
        │                         │ isDone():            │
        │                         │   if(paused)         │
        │                         │     return false     │
        │                         └──────────────────────┘
        │                                     │
        ▼                                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Robot Hardware                            │
│                                                              │
│  Joints: FROZEN at pause moment angles                      │
│  Stiffness: 60 (medium, holds pose)                         │
│  Motion: NONE (completely still)                            │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 状态转换流程

### Pause 触发流程

```
Normal Operation (WalkPhase/StandPhase)
    │
    │ User clicks PAUSE button
    ▼
GameController sends GAME_PHASE_PAUSED
    │
    ▼
GameStateProvider: paused = true
    │
    ├─────────────────────┬─────────────────────┐
    │                     │                     │
    ▼                     ▼                     ▼
Behavior Layer      Motion Layer          Other Systems
    │                     │                     │
    │ Early return        │ Phase check         │ Continue
    │ (no updates)        │                     │ (unaffected)
    │                     ▼                     │
    │            if(paused && !freeze)          │
    │                     │                     │
    │                     ▼                     │
    │            Create FreezePhase             │
    │                     │                     │
    │                     ▼                     │
    │            Capture joint angles           │
    │            Set stiffness = 60             │
    │                     │                     │
    │                     ▼                     │
    └────────────> FROZEN STATE <───────────────┘
                         │
                         │ Robot completely still
                         │ No stepping, no swaying
                         │
                         ▼
                  (Waiting for Resume...)
```

### Resume 恢复流程

```
FROZEN STATE (FreezePhase active)
    │
    │ User clicks RESUME button
    ▼
GameController sends normal game phase
    │
    ▼
GameStateProvider: paused = false
    │
    ├─────────────────────┬─────────────────────┐
    │                     │                     │
    ▼                     ▼                     ▼
Behavior Layer      Motion Layer          Other Systems
    │                     │                     │
    │ Resume updates      │ FreezePhase check   │ Continue
    │                     │                     │
    │                     ▼                     │
    │            isDone() returns true          │
    │            (paused == false)              │
    │                     │                     │
    │                     ▼                     │
    │            Phase transition               │
    │            (to Stand/Walk)                │
    │                     │                     │
    │                     ▼                     │
    └────────────> NORMAL OPERATION <───────────┘
                         │
                         │ Robot resumes motion
                         │ Stand or Walk phase
                         │
                         ▼
                  (Playing normally)
```

## 🎯 关键决策点

### MotionEngine 中的相位选择逻辑

```cpp
void MotionEngine::update(JointRequest& jointRequest)
{
  // ... existing code ...
  
  // Priority 1: Fall detection (highest priority)
  if(phase->type != MotionPhase::fall && 
     theFallGenerator.shouldCatchFall(motionRequest))
  {
    phase = theFallGenerator.createPhase();
  }
  
  // Priority 2: Body disconnect
  else if(phase->type != MotionPhase::freeze && 
          theFreezeGenerator.shouldHandleBodyDisconnect(*phase))
  {
    phase = theFreezeGenerator.createPhase();
  }
  
  // Priority 3: Game Pause (NEW!)
  else if(theGameState.paused && 
          phase->type != MotionPhase::freeze && 
          phase->type != MotionPhase::playDead)
  {
    phase = theFreezeGenerator.createPhase();
  }
  
  // Priority 4: Normal phase transitions
  else if(phase->isDone(motionRequest))
  {
    // Create new phase based on motion request
  }
  
  // ... rest of update ...
}
```

### FreezePhase 退出条件

```cpp
bool FreezePhase::isDone(const MotionRequest&) const
{
  // Condition 1: If paused, NEVER exit
  if(engine.theGameState.paused)
    return false;  // Stay frozen!
  
  // Condition 2: Body disconnect resolved
  bool bodyReconnected = 
    engine.theMotionRobotHealth.frameLostStatus != 
    MotionRobotHealth::bodyDisconnect;
  
  // Condition 3: Timeout or fall detected
  bool timeoutOrFall = 
    engine.theFrameInfo.getTimeSince(reconnectTime) > 
    engine.freezeTime || startFallMotion;
  
  // Exit only if body reconnected AND (timeout OR fall)
  return bodyReconnected && timeoutOrFall;
}
```

## 📊 相位对比

| 特性 | WalkPhase (旧) | StandPhase (旧) | FreezePhase (新) |
|------|---------------|----------------|-----------------|
| 步态生成 | ✅ 持续运行 | ✅ 零步长 | ❌ 完全停止 |
| 陀螺仪平衡 | ✅ 持续调整 | ✅ 持续调整 | ❌ 不调整 |
| 支撑脚切换 | ✅ 可能发生 | ✅ 可能发生 | ❌ 不切换 |
| 关节更新频率 | 每帧 | 每帧 | 仅初始化时 |
| 刚度值 | 动态 | 动态 | 固定 60 |
| 里程计更新 | ✅ 有 | ✅ 有 | ❌ 无 |
| 视觉效果 | 行走/踏步 | 站立/摆动 | 完全静止 ✅ |

## 🔧 技术细节

### FreezePhase 初始化

```cpp
FreezePhase::FreezePhase(const FreezeEngine& engine) :
  MotionPhase(MotionPhase::freeze),
  engine(engine),
  reconnectTime(engine.theFrameInfo.time),
  startRequest(engine.theJointRequest)  // Capture current angles!
{
  FOREACH_ENUM(Joints::Joint, i)
  {
    // Set medium stiffness to hold pose
    startRequest.stiffnessData.stiffnesses[i] = 60;
    
    // Use current measured angles if not set
    if(startRequest.angles[i] == JointAngles::ignore || 
       startRequest.angles[i] == JointAngles::off)
      startRequest.angles[i] = engine.theJointAngles.angles[i];
  }
}
```

### FreezePhase 关节计算

```cpp
void FreezePhase::calcJoints(const MotionRequest&, 
                             JointRequest& jointRequest, 
                             Pose2f&, 
                             MotionInfo&)
{
  // If falling, reduce stiffness
  if(startFallMotion)
  {
    FOREACH_ENUM(Joints::Joint, i)
      startRequest.stiffnessData.stiffnesses[i] = 30;
  }
  
  // Simply output the captured request
  // No gait updates, no balance corrections!
  jointRequest = startRequest;
}
```

## 🎓 设计优势

1. **最小侵入性**：
   - 复用现有的 FreezePhase 机制
   - 只需添加 3 行核心代码
   - 不影响其他运动相位

2. **清晰的职责分离**：
   - Behavior Layer: 停止决策
   - Motion Layer: 冻结执行
   - 各司其职，互不干扰

3. **优先级明确**：
   - Fall > Body Disconnect > Pause > Normal
   - 安全相关的相位优先级最高

4. **易于测试和调试**：
   - 可以通过 MotionInfo.executedPhase 观察
   - 可以通过 GameState.paused 验证
   - 行为清晰可预测

5. **向后兼容**：
   - 不影响非暂停状态的行为
   - FreezePhase 的原有功能保持不变
   - 可以随时回滚修改
