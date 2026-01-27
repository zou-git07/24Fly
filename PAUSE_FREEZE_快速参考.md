# Pause Freeze 快速参考

## 🎯 一句话总结
Pause 时机器人切换到 FreezePhase，保持当前姿态完全静止，无踏步、无摆动。

## 📝 核心修改（3 个文件，9 行代码）

### 1. MotionEngine.cpp (+3 行)
```cpp
else if(theGameState.paused && phase->type != MotionPhase::freeze && 
        phase->type != MotionPhase::playDead)
  phase = theFreezeGenerator.createPhase();
```

### 2. FreezeEngine.h (+2 行)
```cpp
#include "Representations/Infrastructure/GameState.h"
REQUIRES(GameState),
```

### 3. FreezeEngine.cpp (+4 行)
```cpp
bool FreezePhase::isDone(const MotionRequest&) const
{
  if(engine.theGameState.paused) return false;
  // ... original logic ...
}
```

## 🔄 工作流程
1. Pause → `gameState.paused = true`
2. MotionEngine 检测 → 切换到 FreezePhase
3. FreezePhase 捕获关节角度 → 设置刚度 60
4. isDone() 返回 false → 保持冻结
5. Resume → `paused = false` → isDone() 返回 true → 恢复正常

## ✅ 测试验证
```bash
./test_pause_freeze.sh  # 查看测试指南
```

## 📊 效果对比
- **优化前**：原地踏步、重心摆动 ❌
- **优化后**：完全静止、姿态固定 ✅
